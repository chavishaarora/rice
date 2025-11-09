from flask import Flask
from flask_cors import CORS
from flask_session import Session
from database import db
from config import Config
import os

from routes.auth_routes import auth_bp
from routes.profile_routes import profile_bp
from routes.chat_routes import chat_bp
from routes.selection_routes import selection_bp

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    CORS(app, 
         supports_credentials=True, 
         origins=[
             "http://localhost:8080",
             "http://localhost:8081",
         ]
    )
    Session(app)
    db.init_app(app)

    # Register Blueprints
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(profile_bp, url_prefix='/api/profile')
    app.register_blueprint(chat_bp, url_prefix='/api')
    app.register_blueprint(selection_bp, url_prefix='/api')

    # Create tables
    with app.app_context():
        db.create_all()

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5001)