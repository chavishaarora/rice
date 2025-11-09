import http.client
import json
import time
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
API_KEY = "a4635f20famshde916da8e358adbp1ad22ejsn6e8d49abb4b1"


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

    def search_hotels(self, page_number: int = None) -> Optional[Dict[str, Any]]:
        """Searches for hotels based on all configured parameters."""
        if not self.DEST_ID or not self.SEARCH_TYPE:
            print("❌ Cannot search hotels: Destination ID or Search Type is missing.")
            return None
        
        # Use provided page_number or fall back to instance variable
        current_page = page_number if page_number is not None else self.PAGE_NUMBER
            
        hotel_endpoint = (
            f"/api/v1/hotels/searchHotels?"
            f"dest_id={self.DEST_ID}&"
            f"search_type={self.SEARCH_TYPE}&"
            f"arrival_date={self.ARRIVAL_DATE}&"
            f"departure_date={self.DEPARTURE_DATE}&"
            f"adults={self.ADULTS}&"
            f"children_age={self.CHILDREN_AGE}&"
            f"room_qty={self.ROOM_QTY}&"
            f"page_number={current_page}&"
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
            print(f"✅ Hotel Search Results Retrieved: {len(hotel_results.get('hotels', []))} hotels on page {current_page}.")
            return hotel_data_dict
        else:
            print("❌ Failed to get hotel search data.")
            return None
    
    def search_multiple_pages(self, max_pages: int = 5, target_hotels: int = 100) -> List[Dict[str, Any]]:
        """
        Search multiple pages of hotels to get a larger selection.
        
        Args:
            max_pages: Maximum number of pages to fetch (default 5)
            target_hotels: Target number of hotels to collect (default 100)
        
        Returns:
            List of all hotels collected from multiple pages
        """
        all_hotels = []
        
        for page in range(1, max_pages + 1):
            print(f"\n🔍 Fetching page {page}...")
            
            result = self.search_hotels(page_number=page)
            if result and result.get('data', {}).get('hotels'):
                hotels = result['data']['hotels']
                all_hotels.extend(hotels)
                print(f"   Total hotels collected so far: {len(all_hotels)}")
                
                # Stop if we've reached our target
                if len(all_hotels) >= target_hotels:
                    print(f"✅ Reached target of {target_hotels} hotels!")
                    break
            else:
                print(f"   No hotels found on page {page}, stopping search.")
                break
                
            # Small delay to be respectful to the API
            time.sleep(0.5)
        
        return all_hotels

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
    """Executes the API flow with improved multi-page search."""
    
    api_client = BookingComAPI(API_HOST, API_KEY, CITY_QUERY=CITY_QUERY)
    
    # 1. Search Destination
    if not api_client.search_destination():
        print("Final result not available due to destination search failure.")
        return None
    
    # 2. Get Filters to see total available hotels (Optional)
    filter_result = api_client.get_filters()
    
    # 3. Search Multiple Pages of Hotels
    print("\n🏨 Starting comprehensive hotel search...")
    all_hotels = api_client.search_multiple_pages(max_pages=5, target_hotels=100)
    
    if not all_hotels:
        print("No hotels found in search.")
        return None
    
    print(f"\n📊 Total hotels collected: {len(all_hotels)}")
    
    # 4. Filter and rank hotels
    print("\n🎯 Filtering hotels within budget and ranking by value...")
    
    # Filter hotels within budget and sort by rating and price
    filtered_hotels = []
    for hotel in all_hotels:
        try:
            price_breakdown = hotel.get('property', {}).get('priceBreakdown', {}).get('grossPrice', {})
            price = price_breakdown.get('value', 0)
            rating = hotel.get('property', {}).get('reviewScore', 0)
            
            # Skip hotels without price or that exceed budget
            if price == 0 or price > api_client.PRICE_MAX:
                continue
                
            # Calculate value score (rating per price ratio)
            value_score = (rating / price * 100) if price > 0 else 0
            
            filtered_hotels.append({
                'hotel': hotel,
                'price': price,
                'rating': rating,
                'value_score': value_score
            })
        except Exception as e:
            print(f"Error processing hotel: {e}")
            continue
    
    # Sort by value score (best value for money)
    filtered_hotels.sort(key=lambda x: x['value_score'], reverse=True)
    
    print(f"✅ Found {len(filtered_hotels)} hotels within budget (max: {api_client.PRICE_MAX})")
    
    if not filtered_hotels:
        print("❌ No hotels found within the specified budget.")
        return None
    
    # Show top 5 hotels
    print("\n🏆 Top 5 Best Value Hotels:")
    for i, hotel_data in enumerate(filtered_hotels[:5], 1):
        hotel = hotel_data['hotel']
        print(f"\n{i}. {hotel['property']['name']}")
        print(f"   Price: {hotel_data['price']} EUR")
        print(f"   Rating: {hotel_data['rating']}/10")
        print(f"   Value Score: {hotel_data['value_score']:.2f}")
    
    # Get details for the best value hotel
    best_hotel = filtered_hotels[0]['hotel']
    hotel_id = best_hotel['hotel_id']
    
    print(f"\n🔍 Getting full details for the best value hotel...")
    
    # Extract data for the best hotel
    result_data = {
        "destination": api_client.DESTINATION,
        "hotel_name": best_hotel['property']['name'],
        "hotel_description": best_hotel.get('accessibilityLabel', 'N/A'),
        "price": filtered_hotels[0]['price'],
        "currency": "EUR",
        "booking_hotel_id": hotel_id,
        "hotel_photo_url": best_hotel['property'].get('photoUrls', []),
        "room_photo_url": "N/A",
        "booking_url": best_hotel['property'].get('url', f"https://www.booking.com/searchresults.html?ss={api_client.CITY_QUERY}"),
        "rating": filtered_hotels[0]['rating'],
        "value_score": filtered_hotels[0]['value_score']
    }
    
    # Get detailed information
    details_result = api_client.get_hotel_details(hotel_id)
    
    if details_result:
        hotel_data = details_result['data']
        rooms = hotel_data.get('rooms', {})
        
        # Update booking URL if available
        if hotel_data.get("url"):
            result_data["booking_url"] = hotel_data.get("url")
        
        # Extract room photos
        if rooms:
            try:
                first_room_id = next(iter(rooms))
                first_room_data = rooms.get(first_room_id, {})
                photos_list = first_room_data.get('photos', [])
                
                for photo in photos_list:
                    url = photo.get('url_max1280')
                    if url:
                        result_data["room_photo_url"] = url
                        break
            except StopIteration:
                pass
    
    print("\n🎉 Final Selection Complete!")
    return result_data


if __name__ == "__main__":
    final_output = main()
    if final_output:
        print("\n=======================================================")
        print("🚀 FINAL BEST VALUE HOTEL:")
        print(json.dumps(final_output, indent=4))
        print("=======================================================")