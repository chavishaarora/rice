import os
from agents.flight_client import BookingComFlightsAPI


def search_flights(origin_city: str, destination_city: str, departure_date: str, **kwargs):
    """Search for flights using Booking.com API"""
    print(f"Starting flight search from {origin_city} to {destination_city}...")
    try:
        # NOTE: Ensure these are set in your .env file
        API_HOST = os.getenv("BOOKING_API_HOST")
        API_KEY = os.getenv("BOOKING_API_KEY")

        if not API_HOST or not API_KEY:
            print("Flight API credentials (FLIGHT_API_HOST, FLIGHT_API_KEY) not set")
            return None

        api_client = BookingComFlightsAPI(API_HOST, API_KEY)

       # origin_city = 'Amsterdam'
        # 1. Get Origin Airport ID
        if not api_client.search_airport(origin_city, is_origin=True):
            print(f"Could not find origin airport for: {origin_city}")
            return None
        
        # 2. Get Destination Airport ID
        if not api_client.search_airport(destination_city, is_origin=False):
            print(f"Could not find destination airport for: {destination_city}")
            return None

        # 3. Prepare search parameters
        flight_params = {
            'date': departure_date,
            'adults': kwargs.get('ADULTS', 1),
            'stops': 0,
            'cabinClass': 'ECONOMY',
            'sort': 'BEST',
            'currency_code': 'EUR' # Or get from user prefs
        }

        # 4. Search for flights
        flight_result = api_client.search_flights(**flight_params)
        print(f"FOUND FLIGHTS {flight_result}")
        if not flight_result or not flight_result.get('data', {}).get('flightOffers'):
            print("No flight offers found in API response.")
            return None

        # 5. Parse the first flight offer
        flight_offers = flight_result['data']['flightOffers']
        if not flight_offers:
            print("Flight offers list is empty.")
            return None
            
        first_offer = flight_offers[0]

        # Carrier (airline) data
        carriers_data = {
            c['iataCode']: c 
            for c in flight_result['data'].get('aggregation', {}).get('airlines', [])
        }

        # Price data
        price_breakdown = first_offer.get('priceBreakdown', {})
        total_price_obj = price_breakdown.get('totalRounded', {})
        total_price = total_price_obj.get('units', 0) 
        currency = total_price_obj.get('currencyCode', 'N/A')

        # Segment and Leg data
        segments = first_offer.get('segments', [{}])
        first_segment = segments[0]
        legs = first_segment.get('legs', [{}])
        first_leg = legs[0]

        # Airline info
        carrier_code = first_leg.get('flightInfo', {}).get('carrierInfo', {}).get('marketingCarrier', 'N/A')
        airline = carriers_data.get(carrier_code, {})
        airline_name = airline.get('name', 'Unknown Airline')
        airline_logo_url = airline.get('logoUrl', 'N/A')

        # Route and Times
        dep_airport = first_leg.get('departureAirport', {}).get('code', 'N/A')
        arr_airport = first_leg.get('arrivalAirport', {}).get('code', 'N/A')
        dep_time_str = first_leg.get('departureTime', 'N/A')
        arr_time_str = first_leg.get('arrivalTime', 'N/A')

        # Format for display
        title = f"Flight from {dep_airport} to {arr_airport}"
        description = f"Operated by {airline_name}. Departs: {dep_time_str}. Arrives: {arr_time_str}."
        
        # Create the most specific Booking.com flights search URL possible
        # This gets users as close to the exact flight as we can
        from urllib.parse import quote
        
        # Format the date properly (remove time if present)
        date_only = departure_date.split('T')[0] if 'T' in departure_date else departure_date
        
        # Extract carrier code for airline filter
        carrier_code = first_leg.get('flightInfo', {}).get('carrierInfo', {}).get('marketingCarrier', '')
        
        # Build URL with maximum relevant parameters to pre-filter results
        booking_url = (
            f"https://www.booking.com/flights/"
            f"?type=ONEWAY"
            f"&adults={flight_params['adults']}"
            f"&cabinClass={flight_params['cabinClass']}"
            f"&from={quote(dep_airport)}"
            f"&to={quote(arr_airport)}"
            f"&depart={date_only}"
            f"&sort={flight_params['sort']}"
        )
        
        # Add airline filter if available to narrow results
        if carrier_code:
            booking_url += f"&airlines={carrier_code}"

        return {
            'type': 'flight',
            'title': title,
            'description': description,
            'price': total_price,
            'currency': currency,
            'image_url': airline_logo_url,
            'booking_url': booking_url,
            'airline_name': airline_name,
            'departure_time': dep_time_str,
            'arrival_time': arr_time_str,
            'origin_code': dep_airport,
            'destination_code': arr_airport
        }

    except Exception as e:
        print(f"Error in search_flights: {e}")
        return None