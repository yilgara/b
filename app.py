from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from flask_migrate import Migrate
from config import Config
from models import db, bcrypt
from auth import auth_bp
from profile import profile_bp
from nutrition_ai import nutrition_ai_bp
from meals import meals_bp
from video_recipe import video_recipe_bp
from recipes import recipes_bp
from food_analysis import food_analysis_bp
from chat import chat_bp
from community import community_bp
import os

UPLOAD_DIR = os.environ.get('UPLOAD_DIR', 'uploads')
PROFILE_PICTURES_DIR = os.path.join(UPLOAD_DIR, 'profile_pictures')
POST_IMAGES_DIR = os.path.join(UPLOAD_DIR, 'post_images')

# Ensure directories exist
os.makedirs(PROFILE_PICTURES_DIR, exist_ok=True)
os.makedirs(POST_IMAGES_DIR, exist_ok=True)


def create_app():
    app = Flask(__name__)

    # Load config
    app.config.from_object(Config)

    # Initialize extensions
    db.init_app(app)
    bcrypt.init_app(app)
    Migrate(app, db)

    # Setup CORS
    CORS(
        app,
        origins=Config.CORS_ORIGINS,   # MUST be a list
        supports_credentials=True,
        allow_headers=["Content-Type", "Authorization"],
        methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    )

    # Register blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(nutrition_ai_bp)
    app.register_blueprint(meals_bp)
    app.register_blueprint(video_recipe_bp)
    app.register_blueprint(recipes_bp)
    app.register_blueprint(food_analysis_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(community_bp)


    # Health check endpoint
    @app.route("/api/health", methods=["GET"])
    def health_check():
        return jsonify({
            "status": "healthy",
            "message": "NutriAI API is running"
        }), 200

    @app.route('/uploads/profile_pictures/<filename>')
    def serve_profile_picture(filename):
        return send_from_directory(PROFILE_PICTURES_DIR, filename)
    
    @app.route('/uploads/post_images/<filename>')
    def serve_post_image(filename):
        return send_from_directory(POST_IMAGES_DIR, filename)
    

    # Create tables (safe for dev; remove in prod if using migrations)
 
   

    return app
    
app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
