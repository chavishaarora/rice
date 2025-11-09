import google.generativeai as genai
from google.generativeai import types
import os
import json
from database import db, Conversation, Message, TravelSuggestion, Profile
from agents.booking_agent import search_hotels
from agents.flight_agent import search_flights
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

        # Define the tools the LLM can use
        self.tools = [
            types.Tool(
                function_declarations=[
                    # Tool for searching hotels
                    types.FunctionDeclaration(
                        name="search_hotels",
                        description="Searches for hotels in a specific city, for a given date range and budget.",
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
        # The prompt is now much simpler! It just needs to guide the LLM.
        # We can pass current preferences as context.
        return f"""You are an intelligent and friendly AI travel assistant.
        Your goal is to help the user plan their trip.
        First, you MUST gather all the necessary information:
        1. Destination
        2. Origin
        3. Travel Dates (Arrival and Departure)
        4. Number of Travelers (Adults)
        5. Total Budget
        6. Activity Preferences

        Do NOT call any tools until you have all the required information.
        Ask one question at a time. Be concise and helpful.
        
        Current user preferences (that we know so far):
        {json.dumps(self.prefs, indent=2)}
        
        Once you have all information, you can use your tools to find hotels, flights, and activities.
        When you get tool results, present them to the user in a clean, readable format.
        """
    def process_message(self, user_message_content: str):
        # 1. Save user message
        db.session.add(Message(conversation_id=self.conversation.id, role='user', content=user_message_content))
        # We commit at the end

        # 2. Build chat history
        chat_history = self._get_chat_history()

        # 3. Send to Gemini
        response = self.model.generate_content(chat_history)
        
        # 4. Check if the LLM wants to call one *or more* tools
        try:
            model_response_content = response.candidates[0].content
            # This is the key: get ALL function calls, not just parts[0]
            function_calls = [p.function_call for p in model_response_content.parts if p.function_call]
        except (AttributeError, IndexError, ValueError):
            function_calls = [] # No function calls

        if function_calls:
            # 5. The LLM wants to use one or more tools.
            print(f"Detected {len(function_calls)} tool call(s).")
            
            # This list will hold the *results* we send back
            function_response_parts = []

            # We MUST iterate over all function calls requested
            for function_call in function_calls:

                tool_name = function_call.name
                tool_args = {key: value for key, value in function_call.args.items()}
                
                print(f"Executing Tool: {tool_name} with args: {tool_args}")

                tool_result = None
                if tool_name == "search_hotels":
                    self.prefs['destination'] = tool_args.get('city')
                    
                    tool_result = search_hotels(
                        city=tool_args.get('city'),
                        arrival=tool_args.get('arrival'),
                        departure=tool_args.get('departure'),
                        price_max=int(tool_args.get('price_max', 1000)),
                        ADULTS=int(tool_args.get('adults', 1))
                    )
                    self._save_hotel_suggestion(tool_result)
                elif tool_name == "search_flights":
                    try:
                        tool_result = search_flights(
                            origin_city=tool_args.get('origin_city'),
                            destination_city=tool_args.get('destination_city'),
                            departure_date=tool_args.get('departure_date'),
                            ADULTS=int(tool_args.get('adults', 1))
                        )
                        self._save_flight_suggestion(tool_result)
                    except:
                        tool_result = dict()
                        pass
                    
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
            # The logic continues to step 7 with the new response
        
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

    def _save_hotel_suggestion(self, hotel_data: dict):
        """Saves a hotel tool result to the TravelSuggestion table."""
        if not hotel_data or hotel_data.get('error'):
            print("Hotel search returned no data or an error. Not saving.")
            return
        
        try:
            # Replicate logic from your original app.py
            rating_10_point = hotel_data.get('rating', 0)
            rating_5_point = rating_10_point / 2.0 if rating_10_point > 0 else 0

            image_url = hotel_data.get('room_photo_url', 'N/A')
            if image_url == 'N/A' or not image_url:
                hotel_photos = hotel_data.get('hotel_photo_url', [])
                if hotel_photos and len(hotel_photos) > 0:
                    image_url = hotel_photos[0]

            suggestion = TravelSuggestion(
                conversation_id=self.conversation.id,
                type='hotel',
                title=hotel_data.get('hotel_name'),
                description=hotel_data.get('hotel_description'),
                price=hotel_data.get('price'),
                rating=rating_5_point,
                image_url=image_url,
                booking_url=hotel_data.get('booking_url'),
                location={'address': hotel_data.get('destination')}
            )
            db.session.add(suggestion)
            print(f"Added hotel suggestion to session: {hotel_data.get('hotel_name')}")
        except Exception as e:
            print(f"Error saving hotel suggestion: {e}")
            # Don't halt the chat, just log the error

    # *** NEW HELPER FOR SAVING FLIGHTS ***
    def _save_flight_suggestion(self, flight_data: dict):
        """Saves a flight tool result to the TravelSuggestion table."""
        if not flight_data or flight_data.get('error'):
            print("Flight search returned no data or an error. Not saving.")
            return

        try:
            # Replicate logic from your original app.py
            suggestion = TravelSuggestion(
                conversation_id=self.conversation.id,
                type='flight',
                title=flight_data.get('title'),
                description=flight_data.get('description'),
                price=flight_data.get('price'),
                rating=None, # Flights don't have ratings
                image_url=flight_data.get('image_url'),
                booking_url=flight_data.get('booking_url'),
                location={
                    'origin': flight_data.get('origin_code'), 
                    'destination': flight_data.get('destination_code')
                }
            )
            db.session.add(suggestion)
            print(f"Added flight suggestion to session: {flight_data.get('title')}")
        except Exception as e:
            print(f"Error saving flight suggestion: {e}")