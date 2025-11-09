import http.client
import json
from typing import Dict, Any, Optional, List

# --- Configuration Variables ---
# REQUIRED VARIABLES
CITY_QUERY = "rome"

# API VARIABLES
API_HOST = "tripadvisor16.p.rapidapi.com"
API_KEY = "251571329bmsh50fc0efaf150814p10a4b5jsn5753d34c7b48"


class TripAdvisorMuseumAPI:
    """
    A class to interact with the TripAdvisor RapidAPI endpoint,
    specifically for searching museums and attractions.
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
        
        # Search Parameters
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
        location_endpoint = f"/api/v1/attraction/searchLocation?query={self.CITY_QUERY}"
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

    def search_museums(self) -> Optional[Dict[str, Any]]:
        """
        Searches for museums/attractions based on location ID.
        Uses the attractions endpoint with filters for museums.
        """
        if not self.LOCATION_ID:
            print("❌ Cannot search museums: Location ID is missing.")
            return None
            
        # Search for attractions (museums fall under attractions)
        # Adding filters for museums specifically
        museum_endpoint = f"/api/v1/attraction/searchAttractions?locationId={self.LOCATION_ID}&page={self.PAGE_NUMBER}&currencyCode={self.CURRENCY}"

        museum_data_dict = self._make_api_call("GET", museum_endpoint)
        
        if museum_data_dict and museum_data_dict.get('data'):
            museum_results = museum_data_dict['data']
            attractions = museum_results.get('data', [])
            
            # Filter for museums specifically (if subcategory contains museum-related terms)
            museums = []
            for attraction in attractions:
                subcategories = attraction.get('subcategory', [])
                for subcat in subcategories:
                    subcat_name = subcat.get('name', '').lower()
                    if any(keyword in subcat_name for keyword in ['museum', 'gallery', 'art', 'history', 'exhibition']):
                        museums.append(attraction)
                        break
            
            print(f"✅ Museum Search Results Retrieved: {len(museums)} museums found on page {self.PAGE_NUMBER}.")
            
            # Return with filtered museums
            return {
                'data': {
                    'data': museums
                }
            }
        else:
            print("❌ Failed to get museum search data.")
            return None

    def get_museum_details(self, location_id: str) -> Optional[Dict[str, Any]]:
        """Retrieves specific details for a single museum/attraction."""
        details_endpoint = (
            f"/api/v1/attraction/getAttractionDetails?"
            f"locationId={location_id}&"
            f"language={self.LANGUAGE_CODE}&"
            f"currency={self.CURRENCY}"
        )
        
        details_data_dict = self._make_api_call("GET", details_endpoint)

        if details_data_dict and details_data_dict.get('data'):
            print(f"✅ Museum Details Retrieved for location ID: **{location_id}**")
            return details_data_dict
        else:
            print(f"❌ Failed to get museum details for location ID: {location_id}.")
            return None


def main() -> Optional[Dict[str, Any]]:
    """Executes the API flow and returns the final museum data dictionary."""
    
    api_client = TripAdvisorMuseumAPI(API_HOST, API_KEY, CITY_QUERY=CITY_QUERY)
    
    # Initialize variables for the final dictionary
    result_data = {
        "destination": api_client.CITY_QUERY,
        "museum_name": "N/A",
        "museum_description": "N/A",
        "rating": 0,
        "price_level": "N/A",
        "museum_type": "Museum",
        "museum_id": "",
        "museum_photo_url": [],
        "tripadvisor_url": "https://tripadvisor.com",
        "opening_hours": "N/A",
        "address": "N/A"
    }

    # 1. Search Location
    if not api_client.search_location():
        print("Final result not available due to location search failure.")
        return None
    
    # Update destination name
    result_data["destination"] = api_client.LOCATION_NAME

    # 2. Search Museums
    museum_search_result = api_client.search_museums()
    
    if not (museum_search_result and museum_search_result['data'].get('data')):
        print("Final result not available due to museum search failure or no results.")
        return None
    
    first_museum = museum_search_result['data']['data'][0]
    museum_id = str(first_museum.get('locationId', ''))
    
    # Extract data from museum search result
    result_data["museum_id"] = museum_id
    result_data["museum_name"] = first_museum.get('name', 'N/A')
    
    # Get description
    result_data["museum_description"] = first_museum.get('description', 'N/A')
    
    # Extract subcategory (type of museum)
    subcategories = first_museum.get('subcategory', [])
    if subcategories:
        result_data["museum_type"] = subcategories[0].get('name', 'Museum')
        # Use subcategory as description if no description
        if result_data["museum_description"] == 'N/A':
            result_data["museum_description"] = ', '.join([cat.get('name', '') for cat in subcategories])
    
    # Extract rating and price
    result_data["rating"] = first_museum.get('rating', 0)
    result_data["price_level"] = first_museum.get('priceLevel', 'N/A')
    
    # Get hero photo URL
    hero_img = first_museum.get('heroImage')
    if hero_img:
        result_data["museum_photo_url"] = [hero_img]
    
    # Get additional photos
    card_photos = first_museum.get('cardPhotos', [])
    for photo in card_photos[:3]:
        if photo.get('sizes', {}).get('urlTemplate'):
            photo_url = photo['sizes']['urlTemplate'].replace('{width}', '1000').replace('{height}', '667')
            result_data["museum_photo_url"].append(photo_url)
    
    # Get TripAdvisor URL
    fallback_url = first_museum.get('detailsURL', f"https://www.tripadvisor.com/Search?q={api_client.CITY_QUERY}+museums")
    result_data["tripadvisor_url"] = fallback_url
    
    # Get address
    address_obj = first_museum.get('address', {})
    if address_obj:
        result_data["address"] = address_obj.get('address', 'N/A')
    
    # Get opening hours
    hours = first_museum.get('hours', {})
    if hours:
        result_data["opening_hours"] = hours.get('weekdayText', 'N/A')
    
    print(f"\n--- First Museum Found & Data Collected ---")

    # 3. Get Museum Details (for additional information if needed)
    if museum_id:
        details_result = api_client.get_museum_details(museum_id)
        
        if details_result and details_result.get('data'):
            museum_data = details_result['data']
            
            # Update description if available and better
            about_section = museum_data.get('about', {})
            if about_section and about_section.get('description'):
                result_data["museum_description"] = about_section['description']
            
            # Get more detailed photos if available
            photos = museum_data.get('photos', [])
            photo_urls_list: List[str] = []
            
            if photos:
                try:
                    for photo in photos[:5]:
                        url_template = photo.get('urlTemplate')
                        if url_template:
                            photo_url = url_template.replace('{width}', '1280').replace('{height}', '720')
                            photo_urls_list.append(photo_url)
                except Exception as e:
                    print(f"⚠️ Error parsing photos: {e}")
            
            if photo_urls_list:
                result_data["museum_photo_url"] = photo_urls_list
                print(f"✅ Extracted {len(photo_urls_list)} museum photos.")
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