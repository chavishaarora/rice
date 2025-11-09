from flask import Blueprint, request, jsonify, session
from database import db, User, Conversation, Message, TravelSuggestion
from agents.chat_agent import ChatService # The new "brain"
from agents.iternerary_manager import ItineraryManager
import uuid

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/travel-chat', methods=['POST'])
def travel_chat():
    """
    Handles the main chat interaction.
    Delegates all logic to the ChatService.
    """
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    data = request.json
    messages = data.get('messages', [])
    conversation_id = data.get('conversationId')

    # 1. Get conversation
    conversation = Conversation.query.get(conversation_id)
    if not conversation or conversation.user_id != user_id:
        return jsonify({'error': 'Conversation not found'}), 404
    
    # 2. Get the latest user message
    user_message_content = messages[-1]['content']

    # 3. Delegate ALL logic to the ChatService
    try:
        # Initialize the service with the current conversation state
        chat_service = ChatService(conversation)
        
        # Process the message (this handles LLM calls, tool use, and DB saving)
        assistant_response = chat_service.process_message(user_message_content)
        
        # Return the final text response to the user
        return jsonify({'response': assistant_response})

    except Exception as e:
        print(f"Error in travel_chat route: {e}")
        # Add more specific error logging here for production
        return jsonify({'error': 'An internal error occurred'}), 500

# -------------------------------------------------------------------
# MOVED FROM YOUR ORIGINAL APP.PY
# -------------------------------------------------------------------

@chat_bp.route('/conversations', methods=['POST'])
def create_conversation():
    """Create a new conversation"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    conversation = Conversation(
        user_id=user_id,
        id=str(uuid.uuid4()) # Assuming you use UUIDs as strings
    )
    db.session.add(conversation)
    db.session.commit()
    
    return jsonify({
        'id': conversation.id,
        'status': conversation.status
    })

@chat_bp.route('/suggestions/<conversation_id>', methods=['GET'])
def get_suggestions(conversation_id):
    """Get travel suggestions for a conversation"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    conversation = db.session.get(Conversation, conversation_id)
    if not conversation or conversation.user_id != user_id:
        return jsonify({'error': 'Conversation not found'}), 404
    
    suggestions = TravelSuggestion.query.filter_by(conversation_id=conversation_id).all()
    
    return jsonify({
        'suggestions': [{
            'id': s.id,
            'type': s.type,
            'title': s.title,
            'description': s.description,
            'price': float(s.price) if s.price else None,
            'rating': float(s.rating) if s.rating else None,
            'image_url': s.image_url,
            'booking_url': s.booking_url,
            'location': s.location
        } for s in suggestions]
    })


@chat_bp.route('/suggestions/<conversation_id>/itinerary-summary', methods=['GET'])
def get_itinerary(conversation_id):
    """Get travel suggestions for a conversation"""
    try:
        # 1. Load Conversation and Itinerary Manager
        conversation = Conversation.query.get(id)
        print("Hello World!")
        if not conversation:
            return jsonify({"error": "Conversation not found"}), 404
            
        itinerary_manager = ItineraryManager(conversation)
        
        summary_string = itinerary_manager.get_final_itinerary_summary()
        print(summary_string)
        
        return jsonify({"summary": summary_string}), 200
        
    except Exception as e:
        # Handle errors gracefully by returning JSON
        print(f"Error generating itinerary summary: {e}")
        return jsonify({"error": "Internal server error"}), 500