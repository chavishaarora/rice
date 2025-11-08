from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    conversations = db.relationship('Conversation', backref='user', lazy=True, cascade='all, delete-orphan')
    profile = db.relationship('Profile', backref='user', uselist=False, cascade='all, delete-orphan')

class Profile(db.Model):
    __tablename__ = 'profiles'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    full_name = db.Column(db.String(255))
    email = db.Column(db.String(255))
    phone = db.Column(db.String(50))
    passport_number = db.Column(db.String(50))
    date_of_birth = db.Column(db.Date)
    nationality = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Conversation(db.Model):
    __tablename__ = 'conversations'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    destination = db.Column(db.String(255))
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    budget = db.Column(db.String(100))
    travelers_count = db.Column(db.Integer)
    preferences = db.Column(db.JSON)
    status = db.Column(db.String(50), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    messages = db.relationship('Message', backref='conversation', lazy=True, cascade='all, delete-orphan')
    suggestions = db.relationship('TravelSuggestion', backref='conversation', lazy=True, cascade='all, delete-orphan')

class Message(db.Model):
    __tablename__ = 'messages'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = db.Column(db.String(36), db.ForeignKey('conversations.id'), nullable=False)
    role = db.Column(db.String(50), nullable=False)  # 'user' or 'assistant'
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class TravelSuggestion(db.Model):
    __tablename__ = 'travel_suggestions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = db.Column(db.String(36), db.ForeignKey('conversations.id'), nullable=False)
    type = db.Column(db.String(50), nullable=False)  # 'flight', 'hotel', 'attraction', 'restaurant'
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(10, 2))
    rating = db.Column(db.Numeric(3, 2))
    image_url = db.Column(db.Text)
    booking_url = db.Column(db.Text)
    location = db.Column(db.JSON)
    details = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)