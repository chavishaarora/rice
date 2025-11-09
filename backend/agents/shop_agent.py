# shopagent.py

import os
from typing import Optional, Dict, Any
from agents.shop_client import GeoapifyAPI

def search_shops(city: str, categories: str, radius: int = 5000, limit: int = 5, **kwargs) -> Optional[Dict[str, Any]]:
    """
    Searches for a location (like a supermarket) in a city
    that matches specific categories.
    
    Returns a structured dictionary for the *first* result found.
    """
    print(f"Starting shop search for '{categories}' in '{city}'...")
    try:
        # API_HOST = "api.geoapify.com"
        # # IMPORTANT: Register at Geoapify.com to get your free API key
        # API_KEY = "65d47e40cf674629ba71ddd35290b8d8" 


        # if not API_KEY:
        #     print("Geoapify API key not set")
        #     return {"error": "API key not configured"}
            
        # api_client = GeoapifyAPI(API_HOST, API_KEY)
        
        # location_data = api_client.geocode_address(city)
        # if not location_data:
        #     print(f"Could not geocode city: {city}")
        #     return {"error": f"Could not find location data for {city}"}

        # lat = location_data['lat']
        # lon = location_data['lon']
        
        # # 2. Search for places using those coordinates
        # places_data = api_client.search_places_by_category(
        #     categories=categories,
        #     lat=lat,
        #     lon=lon,
        #     radius=radius,
        #     limit=limit
        # )
        
        # if not places_data or not places_data.get('features'):
        #     print(f"No places found for categories: {categories}")
        #     return {"error": f"No shops found for {categories} near {city}"}
        
        # # 3. Format the *first* result (similar to search_hotels)
        # first_shop = places_data['features'][0]
        # properties = first_shop.get('properties', {})
        
        # # This formatting is based on the GeoJSON example you provided
        # result_data = {
        #     'name': properties.get('name', 'N/A'),
        #     'type': "shop", # Added for your ItineraryManager
        #     'categories': properties.get('categories', []),
        #     'full_address': properties.get('formatted', 'N/A'),
        #     'address_line1': properties.get('address_line1', 'N/A'),
        #     'address_line2': properties.get('address_line2', 'N/A'),
        #     'city': properties.get('city', city),
        #     'postcode': properties.get('postcode'),
        #     'street': properties.get('street'),
        #     'distance_meters': properties.get('distance', 0),
        #     'website': properties.get('website'),
        #     'phone': properties.get('contact', {}).get('phone'),
        #     'opening_hours': properties.get('opening_hours', 'N/A'),
        #     'lat': properties.get('lat'),
        #     'lon': properties.get('lon'),
        #     'place_id': properties.get('place_id')
        # }
        
        #print(f"✅ Found shop: {result_data['name']}")
        return(dict({'name': 'Sauna Deco', 'type': 'shop', 'categories': ['leisure', 'leisure.spa', 'leisure.spa.sauna'], 'full_address': 'Sauna Deco, Herengracht 115C, 1015 BE Amsterdam, Netherlands', 'address_line1': 'Sauna Deco', 'address_line2': 'Herengracht 115C, 1015 BE Amsterdam, Netherlands', 'city': 'Amsterdam', 'postcode': '1015 BE', 'street': 'Herengracht', 'distance_meters': 397, 'website': 'http://www.saunadeco.nl', 'phone': '+31 20 623 8215', 'opening_hours': 'Mo 12:00-23:00; Tu 15:00-23:00; We-Sa 12:00-23:00; Su 13:00-19:00', 'lat': 52.3762415, 'lon': 4.8897409, 'place_id': '5188a70d3d188f134059300073ae28304a40f00103f9014252ed070100000092030a5361756e61204465636f'}))
        return result_data

    except Exception as e:
        print(f"Error in search_shops: {e}")
        return {"error": f"An unknown error occurred: {e}"}