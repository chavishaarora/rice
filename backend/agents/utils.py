from datetime import datetime, timedelta, date
import urllib.parse


def normalize_date(date_str: str) -> date:
    """Normalize dates to YYYY-MM-DD format and return date object"""
    try:
        # Try to parse YYYY-MM-DD format
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        return date_obj.date()
    except:
        # Fallback to current date + 30 days
        now = datetime.now() + timedelta(days=30)
        return now.date()
   
def create_google_maps_url(place_name: str, destination: str) -> str:
    """Create Google Maps search URL"""
    query = f"{place_name} {destination}"
    # Use urllib.parse.quote_plus for correct URL encoding
    encoded_query = urllib.parse.quote_plus(query) 
    # This is the correct, modern URL format for a map search
    return f"https://www.google.com/maps/search/?api=1&query={encoded_query}"
 
def parse_recommendations_with_links(response: str, destination: str) -> str:
    """Add Google Maps links to activities in the response"""
    place_pattern = r'(?:Visit|Dine at|Explore|Try|Experience|Enjoy|Go to|See|Check out|Discover|Browse|Sample|Hike|Trek|Climb|Tour|Take|Do|Participate in|Attend|Join|Relax at|Swim at|Kayak in|Bike through|Walk to|Drive to|Sail on|Surf at|Ski on|Watch|Taste|Drink|Eat at|Have|Book|Reserve|Book a tour|Take a tour|Go on|View|Visit the|Go for|Catch|Watch the|Ride|Take a|Have a|Enjoy the|Admire|Appreciate|See the|Walk around|Stroll through|Wander in)\s+([^-\n.;,]*?)(?:\s*[-:.;,]|$|\n)'
    
    enhanced_response = response
    matches = re.finditer(place_pattern, response, re.IGNORECASE)
    processed_places = set()
    
    for match in matches:
        place_name = match.group(1).strip()
        
        if place_name and len(place_name) > 2 and place_name.lower() not in processed_places:
            place_name = place_name.split(' - ')[0].split(' (')[0].strip()
            
            if len(place_name) > 2:
                processed_places.add(place_name.lower())
                maps_url = create_google_maps_url(place_name, destination)
                original = match.group(0)
                
                if maps_url not in enhanced_response:
                    enhanced = f"{original}\n🗺️ [{place_name}]({maps_url})"
                    enhanced_response = enhanced_response.replace(original, enhanced)
    
    return enhanced_response
