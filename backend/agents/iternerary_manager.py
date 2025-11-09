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
        self.shops = []
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
            elif s.type == 'shop':
                self.shops.append(self._format_suggestion(s))
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
            "type": s.type,
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
    
    
    def get_final_itinerary_summary(self) -> str:
        """
        Generates a human-readable, detailed summary of the current, confirmed 
        itinerary items (flights, hotel, POIs) to be printed to the user.
        """
        summary = ["\n🎉 **Your Epic Trip Itinerary is Ready!** ✈️🏨\n"]
        total_price = 0.0

        # --- FLIGHTS ---
        summary.append("## ✈️ Flights")
        
        # Outbound Flight
        if self.journey_to:
            flight = self.journey_to
            summary.append(f"* **Outbound:** {flight['title']} - Price: ${flight['price']:.2f}")
            summary.append(f"  > 📅 Date: {flight['location'].get('departure', 'N/A')} | [Book Now]({flight['booking_url']})")
            total_price += flight['price'] if flight['price'] > 0 else 0
        else:
            summary.append("* **Outbound Flight:** Not yet booked.")

        # Inbound Flight
        if self.journey_from:
            flight = self.journey_from
            summary.append(f"* **Inbound:** {flight['title']} - Price: ${flight['price']:.2f}")
            summary.append(f"  > 📅 Date: {flight['location'].get('departure', 'N/A')} | [Book Now]({flight['booking_url']})")
            total_price += flight['price'] if flight['price'] > 0 else 0
        else:
            summary.append("* **Inbound Flight:** Not yet booked.")

        summary.append("\n---")
        
        # --- ACCOMMODATION ---
        summary.append("## 🏨 Accommodation")
        if self.stays:
            # We assume the user has 'selected' one, but list all if multiple are present
            for i, stay in enumerate(self.stays):
                title = stay['title']
                rating = f" ({stay['rating']:.1f}/5 stars)" if stay['rating'] else ""
                summary.append(f"* **{title}**{rating} - Price (Total): ${stay['price']:.2f}")
                summary.append(f"  > 📍 Address: {stay['location'].get('address', 'N/A')}")
                summary.append(f"  > [View Deal]({stay['booking_url']})")
                
                # Only add the cost of the *first* hotel to the total if multiple are listed
                # (Assuming multiple hotels are alternatives, not consecutive stays)
                if i == 0:
                     total_price += stay['price'] if stay['price'] > 0 else 0
        else:
            summary.append("* **Hotel/Stay:** No accommodation selected yet.")

        summary.append("\n---")
        
        # --- LOCAL POINTS OF INTEREST (Shops & Leisure) ---
        
        # Local Shops
        summary.append("## 🛒 Essential Stops (Supermarkets/Shops)")
        if self.shops:
            shop_names = [f"**{s['title']}** ({s['location'].get('address', 'N/A')})" for s in self.shops[:3]]
            summary.append(f"* Found {len(self.shops)} nearby essential shops. Top 3 are:")
            summary.append(f"  > {'; '.join(shop_names)}")
        else:
            summary.append("* No local essential shops pre-loaded.")

        # Local Leisure
        summary.append("\n## 🎭 Local Leisure & Entertainment")
        if self.leisure:
            leisure_names = [f"**{l['title']}** ({l['location'].get('city', 'N/A')})" for l in self.leisure[:5]]
            summary.append(f"* Found {len(self.leisure)} leisure activities. Top 5 suggestions:")
            summary.append(f"  > {'; '.join(leisure_names)}")
        else:
            summary.append("* No local leisure activities pre-loaded.")

        summary.append("\n---")

        # --- TOTAL COST ESTIMATE ---
        summary.append(f"## 💰 **Estimated Confirmed Trip Cost** (Flights + Accommodation)")
        summary.append(f"* **Total Estimate:** **${total_price:.2f}** (Excluding Activities/Meals)")

        return "\n".join(summary)

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
    
    def select_ideal_choice(self, suggestion_id: int) -> dict:
        """
        Public method to select a specific TravelSuggestion by ID.
        It calls the internal method to delete all other suggestions of the same type.
        """
        print(f"ItineraryManager: Executing 'select_ideal_choice' for ID: {suggestion_id}")
        
        available_ids = TravelSuggestion.query.with_entities(TravelSuggestion.id).filter_by(
            conversation_id=self.conversation_id
        ).limit(20).all()
        
        # Extract just the ID numbers
        id_list = [id[0] for id in available_ids]
        print(f"DEBUG: Available Suggestion IDs in DB session: {id_list}")
        
        if suggestion_id not in id_list:
            print(f"DEBUG ALERT: Requested ID {suggestion_id} is NOT in the available list.")

        selected_suggestion = TravelSuggestion.query.filter_by(
            conversation_id=self.conversation_id,
            id=suggestion_id,
        ).first()

        if not selected_suggestion:
            return {"status": "error", "message": f"Suggestion with ID {suggestion_id} not found."}

        # Use the internal function to destroy all non-selected items of this type
        self._select_and_destroy_suggestions(selected_suggestion)
        
        # Reload state to reflect the changes
        self.load_from_db()

        return {
            "status": "success", 
            "message": f"Selected '{selected_suggestion.title}' ({selected_suggestion.type}). All other {selected_suggestion.type} suggestions have been removed.",
            "selected_title": selected_suggestion.title,
            "selected_type": selected_suggestion.type
        }


    def _select_and_destroy_suggestions(self, selected_suggestion: TravelSuggestion):
        """
        Internal method: Keeps the selected item and deletes all other
        TravelSuggestion items of the same 'type' for the conversation.
        """
        item_type = selected_suggestion.type
        item_id = selected_suggestion.id
        
        # 1. Query for ALL items of the same type in this conversation
        suggestions_to_delete = TravelSuggestion.query.filter(
            TravelSuggestion.conversation_id == self.conversation_id,
            TravelSuggestion.type == item_type,
            TravelSuggestion.id != item_id # Exclude the one we want to keep
        ).all()

        deleted_count = 0
        for suggestion in suggestions_to_delete:
            db.session.delete(suggestion)
            deleted_count += 1
            print(f"ItineraryManager: Deleted unselected {item_type}: {suggestion.title}")

        print(f"ItineraryManager: Successfully removed {deleted_count} unselected '{item_type}' suggestions.")

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


    def _save_shop_to_db(self, shop_data: dict):
        """Internal method to save a shop (POI) to the DB."""
        if not shop_data or shop_data.get('error'):
            print("Shop search returned no data or an error.")
            return

        shop_name = shop_data.get('name')
        if not shop_name:
            print("Shop data is missing a name and cannot be saved.")
            return

        # 1. 🔍 Check for existing shop (Duplicate Check)
        existing_shop = TravelSuggestion.query.filter_by(
            conversation_id=self.conversation_id,
            type='shop',
            title=shop_name  # Filter by the shop's name
        ).first()

        if existing_shop:
            print(f"ItineraryManager: Shop '{shop_name}' already exists in DB. Skipping.")
            return # Exit the function, preventing a duplicate from being added

        print(f"ItineraryManager: Saving shop '{shop_name}' to DB.")

        # Build the location JSON
        location_data = {
            'address': shop_data.get('full_address'),
            'lat': shop_data.get('lat'),
            'lon': shop_data.get('lon'),
            'phone': shop_data.get('phone'),
            'opening_hours': shop_data.get('opening_hours'),
            'city': shop_data.get('city'),
            'postcode': shop_data.get('postcode'),
            'street': shop_data.get('street')
        }
        
        suggestion = TravelSuggestion(
            conversation_id=self.conversation_id,
            type='shop',
            title=shop_name,
            description=shop_data.get('full_address') or shop_data.get('address_line2'),
            price=None,
            rating=None,
            image_url=None,
            booking_url=shop_data.get('website'),
            location=location_data
        )
        db.session.add(suggestion)
        print(f"Added shop suggestion: {shop_name}")

    def _save_leisure_to_db(self, leisure_data: dict):
        """Internal method to save a shop (POI) to the DB."""
        if not leisure_data or leisure_data.get('error'):
            print("Leisure search returned no data or an error.")
            return

        leisure_name = leisure_data.get('name')
        if not leisure_name:
            print("Leisure data is missing a name and cannot be saved.")
            return

        # 1. 🔍 Check for existing shop (Duplicate Check)
        existing_leisure = TravelSuggestion.query.filter_by(
            conversation_id=self.conversation_id,
            type='leisure',
            title=leisure_name  # Filter by the shop's name
        ).first()

        if existing_leisure:
            print(f"ItineraryManager: Leisure '{leisure_name}' already exists in DB. Skipping.")
            return # Exit the function, preventing a duplicate from being added

        print(f"ItineraryManager: Saving leisure '{leisure_name}' to DB.")

        # Build the location JSON
        location_data = {
            'address': leisure_data.get('full_address'),
            'lat': leisure_data.get('lat'),
            'lon': leisure_data.get('lon'),
            'phone': leisure_data.get('phone'),
            'opening_hours': leisure_data.get('opening_hours'),
            'city': leisure_data.get('city'),
            'postcode': leisure_data.get('postcode'),
            'street': leisure_data.get('street')
        }
        
        suggestion = TravelSuggestion(
            conversation_id=self.conversation_id,
            type='leisure',
            title=leisure_name,
            description=leisure_data.get('full_address') or leisure_data.get('address_line2'),
            price=None,
            rating=None,
            image_url=None,
            booking_url=leisure_data.get('website'),
            location=location_data
        )
        db.session.add(suggestion)
        print(f"Added leisure suggestion: {leisure_name}")