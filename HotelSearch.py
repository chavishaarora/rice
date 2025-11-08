import http.client
import json
from typing import Dict, Any, Optional, List

# --- Configuration Variables ---
# REQUIRED VARIABLES
CITY_QUERY = "corsica"
ARRIVAL_DATE = "2025-11-10"
DEPARTURE_DATE = "2025-11-15"

ADULTS = 2
CHILDREN_AGE = "0%2C17" # URL-encoded: 0,17
ROOM_QTY = 1
PRICE_MIN = 0
PRICE_MAX = 1000

# API VARIABLES
API_HOST = "booking-com15.p.rapidapi.com"
API_KEY = ""


class BookingComAPI:
    """
    A class to interact with the Booking.com RapidAPI endpoint,
    encapsulating different search and details calls.
    """
    
    def __init__(self, api_host: str, api_key: str, **kwargs):
        """
        Initializes the API client with host, key, and default search parameters.
        """
        self.API_HOST = api_host
        self.HEADERS = {
            'x-rapidapi-key': api_key,
            'x-rapidapi-host': api_host
        }
        
        # Search Parameters (Default values, can be overridden per call if needed)
        self.CITY_QUERY = kwargs.get('CITY_QUERY', CITY_QUERY)
        self.ARRIVAL_DATE = kwargs.get('ARRIVAL_DATE', ARRIVAL_DATE)
        self.DEPARTURE_DATE = kwargs.get('DEPARTURE_DATE', DEPARTURE_DATE)
        self.ADULTS = kwargs.get('ADULTS', ADULTS)
        self.CHILDREN_AGE = kwargs.get('CHILDREN_AGE', CHILDREN_AGE)
        self.ROOM_QTY = kwargs.get('ROOM_QTY', ROOM_QTY)
        self.PRICE_MIN = kwargs.get('PRICE_MIN', PRICE_MIN)
        self.PRICE_MAX = kwargs.get('PRICE_MAX', PRICE_MAX)
        
        # Booking/Display Specific Variables
        self.PAGE_NUMBER = 1
        self.UNITS = "metric"
        self.TEMPERATURE_UNIT = "c"
        self.LANGUAGE_CODE = "en-us"
        self.CURRENCY_CODE = "EUR"
        self.LOCATION = "NL"
        
        # Variables set dynamically
        self.DEST_ID = ""
        self.DESTINATION = ""
        self.SEARCH_TYPE = ""

    def _make_api_call(self, method: str, endpoint: str) -> Optional[Dict[str, Any]]:
        """Handles the connection and makes the API request."""
        conn = http.client.HTTPSConnection(self.API_HOST)
        print(f"\n--- Making {method} request to: {endpoint} ---")
        try:
            conn.request(method, endpoint, headers=self.HEADERS)
            res = conn.getresponse()
            data = res.read()
            conn.close()
            
            # Decode the bytes to a string and parse the JSON
            return json.loads(data.decode("utf-8"))
            
        except Exception as e:
            print(f"An error occurred: {e}")
            return None

    def search_destination(self) -> bool:
        """Finds the destination ID and search type based on CITY_QUERY."""
        city_endpoint = f"/api/v1/hotels/searchDestination?query={self.CITY_QUERY}"
        city_data_dict = self._make_api_call("GET", city_endpoint)

        if city_data_dict and city_data_dict.get('data'):
            city_results = city_data_dict['data']
            
            if city_results:
                first_result = city_results[0]
                self.DEST_ID = first_result.get('dest_id')
                self.DESTINATION = first_result.get('label')
                # Ensure SEARCH_TYPE is uppercase as per API requirement
                self.SEARCH_TYPE = first_result.get('search_type', '').upper()
                
                print(f"✅ City Search Success: Using '{self.DESTINATION}'")
                print(f"   -> DEST_ID: {self.DEST_ID}, SEARCH_TYPE: {self.SEARCH_TYPE}")
                return True
            else:
                print(f"❌ City Search Failed: No results found for '{self.CITY_QUERY}'.")
        else:
            print("❌ City Search Failed: API error or empty response.")
        
        return False

    def get_filters(self) -> Optional[Dict[str, Any]]:
        """Retrieves filter data, including the total number of hotels."""
        if not self.DEST_ID or not self.SEARCH_TYPE:
            print("❌ Cannot get filters: Destination ID or Search Type is missing.")
            return None
            
        filter_endpoint = (
            f"/api/v1/hotels/getFilter?"
            f"dest_id={self.DEST_ID}&"
            f"search_type={self.SEARCH_TYPE}&"
            f"arrival_date={self.ARRIVAL_DATE}&"
            f"departure_date={self.DEPARTURE_DATE}&"
            f"adults={self.ADULTS}&"
            f"children_age={self.CHILDREN_AGE}&"
            f"room_qty={self.ROOM_QTY}"
        )

        filter_data_dict = self._make_api_call("GET", filter_endpoint)
        
        if filter_data_dict and filter_data_dict.get('data'):
            total_hotels = filter_data_dict['data'].get('pagination', {}).get('nbResultsTotal', 'N/A')
            print(f"✅ Filter Data Retrieved. Total Hotels Available for dates {self.ARRIVAL_DATE} to {self.DEPARTURE_DATE}: {total_hotels}")
            return filter_data_dict
        else:
            print("❌ Failed to get filter data.")
            return None

    def search_hotels(self) -> Optional[Dict[str, Any]]:
        """Searches for hotels based on all configured parameters."""
        if not self.DEST_ID or not self.SEARCH_TYPE:
            print("❌ Cannot search hotels: Destination ID or Search Type is missing.")
            return None
            
        hotel_endpoint = (
            f"/api/v1/hotels/searchHotels?"
            f"dest_id={self.DEST_ID}&"
            f"search_type={self.SEARCH_TYPE}&"
            f"arrival_date={self.ARRIVAL_DATE}&"
            f"departure_date={self.DEPARTURE_DATE}&"
            f"adults={self.ADULTS}&"
            f"children_age={self.CHILDREN_AGE}&"
            f"room_qty={self.ROOM_QTY}&"
            f"page_number={self.PAGE_NUMBER}&"
            f"price_min={self.PRICE_MIN}&"
            f"price_max={self.PRICE_MAX}&"
            f"units={self.UNITS}&"
            f"temperature_unit={self.TEMPERATURE_UNIT}&"
            f"languagecode={self.LANGUAGE_CODE}&"
            f"currency_code={self.CURRENCY_CODE}&"
            f"location={self.LOCATION}"
        )

        hotel_data_dict = self._make_api_call("GET", hotel_endpoint)
        
        if hotel_data_dict and hotel_data_dict.get('data'):
            hotel_results = hotel_data_dict['data']
            print(f"✅ Hotel Search Results Retrieved: {len(hotel_results.get('hotels', []))} hotels on page {self.PAGE_NUMBER}.")
            return hotel_data_dict
        else:
            print("❌ Failed to get hotel search data.")
            return None

    def get_hotel_details(self, hotel_id: int) -> Optional[Dict[str, Any]]:
        """Retrieves specific details for a single hotel, including room photos."""
        details_endpoint = (
            f"/api/v1/hotels/getHotelDetails?"
            f"hotel_id={hotel_id}&"
            f"adults={self.ADULTS}&"
            f"children_age={self.CHILDREN_AGE}&"
            f"room_qty={self.ROOM_QTY}&"
            f"units={self.UNITS}&"
            f"arrival_date={self.ARRIVAL_DATE}&"
            f"departure_date={self.DEPARTURE_DATE}&"
            f"temperature_unit={self.TEMPERATURE_UNIT}&"
            f"languagecode={self.LANGUAGE_CODE}&"
            f"currency_code={self.CURRENCY_CODE}"
        )
        details_data_dict = self._make_api_call("GET", details_endpoint)
        
        if details_data_dict and details_data_dict.get('data'):
            print(f"✅ Hotel Details Retrieved for hotel ID: **{hotel_id}**")
            return details_data_dict
        else:
            print(f"❌ Failed to get hotel details for hotel ID: {hotel_id}.")
            return None

def main() -> Optional[Dict[str, Any]]:
    """Executes the API flow and returns the final hotel data dictionary."""
    
    api_client = BookingComAPI(API_HOST, API_KEY, CITY_QUERY=CITY_QUERY)
    
    # Initialize variables for the final dictionary
    result_data = {
        "destionation": api_client.CITY_QUERY, # Default to query, will update if search succeeds
        "hotel_name": "N/A",
        "hotel_description": "N/A",
        "price": 0,
        "currency": "N/A",
        "booking_hotel_id": 0,
        "hotel_photo_url": [],
        "room_photo_url": "N/A",
    }


    # 1. Search Destination
    if not api_client.search_destination():
        print("Final result not available due to destination search failure.")
        return None
    
    # Update destination name
    result_data["destionation"] = api_client.DESTINATION

    # 2. Get Filters (Optional, for count)
    api_client.get_filters()

    # 3. Search Hotels
    hotel_search_result = api_client.search_hotels()
    
    if not (hotel_search_result and hotel_search_result['data'].get('hotels')):
        print("Final result not available due to hotel search failure or no results.")
        return None
    
    first_hotel = hotel_search_result['data']['hotels'][0]
    hotel_id = first_hotel['hotel_id']
    
    # Extract data from hotel search result
    result_data["booking_hotel_id"] = hotel_id
    result_data["hotel_name"] = first_hotel['property']['name']
    result_data["hotel_description"] = first_hotel.get('accessibilityLabel', 'N/A')
    
    # Safely extract price details
    price_breakdown = first_hotel['property']['priceBreakdown']['grossPrice']
    result_data["price"] = price_breakdown.get('value', 0)
    result_data["currency"] = price_breakdown.get('currency', 'N/A')
    
    # Get general photo URLs
    result_data["hotel_photo_url"] = first_hotel['property'].get('photoUrls', [])
    
    print(f"\n--- First Hotel Found & Data Collected ---")


    # 4. Get Hotel Details (For specific room photo)
    details_result = api_client.get_hotel_details(hotel_id)
    
    if details_result:
        hotel_data = details_result['data']
        rooms = hotel_data.get('rooms', {})
        photo_urls_rooms: List[str] = []
        
        # Extract high-res room photos
        if rooms:
            try:
                # Get the first room ID/key
                first_room_id = next(iter(rooms))
                first_room_data = rooms.get(first_room_id, {})
                photos_list = first_room_data.get('photos', [])
                
                # Collect all high-res URLs for the room
                for photo in photos_list:
                    url = photo.get('url_max1280')
                    if url:
                        photo_urls_rooms.append(url)
            except StopIteration:
                pass # No rooms found
        
        # Update final dictionary with the first room photo URL
        if photo_urls_rooms:
            result_data["room_photo_url"] = photo_urls_rooms[0]
            print(f"✅ Extracted first room photo URL.")
        else:
            print(f"⚠️ No high-res room photos found in the details.")

    print("\n🎉 Final Dictionary Complete.")
    return result_data

if __name__ == "__main__":
    final_output = main()
    if final_output:
        print("\n=======================================================")
        print("🚀 FINAL RETURNED DATA:")
        print(json.dumps(final_output, indent=4))
        print("=======================================================")
