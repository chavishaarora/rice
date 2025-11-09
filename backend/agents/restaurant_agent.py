import os
from agents.restaurant_client import TripAdvisorAPI

def search_restaurants(city: str, **kwargs):
    """Search for restaurants using TripAdvisor API"""
    print(f"Starting restaurant search for {city}...")
    try:
        API_HOST = os.getenv("TRIPADVISOR_API_HOST")
        API_KEY = os.getenv("TRIPADVISOR_API_KEY")
        
        if not API_HOST or not API_KEY:
            print("TripAdvisor API credentials not set")
            return None
        
        # Start with base parameters
        params = {
            'CITY_QUERY': city
        }
        
        # Add any additional parameters from kwargs
        params.update(kwargs)

        api_client = TripAdvisorAPI(API_HOST, API_KEY, **params)
        
        # Search location
        if not api_client.search_location():
            return None
        
        # Search restaurants
        restaurant_result = api_client.search_restaurants()
        if not restaurant_result or not restaurant_result.get('data', {}).get('data'):
            return None
        
        first_restaurant = restaurant_result['data']['data'][0]
        restaurant_id = first_restaurant.get('restaurantsId', '')  # Keep the full ID
        
        fallback_url = first_restaurant.get('restaurantsDetailsURL', f"https://www.tripadvisor.com/Search?q={city}")
        
        result_data = {
            'destination': api_client.LOCATION_NAME,
            'restaurant_name': first_restaurant.get('name', 'N/A'),
            'restaurant_description': first_restaurant.get('description', 'N/A'),
            'restaurant_id': restaurant_id,
            'restaurant_photo_url': [],
            'rating': first_restaurant.get('averageRating', 0),
            'tripadvisor_url': fallback_url
        }
        
        # Extract price level
        result_data['price_level'] = first_restaurant.get('priceTag', 'N/A')
        
        # Extract cuisine types
        cuisine_tags = first_restaurant.get('establishmentTypeAndCuisineTags', [])
        result_data['cuisine'] = cuisine_tags
        
        # Use cuisine tags as description if no description exists
        if result_data['restaurant_description'] == 'N/A' and cuisine_tags:
            result_data['restaurant_description'] = ', '.join(cuisine_tags)
        
        # Get hero image
        hero_img = first_restaurant.get('heroImgUrl')
        if hero_img:
            result_data['restaurant_photo_url'].append(hero_img)
        
        # ✅ SKIP get_restaurant_details - it's not working reliably
        # The API returns enough data from the search results already
        # If you want to try details later, use the FULL restaurantsId string
        
        return result_data
        
    except Exception as e:
        print(f"Error in search_restaurants: {e}")
        return None


