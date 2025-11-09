# AI Travel Agent 🌍✈️

An intelligent travel planning assistant that helps you create personalized trip itineraries. The AI agent collects your travel preferences and generates comprehensive travel plans including flights, hotels, restaurants, museums, leisure activities, and shopping destinations.

## Features

- **Smart Trip Planning**: AI-powered agent that asks relevant questions about your trip
- **Intelligent Chatbot**: Powered by Google Gemini for natural conversation
- **Information Extraction**: Gemini AI extracts crucial travel details from conversations
- **Flight Booking**: Integration with Booking.com API for flight searches
- **Hotel Reservations**: Find and book accommodations through Booking.com API
- **Restaurant Recommendations**: Discover dining options via TripAdvisor API
- **Museum & Attractions**: Explore cultural sites using TripAdvisor API
- **Leisure & Shopping**: Find entertainment venues and shopping areas with Geoapify API

## Prerequisites

Before running this application, ensure you have the following installed:

- Python 3.8 or higher
- Node.js 16 or higher
- npm or yarn

## Installation & Setup

### Backend Setup

1. Navigate to the backend directory:
```bash
cd backend
```

2. Install Python dependencies:
```bash
pip install -r requirements.txt
```

3. Run the backend server:
```bash
python app.py
```

The backend server should now be running on `http://localhost:5000`.

### Frontend Setup

1. Navigate to the frontend directory:
```bash
cd frontend
```

2. Install Node.js dependencies:
```bash
npm install
```

3. Start the development server:
```bash
npm run dev
```

The frontend application should now be accessible at `http://localhost:8080`.

## Getting Started

1. Open your browser and navigate to `http://localhost:8080`
2. **Sign Up**: Create a new account with your email and password
3. **Log In**: Use your credentials to access the AI Travel Agent
4. Start planning your trip by chatting with the AI agent!

## How It Works

The AI Travel Agent will guide you through the trip planning process by asking about:

- **Number of travelers**: How many people are traveling?
- **Travel dates**: When do you plan to travel?
- **Destination**: Where would you like to go?
- **Origin**: Where are you traveling from?
- **Budget**: What is your budget for the trip?
- **Preferences**: Additional preferences for your trip

Based on your responses, the agent creates a comprehensive trip plan with:
- Flight options
- Hotel recommendations
- Restaurant suggestions
- Museums and cultural attractions
- Leisure activities
- Shopping destinations

## API Integrations

This project integrates with the following APIs:

- **Google Gemini API**: Powers the conversational AI chatbot and extracts crucial travel information
- **Booking.com API**: Flights and hotels
- **TripAdvisor API**: Restaurants and museums
- **Geoapify API**: Leisure activities and shopping locations

*Note: You may need to configure API keys in the backend configuration files.*

## Current Limitations

**Booking Restrictions**: Due to current API limitations, the application does not make actual reservations on behalf of users. The AI agent provides recommendations and information about flights, hotels, restaurants, and attractions, but users must complete bookings independently through the respective platforms.

*Note: The system is designed to support automated reservations, and this functionality can be easily enabled once API permissions for booking are obtained.*

---

Happy travels! 🎒✨

