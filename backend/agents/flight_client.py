#FlightSearch.py
import http.client
import json
from typing import Optional, Dict, Any, List
from urllib.parse import urlencode, urlparse, parse_qs

# --- User-Defined Parameters ---
API_HOST = "booking-com15.p.rapidapi.com"
API_KEY = "a4635f20famshde916da8e358adbp1ad22ejsn6e8d49abb4b1"

# --- Flight Search Configuration ---
ORIGIN_QUERY = "Mumbai" # e.g., "New York", "London"
DESTINATION_QUERY = "New Delhi" # e.g., "Paris", "Tokyo"

# 2. Flight Search Parameters
# Note: The API call needs the Airport IDs (e.g., BOM.AIRPORT, DEL.AIRPORT) 
# which will be dynamically obtained from the search_airport() method.
FLIGHT_DEPARTURE_DATE = "2025-12-01" # YYYY-MM-DD
STOPS = "none"                       # Options: "none", "one", "two", "all"
PAGE_NO = 1                          # For pagination
ADULTS = 1                           # Number of adults
CHILDREN_AGES = "0,17"               # Comma-separated ages, e.g., "0,17" (Infant, Child)
SORT_BY = "BEST"                     # Options: "BEST", "CHEAPEST", "DURATION"
CABIN_CLASS = "ECONOMY"              # Options: "ECONOMY", "PREMIUM_ECONOMY", "BUSINESS", "FIRST"
CURRENCY_CODE = "EUR"                # Currency code for prices

class BookingComFlightsAPI:
    """
    A class to interact with the Booking.com RapidAPI Flights endpoint,
    handling destination search and flight options retrieval with fallback to nearest airports.
    """
    
    def __init__(self, api_host: str, api_key: str):
        """
        Initializes the API client with host and key.
        """
        self.API_HOST = api_host
        self.HEADERS = {
            'x-rapidapi-key': api_key,
            'x-rapidapi-host': api_host
        }
        
        # Variables set dynamically
        self.ORIGIN_ID = ""
        self.DESTINATION_ID = ""

    def _make_api_call(self, method: str, endpoint: str) -> Optional[Dict[str, Any]]:
        """Handles the connection and makes the API request."""
        conn = http.client.HTTPSConnection(self.API_HOST)
        print(f"\n--- Making {method} request to: {endpoint} ---")
        try:
            conn.request(method, endpoint, headers=self.HEADERS)
            res = conn.getresponse()
            data = res.read()
            conn.close()
            
            return json.loads(data.decode("utf-8"))
            
        except Exception as e:
            # This is where your previous error occurred! 
            # It should now be fixed by the encoding below.
            print(f"❌ An error occurred during API call: {e}")
            return None
            
        except Exception as e:
            print(f"❌ An error occurred during API call: {e}")
            return None

    def _extract_country_or_region(self, query: str) -> Optional[str]:
        """
        Extracts country or region from a query string.
        For example: 'Cabanes' -> 'Spain', 'Valencia' -> 'Valencia'
        This is a simple heuristic - you can make it more sophisticated.
        """
        # Common patterns to try
        country_patterns = [
            query,  # Try the query itself first
            # You could add common city -> country mappings here
        ]
        return None

    def search_airport(self, query: str, is_origin: bool, max_retries: int = 5) -> bool:
        """
        Finds the airport ID based on the city/airport query.
        If no airport is found, tries broader searches in the region.
        
        Args:
            query: The city/location to search for
            is_origin: Whether this is the origin or destination
            max_retries: Maximum number of retry attempts with broader searches
        
        Returns:
            bool: True if an airport was found, False otherwise
        """
        search_type = "Origin" if is_origin else "Destination"
        
        # Try 1: Direct search with the exact query
        print(f"\n🔍 Attempting {search_type} search for: '{query}'")
        if self._try_airport_search(query, is_origin, search_type):
            return True
        
        # Try 2: If the query has multiple words, try the last word (often the country)
        query_parts = query.split(',')
        if len(query_parts) > 1:
            # Try searching for each part, starting from the end (most general)
            for i in range(len(query_parts) - 1, -1, -1):
                broader_query = query_parts[i].strip()
                print(f"\n🔍 Trying broader search with: '{broader_query}'")
                if self._try_airport_search(broader_query, is_origin, search_type):
                    return True
        
        # Try 3: Common regional capitals/major cities based on the query
        fallback_searches = self._get_fallback_cities(query)
        for fallback_city in fallback_searches:
            print(f"\n🔍 Trying fallback city: '{fallback_city}'")
            if self._try_airport_search(fallback_city, is_origin, search_type):
                return True
        
        print(f"\n❌ Could not find any airport for {search_type} after {max_retries} attempts")
        return False

    def _try_airport_search(self, query: str, is_origin: bool, search_type: str) -> bool:
        """
        Attempts a single airport search with the given query.
        
        Returns:
            bool: True if an airport was found, False otherwise
        """
        params = {'query': query}
        encoded_params = urlencode(params)
        airport_endpoint = f"/api/v1/flights/searchDestination?{encoded_params}"
        
        airport_data_dict = self._make_api_call("GET", airport_endpoint)
        
        # Retry the same query a few times in case of transient failures
        idx = 0
        while not airport_data_dict.get('data') and idx < 3:
            idx += 1
            print(f"   ⏳ Retry {idx}/3 for query: '{query}'")
            airport_data_dict = self._make_api_call("GET", airport_endpoint)

        if airport_data_dict and airport_data_dict.get('data'):
            airport_results = airport_data_dict['data']
            
            # Try to find an AIRPORT type first
            airport_result = next((item for item in airport_results if item.get('type') == 'AIRPORT'), None)
            
            # If no AIRPORT, try CITY (some cities can be used as flight destinations)
            if not airport_result:
                airport_result = next((item for item in airport_results if item.get('type') == 'CITY'), None)
            
            if airport_result:
                airport_id = airport_result.get('id')
                airport_name = airport_result.get('name')
                airport_type = airport_result.get('type')
                
                if is_origin:
                    self.ORIGIN_ID = airport_id
                else:
                    self.DESTINATION_ID = airport_id
                
                print(f"✅ {search_type} Search Success: Using **{airport_name}** ({airport_type})")
                print(f"   -> ID: {airport_id}")
                return True
            else:
                print(f"   ⚠️ No usable results (AIRPORT or CITY) found for '{query}'")
        else:
            print(f"   ⚠️ No data returned for query: '{query}'")
        
        return False

    def _get_fallback_cities(self, original_query: str) -> List[str]:
        """
        Returns a list of fallback cities to try based on the original query.
        This is a heuristic approach - you can expand this dictionary.
        
        Args:
            original_query: The original search query that failed
            
        Returns:
            List of alternative city names to try
        """
        # Convert query to lowercase for matching
        query_lower = original_query.lower()
        
        # Dictionary of common small cities/towns and their nearest major airports
        fallback_mapping = {
            # Spain
            'cabanes': ['Valencia', 'Castellon', 'Barcelona', 'Alicante', 'Spain'],
            'castellon': ['Valencia', 'Barcelona', 'Alicante', 'Spain'],
            'benicassim': ['Valencia', 'Castellon', 'Barcelona', 'Spain'],
            
            # France
            'nice suburbs': ['Nice', 'France'],
            'cannes': ['Nice', 'Marseille', 'France'],
            
            # Italy
            'tuscany': ['Florence', 'Pisa', 'Rome', 'Italy'],
            'cinque terre': ['Genoa', 'Pisa', 'Milan', 'Italy'],
            
            # Add more mappings as needed
        }
        
        # Check if the query matches any known small cities
        for small_city, major_cities in fallback_mapping.items():
            if small_city in query_lower:
                return major_cities
        
        # If no specific mapping found, try some generic fallbacks
        # Based on common patterns (e.g., if query ends with country name)
        generic_fallbacks = []
        
        # If the query contains 'spain', try major Spanish cities
        if 'spain' in query_lower or 'españa' in query_lower:
            generic_fallbacks = ['Valencia', 'Barcelona', 'Madrid', 'Alicante', 'Spain']
        elif 'france' in query_lower:
            generic_fallbacks = ['Paris', 'Nice', 'Lyon', 'Marseille', 'France']
        elif 'italy' in query_lower:
            generic_fallbacks = ['Rome', 'Milan', 'Venice', 'Florence', 'Italy']
        elif 'poland' in query_lower:
            generic_fallbacks = ['Warsaw', 'Krakow', 'Gdansk', 'Poland']
        
        return generic_fallbacks

    def search_flights(self, **kwargs) -> Optional[Dict[str, Any]]:
        """Searches for flight options based on configured parameters."""
        if not self.ORIGIN_ID or not self.DESTINATION_ID:
            print("❌ Cannot search flights: Origin ID or Destination ID is missing.")
            return None
            
        # Compile all parameters, using self. properties as fallbacks
        params = {
            'fromId': self.ORIGIN_ID,
            'toId': self.DESTINATION_ID,
            'stops': kwargs.get('stops', STOPS),
            'pageNo': kwargs.get('pageNo', PAGE_NO),
            'adults': kwargs.get('adults', ADULTS),
            'children': kwargs.get('children', CHILDREN_AGES),
            'sort': kwargs.get('sort', SORT_BY),
            'cabinClass': kwargs.get('cabinClass', CABIN_CLASS),
            'currency_code': kwargs.get('currency_code', CURRENCY_CODE),
            'departDate': kwargs.get('date', FLIGHT_DEPARTURE_DATE),
        }
        
        # Construct the query string from the parameters
        query_string = urlencode(params)
        flight_endpoint = f"/api/v1/flights/searchFlights?{query_string}"

        flight_data_dict = self._make_api_call("GET", flight_endpoint)
        
        idx = 0
        while not flight_data_dict.get('data') and idx < 3:
            idx += 1
            flight_data_dict = self._make_api_call("GET", flight_endpoint)

        if flight_data_dict and flight_data_dict['data'].get('flightOffers'):
            total_count = flight_data_dict['data'].get('aggregation', {}).get('totalCount', 0)
            print(f"✅ Flight Search Success: Found **{total_count}** flight offers.")
            return flight_data_dict
        else:
            print("❌ Failed to get flight search data or no flights found.")
            return None


def display_flight_offers(response_data: Optional[Dict[str, Any]]):
    """
    Parses and prints the returned flight offers in a readable format,
    handling the 'data' key nesting.
    """
    if not response_data or not response_data.get('data'):
        print("\n--- No Flight Data or 'data' Key Missing in Response ---")
        return

    flight_data = response_data['data']

    # Safely get flight offers and carrier data
    flight_offers: List[Dict[str, Any]] = flight_data.get('flightOffers', [])
    carriers_data = {
        c['iataCode']: c 
        for c in flight_data.get('aggregation', {}).get('airlines', []) # Carriers are within 'aggregation'
    }

    if not flight_offers:
        print("\n⚠️ Found the data structure, but no flight offers were listed.")
        return

    print(f"\n--- Displaying Top {len(flight_offers)} Flight Offers ---")
    
    # Iterate through the returned flight offers
    for i, offer in enumerate(flight_offers[:5]): # Limiting to 5 offers for brevity
        
        # Offers can contain multiple segments (outbound, return, etc. for round trip)
        segments = offer.get('segments', [{}])
        
        # --- Extract Price Info (usually the easiest) ---
        price_breakdown = offer.get('priceBreakdown', {})
        total_price_obj = price_breakdown.get('totalRounded', {})
        # Note: The 'totalRounded' structure contains the price we want
        total_price = f"{total_price_obj.get('units', 'N/A')}.{str(total_price_obj.get('nanos', 0)).zfill(9)}"
        currency = total_price_obj.get('currencyCode', 'N/A')
        
        print(f"\n--- Offer {i+1} ---")
        print(f"**Price:** {total_price} {currency}")
        print(f"**Trip Type:** {offer.get('tripType', 'N/A')}")
        print(f"**Token:** {offer.get('token', 'N/A')}")
        print("-" * 20)

        # --- Iterate through Segments (Outbound and Return) ---
        for j, segment in enumerate(segments):
            
            # Use 'Outbound' or 'Return' for label
            segment_label = "OUTBOUND" if j == 0 else "RETURN" if len(segments) > 1 else "ONE-WAY"
            
            # Segments contain one or more 'legs' (flights between stops)
            legs = segment.get('legs', [{}])
            
            # --- Get details from the first leg (the first flight) ---
            first_leg = legs[0]
            
            # Extract carrier info
            carrier_code = first_leg.get('flightInfo', {}).get('carrierInfo', {}).get('marketingCarrier', 'N/A')
            
            # Use the lookup table created from the 'aggregation' section
            airline_name = carriers_data.get(carrier_code, {}).get('name', 'Unknown Airline')
            
            # Extract route and times
            dep_airport = first_leg.get('departureAirport', {}).get('code', '???')
            arr_airport = first_leg.get('arrivalAirport', {}).get('code', '???')
            dep_time = first_leg.get('departureTime', 'N/A')[11:16] 
            arr_time = first_leg.get('arrivalTime', 'N/A')[11:16] 
            
            print(f"  **{segment_label} Segment:** ({len(legs)} Leg{'s' if len(legs) > 1 else ''})")
            print(f"  Airline: {airline_name} ({carrier_code})")
            print(f"  Route: **{dep_airport}** ({dep_time}) -> **{arr_airport}** ({arr_time})")
            print(f"  Flight No: {first_leg.get('flightInfo', {}).get('flightNumber', 'N/A')}")
            print(f"  Stops: {len(legs) - 1}") # Stops is one less than the number of legs
            print("  ---")

if __name__ == "__main__":
    
    # 1. Initialize the API client
    flight_api = BookingComFlightsAPI(API_HOST, API_KEY)
    
    # 2. Get Origin Airport ID (e.g., Mumbai -> BOM.AIRPORT)
    origin_success = flight_api.search_airport(ORIGIN_QUERY, is_origin=True)
    
    # 3. Get Destination Airport ID (e.g., New Delhi -> DEL.AIRPORT)
    destination_success = flight_api.search_airport(DESTINATION_QUERY, is_origin=False)

    print("\n" + "="*50)
    
    if origin_success and destination_success:
        # 4. Search for flights using the obtained IDs and desired parameters
        flight_options = flight_api.search_flights(date=FLIGHT_DEPARTURE_DATE)
        
        # 5. Display the results
        display_flight_offers(flight_options)
    else:
        print("\n⚠️ Flight search aborted due to failure in finding required airport IDs.")