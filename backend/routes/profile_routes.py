from flask import Blueprint, request, jsonify, session
from database import db, Profile
from datetime import datetime

profile_bp = Blueprint('profile', __name__)

@profile_bp.route('/', methods=['GET', 'PUT'])
def profile():
    """Get or update user profile"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    profile = Profile.query.filter_by(user_id=user_id).first()
    
    if request.method == 'GET':
        if not profile:
            # Return empty object or default data
            return jsonify({}) 
        
        return jsonify({
            'full_name': profile.full_name,
            'email': profile.email,
            'phone': profile.phone,
            'passport_number': profile.passport_number,
            'date_of_birth': profile.date_of_birth.isoformat() if profile.date_of_birth else None,
            'nationality': profile.nationality
        })
    
    elif request.method == 'PUT':
        data = request.json
        
        if not profile:
            # Create a new profile if one doesn't exist
            profile = Profile(user_id=user_id)
            db.session.add(profile)
        
        # Update fields from request data
        profile.full_name = data.get('full_name', profile.full_name)
        profile.email = data.get('email', profile.email)
        profile.phone = data.get('phone', profile.phone)
        profile.passport_number = data.get('passport_number', profile.passport_number)
        
        if data.get('date_of_birth'):
            try:
                # Ensure date is parsed correctly
                profile.date_of_birth = datetime.strptime(data['date_of_birth'], '%Y-%m-%d').date()
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid date_of_birth format. Use YYYY-MM-DD.'}), 400
        
        profile.nationality = data.get('nationality', profile.nationality)
        
        db.session.commit()
        
        return jsonify({'message': 'Profile updated successfully'})