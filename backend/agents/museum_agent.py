import os
from agents.museum_client import TripAdvisorMuseumAPI

def search_museums(city: str, **kwargs):
    """Search for museums using TripAdvisor API"""
    print(f"Starting museum search for {city}...")
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

        api_client = TripAdvisorMuseumAPI(API_HOST, API_KEY, **params)
        
        # Search location
        if not api_client.search_location():
            return None
        
        # Search museums
        museum_result = api_client.search_museums()
        if not museum_result or not museum_result.get('data', {}).get('data'):
            return None
        
        first_museum = museum_result['data']['data'][0]
        museum_id = first_museum.get('locationId', '')
        
        fallback_url = first_museum.get('detailsURL', f"https://www.tripadvisor.com/Search?q={city}+museums")
        
        result_data = {
            'destination': api_client.LOCATION_NAME,
            'museum_name': first_museum.get('name', 'N/A'),
            'museum_description': first_museum.get('description', 'N/A'),
            'museum_id': museum_id,
            'museum_photo_url': [],
            'rating': first_museum.get('rating', 0),
            'tripadvisor_url': fallback_url
        }
        
        # Extract price level if available
        result_data['price_level'] = first_museum.get('priceLevel', 'N/A')
        
        # Extract category/subcategory
        subcategory = first_museum.get('subcategory', [])
        if subcategory:
            result_data['museum_type'] = subcategory[0].get('name', 'Museum')
        else:
            result_data['museum_type'] = 'Museum'
        
        # Use subcategory as description if no description exists
        if result_data['museum_description'] == 'N/A' and subcategory:
            result_data['museum_description'] = ', '.join([cat.get('name', '') for cat in subcategory])
        
        # Get hero image
        hero_img = first_museum.get('heroImage')
        if hero_img:
            result_data['museum_photo_url'].append(hero_img)
        
        # Get additional photos if available
        photos = first_museum.get('cardPhotos', [])
        for photo in photos[:3]:  # Get up to 3 additional photos
            if photo.get('sizes', {}).get('urlTemplate'):
                photo_url = photo['sizes']['urlTemplate'].replace('{width}', '1000').replace('{height}', '667')
                result_data['museum_photo_url'].append(photo_url)
        
        # Get opening hours if available
        hours = first_museum.get('hours', {})
        if hours:
            result_data['opening_hours'] = hours.get('weekdayText', 'N/A')
        
        # Get address
        address_obj = first_museum.get('address', {})
        if address_obj:
            result_data['address'] = address_obj.get('address', 'N/A')
        
        return result_data
        
    except Exception as e:
        print(f"Error in search_museums: {e}")
        return None