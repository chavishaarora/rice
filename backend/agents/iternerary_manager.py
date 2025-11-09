import json
from database import db, TravelSuggestion, Conversation
from agents.booking_agent import search_hotels
from agents.flight_agent import search_flights

class ItineraryManager:
    """
    The "Coat Rack" for the application. This is the "boss."
    
    It actively manages the itinerary by calling APIs 
    and committing changes to the database.
    """
    
    def __init__(self, conversation: Conversation):
        self.conversation = conversation
        self.conversation_id = conversation.id
        self.prefs = conversation.preferences or {}
        
        # These are the attributes the agent "sees"
        self.journey_to = None
        self.journey_from = None
        self.stays = []
        self.activities = {}

        # Load its own state from the DB
        self.load_from_db()

    def load_from_db(self):
        """
        Queries the TravelSuggestion table and populates the
        itinerary attributes (journeys, stays).
        """
        print(f"ItineraryManager: Loading state from DB for conv_id: {self.conversation_id}")
        
        self.stays = []
        self.journey_to = None
        self.journey_from = None
        
        trip_destination = self.prefs.get('destination')
        trip_origin = self.prefs.get('origin')

        suggestions = TravelSuggestion.query.filter_by(
            conversation_id=self.conversation_id
        ).order_by(TravelSuggestion.created_at).all()

        for s in suggestions:
            if s.type == 'hotel':
                self.stays.append(self._format_suggestion(s))
            
            elif s.type == 'flight':
                flight_origin = s.location.get('origin', 'N/A').upper()
                flight_dest = s.location.get('destination', 'N/A').upper()

                if trip_origin and trip_destination and \
                   flight_origin in trip_origin.upper() and flight_dest in trip_destination.upper():
                    self.journey_to = self._format_suggestion(s)
                
                elif trip_origin and trip_destination and \
                     flight_origin in trip_destination.upper() and flight_dest in trip_origin.upper():
                    self.journey_from = self._format_suggestion(s)
                
                elif not self.journey_to:
                    self.journey_to = self._format_suggestion(s)
                    
    def _format_suggestion(self, s: TravelSuggestion) -> dict:
        """Helper to return a clean dict for the agent's memory."""
        return {
            "id": s.id,
            "title": s.title,
            "description": s.description,
            "price": float(s.price) if s.price is not None else -10,
            "booking_url": s.booking_url,
            "location": s.location
        }

    def to_dict(self) -> dict:
        """
        Returns a serializable dictionary representation of the
        current itinerary for the LLM's system prompt.
        """
        return {
            "journey_to": self.journey_to,
            "journey_from": self.journey_from,
            "stays": self.stays,
            "activities": self.activities
        }

    def add_hotel(self, hotel_data, **kwargs) -> dict:
        """
        Add hotel(s) to the itinerary. 
        Handles both single hotel dict and list of hotel dicts.
        """
        print(f"ItineraryManager: Executing 'add_hotel'")
        try:
            # Check if hotel_data is a list (multiple hotels) or dict (single hotel)
            if isinstance(hotel_data, list):
                # Handle multiple hotels
                saved_count = 0
                hotel_names = []
                total_price = 0
                
                for hotel in hotel_data:
                    self._save_hotel_to_db(hotel)
                    saved_count += 1
                    hotel_names.append(hotel.get('hotel_name', 'Unknown'))
                    total_price += hotel.get('price', 0)
                
                self.load_from_db()
                
                return {
                    "status": "success", 
                    "message": f"Added {saved_count} hotels",
                    "hotel_names": hotel_names,
                    "hotels_saved": saved_count
                }
            else:
                # Handle single hotel (backward compatibility)
                self._save_hotel_to_db(hotel_data)
                self.load_from_db()

                return {
                    "status": "success", 
                    "hotel_name": hotel_data.get('hotel_name'), 
                    "price": hotel_data.get('price')
                }

        except Exception as e:
            print(f"ItineraryManager: Error in add_hotel: {e}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "message": str(e)}

    def add_flight(self, flight_data, **kwargs) -> dict:
        """
        Add flight to the itinerary.
        """
        print(f"ItineraryManager: Executing 'add_flight'")
        try:
            self._save_flight_to_db(flight_data)
            self.load_from_db()

            return {
                "status": "success", 
                "flight_title": flight_data.get('title'), 
                "price": flight_data.get('price')
            }

        except Exception as e:
            print(f"ItineraryManager: Error in add_flight: {e}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "message": str(e)}

    def _save_hotel_to_db(self, hotel_data: dict):
        """Internal method to save a hotel to the DB."""
        print(f"ItineraryManager: Saving hotel '{hotel_data.get('hotel_name')}' to DB.")
        
        rating_10_point = hotel_data.get('rating', 0)
        rating_5_point = rating_10_point / 2.0 if rating_10_point > 0 else 0
        
        image_url = hotel_data.get('room_photo_url', 'N/A')
        if image_url == 'N/A' or not image_url:
            hotel_photos = hotel_data.get('hotel_photo_url', [])
            if hotel_photos and len(hotel_photos) > 0:
                image_url = hotel_photos[0]

        suggestion = TravelSuggestion(
            conversation_id=self.conversation_id,
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
        # Note: We don't commit here. The main app request/response
        # cycle in 'process_message' will handle the commit.

    def _save_flight_to_db(self, flight_data: dict):
        """Internal method to save a flight to the DB."""
        print(f"ItineraryManager: Saving flight '{flight_data.get('title')}' to DB.")
        suggestion = TravelSuggestion(
            conversation_id=self.conversation_id,
            type='flight',
            title=flight_data.get('title'),
            description=flight_data.get('description'),
            price=flight_data.get('price'),
            rating=None,
            image_url=flight_data.get('image_url'),
            booking_url=flight_data.get('booking_url'),
            location={
                'origin': flight_data.get('origin_code'), 
                'destination': flight_data.get('destination_code')
            }
        )
        db.session.add(suggestion)