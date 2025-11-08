from flask import Flask, request, jsonify, session
from flask_cors import CORS
from flask_session import Session
import os
from datetime import datetime, timedelta, date
import re
from dotenv import load_dotenv
from openai import OpenAI
from booking_client import BookingComAPI
from flight_client import BookingComFlightsAPI
from database import db, User, Conversation, Message, TravelSuggestion, Profile
from werkzeug.security import generate_password_hash, check_password_hash
import uuid


import json
import urllib.parse

import google.generativeai as genai

# Load environment variables
load_dotenv(override=True)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-here')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///travel_agent.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_TYPE'] = 'filesystem'
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)


#client = OpenAI(api_key="")
# Initialize extensions
CORS(app, 
     supports_credentials=True,
     origins=["http://localhost:8080", "http://localhost:8081"], # Add your frontend URLs
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
Session(app)
db.init_app(app)

# Helper functions
def create_google_maps_url(place_name: str, destination: str) -> str:
    """Create Google Maps search URL"""
    query = f"{place_name} {destination}"
    # Use urllib.parse.quote_plus for correct URL encoding
    encoded_query = urllib.parse.quote_plus(query) 
    # This is the correct, modern URL format for a map search
    return f"https://www.google.com/maps/search/?api=1&query={encoded_query}"

def get_month_number(month_name: str) -> str:
    """Convert month name to number"""
    months = {
        'january': '01', 'jan': '01',
        'february': '02', 'feb': '02',
        'march': '03', 'mar': '03',
        'april': '04', 'apr': '04',
        'may': '05',
        'june': '06', 'jun': '06',
        'july': '07', 'jul': '07',
        'august': '08', 'aug': '08',
        'september': '09', 'sep': '09', 'sept': '09',
        'october': '10', 'oct': '10',
        'november': '11', 'nov': '11',
        'december': '12', 'dec': '12'
    }
    return months.get(month_name.lower(), '01')

def normalize_date(date_str: str) -> date:
    """Normalize dates to YYYY-MM-DD format and return date object"""
    try:
        # Try to parse YYYY-MM-DD format
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        return date_obj.date()
    except:
        # Fallback to current date + 30 days
        now = datetime.now() + timedelta(days=30)
        return now.date()

def parse_recommendations_with_links(response: str, destination: str) -> str:
    """Add Google Maps links to activities in the response"""
    place_pattern = r'(?:Visit|Dine at|Explore|Try|Experience|Enjoy|Go to|See|Check out|Discover|Browse|Sample|Hike|Trek|Climb|Tour|Take|Do|Participate in|Attend|Join|Relax at|Swim at|Kayak in|Bike through|Walk to|Drive to|Sail on|Surf at|Ski on|Watch|Taste|Drink|Eat at|Have|Book|Reserve|Book a tour|Take a tour|Go on|View|Visit the|Go for|Catch|Watch the|Ride|Take a|Have a|Enjoy the|Admire|Appreciate|See the|Walk around|Stroll through|Wander in)\s+([^-\n.;,]*?)(?:\s*[-:.;,]|$|\n)'
    
    enhanced_response = response
    matches = re.finditer(place_pattern, response, re.IGNORECASE)
    processed_places = set()
    
    for match in matches:
        place_name = match.group(1).strip()
        
        if place_name and len(place_name) > 2 and place_name.lower() not in processed_places:
            place_name = place_name.split(' - ')[0].split(' (')[0].strip()
            
            if len(place_name) > 2:
                processed_places.add(place_name.lower())
                maps_url = create_google_maps_url(place_name, destination)
                original = match.group(0)
                
                if maps_url not in enhanced_response:
                    enhanced = f"{original}\n🗺️ [{place_name}]({maps_url})"
                    enhanced_response = enhanced_response.replace(original, enhanced)
    
    return enhanced_response

def search_hotels(city: str, arrival: str, departure: str, price_max: int):
    """Search for hotels using Booking.com API"""
    print(f"Starting hotel search for {city}...")
    try:
        API_HOST = os.getenv("BOOKING_API_HOST")
        API_KEY = os.getenv("BOOKING_API_KEY")
        
        if not API_HOST or not API_KEY:
            print("Booking API credentials not set")
            return None
        
        params = {
            'CITY_QUERY': city,
            'ARRIVAL_DATE': arrival,
            'DEPARTURE_DATE': departure,
            'PRICE_MAX': price_max
        }

        api_client = BookingComAPI(API_HOST, API_KEY, **params)
        
        # Search destination
        if not api_client.search_destination():
            return None
        
        # Get filters (optional)
        api_client.get_filters()
        
        # Search hotels
        hotel_result = api_client.search_hotels()
        if not hotel_result or not hotel_result.get('data', {}).get('hotels'):
            return None
        
        first_hotel = hotel_result['data']['hotels'][0]
        hotel_id = first_hotel['hotel_id']
        
        result_data = {
            'destination': api_client.DESTINATION,
            'hotel_name': first_hotel.get('property', {}).get('name', 'N/A'),
            'hotel_description': first_hotel.get('accessibilityLabel', 'N/A'),
            'booking_hotel_id': hotel_id,
            'hotel_photo_url': first_hotel.get('property', {}).get('photoUrls', []),
            'rating': first_hotel.get('property', {}).get('reviewScore', 0),
            'room_photo_url': 'N/A',
            'booking_url': f"https://www.booking.com/"
        }
        
        # Extract price
        price_breakdown = first_hotel.get('property', {}).get('priceBreakdown', {}).get('grossPrice', {})
        result_data['price'] = price_breakdown.get('value', 0)
        result_data['currency'] = price_breakdown.get('currency', 'N/A')
        
        # Get room details
        details_result = api_client.get_hotel_details(hotel_id)
        print(details_result.keys())
        if details_result and details_result.get('data'):
            rooms = details_result['data'].get('rooms', {})
            if rooms:
                first_room_id = list(rooms.keys())[0]
                first_room = rooms[first_room_id]
                photos = first_room.get('photos', [])
                result_data['booking_url'] = details_result['data'].get('url')
                for photo in photos:
                    if photo.get('url_max1280'):
                        result_data['room_photo_url'] = photo['url_max1280']
                        break
        
        return result_data
        
    except Exception as e:
        print(f"Error in search_hotels: {e}")
        return None

# Routes

@app.route('/api/auth/signup', methods=['POST'])
def signup():
    """User registration"""
    data = request.json
    email = data.get('email')
    password = data.get('password')
    full_name = data.get('fullName')
    
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    # Check if user exists
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({'error': 'User already exists'}), 400
    
    # Create user
    user = User(
        id=str(uuid.uuid4()),
        email=email,
        password_hash=generate_password_hash(password)
    )
    db.session.add(user)
    
    # Create profile
    profile = Profile(
        user_id=user.id,
        email=email,
        full_name=full_name
    )
    db.session.add(profile)
    
    db.session.commit()
    
    return jsonify({'message': 'User created successfully'}), 201

@app.route('/api/auth/login', methods=['POST'])
def login():
    """User login"""
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    user = User.query.filter_by(email=email).first()
    
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    session['user_id'] = user.id
    
    return jsonify({
        'user': {
            'id': user.id,
            'email': user.email
        }
    })

@app.route('/api/auth/logout', methods=['POST'])
def logout():
    """User logout"""
    session.pop('user_id', None)
    return jsonify({'message': 'Logged out successfully'})

@app.route('/api/auth/user', methods=['GET'])
def get_user():
    """Get current user"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({
        'user': {
            'id': user.id,
            'email': user.email
        }
    })

@app.route('/api/profile', methods=['GET', 'PUT'])
def profile():
    """Get or update user profile"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    profile = Profile.query.filter_by(user_id=user_id).first()
    
    if request.method == 'GET':
        if not profile:
            return jsonify({})
        
        return jsonify({
            'full_name': profile.full_name,
            'email': profile.email,
            'phone': profile.phone,
            'passport_number': profile.passport_number,
            'date_of_birth': profile.date_of_birth.isoformat() if profile.date_of_birth else None,
            'nationality': profile.nationality
        })
    
    elif request.method == 'PUT':
        data = request.json
        
        if not profile:
            profile = Profile(user_id=user_id)
            db.session.add(profile)
        
        profile.full_name = data.get('full_name', profile.full_name)
        profile.email = data.get('email', profile.email)
        profile.phone = data.get('phone', profile.phone)
        profile.passport_number = data.get('passport_number', profile.passport_number)
        
        if data.get('date_of_birth'):
            profile.date_of_birth = datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date()
        
        profile.nationality = data.get('nationality', profile.nationality)
        
        db.session.commit()
        
        return jsonify({'message': 'Profile updated successfully'})

@app.route('/api/conversations', methods=['POST'])
def create_conversation():
    """Create a new conversation"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    conversation = Conversation(user_id=user_id)
    db.session.add(conversation)
    db.session.commit()
    
    return jsonify({
        'id': conversation.id,
        'status': conversation.status
    })

@app.route('/api/debug/get-rome-hotel', methods=['GET'])
def get_rome_hotel():
    """
    DEBUG ROUTE: Fetches a single static hotel for Rome to test the frontend.
    """
    print("--- DEBUG: /api/debug/get-rome-hotel route hit ---")
    try:
        # 1. Define static search parameters
        city = "Rome"
        # Set future dates to ensure API finds results
        arrival_date_obj = datetime.now().date() + timedelta(days=60)
        departure_date_obj = datetime.now().date() + timedelta(days=61)
        arrival_str = arrival_date_obj.isoformat()
        departure_str = departure_date_obj.isoformat()
        budget = 1000

        # 2. Call your existing search_hotels function
        hotel_data = search_hotels(city, arrival_str, departure_str, budget)
        
        if not hotel_data:
            return jsonify({'error': 'Failed to fetch hotel from Booking.com'}), 500

        # 3. Format the data to match the frontend 'Suggestion' interface
        booking_url = f"https://www.booking.com/hotel/xx/{hotel_data['booking_hotel_id']}.html?checkin={arrival_str}&checkout={departure_str}"
        
        # Pick the best available image
        image_url = hotel_data.get('room_photo_url', 'N/A')
        if image_url == 'N/A' and hotel_data.get('hotel_photo_url'):
            image_url = hotel_data['hotel_photo_url'][0]

        suggestion = {
            'id': f"debug-{hotel_data['booking_hotel_id']}",
            'type': 'hotel',
            'title': hotel_data.get('hotel_name'),
            'description': hotel_data.get('hotel_description'),
            'price': hotel_data.get('price'),
            'image_url': image_url,
            'booking_url': booking_url,
            'location': {'address': hotel_data.get('destination')}
        }
        
        return jsonify(suggestion)

    except Exception as e:
        print(f"Error in /api/debug/get-rome-hotel: {e}")
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/travel-chat', methods=['POST'])
def travel_chat():
    """Handle travel chat messages"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    messages = data.get('messages', [])
    conversation_id = data.get('conversationId')
    
    # Get conversation
    conversation = Conversation.query.get(conversation_id)
    if not conversation or conversation.user_id != user_id:
        return jsonify({'error': 'Conversation not found'}), 404
    
    # Get conversation state
    prefs = conversation.preferences or {}
    has_origin = prefs.get('origin')
    has_destination = conversation.destination or prefs.get('destination')
    has_travelers = prefs.get('number_of_travelers')
    has_weather_preference = prefs.get('weather_preference')
    has_activities = prefs.get('activities')
    has_budget = conversation.budget or prefs.get('budget')
    has_budget_allocation = prefs.get('budget_allocation')
    has_arrival_date = prefs.get('arrival_date')
    has_departure_date = prefs.get('departure_date')
    has_dates = has_arrival_date and has_departure_date
    has_flexibility = prefs.get('date_flexibility')
    has_confirmed = prefs.get('confirmed')
    
    # Build system prompt based on conversation stage
    system_prompt = """You are an intelligent, minimal, and structured AI travel assistant.

        Your task is to help the user plan their trip step-by-step. 
        You MUST strictly follow the conversation stages defined below. 
        Do NOT add friendly reactions or commentary. 
        Do NOT repeat any previously confirmed information. 
        Do NOT say things like "Great!", "Okay!", "Sounds good!", or "I'll help you plan it". 
        Each response should only:
        1. Ask the next relevant question.
        2. Contain ONLY the question and optional brief context.
        3. Be maximum 3 sentences long.
        4. End naturally without filler text.

        Always stay concise, factual, and focused.

        CONVERSATION STAGE RULES:"""
    print(has_destination, has_dates)
    if has_destination and has_dates:
        print("Give me hotel? ")
        # Extract budget number for hotel search
        budget_max = 1000
        budget_match = re.search(r'(\d+)', str(has_budget))
        if budget_match:
            budget_max = int(budget_match.group(1))

        arrival_date_obj = normalize_date(str(has_arrival_date))
        departure_date_obj = normalize_date(str(has_departure_date))
        
        hotel_data = search_hotels(has_destination, arrival_date_obj.isoformat(), departure_date_obj.isoformat(), budget_max)
        print(hotel_data)
        if hotel_data:
            booking_url = hotel_data['booking_url']#f"https://www.booking.com/hotel/xx/{hotel_data['booking_hotel_id']}.html?checkin={arrival_date_obj.isoformat()}&checkout={departure_date_obj.isoformat()}"

            # Pick the best available image
            image_url = hotel_data.get('room_photo_url', 'N/A')
            if image_url == 'N/A':
                hotel_photos = hotel_data.get('hotel_photo_url', [])
                if hotel_photos and len(hotel_photos) > 0:
                    image_url = hotel_photos[0]
            
            rating_10_point = hotel_data.get('rating', 0)
            rating_5_point = rating_10_point / 2.0 if rating_10_point > 0 else 0

            # Create and save the new suggestion
            new_suggestion = TravelSuggestion(
                conversation_id=conversation_id,
                type='hotel',
                title=hotel_data.get('hotel_name'),
                description=hotel_data.get('hotel_description'),
                price=hotel_data.get('price'),
                rating=rating_5_point,
                image_url=image_url,
                booking_url=booking_url,
                location={'address': hotel_data.get('destination')}
            )
            db.session.add(new_suggestion)

    if not has_destination:
        system_prompt += """
    STAGE 1: GET DESTINATION
    - Ask where they'd like to travel to — their **destination city or country**
    - If they don't have a specific place in mind, ask about their **preferred weather/climate** (tropical, temperate, cold, dry, rainy, etc.) and suggest **2–3 destination options**
    - Do NOT ask about origin, activities, or budget yet
    - KEEP YOUR RESPONSE TO MAX 3 SENTENCES"""

    elif not has_origin:
        system_prompt += f"""
    STAGE 2: GET ORIGIN (Destination: {has_destination})
    - Ask where they'll be traveling **from** — their **origin city or country**
    - Explain that this helps plan **flight routes and travel times**
    - Do NOT ask about travelers, activities, dates, or budget yet
    - KEEP YOUR RESPONSE TO MAX 3 SENTENCES"""

    elif not has_travelers:
        system_prompt += f"""
    STAGE 3: GET NUMBER OF TRAVELERS
    - Ask if they're traveling **solo** or with others
    - Ask for the **total number of travelers** (including them)
    - Explain this helps plan accommodations and group activities
    - Do NOT ask about activities, dates, or budget yet
    - KEEP YOUR RESPONSE TO MAX 3 SENTENCES"""

    elif not has_activities:
        system_prompt += f"""
    STAGE 4: GET ACTIVITY PREFERENCES
    - Ask what type of **activities** they're interested in:
    * Relaxing (beach, spa, cultural tours, museums)
    * Adventurous (hiking, water sports, nightlife)
    * A **mix of both**
    - Do NOT ask about budget or dates yet
    - KEEP YOUR RESPONSE TO MAX 3 SENTENCES"""

    elif not has_budget:
        system_prompt += f"""
    STAGE 5: GET BUDGET
    - Ask for their **total trip budget**
    - Then ask roughly how they'd like to **allocate it**:
    * Accommodation
    * Flights
    * Activities
    - Do NOT provide recommendations yet
    - KEEP YOUR RESPONSE TO MAX 3 SENTENCES"""

    elif not has_budget_allocation:
        system_prompt += f"""
    STAGE 6: ALLOCATE BUDGET
    - Confirm they have a total budget of **{has_budget}**
    - Ask them to divide it across:
    * **Accommodation**
    * **Flights**
    * **Activities**
    - Ensure the total equals 100%
    - KEEP YOUR RESPONSE TO MAX 3 SENTENCES"""

    elif not has_dates:
        system_prompt += f"""
    STAGE 7: GET DATES
    - Ask for their **check-in** and **check-out** dates
    - Ask if the dates are **flexible** or fixed
    - Explain that flexibility may help find **better prices**
    - KEEP YOUR RESPONSE TO MAX 3 SENTENCES"""

    elif not has_flexibility:
        system_prompt += f"""
    STAGE 8: DATE FLEXIBILITY
    - Ask if their travel dates are **strictly fixed** or if they can shift by **±3–7 days**
    - Mention this will affect **flight and hotel availability**
    - KEEP YOUR RESPONSE TO MAX 3 SENTENCES"""

    elif not has_confirmed:
        system_prompt += f"""
    STAGE 9: CONFIRMATION — REVIEW ALL DETAILS
    Show all collected data clearly and ask for confirmation:

    "Let me confirm your trip details:
    ✈️ **Destination:** {has_destination}
    🌍 **Origin:** {has_origin}
    👥 **Number of Travelers:** {has_travelers}
    🌤️ **Weather Preference:** {has_weather_preference}
    🎯 **Activities:** {has_activities}
    💰 **Budget:** {has_budget}
    📊 **Budget Allocation:** {has_budget_allocation}
    📅 **Check-in:** {has_arrival_date}
    📅 **Check-out:** {has_departure_date}
    🔄 **Flexibility:** {has_flexibility}

    Is this correct? Reply **'yes'** to proceed with recommendations, or tell me what to change."

    - Do NOT provide any recommendations yet
    - KEEP YOUR RESPONSE CONCISE — just show the details and ask for confirmation"""
    
    else:
        # All data collected and confirmed - provide recommendations
        arrival_date_obj = normalize_date(str(has_arrival_date))
        departure_date_obj = normalize_date(str(has_departure_date))
        
        # Extract budget number for hotel search
        budget_max = 1000
        budget_match = re.search(r'(\d+)', str(has_budget))
        if budget_match:
            budget_max = int(budget_match.group(1))
        
        # Calculate hotel budget based on allocation
        if has_budget_allocation and isinstance(has_budget_allocation, dict):
            accommodation_percent = has_budget_allocation.get('accommodation', 40) / 100
            budget_max = int(budget_max * accommodation_percent)
        
        system_prompt += f"""
STAGE 10: PROVIDE RECOMMENDATIONS
Current Trip Details:
- Origin: {has_origin}
- Destination: {has_destination}
- Number of Travelers: {has_travelers}
- Weather Preference: {has_weather_preference}
- Activities: {has_activities}
- Total Budget: {has_budget}
- Budget Allocation: {has_budget_allocation}
- Check-in: {has_arrival_date}
- Check-out: {has_departure_date}
- Flexibility: {has_flexibility}
"""
        
        # # Search hotels
        # hotel_data = search_hotels(has_destination, arrival_date_obj.isoformat(), departure_date_obj.isoformat(), budget_max)
        # print(hotel_data)
        # if hotel_data:
        #     booking_url = f"https://www.booking.com/hotel/xx/{hotel_data['booking_hotel_id']}.html?checkin={arrival_date_obj.isoformat()}&checkout={departure_date_obj.isoformat()}"

        #     # Pick the best available image
        #     image_url = hotel_data.get('room_photo_url', 'N/A')
        #     if image_url == 'N/A':
        #         hotel_photos = hotel_data.get('hotel_photo_url', [])
        #         if hotel_photos and len(hotel_photos) > 0:
        #             image_url = hotel_photos[0]
            
        #     rating_10_point = hotel_data.get('rating', 0)
        #     rating_5_point = rating_10_point / 2.0 if rating_10_point > 0 else 0

        #     # Create and save the new suggestion
        #     new_suggestion = TravelSuggestion(
        #         conversation_id=conversation_id,
        #         type='hotel',
        #         title=hotel_data.get('hotel_name'),
        #         description=hotel_data.get('hotel_description'),
        #         price=hotel_data.get('price'),
        #         rating=rating_5_point,
        #         image_url=image_url,
        #         booking_url=booking_url,
        #         location={'address': hotel_data.get('destination')}
        #     )
        #     db.session.add(new_suggestion)

            # The system prompt logic stays the same
        system_prompt += f"""

🏨 **REAL HOTEL FROM BOOKING.COM:**

You MUST include this exact hotel recommendation in your response:

**{hotel_data['hotel_name']}**
📍 Location: {hotel_data['destination']}
💰 Price: {hotel_data['currency']} {hotel_data['price']:.2f} for the entire stay
📝 {hotel_data['hotel_description']}
🔗 Book now: {booking_url}

HOTEL INSTRUCTIONS:
1. Start by saying you found a hotel on Booking.com
2. Copy the hotel details EXACTLY as shown above
3. Include the booking link
4. Keep this section SHORT
"""
        
        system_prompt += f"""

ACTIVITY RECOMMENDATIONS INSTRUCTIONS:

1. **ONLY ACTIVITIES** - Hotels are already provided above, do NOT recommend additional hotels

2. **FORMAT FOR EACH ACTIVITY:**
   - Use action verbs (Visit, Explore, Dine at, Try, Experience, etc.)
   - ONE sentence description maximum
   - The activity name will automatically get a Google Maps link added
   - Keep it minimal

3. **EXAMPLE FORMAT:**
   Day 1:
   - Visit Louvre Museum - Home to the Mona Lisa and 35,000 artworks
   
   - Dine at Le Comptoir du Relais - Classic French bistro in Saint-Germain
   
   - Explore Eiffel Tower - Iconic landmark with stunning city views

4. **REQUIREMENTS:**
   - Create day-by-day itinerary based on their stay duration
   - Match their activity preference ({has_activities})
   - Include 2-4 activities per day
   - Include breakfast/lunch/dinner spots
   - Add cultural sites, attractions, and experiences
   - Each activity = action verb + name + one sentence description
   - Google Maps links will be added automatically

5. **STAY CONCISE:**
   - No long descriptions or explanations
   - Just: Activity description in one sentence
   - The system will add interactive map links

6. **DO NOT INCLUDE:**
   - Additional hotel recommendations
   - Flight details  
   - Transportation logistics
   - Lengthy background information

Remember: Keep it short and actionable. Focus on what they can DO and SEE!"""
    
    system_prompt += """

GENERAL RULES:
- Be conversational, friendly, and helpful
- Ask ONE main question at a time
- Listen carefully to what the user says and extract information
- If they mention multiple pieces of info, extract ALL of them
- Never skip stages unless user provides info for future stages
- Be concise - keep responses under 150 words for stage transitions
- Once all data is collected, provide hotel + activity recommendations

CRITICAL - INFORMATION EXTRACTION:
After each user response, you MUST extract structured data and return it at the END of your message.
Format: |||EXTRACT|||{json}|||END|||

Extract these fields when mentioned:
{
  "origin": "string | null",
  "destination": "string | null",
  "number_of_travelers": "number | null",
  "weather_preference": "tropical | temperate | cold | dry | null",
  "activities": "passive | active | mixed | null",
  "budget": "string | null",
  "budget_allocation": {"accommodation": number, "flights": number, "activities": number} | null,
  "arrival_date": "string | null (format: YYYY-MM-DD)",
  "departure_date": "string | null (format: YYYY-MM-DD)",
  "date_flexibility": "flexible | strict | somewhat | null",
  "confirmed": boolean | null
}

EXTRACTION EXAMPLES:

User: "I'm traveling from New York to Paris in June with $3000"
Your extraction: |||EXTRACT|||{"origin": "New York", "destination": "Paris", "arrival_date": "2025-06-01", "departure_date": "2025-06-07", "budget": "3000"}|||END|||

User: "I want tropical weather and beach activities"
Your extraction: |||EXTRACT|||{"weather_preference": "tropical", "activities": "passive"}|||END|||

User: "It's just me traveling solo"
Your extraction: |||EXTRACT|||{"number_of_travelers": 1}|||END|||

User: "There will be 4 of us"
Your extraction: |||EXTRACT|||{"number_of_travelers": 4}|||END|||

User: "50% hotels, 30% flights, 20% activities"
Your extraction: |||EXTRACT|||{"budget_allocation": {"accommodation": 50, "flights": 30, "activities": 20}}|||END|||

User: "Check in April 11, check out April 12"
Your extraction: |||EXTRACT|||{"arrival_date": "2025-04-11", "departure_date": "2025-04-12"}|||END|||

User: "Yes, that's all correct"
Your extraction: |||EXTRACT|||{"confirmed": true}|||END|||

IMPORTANT PARSING RULES:
- When user gives dates like "11 april 12 april", parse as arrival_date and departure_date
- For month names, convert to YYYY-MM-DD format (assume current year 2025)
- If user provides two dates, first is arrival, second is departure
- Extract budget as string (keep currency symbols if present)
- Parse number of travelers from phrases like "solo", "just me", "2 people", "4 of us", etc.
- Always include the extraction block: |||EXTRACT|||{}|||END|||"""

    # Call Gemini API
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        system_instruction=system_prompt
    )

    generation_config = genai.GenerationConfig(
        temperature=0.7,
        max_output_tokens=1200
    )

    gemini_messages = []
    for msg in messages:
        role = "model" if msg["role"] == "assistant" else msg["role"]
        gemini_messages.append({
            "role": role,
            "parts": [msg["content"]]
        })

    ai_response = "I'm here to help you plan your trip! Let's get started."
    try:
        response = model.generate_content(
            gemini_messages,
            generation_config=generation_config
        )
        print("brrrr")
        ai_response = response.text
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        
    # Extract structured data
    extract_match = re.search(r'\|\|\|EXTRACT\|\|\|(.*?)\|\|\|END\|\|\|', ai_response, re.DOTALL)
    extracted_data = {}

    if extract_match:
        json_string = extract_match.group(1).strip()
        
        # Remove markdown code fences if present
        if json_string.startswith("```json"):
            json_string = json_string[7:]
        if json_string.endswith("```"):
            json_string = json_string[:-3]
        json_string = json_string.strip()
        
        try:
            extracted_data = json.loads(json_string)
            # Remove extraction block from user-facing response
            ai_response = re.sub(r'\|\|\|EXTRACT\|\|\|.*?\|\|\|END\|\|\|', '', ai_response, flags=re.DOTALL).strip()
        except Exception as e:
            print(f"Error parsing extracted JSON: {e}")
    
    # Add Google Maps links if we're at recommendation stage
    if has_confirmed and has_destination:
        ai_response = parse_recommendations_with_links(ai_response, has_destination)
    
    # Update conversation with extracted data
    if extracted_data.get('origin'):
        prefs['origin'] = extracted_data['origin']
    
    if extracted_data.get('destination'):
        conversation.destination = extracted_data['destination']
        prefs['destination'] = extracted_data['destination']
    
    if extracted_data.get('number_of_travelers'):
        prefs['number_of_travelers'] = extracted_data['number_of_travelers']
    
    if extracted_data.get('weather_preference'):
        prefs['weather_preference'] = extracted_data['weather_preference']
    
    if extracted_data.get('activities'):
        prefs['activities'] = extracted_data['activities']
    
    if extracted_data.get('budget'):
        conversation.budget = extracted_data['budget']
        prefs['budget'] = extracted_data['budget']
    
    if extracted_data.get('budget_allocation'):
        prefs['budget_allocation'] = extracted_data['budget_allocation']
    
    if extracted_data.get('arrival_date'):
        prefs['arrival_date'] = extracted_data['arrival_date']
        conversation.start_date = normalize_date(extracted_data['arrival_date'])
    
    if extracted_data.get('departure_date'):
        prefs['departure_date'] = extracted_data['departure_date']
    
    if extracted_data.get('date_flexibility'):
        prefs['date_flexibility'] = extracted_data['date_flexibility']
    
    if extracted_data.get('confirmed'):
        prefs['confirmed'] = extracted_data['confirmed']
    
    conversation.preferences = prefs
    conversation.updated_at = datetime.utcnow()
    
    # Save messages
    user_message = Message(
        conversation_id=conversation_id,
        role='user',
        content=messages[-1]['content']
    )
    db.session.add(user_message)
    
    assistant_message = Message(
        conversation_id=conversation_id,
        role='assistant',
        content=ai_response
    )
    db.session.add(assistant_message)
    
    db.session.commit()
    
    return jsonify({'response': ai_response})

@app.route('/api/suggestions/<conversation_id>', methods=['GET'])
def get_suggestions(conversation_id):
    """Get travel suggestions for a conversation"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    conversation = db.session.get(Conversation, conversation_id)
    if not conversation or conversation.user_id != user_id:
        return jsonify({'error': 'Conversation not found'}), 404
    
    suggestions = TravelSuggestion.query.filter_by(conversation_id=conversation_id).all()
    
    return jsonify({
        'suggestions': [{
            'id': s.id,
            'type': s.type,
            'title': s.title,
            'description': s.description,
            'price': float(s.price) if s.price else None,
            'rating': float(s.rating) if s.rating else None,
            'image_url': s.image_url,
            'booking_url': s.booking_url,
            'location': s.location
        } for s in suggestions]
    })

# Initialize database
with app.app_context():
    db.create_all()

if __name__ == '__main__':
    app.run(debug=True, port=5001)