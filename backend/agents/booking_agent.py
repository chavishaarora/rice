import os
import time
from typing import Dict, List, Optional, Any

def search_hotels(city: str, arrival: str, departure: str, price_max: int, **kwargs):
    """
    Enhanced hotel search using Booking.com API with multi-page search and ranking.
    
    Searches through multiple pages (up to 100 hotels) to find the best value hotels
    within the specified budget. Returns top 3 hotels.
    """
    print(f"🏨 Starting comprehensive hotel search for {city}...")
    print(f"   Budget: up to {price_max} EUR")
    print(f"   Dates: {arrival} to {departure}")
    
    try:
        # Import the enhanced BookingComAPI
        from agents.booking_client import BookingComAPI
        
        API_HOST = os.getenv("BOOKING_API_HOST", "booking-com15.p.rapidapi.com")
        API_KEY = os.getenv("BOOKING_API_KEY")
        
        if not API_HOST or not API_KEY:
            print("❌ Booking API credentials not set")
            return None
        
        # Prepare parameters
        params = {
            'CITY_QUERY': city,
            'ARRIVAL_DATE': arrival,
            'DEPARTURE_DATE': departure,
            'PRICE_MAX': price_max,
            'ADULTS': kwargs.get('ADULTS', 2),
            'PRICE_MIN': kwargs.get('PRICE_MIN', 0)
        }
        
        # Add any additional parameters
        params.update(kwargs)
        
        api_client = BookingComAPI(API_HOST, API_KEY, **params)
        
        # Step 1: Search destination
        if not api_client.search_destination():
            print(f"❌ Could not find destination: {city}")
            return None
        
        # Step 2: Get filter data to see total available hotels (optional)
        filter_data = api_client.get_filters()
        if filter_data:
            total_available = filter_data.get('data', {}).get('pagination', {}).get('nbResultsTotal', 'Unknown')
            print(f"📊 Total hotels available in {city}: {total_available}")
        
        # Step 3: Search multiple pages to get a comprehensive list
        print("\n🔍 Searching multiple pages for the best deals...")
        all_hotels = api_client.search_multiple_pages(max_pages=5, target_hotels=100)
        
        if not all_hotels:
            print(f"❌ No hotels found in {city}")
            return None
        
        print(f"\n✅ Collected {len(all_hotels)} hotels for analysis")
        
        # Step 4: Filter, analyze and rank hotels
        filtered_hotels = filter_and_rank_hotels(all_hotels, price_max)
        
        if not filtered_hotels:
            print(f"❌ No hotels found within budget of {price_max} EUR")
            # Try with a slightly higher budget
            print(f"💡 Trying with 20% higher budget...")
            filtered_hotels = filter_and_rank_hotels(all_hotels, int(price_max * 1.2))
            
            if not filtered_hotels:
                return None
        
        print(f"\n🎯 Found {len(filtered_hotels)} hotels within budget")
        
        # Step 5: Select the TOP 3 hotels based on value score
        top_hotels = select_top_hotels(filtered_hotels, api_client, top_n=3)
        
        if not top_hotels:
            return None
        
        return top_hotels
        
    except Exception as e:
        print(f"❌ Error in search_hotels: {e}")
        import traceback
        traceback.print_exc()
        return None


def filter_and_rank_hotels(hotels: List[Dict], price_max: int) -> List[Dict]:
    """
    Filter hotels by budget and rank them by value score.
    
    Value score is calculated based on:
    - Rating (review score)
    - Price (lower is better)
    - Amenities and features
    """
    filtered = []
    
    for hotel in hotels:
        try:
            # Extract price information
            price_breakdown = hotel.get('property', {}).get('priceBreakdown', {}).get('grossPrice', {})
            price = price_breakdown.get('value', 0)
            currency = price_breakdown.get('currency', 'EUR')
            
            # Skip hotels without price or exceeding budget
            if price == 0 or price > price_max:
                continue
            
            # Extract rating
            rating = hotel.get('property', {}).get('reviewScore', 0)
            review_count = hotel.get('property', {}).get('reviewCount', 0)
            
            # Extract other features
            property_data = hotel.get('property', {})
            has_free_wifi = 'free wifi' in property_data.get('accessibilityLabel', '').lower()
            has_breakfast = 'breakfast' in property_data.get('accessibilityLabel', '').lower()
            
            # Calculate value score
            # Higher rating is better (weight: 40%)
            rating_score = (rating / 10) * 40 if rating > 0 else 0
            
            # Lower price is better (weight: 30%)
            price_score = (1 - (price / price_max)) * 30 if price_max > 0 else 0
            
            # More reviews indicate reliability (weight: 20%)
            review_score = min(review_count / 100, 1) * 20
            
            # Amenities bonus (weight: 10%)
            amenities_score = 0
            if has_free_wifi:
                amenities_score += 5
            if has_breakfast:
                amenities_score += 5
            
            total_value_score = rating_score + price_score + review_score + amenities_score
            
            filtered.append({
                'hotel': hotel,
                'price': price,
                'currency': currency,
                'rating': rating,
                'review_count': review_count,
                'value_score': total_value_score,
                'has_wifi': has_free_wifi,
                'has_breakfast': has_breakfast
            })
            
        except Exception as e:
            print(f"   Warning: Error processing hotel: {e}")
            continue
    
    # Sort by value score (best value first)
    filtered.sort(key=lambda x: x['value_score'], reverse=True)
    
    return filtered


def select_top_hotels(ranked_hotels: List[Dict], api_client: Any, top_n: int = 3) -> List[Dict]:
    """
    Select the top N hotels and get their detailed information.
    Returns a list of hotel data dictionaries.
    """
    # Show top candidates
    print(f"\n🏆 Top {min(top_n, len(ranked_hotels))} Best Value Hotels:")
    
    results = []
    
    # Process top N hotels
    for i, hotel_data in enumerate(ranked_hotels[:top_n], 1):
        hotel = hotel_data['hotel']
        hotel_id = hotel['hotel_id']
        
        print(f"\n{i}. {hotel['property']['name']}")
        print(f"   💰 Price: {hotel_data['price']} {hotel_data['currency']}")
        print(f"   ⭐ Rating: {hotel_data['rating']}/10 ({hotel_data['review_count']} reviews)")
        print(f"   📊 Value Score: {hotel_data['value_score']:.1f}/100")
        if hotel_data['has_wifi']:
            print(f"   📶 Free WiFi")
        if hotel_data['has_breakfast']:
            print(f"   🍳 Breakfast included")
        
        # Prepare the result
        fallback_url = hotel['property'].get('url', f"https://www.booking.com/searchresults.html")
        
        result_data = {
            'destination': api_client.DESTINATION,
            'hotel_name': hotel.get('property', {}).get('name', 'N/A'),
            'hotel_description': hotel.get('accessibilityLabel', 'N/A'),
            'booking_hotel_id': hotel_id,
            'hotel_photo_url': hotel.get('property', {}).get('photoUrls', []),
            'rating': hotel_data['rating'],
            'review_count': hotel_data['review_count'],
            'room_photo_url': 'N/A',
            'booking_url': fallback_url,
            'price': hotel_data['price'],
            'currency': hotel_data['currency'],
            'value_score': hotel_data['value_score'],
            'has_wifi': hotel_data['has_wifi'],
            'has_breakfast': hotel_data['has_breakfast']
        }
        
        # Try to get detailed information for better URL and room photos
        print(f"   🔍 Fetching detailed information...")
        try:
            details_result = api_client.get_hotel_details(hotel_id)
            if details_result and details_result.get('data'):
                # Get specific booking URL
                specific_url = details_result['data'].get('url')
                if specific_url:
                    result_data['booking_url'] = specific_url
                
                # Get room photos
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
                        print(f"      Note: Could not extract room photos: {e}")
        except Exception as e:
            print(f"      Note: Could not get detailed information: {e}")
        
        results.append(result_data)
        
        # Small delay between detail requests to be respectful to the API
        if i < top_n:
            time.sleep(0.3)
    
    print(f"\n✅ Successfully prepared {len(results)} hotels")
    return results


def search_hotels_with_retry(city: str, arrival: str, departure: str, 
                            price_max: int, **kwargs) -> Optional[List[Dict]]:
    """
    Search hotels with automatic retry on different price points if needed.
    Returns a list of top 3 hotels.
    """
    # Try with original budget
    result = search_hotels(city, arrival, departure, price_max, **kwargs)
    
    if result:
        return result
    
    # If no results, try with adjusted parameters
    print(f"\n🔄 No results found with max price {price_max}. Trying alternative search strategies...")
    
    # Strategy 1: Try with 25% higher budget
    higher_budget = int(price_max * 1.25)
    print(f"   Trying with higher budget: {higher_budget} EUR")
    result = search_hotels(city, arrival, departure, higher_budget, **kwargs)
    
    if result:
        print(f"   ⚠️ Note: Found hotels slightly above original budget")
        return result
    
    return None