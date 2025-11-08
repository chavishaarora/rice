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
    place_pattern = r'(?:Visit|Dine at|Explore|Try|Experience|Enjoy|Go to|See|Check out|Discover)\s+([^-\n.;,]*?)(?:\s*[-:.;,]|$|\n)'
    
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
        
        # Extract hotel data
        result_data = {
            'destination': api_client.DESTINATION,
            'hotel_name': first_hotel.get('property', {}).get('name', 'N/A'),
            'hotel_description': first_hotel.get('accessibilityLabel', 'N/A'),
            'booking_hotel_id': hotel_id,
            'hotel_photo_url': first_hotel.get('property', {}).get('photoUrls', []),
            'room_photo_url': 'N/A'
        }
        
        # Extract price
        price_breakdown = first_hotel.get('property', {}).get('priceBreakdown', {}).get('grossPrice', {})
        result_data['price'] = price_breakdown.get('value', 0)
        result_data['currency'] = price_breakdown.get('currency', 'N/A')
        
        # Get room details
        details_result = api_client.get_hotel_details(hotel_id)
        if details_result and details_result.get('data'):
            rooms = details_result['data'].get('rooms', {})
            if rooms:
                first_room_id = list(rooms.keys())[0]
                first_room = rooms[first_room_id]
                photos = first_room.get('photos', [])
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
    
    user = User.query.get(user_id)
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
    has_destination = conversation.destination or prefs.get('destination')
    has_arrival_date = prefs.get('arrival_date')
    has_departure_date = prefs.get('departure_date')
    has_dates = has_arrival_date and has_departure_date # We need both
    has_budget = conversation.budget or prefs.get('budget')
    
    # Build system prompt
    system_prompt = """You are an intelligent AI travel agent. Your goal is to help users plan their perfect trip by gathering information and providing real hotel recommendations from Booking.com.

CONVERSATION STAGE RULES:
"""
    
    can_search_hotels = has_destination and has_dates and has_budget
    
    if not has_destination:
        system_prompt += """
STAGE 1: GET DESTINATION
- Ask where they want to travel
- Be friendly and conversational
- KEEP YOUR RESPONSE TO MAX 2 SENTENCES"""
    elif not has_dates:
        system_prompt += """
STAGE 2: GET DATES
- Ask for their travel dates (check-in and check-out)
- KEEP YOUR RESPONSE TO MAX 2 SENTENCES"""
    elif not has_budget:
        system_prompt += """
STAGE 3: GET BUDGET
- Ask for their budget for accommodation
- KEEP YOUR RESPONSE TO MAX 2 SENTENCES"""
    elif can_search_hotels:
        arrival_date = prefs.get('arrival_date')
        departure_date = prefs.get('departure_date')
        system_prompt += f"""
STAGE 4: PROVIDE HOTEL RECOMMENDATIONS
Current Trip Details:
- Destination: {has_destination}
- Check-in: {arrival_date}
- Check-out: {departure_date}
- Budget: {has_budget}"""
        
        # Parse dates and search for hotels
        arrival_date_obj = normalize_date(str(has_dates))
        departure_date_obj = normalize_date(str(has_dates))
        
        # Extract budget number
        budget_max = 1000
        budget_match = re.search(r'(\d+)', str(has_budget))
        if budget_match:
            budget_max = int(budget_match.group(1))
        
        # Search hotels
        hotel_data = search_hotels(has_destination, arrival_date_obj.isoformat(), departure_date_obj.isoformat(), budget_max)
        
        if hotel_data:
            booking_url = f"https://www.booking.com/hotel/xx/{hotel_data['booking_hotel_id']}.html?checkin={arrival_date_obj.isoformat()}&checkout={departure_date_obj.isoformat()}"
            system_prompt += f"""

🏨 **REAL HOTEL FROM BOOKING.COM:**

You MUST include this exact hotel recommendation in your response:

**{hotel_data['hotel_name']}**
📍 Location: {hotel_data['destination']}
💰 Price: {hotel_data['currency']} {hotel_data['price']:.2f} for the entire stay
📝 {hotel_data['hotel_description']}
🔗 Book now: {booking_url}

INSTRUCTIONS:
1. Start by saying you found a hotel on Booking.com
2. Copy the hotel details EXACTLY as shown
3. Include the booking link
4. Keep your response SHORT
5. Do NOT suggest other hotels
6. Do NOT make up details"""
    
    system_prompt += """

GENERAL RULES:
- Be conversational, friendly, and helpful
- Ask ONE question at a time
- Extract information from user responses
- Once you have destination, dates, and budget, provide the Booking.com hotel

CRITICAL - INFORMATION EXTRACTION:
After each user response, extract structured data and return it at the END of your message.
Format: |||EXTRACT|||{json}|||END|||

Extract these fields:
{
  "destination": "string | null",
  "arrival_date": "string | null (format: YYYY-MM-DD)",
  "departure_date": "string | null (format: YYYY-MM-DD)",
  "budget": "string | null"
}

- When the user gives dates (e.g., "11 april 12 april"), parse them into "YYYY-MM-DD" format.
- If user provides two dates, fill both arrival_date and departure_date.

ALWAYS include the extraction block: |||EXTRACT|||{}|||END|||"""
    
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",  # Fast and capable model
        system_instruction=system_prompt
    )

    generation_config = genai.GenerationConfig(
        temperature=0.7,
        max_output_tokens=1200
    )

    gemini_messages = []
    for msg in messages:
        # Gemini's 'model' role is equivalent to OpenAI's 'assistant'
        role = "model" if msg["role"] == "assistant" else msg["role"]
        gemini_messages.append({
            "role": role,
            "parts": [msg["content"]]
        })

    ai_response = "Default response"
    try:
        response = model.generate_content(
            gemini_messages,
            generation_config=generation_config
        )
        ai_response = response.text
    except Exception as e:
        print(Exception)
        pass
        
    # 5. Get the text response
    
    # Extract structured data
    extract_match = re.search(r'\|\|\|EXTRACT\|\|\|(.*?)\|\|\|END\|\|\|', ai_response, re.DOTALL)
    extracted_data = {}

    if extract_match:
        json_string = extract_match.group(1).strip()

        # --- FIX: Remove ```json and ``` fences ---
        if json_string.startswith("```json"):
            json_string = json_string[7:]
        if json_string.endswith("```"):
            json_string = json_string[:-3]
        json_string = json_string.strip()
        # --- END FIX ---

        try:
            extracted_data = json.loads(json_string)
            # Now that parsing is successful, clean the ai_response for the user
            ai_response = re.sub(r'\|\|\|EXTRACT\|\|\|.*?\|\|\|END\|\|\|', '', ai_response, flags=re.DOTALL).strip()

        except Exception as e:
            print(f"Error parsing extracted JSON: {e}")
            # If parsing fails, just send the raw response (but log the error)
            pass
        
    # Update conversation
    if extracted_data.get('destination'):
        conversation.destination = extracted_data['destination']
        prefs['destination'] = extracted_data['destination']
    
    if extracted_data.get('arrival_date'):
        arrival_str = extracted_data['arrival_date']
        prefs['arrival_date'] = arrival_str
        
        # --- THIS IS THE FIX FOR YOUR SQL ERROR ---
        # normalize_date converts the string to a DATE object
        conversation.start_date = normalize_date(arrival_str)
    
    if extracted_data.get('departure_date'):
        prefs['departure_date'] = extracted_data['departure_date']
    
    if extracted_data.get('budget'):
        conversation.budget = extracted_data['budget']
        prefs['budget'] = extracted_data['budget']
    
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
    
    conversation = Conversation.query.get(conversation_id)
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
    app.run(debug=True, port=5000)
