from flask import Blueprint, request, jsonify
from database import db, Conversation, TravelSuggestion
from agents.iternerary_manager import ItineraryManager # Import the manager
import json

# Define a blueprint for your API endpoints
selection_bp = Blueprint('selection_api', __name__)

@selection_bp.route('/select_suggestion/<string:conversation_id>', methods=['POST'])
def select_suggestion_route(conversation_id):
    """
    POST /api/select_suggestion/<conversation_id>
    Finalizes a specific flight or hotel suggestion and deletes all other
    suggestions of the same type for the given conversation.
    
    Expected JSON body: {"suggestion_id": <string>}
    """
    data = request.get_json()
    suggestion_id = data.get('suggestion_id')
    print(suggestion_id)

    if suggestion_id is None:
        return jsonify({"status": "error", "message": "Missing 'suggestion_id' in request body."}), 400

    try:
        # 1. Fetch the conversation object
        conversation = Conversation.query.filter_by(id=conversation_id).first()
        if not conversation:
            return jsonify({"status": "error", "message": f"Conversation with ID {conversation_id} not found."}), 404

        # 2. Initialize the ItineraryManager
        manager = ItineraryManager(conversation)

        # 3. Execute the selection logic
        result = manager.select_ideal_choice(suggestion_id)

        # 4. Commit changes to the database
        db.session.commit()

        # 5. Return the result
        return jsonify(result), 200
        
    except Exception as e:
        db.session.rollback() # Rollback the session on error
        print(f"Error selecting suggestion: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"status": "error", "message": f"An unexpected error occurred: {str(e)}"}), 500