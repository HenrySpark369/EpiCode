# manage.py
import os
import click
import logging
from functools import wraps # Only needed if you have custom decorators here, otherwise can remove

from flask import Flask, abort # abort might not be used here anymore, can remove if so
from flask.cli import with_appcontext
from flask_sqlalchemy import SQLAlchemy # This import can be removed, as db is imported from models
from flask_migrate import Migrate
from dotenv import load_dotenv
from flask_login import LoginManager, current_user
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView

from models import db, User # Keep this for database interaction and User model
import routes # Keep this to initialize your main application routes
from auth import auth_bp # **Keep this to register your authentication blueprint**

load_dotenv(override=True)

migrate = Migrate()
login_manager = LoginManager()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@click.command("init-admin")
@with_appcontext
def init_admin_env():
    """
    Crea o actualiza el usuario administrador
    usando ADMIN_USERNAME y ADMIN_PASSWORD de .env
    """
    username = os.getenv("ADMIN_USERNAME")
    password = os.getenv("ADMIN_PASSWORD")
    email = os.getenv("ADMIN_EMAIL")

    if not username or not password or not email:
        click.echo("ERROR: define ADMIN_USERNAME, ADMIN_PASSWORD Y ADMIN_EMAIL en .env", err=True)
        raise click.Abort()

    user = User.query.filter_by(username=username).first()
    if not user:
        user = User(username=username)
    user.email = email
    user.set_password(password)
    user.is_admin = True
    user.is_approved = True
    db.session.add(user)
    db.session.commit()
    click.echo(f"✅  Administrador `{username}` con email `{email}` listo (desde .env).")


class SecureModelView(ModelView):
    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin

def create_app():
    app = Flask(__name__)

    # --- Configuración desde .env ---
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "cambia_esto")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL",
        "postgresql://usuario:clave@localhost:5432/chatgpt_db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["ALLOWED_MODELS"] = [
        "chatgpt-4o-latest", "o4-mini", "gpt-4o-mini-2024-07-18"
    ]
    app.config["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
    # ---------------------------------

    db.init_app(app)
    migrate.init_app(app, db)

    login_manager.init_app(app)
    login_manager.login_view = "auth.login" # Correctly points to the blueprint's login endpoint
    login_manager.login_message = "Por favor, inicia sesión para acceder."
    login_manager.login_message_category = "warning"

    logging.basicConfig(level=logging.DEBUG)

    # **Register the authentication blueprint FIRST**
    app.register_blueprint(auth_bp)

    # Initialize your main application routes AFTER the blueprint
    # This ensures that any `url_for` calls within 'routes' for 'auth.login' work correctly.
    routes.init_app(app)

    # Registra el comando que lee de .env
    app.cli.add_command(init_admin_env)

    # Flask-Admin
    admin = Admin(app, name="Panel Admin", template_mode="bootstrap3")
    admin.add_view(SecureModelView(User, db.session))

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5002, debug=True)