# manage.py
import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from dotenv import load_dotenv
import logging

# Your existing global db instance (from models.py)
from models import db
# Your routes initialization function
import routes

load_dotenv(override=True)

# Instantiate Migrate globally
migrate = Migrate()

def create_app():
    app = Flask(__name__)

    # --- Your existing config setup ---
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    if not OPENAI_API_KEY:
        raise RuntimeError("La variable de entorno OPENAI_API_KEY no está definida.")

    app.config["OPENAI_API_KEY"] = OPENAI_API_KEY
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "postgresql://usuario:your_secure_password@localhost:5432/chatgpt_db")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # --- THIS IS WHERE ALLOWED_MODELS SHOULD BE SET ---
    app.config["ALLOWED_MODELS"] = ["chatgpt-4o-latest", "o4-mini", "gpt-4o-mini-2024-07-18"]
    # ----------------------------------------------------

    db.init_app(app)
    migrate.init_app(app, db) # Initialize Flask-Migrate with app and db

    # Configure logging for the app
    logging.basicConfig(level=logging.DEBUG)

    # Initialize your routes with the app instance
    routes.init_app(app)

    return app

if __name__ == "__main__":
    app = create_app()
    # No need for db.create_all() here if you're using Flask-Migrate
    app.run(host="0.0.0.0", port=5002, debug=True)