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
from agents.itinerary_generator import generate_detailed_itinerary
from agents.utils import normalize_date, parse_recommendations_with_links
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
                        description="Searches for leisure activities near a location.",
                        parameters={
                            "type": "OBJECT",
                            "properties": {
                                "city": {"type": "STRING", "description": "The city to search in, e.g., 'Amsterdam'"},
                                "categories": {"type": "STRING", "description": "'leisure'"},
                            },
                            "required": ["city", "categories"]
                        }
                    ),
                    types.FunctionDeclaration(
                        name="generate_detailed_itinerary",
                        description="Generates a comprehensive day-by-day itinerary for the trip. ONLY call this when: 1) The user has confirmed/selected their flights AND hotels, OR 2) The user explicitly asks for an itinerary/day-by-day plan. Do not call this during initial planning.",
                        parameters={
                            "type": "OBJECT",
                            "properties": {
                                "destination": {"type": "STRING", "description": "The destination city, e.g., 'Paris'"},
                                "arrival_date": {"type": "STRING", "description": "Check-in date (YYYY-MM-DD)"},
                                "departure_date": {"type": "STRING", "description": "Check-out date (YYYY-MM-DD)"},
                                "activity_preferences": {"type": "STRING", "description": "Type of activities: 'relaxing', 'adventurous', 'cultural', 'mixed', etc."}
                            },
                            "required": ["destination", "arrival_date", "departure_date"]
                        }
                    )
                ]
            )
        ]

        # Create the model with tools
        self.model = genai.GenerativeModel(
            model_name="gemini-2.0-flash-exp",
            system_instruction=self.get_system_prompt(),
            tools=self.tools,
        )

    def get_system_prompt(self):
        # UPGRADED SYSTEM PROMPT: Dynamic, Multi-Stage Guidance with Itinerary Generation
        current_itinerary_str = json.dumps(self.IteneraryManager.to_dict(), indent=2)

        
        return f"""You are an intelligent and friendly AI travel assistant.
Your goal is to help the user plan their trip.
First, you MUST gather all the necessary information:
1. Destination
2. Origin
3. Travel Dates (Arrival and Departure)
4. Number of Travelers (Adults)
5. Total Budget
6. Activity Preferences

Do NOT call any booking tools until you have all the required information.
Ask one question at a time. Be concise and helpful.

## Current Itinerary State
{current_itinerary_str}

Note: The search_hotels tool returns the top 3 best value hotels for the destination.

**CRITICAL FLIGHT BOOKING LOGIC**:
The user will provide an "Arrival Date" (when they land at the destination) and a "Departure Date" (when they leave the destination).
1. To find the **outbound** flight, you MUST call `search_flights` using the user's **Origin** as the `origin_city` and their **Destination** as the `destination_city`. The `departure_date` for this flight is the user's **Arrival Date**.
2. To find the **inbound** (return) flight, you MUST call `search_flights` a second time, but swap the cities: use the user's **Destination** as the `origin_city` and their **Origin** as the `destination_city`. The `departure_date` for this flight is the user's **Departure Date**.

**CRITICAL ITINERARY DISPLAY RULE**:
When you call `generate_detailed_itinerary`, the tool will return the complete itinerary text.
You MUST include this FULL itinerary in your response to the user. Never say "I sent it" or "I generated it" without actually displaying the content.
Format it nicely with markdown headers and sections so it's easy to read.

**CRITICAL RULE**: If an item is already in the ITINERARY (see above),
do NOT call a tool to find it again unless the user explicitly asks.
"""
        
        
    def process_message(self, user_message_content: str):
        # Save user message
        db.session.add(Message(conversation_id=self.conversation.id, role='user', content=user_message_content))
        
        chat_history = self._get_chat_history()
        # Send to Gemini
        response = self.model.generate_content(chat_history)

        # Check if the LLM wants to call one *or more* tools
        try:
            model_response_content = response.candidates[0].content
            function_calls = [p.function_call for p in model_response_content.parts if p.function_call]
        except (AttributeError, IndexError, ValueError):
            function_calls = []

        if function_calls:
            self._save_status(f"Engine is now performing {len(function_calls)} actions. Processing...")
            print(f"Detected {len(function_calls)} tool call(s).")
            
            function_response_parts = []
            
            for function_call in function_calls:
                tool_name = function_call.name
                tool_args = {key: value for key, value in function_call.args.items()}
                
                print(f"Executing Tool: {tool_name} with args: {tool_args}")

                if tool_name == "search_hotels":
                    self._save_status(f"⏳ Searching for hotels in **{tool_args.get('city')}**...")
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
                        hotels_list = tool_result if isinstance(tool_result, list) else [tool_result]
                        for hotel in hotels_list:
                            self.IteneraryManager._save_hotel_to_db(hotel) 
                        print(f"✅ Saved {len(hotels_list)} hotels to database")
                        tool_result = hotels_list
                    else:
                        tool_result = {"status": "error", "message": "No hotels found matching criteria."}

                elif tool_name == "search_flights":
                    self._save_status(f"✈️ Searching for flights from **{tool_args.get('origin_city')}** to **{tool_args.get('destination_city')}**...")
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
                    self._save_status(f"✨ Generating personalized activities for **{tool_args.get('destination')}**...")
                    itinerary_text = self._get_activity_itinerary(
                        tool_args.get('destination'), 
                        tool_args.get('activities')
                    )
                    
                    # Return the actual content so LLM can display it
                    tool_result = {
                        "status": "success",
                        "recommendations": itinerary_text,
                        "instruction": "Display these recommendations to the user in your response."
                    }

                elif tool_name == "search_shops":
                    self._save_status(f"🛒 Pre-loading local points of interest (supermarkets, essentials) in **{tool_args.get('city')}**...")
                    tool_result = search_shops(
                        city=tool_args.get('city'),
                        categories=tool_args.get('categories')
                    )
                    self.IteneraryManager._save_shop_to_db(tool_result)
                    print(tool_result)
                
                elif tool_name == "search_leisure":
                    self._save_status(f"🎭 Pre-loading leisure activities and entertainment options in **{tool_args.get('city')}**...")
                    tool_result = search_leisure(
                        city=tool_args.get('city'),
                        categories=tool_args.get('categories')
                    )
                    self.IteneraryManager._save_leisure_to_db(tool_result)
                    print(tool_result)

                elif tool_name == "generate_detailed_itinerary":
                    print("🗓️ Generating detailed day-by-day itinerary...")
                    
                    # Store the parameters in preferences for future reference
                    self.prefs['itinerary_generated'] = True
                    self.prefs['arrival_date'] = tool_args.get('arrival_date')
                    self.prefs['departure_date'] = tool_args.get('departure_date')
                    
                    try:
                        itinerary_text = generate_detailed_itinerary(
                            destination=tool_args.get('destination'),
                            arrival_date=tool_args.get('arrival_date'),
                            departure_date=tool_args.get('departure_date'),
                            activity_preferences=tool_args.get('activity_preferences', 'mixed')
                        )
                        
                        # Return the FULL itinerary to the LLM so it can display it
                        tool_result = {
                            "status": "success",
                            "itinerary": itinerary_text,  # Include full content
                            "instruction": "Display this complete itinerary to the user in your response. Format it nicely with markdown."
                        }
                        
                        print(f"✅ Generated itinerary successfully")
                    except Exception as e:
                        print(f"❌ Error generating itinerary: {e}")
                        tool_result = {
                            "status": "error",
                            "message": f"Failed to generate itinerary: {str(e)}"
                        }

                function_response_parts.append(
                    types.PartDict(
                        function_response=types.ContentDict(
                            name=tool_name,
                            response={"result": json.dumps(tool_result)} 
                        )
                    )
                )

            # Build the function response message
            function_response_content = types.ContentDict(
                role="function",
                parts=function_response_parts
            )
            
            # Send history, the model's request, and our results
            response = self.model.generate_content([
                *chat_history,                
                model_response_content,
                function_response_content
            ])
        
        final_response_text = response.candidates[0].content.parts[0].text

        db.session.add(Message(conversation_id=self.conversation.id, role='assistant', content=final_response_text))
        
        # Update conversation preferences
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
        itinerary_model = genai.GenerativeModel(
            model_name="gemini-2.0-flash-exp",
            system_instruction=f"You are a travel expert. Create a day-by-day itinerary for a trip to {destination} with a focus on {activities} activities. Be creative and engaging. Add map links."
        )
        response = itinerary_model.generate_content(f"Give me an itinerary for {destination}.")
        final_text = parse_recommendations_with_links(response.text, destination)
        
        return final_text
    
    def _update_prefs_from_text(self, text):
        # A simple LLM call or regex to extract entities from the user's
        pass

    def _save_status(self, status_text: str):
        """Saves a temporary status message to the database for frontend display."""
        # Use a special 'status' role so the frontend knows to display this 
        # as a non-conversational update.
        db.session.add(Message(
            conversation_id=self.conversation.id, 
            role='status', 
            content=status_text
        ))
        # Commit immediately so the frontend can retrieve it
        db.session.commit()
        # Optional: log to console as well for debugging
        print(f"**STATUS UPDATE**: {status_text}")
