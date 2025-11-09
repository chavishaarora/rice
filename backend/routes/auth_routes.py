from flask import Blueprint, request, jsonify, session
from database import db, User, Profile
from werkzeug.security import generate_password_hash, check_password_hash
import uuid

# Define the blueprint
auth_bp = Blueprint('auth', __name__)

# Note: The URL prefix '/api/auth' is added in app.py
# So, this route will be POST /api/auth/signup
@auth_bp.route('/signup', methods=['POST'])
def signup():
    """User registration"""
    data = request.json
    email = data.get('email')
    password = data.get('password')
    full_name = data.get('fullName')
    
    if not email or not password:
        return jsonify({'error': 'Email and password required'}), 400
    
    # Check if user exists
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({'error': 'User already exists'}), 400
    
    # Create user
    user = User(
        id=str(uuid.uuid4()),
        email=email,
        password_hash=generate_password_hash(password)
    )
    db.session.add(user)
    
    # Create profile
    profile = Profile(
        user_id=user.id,
        email=email,
        full_name=full_name
    )
    db.session.add(profile)
    
    db.session.commit()
    
    # Log the user in immediately after signup
    session['user_id'] = user.id
    
    return jsonify({
        'message': 'User created successfully',
        'user': {
            'id': user.id,
            'email': user.email
        }
    }), 201

# This route will be POST /api/auth/login
@auth_bp.route('/login', methods=['POST'])
def login():
    """User login"""
    data = request.json
    email = data.get('email')
    password = data.get('password')
    
    user = User.query.filter_by(email=email).first()
    
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({'error': 'Invalid credentials'}), 401
    
    session['user_id'] = user.id
    
    return jsonify({
        'user': {
            'id': user.id,
            'email': user.email
        }
    })

# This route will be POST /api/auth/logout
@auth_bp.route('/logout', methods=['POST'])
def logout():
    """User logout"""
    session.pop('user_id', None)
    return jsonify({'message': 'Logged out successfully'})

# This route will be GET /api/auth/user
@auth_bp.route('/user', methods=['GET'])
def get_user():
    """Get current user from session"""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401
    
    user = db.session.get(User, user_id)
    if not user:
        # This can happen if the user was deleted but the session persists
        session.pop('user_id', None) 
        return jsonify({'error': 'User not found'}), 404
    
    return jsonify({
        'user': {
            'id': user.id,
            'email': user.email
        }
    })