import google.generativeai as genai
from google.generativeai import types
import os
import json
from database import db, Conversation, Message, TravelSuggestion, Profile
from agents.iternerary_manager import ItineraryManager
from agents.booking_agent import search_hotels
from agents.flight_agent import search_flights
from agents.shop_agent import search_shops
from agents.leisure_agent import search_leisure
from agents.utils import normalize_date, parse_recommendations_with_links # (Move your helpers to a utils file)
import re

# Configure Gemini
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

class ChatService:
    def __init__(self, conversation: Conversation):
        self.conversation = conversation
        self.user_id = conversation.user_id
        self.prefs = conversation.preferences or {}
        self.IteneraryManager = ItineraryManager(self.conversation)

        # Define the tools the LLM can use
        self.tools = [
            types.Tool(
                function_declarations=[
                    # Tool for searching hotels
                    types.FunctionDeclaration(
                        name="search_hotels",
                        description="Searches for hotels in a specific city, for a given date range and budget. Returns top 3 best value hotels.",
                        parameters={
                            "type": "OBJECT",
                            "properties": {
                                "city": {"type": "STRING", "description": "The destination city, e.g., 'Paris'"},
                                "arrival": {"type": "STRING", "description": "Check-in date (YYYY-MM-DD)"},
                                "departure": {"type": "STRING", "description": "Check-out date (YYYY-MM-DD)"},
                                "price_max": {"type": "NUMBER", "description": "The maximum price for the stay"},
                                "adults": {"type": "NUMBER", "description": "Number of adults"}
                            },
                            "required": ["city", "arrival", "departure", "price_max", "adults"]
                        }
                    ),
                    # Tool for searching flights
                    types.FunctionDeclaration(
                        name="search_flights",
                        description="Searches for flights from an origin to a destination on a specific date.",
                        parameters={
                            "type": "OBJECT",
                            "properties": {
                                "origin_city": {"type": "STRING", "description": "The departure city, e.g., 'New York'"},
                                "destination_city": {"type": "STRING", "description": "The arrival city, e.g., 'London'"},
                                "departure_date": {"type": "STRING", "description": "The departure date (YYYY-MM-DD)"},
                                "adults": {"type": "NUMBER", "description": "Number of adults"}
                            },
                            "required": ["origin_city", "destination_city", "departure_date", "adults"]
                        }
                    ),
                    # Tool for getting general recommendations (no API call)
                    types.FunctionDeclaration(
                        name="get_activity_recommendations",
                        description="Provides a list of activities and restaurant recommendations for a destination.",
                        parameters={
                            "type": "OBJECT",
                            "properties": {
                                "destination": {"type": "STRING", "description": "The city for recommendations, e.g., 'Rome'"},
                                "activities": {"type": "STRING", "description": "Activity preference (e.g., 'relaxing', 'adventurous', 'mixed')"}
                            },
                            "required": ["destination", "activities"]
                        }
                    ),
                    types.FunctionDeclaration(
                        name="search_shops",
                        description="Searches for shops, supermarkets, or points of interest near a location.",
                        parameters={
                            "type": "OBJECT",
                            "properties": {
                                "city": {"type": "STRING", "description": "The city to search in, e.g., 'Amsterdam'"},
                                "categories": {"type": "STRING", "description": "'commercial.supermarket'"},
                            },
                            "required": ["city", "categories"]
                        }
                    ),
                    types.FunctionDeclaration(
                        name="search_leisure",
                        description="Searches for shops, supermarkets, or points of interest near a location.",
                        parameters={
                            "type": "OBJECT",
                            "properties": {
                                "city": {"type": "STRING", "description": "The city to search in, e.g., 'Amsterdam'"},
                                "categories": {"type": "STRING", "description": "'leisure'"},
                            },
                            "required": ["city", "categories"]
                        }
                    )
                ]
            )
        ]

        # Create the model with tools
        self.model = genai.GenerativeModel(
            model_name="gemini-2.5-flash-lite",
            system_instruction=self.get_system_prompt(),
            tools=self.tools,
        )

    def get_system_prompt(self):
        # UPGRADED SYSTEM PROMPT: Dynamic, Multi-Stage Guidance
        current_itinerary_str = json.dumps(self.IteneraryManager.to_dict(), indent=2)

        return f"""You are an intelligent and friendly AI travel assistant.
        Your goal is to help the user plan their trip efficiently.
        First, you MUST gather all necessary information before searching for flights, hotels, or activities. Ask one question at a time, each concise and under 3 sentences. Avoid commentary, JSON texts, or unnecessary words.
        Do NOT repeat, summarize, or comment on previously provided information. Only ask for the next missing piece of information. 

        Your goal B is to collect the **CRITICAL 6** planning variables:
        1. Destination: Ask for a specific city or region. If the user mentions a climate or general preference instead of a place, suggest suitable destinations based on that climate.
        2. Origin: Ask where the trip will start.
        3. Travel Dates: Ask for Arrival and Departure dates. If the year is missing, ask specifically for it. If exact dates are not known, ask for the duration of the trip in days.
        4. Number of Travelers: Ask for the number of adults traveling.
        5. Total Budget: Ask for the overall budget for the trip.
        6. Activity Preferences: Ask what type of activities or experiences the user prefers.

        ---
        ## 🗺️ Mode 1: PLANNING & EXPLORATION (Initial Phase)

        You are an powerful AI travel assistant. However, users are often not really good in knowing what they exactly want
        Help them plan! Suggest activities, iteneraries, etc. Plan the epic holiday for the user.

        Your goal B is to collect the **CRITICAL 6** planning variables:
        1. **Destination**
        2. **Origin**
        3. **Travel Dates** (Arrival/Departure YYYY-MM-DD) (with no year provided, this is ALWAYS after the current date)
        4. **Number of Travelers** (Adults)
        5. **Total Budget** (or budget for flights/hotels)
        6. **Activity Preferences** (e.g., 'relaxing', 'culture', 'mixed')

        Now, goal A is exploratory. First propose some holidays to the user. Ask the user what kind of wheather is desired. What kind of holiday is preferred. Suggest locations based on this.
        
        * **Exploratory Rule:** If the user is vague (e.g., "I want a trip to Europe"), be very helpful. You are an powerful travel AI. Help the user finding its destination. For instance, show an iternerary! First focus on general vibe: weather, climate, activities. Narrow it down.
        * **Immediate Utility Rule:** You MUST call `search_shops` (categories='commercial.supermarket') and `search_leisure` (categories='leisure') as soon as you have a **Destination** to pre-load useful local information into the ITINERARY.
        ---
        ## ✈️ Mode 2: BOOKING & EXECUTION (When CRITICAL 6 are met)

        Once you have the CRITICAL 6, you MUST proceed directly to booking, **checking the ITINERARY first** to avoid duplicates:
        1.  **Outbound Flight**: Search from Origin to Destination using the Arrival Date.
        2.  **Inbound Flight**: Search from Destination to Origin using the Departure Date.
        3.  **Hotels**: Search for the top 3 hotels using the City, Date range, Budget, and Adults.
        4.  **Final Recommendation**: Summarize the itinerary and ask the user for confirmation.

        Now, goal A is exploratory. First propose some holidays to the user. Ask the user what kind of wheather is desired. What kind of holiday is preferred. Suggest locations based on this.
        
        * **Exploratory Rule:** If the user is vague (e.g., "I want a trip to Europe"), be very helpful. You are an powerful travel AI. Help the user finding its destination. For instance, show an iternerary! First focus on general vibe: weather, climate, activities. Narrow it down.
        * **Immediate Utility Rule:** You MUST call `search_shops` (categories='commercial.supermarket') and `search_leisure` (categories='leisure') as soon as you have a **Destination** to pre-load useful local information into the ITINERARY.
        
        Once you have the CRITICAL 6, you MUST proceed directly to booking, **checking the ITINERARY first** to avoid duplicates:
        1.  **Outbound Flight**: To find the **outbound** flight, you MUST call `search_flights` using the user's **Origin** as the `origin_city` and their **Destination** as the `destination_city`. The `departure_date` for this flight is the user's **Arrival Date**.
        2.  **Inbound Flight**: To find the **inbound** (return) flight, you MUST call `search_flights` a second time, but swap the cities: use the user's **Destination** as the `origin_city` and their **Origin** as the `destination_city`. The `departure_date` for this flight is the user's **Departure Date**.
        3.  **Hotels**: Search for the top 3 hotels using the City, Date range, Budget, and Adults.
        4.  **Final Recommendation**: Summarize the itinerary and ask the user for confirmation.

        **Critical Rules**:
        - If an item is already in the ITINERARY (see above), do NOT call a tool to find it again unless the user explicitly asks..
        - Ask each question clearly, sequentially, avoiding repetition of previously gathered info.
        - Always clarify missing years or exact dates, and suggest destinations if only climate is given.
        """
        
        
    def process_message(self, user_message_content: str):
        # Save user message
        db.session.add(Message(conversation_id=self.conversation.id, role='user', content=user_message_content))
        # We commit at the end
        chat_history = self._get_chat_history()
        # Send to Gemini
        response = self.model.generate_content(chat_history)
        tool_result = search_leisure(
            city='amsterdam',
            categories='leisure'
        )
        self.IteneraryManager._save_leisure_to_db(tool_result)

        print(tool_result)

        # Check if the LLM wants to call one *or more* tools
        try:
            model_response_content = response.candidates[0].content
            # This is the key: get ALL function calls, not just parts[0]
            function_calls = [p.function_call for p in model_response_content.parts if p.function_call]
        except (AttributeError, IndexError, ValueError):
            function_calls = [] # No function calls

        if function_calls:
            print(f"Detected {len(function_calls)} tool call(s).")
            
            # This list will hold the *results* we send back
            function_response_parts = []
            # We MUST iterate over all function calls requested
            for function_call in function_calls:
                tool_name = function_call.name
                tool_args = {key: value for key, value in function_call.args.items()}
                
                print(f"Executing Tool: {tool_name} with args: {tool_args}")

                if tool_name == "search_hotels":
                    # Update destination preference immediately
                    self.prefs['destination'] = tool_args.get('city') 
                    
                    tool_result = search_hotels(
                        city=tool_args.get('city'),
                        arrival=tool_args.get('arrival'),
                        departure=tool_args.get('departure'),
                        price_max=int(tool_args.get('price_max', 1000)),
                        adults=int(tool_args.get('adults', 1))
                    )
                    
                    if tool_result:
                        # Ensures result is a list for uniform processing, even if one hotel is returned
                        hotels_list = tool_result if isinstance(tool_result, list) else [tool_result]
                        for hotel in hotels_list:
                            # Use the correct manager instance name
                            self.IteneraryManager._save_hotel_to_db(hotel) 
                        print(f"✅ Saved {len(hotels_list)} hotels to database")
                        tool_result = hotels_list # Pass the list back to the LLM
                    else:
                        tool_result = {"status": "error", "message": "No hotels found matching criteria."}


                elif tool_name == "search_flights":
                    try:
                        tool_result = search_flights(
                            origin_city=tool_args.get('origin_city'),
                            destination_city=tool_args.get('destination_city'),
                            departure_date=tool_args.get('departure_date'),
                            ADULTS=int(tool_args.get('adults', 1))
                        )
                        if tool_result:
                            self.IteneraryManager._save_flight_to_db(tool_result)
                            print(f"✅ Saved flight to database")
                    except Exception as e:
                        print(f"❌ Error searching flights: {e}")
                        tool_result = {"error": str(e)}
                    
                elif tool_name == "get_activity_recommendations":
                    itinerary_text = self._get_activity_itinerary(
                        tool_args.get('destination'), 
                        tool_args.get('activities')
                    )
                    
                    db.session.add(Message(conversation_id=self.conversation.id, role='assistant', content=itinerary_text))
                    
                    tool_result = {
                        "status": "success", 
                        "message": f"Activity itinerary for {tool_args.get('destination')} was generated and sent to the user."
                    }

                elif tool_name == "search_shops":
                    tool_result = search_shops(
                        city=tool_args.get('city'),
                        categories=tool_args.get('categories')
                    )
                    self.IteneraryManager._save_shop_to_db(tool_result)

                    print(tool_result)
                
                elif tool_name == "search_leisure":
                    tool_result = search_leisure(
                        city=tool_args.get('city'),
                        categories=tool_args.get('categories')
                    )
                    self.IteneraryManager._save_leisure_to_db(tool_result)

                    print(tool_result)


                function_response_parts.append(
                    types.PartDict(
                        function_response=types.ContentDict(
                            name=tool_name,
                            # Send the actual JSON-serializable result
                            response={"result": json.dumps(tool_result)} 
                        )
                    )
                )

            # Now we build the *single* function response message
            function_response_content = types.ContentDict(
                role="function",
                parts=function_response_parts # This list now has N parts
            )
            # Send history, the model's request, and our N results
            response = self.model.generate_content([
                *chat_history,                
                model_response_content,     # The model's tool call request(s)
                function_response_content   # Our N results
            ])
        
        final_response_text = response.candidates[0].content.parts[0].text

        db.session.add(Message(conversation_id=self.conversation.id, role='assistant', content=final_response_text))
        
        # Also update the conversation preferences from any extracted data
        self._update_prefs_from_text(user_message_content) 
        self.conversation.preferences = self.prefs
        
        db.session.commit()
        return final_response_text

    def _get_chat_history(self):
        # Loads messages from DB and formats them for Gemini
        messages = Message.query.filter_by(conversation_id=self.conversation.id).order_by(Message.created_at).all()
        history = []
        for msg in messages:
            role = "model" if msg.role == "assistant" else "user"
            history.append(types.ContentDict(role=role, parts=[types.PartDict(text=msg.content)]))
        return history

    def _get_activity_itinerary(self, destination, activities):
        # A separate, simpler model call just for generating the itinerary
        # This avoids calling the booking APIs again.
        itinerary_model = genai.GenerativeModel(
            model_name="gemini-2.5-flash-lite",
            system_instruction=f"You are a travel expert. Create a day-by-day itinerary for a trip to {destination} with a focus on {activities} activities. Be creative and engaging. Add map links."
        )
        response = itinerary_model.generate_content(f"Give me an itinerary for {destination}.")
        final_text = parse_recommendations_with_links(response.text, destination)
        
        db.session.add(Message(conversation_id=self.conversation.id, role='assistant', content=final_text))
        db.session.commit()
        return final_text
    
    def _update_prefs_from_text(self, text):
        # A simple LLM call or regex to extract entities from the user's
        pass
