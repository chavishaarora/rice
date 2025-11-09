# shopclient.py

import http.client
import json
from typing import Optional, Dict, Any, List
from urllib.parse import urlencode

class GeoapifyAPI:
    """
    A class to interact with the Geoapify Geocoding and Places APIs,
    handling address-to-coordinate lookup and category search.
    """
    
    def __init__(self, api_host: str, api_key: str):
        """
        Initializes the API client with host and key.
        """
        self.api_host = api_host
        self.api_key = api_key
        self.headers = {} 

    def _make_api_call(self, endpoint: str) -> Optional[Dict[str, Any]]:
        """Handles the connection and makes the API GET request."""
        conn = http.client.HTTPSConnection(self.api_host)
        
        # Ensure the endpoint starts with a '/'
        if not endpoint.startswith('/'):
            endpoint = '/' + endpoint
            
        print(f"\n--- Making GET request to: {self.api_host}{endpoint[:100]}... ---")
        try:
            conn.request("GET", endpoint, headers=self.headers)
            res = conn.getresponse()
            data = res.read()
            conn.close()
            
            response_json = json.loads(data.decode("utf-8"))
            
            if res.status != 200:
                print(f"❌ API Error (Status {res.status}): {response_json.get('message')}")
                return None
                
            return response_json
            
        except Exception as e:
            print(f"❌ An error occurred during API call: {e}")
            return None

    def geocode_address(self, address_text: str) -> Optional[Dict[str, Any]]:
        """
        Finds the coordinates for a given text address using
        the Forward Geocoding API (v1/geocode/search).
        
        Returns a dict with {'lat', 'lon', 'formatted'} or None.
        """
        if not self.api_key:
            print("❌ Cannot geocode: API_KEY is not set.")
            return None
        
        params = {
            'text': address_text,
            'limit': 1,       # We only want the top result
            'format': 'json',
            'apiKey': self.api_key
        }
        
        query_string = urlencode(params)
        geocode_endpoint = f"/v1/geocode/search?{query_string}"
        
        response_data = self._make_api_call(geocode_endpoint)
        
        if (response_data and 
            response_data.get('results') and 
            len(response_data['results']) > 0):
            
            first_result = response_data['results'][0]
            lat = first_result.get('lat')
            lon = first_result.get('lon')
            formatted_address = first_result.get('formatted', 'N/A')
            
            if lat and lon:
                print(f"✅ Geocoding Success: Found '{formatted_address}'")
                return {
                    'lat': lat,
                    'lon': lon,
                    'formatted': formatted_address
                }
        
        print(f"❌ Geocoding Failed: No results found for '{address_text}'.")
        return None

    def search_places_by_category(self, 
                                  categories: str, 
                                  lat: float, 
                                  lon: float, 
                                  radius: int, 
                                  limit: int) -> Optional[Dict[str, Any]]:
        """
        Searches for places (v2/places) matching a category within a circle.
        """
        if not self.api_key:
            print("❌ Cannot search places: API_KEY is not set.")
            return None
            
        # Construct the filter and bias strings
        filter_str = f"circle:{lon},{lat},{radius}"
        bias_str = f"proximity:{lon},{lat}"
        
        # Compile all parameters
        params = {
            'categories': categories,
            'filter': filter_str,
            'bias': bias_str,
            'limit': limit,
            'apiKey': self.api_key
        }
        
        # Construct the query string from the parameters
        query_string = urlencode(params)
        places_endpoint = f"/v2/places?{query_string}"

        places_data_dict = self._make_api_call(places_endpoint)
        
        if places_data_dict and places_data_dict.get('features'):
            found_count = len(places_data_dict['features'])
            print(f"✅ Places Search Success: Found **{found_count}** locations.")
            return places_data_dict
        else:
            print(f"❌ Failed to get places data or no locations found for categories: {categories}")
            return None