import os
from agents.booking_client import BookingComAPI

def search_hotels(city: str, arrival: str, departure: str, price_max: int, **kwargs):
    """Search for hotels using Booking.com API"""
    print(f"Starting hotel search for {city}...")
    try:
        API_HOST = os.getenv("BOOKING_API_HOST")
        API_KEY = os.getenv("BOOKING_API_KEY")
        
        if not API_HOST or not API_KEY:
            print("Booking API credentials not set")
            return None
        
        # Start with base parameters
        params = {
            'CITY_QUERY': city,
            'ARRIVAL_DATE': arrival,
            'DEPARTURE_DATE': departure,
            'PRICE_MAX': price_max
        }
        
        # This will add 'ADULTS', 'PRICE_MIN', etc., if they exist in kwargs
        params.update(kwargs)

        api_client = BookingComAPI(API_HOST, API_KEY, **params)
        
        # Search destination
        if not api_client.search_destination():
            return None
        
        # Get filters (optional)
        api_client.get_filters()
        
        # Search hotels
        hotel_result = api_client.search_hotels()
        if not hotel_result or not hotel_result.get('data', {}).get('hotels'):
            return None
        
        first_hotel = hotel_result['data']['hotels'][0]
        hotel_id = first_hotel['hotel_id']
        
        fallback_url = first_hotel['property'].get('url', f"https://www.booking.com/searchresults.html?ss={city}")
        
        result_data = {
            'destination': api_client.DESTINATION,
            'hotel_name': first_hotel.get('property', {}).get('name', 'N/A'),
            'hotel_description': first_hotel.get('accessibilityLabel', 'N/A'),
            'booking_hotel_id': hotel_id,
            'hotel_photo_url': first_hotel.get('property', {}).get('photoUrls', []),
            'rating': first_hotel.get('property', {}).get('reviewScore', 0),
            'room_photo_url': 'N/A',
            'booking_url': fallback_url # Use the good fallback URL
        }
        
        # Extract price
        price_breakdown = first_hotel.get('property', {}).get('priceBreakdown', {}).get('grossPrice', {})
        result_data['price'] = price_breakdown.get('value', 0)
        result_data['currency'] = price_breakdown.get('currency', 'N/A')
        
        # Get room details to find a *better* URL and room photo
        details_result = api_client.get_hotel_details(hotel_id)
        if details_result and details_result.get('data'):
            
            specific_url = details_result['data'].get('url')
            if specific_url:
                result_data['booking_url'] = specific_url # Overwrite fallback
            
            rooms = details_result['data'].get('rooms', {})
            if rooms:
                try:
                    first_room_id = list(rooms.keys())[0]
                    first_room = rooms[first_room_id]
                    photos = first_room.get('photos', [])
                    for photo in photos:
                        if photo.get('url_max1280'):
                            result_data['room_photo_url'] = photo['url_max1280']
                            break
                except Exception as e:
                    print(f"Error parsing room photos: {e}")
        
        return result_data
        
    except Exception as e:
        print(f"Error in search_hotels: {e}")
        return None