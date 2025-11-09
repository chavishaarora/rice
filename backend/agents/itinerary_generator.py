import google.generativeai as genai
import os

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=GOOGLE_API_KEY)

def generate_detailed_itinerary(destination: str, arrival_date: str, departure_date: str, 
                                 activity_preferences: str = "mixed", **kwargs) -> str:
    """
    Generate a detailed day-by-day itinerary for a trip.
    
    Args:
        destination: The city/location for the trip
        arrival_date: Check-in date (YYYY-MM-DD)
        departure_date: Check-out date (YYYY-MM-DD)
        activity_preferences: Type of activities (e.g., 'relaxing', 'adventurous', 'cultural', 'mixed')
        **kwargs: Additional preferences like budget_per_day, dietary_restrictions, etc.
    
    Returns:
        A detailed day-by-day itinerary as a formatted string
    """
    from datetime import datetime, timedelta
    
    print(f"🗓️ Generating itinerary for {destination} from {arrival_date} to {departure_date}")
    
    # Calculate number of days
    start = datetime.strptime(arrival_date, "%Y-%m-%d")
    end = datetime.strptime(departure_date, "%Y-%m-%d")
    num_days = (end - start).days
    
    if num_days <= 0:
        return "Invalid dates: departure must be after arrival."
    
    # Create detailed prompt for Gemini
    system_instruction = f"""You are an expert travel planner specializing in creating detailed, 
    practical day-by-day itineraries. Create a comprehensive itinerary that:
    
    1. Balances activities with rest time
    2. Groups nearby attractions together for efficiency
    3. Includes specific timing suggestions (morning, afternoon, evening)
    4. Recommends local restaurants for meals
    5. Suggests transportation between locations
    6. Includes practical tips (what to bring, best times to visit, etc.)
    7. Considers the user's activity preferences: {activity_preferences}
    
    Format each day clearly with:
    - Day number and date
    - Morning activities (with timing)
    - Lunch recommendation
    - Afternoon activities (with timing)
    - Dinner recommendation
    - Evening activities or rest time
    - Practical tips for that day
    
    Make it engaging, practical, and realistic. Include Google Maps links for major attractions.
    """
    
    user_prompt = f"""Create a detailed {num_days}-day itinerary for {destination}.
    
    Trip Details:
    - Arrival: {arrival_date}
    - Departure: {departure_date}
    - Number of days: {num_days}
    - Activity preference: {activity_preferences}
    
    Additional preferences:
    - Budget per day: {kwargs.get('budget_per_day', 'moderate')}
    - Dietary restrictions: {kwargs.get('dietary_restrictions', 'none')}
    - Mobility considerations: {kwargs.get('mobility', 'none')}
    
    Please create a day-by-day plan that maximizes the experience while being practical and realistic.
    Include specific restaurant recommendations, attraction names, and timing suggestions.
    """
    
    try:
        # Create model for itinerary generation
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash-exp",
            system_instruction=system_instruction
        )
        
        response = model.generate_content(user_prompt)
        itinerary_text = response.text
        
        # Add Google Maps links for better UX
        itinerary_with_links = add_maps_links(itinerary_text, destination)
        
        print(f"✅ Generated {num_days}-day itinerary successfully")
        return itinerary_with_links
        
    except Exception as e:
        print(f"❌ Error generating itinerary: {e}")
        return f"Failed to generate itinerary: {str(e)}"


def add_maps_links(text: str, destination: str) -> str:
    """Add Google Maps links to locations mentioned in the itinerary"""
    import re
    from urllib.parse import quote_plus
    
    # Pattern to find location names (after common indicators)
    # This is a simple implementation - you can make it more sophisticated
    location_indicators = [
        r'Visit ([A-Z][A-Za-z\s]+)',
        r'Go to ([A-Z][A-Za-z\s]+)',
        r'Explore ([A-Z][A-Za-z\s]+)',
        r'Head to ([A-Z][A-Za-z\s]+)',
        r'Start at ([A-Z][A-Za-z\s]+)',
    ]
    
    modified_text = text
    found_locations = set()
    
    for pattern in location_indicators:
        matches = re.finditer(pattern, text)
        for match in matches:
            location = match.group(1).strip()
            # Avoid duplicates
            if location not in found_locations and len(location) > 3:
                found_locations.add(location)
                query = quote_plus(f"{location}, {destination}")
                maps_url = f"https://www.google.com/maps/search/?api=1&query={query}"
                # Add clickable link after the location mention
                replacement = f"{match.group(0)} ([View on map]({maps_url}))"
                modified_text = modified_text.replace(match.group(0), replacement, 1)
    
    return modified_text


def generate_quick_suggestions(destination: str, num_days: int, activity_type: str = "mixed") -> str:
    """Generate quick activity suggestions for a destination (lighter version)"""
    
    print(f"🎯 Generating quick suggestions for {destination} ({num_days} days)")
    
    prompt = f"""Suggest the top {min(num_days * 3, 15)} must-see attractions and experiences in {destination}.
    Focus on {activity_type} activities.
    
    Format as a simple list with:
    - Name of attraction/activity
    - Brief one-sentence description
    - Estimated time needed
    
    Make it concise and actionable."""
    
    try:
        model = genai.GenerativeModel(model_name="gemini-2.0-flash-exp")
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"❌ Error generating suggestions: {e}")
        return "Could not generate suggestions at this time."