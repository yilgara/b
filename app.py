from flask import Flask, jsonify
from flask_cors import CORS
from flask_migrate import Migrate
from config import Config
from models import db, bcrypt
from auth import auth_bp

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

    # Health check endpoint
    @app.route("/api/health", methods=["GET"])
    def health_check():
        return jsonify({
            "status": "healthy",
            "message": "NutriAI API is running"
        }), 200

    # Create tables (safe for dev; remove in prod if using migrations)
    with app.app_context():
        db.create_all()

    return app
    
app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
