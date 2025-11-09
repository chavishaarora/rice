import http.client
import json
from typing import Dict, Any, Optional, List

# --- Configuration Variables ---
# REQUIRED VARIABLES
CITY_QUERY = "rome"

# API VARIABLES
API_HOST = "tripadvisor16.p.rapidapi.com"
API_KEY = "251571329bmsh50fc0efaf150814p10a4b5jsn5753d34c7b48"


class TripAdvisorAPI:
    """
    A class to interact with the TripAdvisor RapidAPI endpoint,
    encapsulating different search and details calls for restaurants.
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
        
        # Display Specific Variables
        self.PAGE_NUMBER = 1
        self.LANGUAGE_CODE = "en"
        self.CURRENCY = "USD"
        
        # Variables set dynamically
        self.LOCATION_ID = ""
        self.LOCATION_NAME = ""

    def _make_api_call(self, method: str, endpoint: str) -> Optional[Dict[str, Any]]:
        """Handles the connection and makes the API request."""
        conn = http.client.HTTPSConnection(self.API_HOST)
        print(f"\n--- Making {method} request to: {endpoint} ---")
        try:
            conn.request(method, endpoint, headers=self.HEADERS)
            res = conn.getresponse()
            data = res.read()
            conn.close()
            
            # Decode and print raw response for debugging
            decoded_data = data.decode("utf-8")
            print(f"📡 API Response Status: {res.status}")
            print(f"📡 API Response (first 500 chars): {decoded_data[:500]}")
            
            # Parse JSON
            return json.loads(decoded_data)
            
        except Exception as e:
            print(f"❌ An error occurred: {e}")
            print(f"📡 Raw data: {data.decode('utf-8') if data else 'No data'}")
            return None

    def search_location(self) -> bool:
        """Finds the location ID based on CITY_QUERY."""
        location_endpoint = f"/api/v1/restaurant/searchLocation?query={self.CITY_QUERY}"
        location_data_dict = self._make_api_call("GET", location_endpoint)

        if location_data_dict and location_data_dict.get('data'):
            location_results = location_data_dict['data']
            
            if location_results:
                first_result = location_results[0]
                self.LOCATION_ID = first_result.get('locationId')
                self.LOCATION_NAME = first_result.get('localizedName', self.CITY_QUERY)
                
                print(f"✅ Location Search Success: Using '{self.LOCATION_NAME}'")
                print(f"   -> LOCATION_ID: {self.LOCATION_ID}")
                return True
            else:
                print(f"❌ Location Search Failed: No results found for '{self.CITY_QUERY}'.")
        else:
            print("❌ Location Search Failed: API error or empty response.")
        
        return False

    def search_restaurants(self) -> Optional[Dict[str, Any]]:
        """Searches for restaurants based on location ID."""
        if not self.LOCATION_ID:
            print("❌ Cannot search restaurants: Location ID is missing.")
            return None
            
        restaurant_endpoint = f"/api/v1/restaurant/searchRestaurants?locationId={self.LOCATION_ID}&page={self.PAGE_NUMBER}"

        restaurant_data_dict = self._make_api_call("GET", restaurant_endpoint)
        
        if restaurant_data_dict and restaurant_data_dict.get('data'):
            restaurant_results = restaurant_data_dict['data']
            restaurants = restaurant_results.get('data', [])
            print(f"✅ Restaurant Search Results Retrieved: {len(restaurants)} restaurants found on page {self.PAGE_NUMBER}.")
            return restaurant_data_dict
        else:
            print("❌ Failed to get restaurant search data.")
            return None

    def get_restaurant_details(self, restaurant_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves specific details for a single restaurant, including photos."""
        details_endpoint = (
            f"/api/v1/restaurant/getRestaurantDetails?"
            f"restaurantId={restaurant_id}&"
            f"language={self.LANGUAGE_CODE}&"
            f"currency={self.CURRENCY}"
        )
        
        details_data_dict = self._make_api_call("GET", details_endpoint)

        if details_data_dict and details_data_dict.get('data'):
            print(f"✅ Restaurant Details Retrieved for restaurant ID: **{restaurant_id}**")
            return details_data_dict
        else:
            print(f"❌ Failed to get restaurant details for restaurant ID: {restaurant_id}.")
            return None


def main() -> Optional[Dict[str, Any]]:
    """Executes the API flow and returns the final restaurant data dictionary."""
    
    api_client = TripAdvisorAPI(API_HOST, API_KEY, CITY_QUERY=CITY_QUERY)
    
    # Initialize variables for the final dictionary
    result_data = {
        "destination": api_client.CITY_QUERY,
        "restaurant_name": "N/A",
        "restaurant_description": "N/A",
        "rating": 0,
        "price_level": "N/A",
        "cuisine": [],
        "restaurant_id": "",
        "restaurant_photo_url": [],
        "tripadvisor_url": "https://tripadvisor.com"
    }

    # 1. Search Location
    if not api_client.search_location():
        print("Final result not available due to location search failure.")
        return None
    
    # Update destination name
    result_data["destination"] = api_client.LOCATION_NAME

    # 2. Search Restaurants
    restaurant_search_result = api_client.search_restaurants()
    
    if not (restaurant_search_result and restaurant_search_result['data'].get('data')):
        print("Final result not available due to restaurant search failure or no results.")
        return None
    
    first_restaurant = restaurant_search_result['data']['data'][0]
    restaurant_id = str(first_restaurant.get('restaurantsId', ''))
    
    # Extract data from restaurant search result
    result_data["restaurant_id"] = restaurant_id
    result_data["restaurant_name"] = first_restaurant.get('name', 'N/A')
    
    # Build description from cuisine tags
    cuisine_tags = first_restaurant.get('establishmentTypeAndCuisineTags', [])
    result_data["restaurant_description"] = ', '.join(cuisine_tags) if cuisine_tags else 'N/A'
    result_data["cuisine"] = cuisine_tags
    
    # Extract rating and price
    result_data["rating"] = first_restaurant.get('averageRating', 0)
    result_data["price_level"] = first_restaurant.get('priceTag', 'N/A')
    
    # Get hero photo URL
    hero_img = first_restaurant.get('heroImgUrl')
    if hero_img:
        result_data["restaurant_photo_url"] = [hero_img]
    
    # Get TripAdvisor URL
    fallback_url = first_restaurant.get('restaurantsDetailsURL', f"https://www.tripadvisor.com/Search?q={api_client.CITY_QUERY}")
    result_data["tripadvisor_url"] = fallback_url
    
    print(f"\n--- First Restaurant Found & Data Collected ---")

    # 3. Get Restaurant Details (For additional photos and description)
    if restaurant_id:
        details_result = api_client.get_restaurant_details(restaurant_id)
        
        if details_result and details_result.get('data'):
            restaurant_data = details_result['data']
            
            # Update description if available
            about_section = restaurant_data.get('about', {})
            if about_section and about_section.get('description'):
                result_data["restaurant_description"] = about_section['description']
            
            # Get more photos if available
            photos = restaurant_data.get('photos', [])
            photo_urls_list: List[str] = []
            
            if photos:
                try:
                    # Collect high-res URLs for photos
                    for photo in photos[:5]:  # Get up to 5 photos
                        url_template = photo.get('urlTemplate')
                        if url_template:
                            # Replace template placeholders with actual dimensions
                            photo_url = url_template.replace('{width}', '1280').replace('{height}', '720')
                            photo_urls_list.append(photo_url)
                except Exception as e:
                    print(f"⚠️ Error parsing photos: {e}")
            
            # Update with photos if we found any
            if photo_urls_list:
                result_data["restaurant_photo_url"] = photo_urls_list
                print(f"✅ Extracted {len(photo_urls_list)} restaurant photos.")
            else:
                print(f"⚠️ No high-res photos found in the details.")

    print("\n🎉 Final Dictionary Complete.")
    return result_data


if __name__ == "__main__":
    final_output = main()
    if final_output:
        print("\n=======================================================")
        print("🚀 FINAL RETURNED DATA:")
        print(json.dumps(final_output, indent=4))
        print("=======================================================")


