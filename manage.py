# manage.py
import os
import click
import logging
from functools import wraps # Only needed if you have custom decorators here, otherwise can remove

from flask import Flask, abort # abort might not be used here anymore, can remove if so
from flask.cli import with_appcontext
# from flask_sqlalchemy import SQLAlchemy # This import can be removed, as db is imported from models
from flask_migrate import Migrate
import config
from flask_login import LoginManager, current_user
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_admin.actions import action
from models import db, User 
import routes 
from auth import auth_bp

from wtforms.fields import Field


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
    def scaffold_form(self):
        form_class = super().scaffold_form()
        for name, field in list(form_class.__dict__.items()):
            if isinstance(field, Field) and hasattr(field, 'query_factory'):
                delattr(form_class, name)
        return form_class
    form_excluded_columns = ('conversations',)

    # Sólo estos campos en el form de edición
    form_columns = ['username', 'email', 'is_admin', 'is_approved']

    # Columnas visibles
    column_list = ['id', 'username', 'email', 'is_admin', 'is_approved']
    column_filters = ['is_admin', 'is_approved']
    column_searchable_list = ['username', 'email']
    can_create = False    # opcional
    can_delete = True
    can_edit   = True
    can_view_details = True

    def is_accessible(self):
        return current_user.is_authenticated and current_user.is_admin

    # acción en lote para aprobar usuarios
    @action('approve', 'Aprobar seleccionados', '¿Seguro que quieres aprobar estos usuarios?')
    def action_approve(self, ids):
        query = User.query.filter(User.id.in_(ids))
        n = 0
        for u in query.all():
            if not u.is_approved:
                u.is_approved = True
                n += 1
        db.session.commit()
        flash(f"{n} usuario(s) aprobado(s).", "success")

def create_app():
    app = Flask(__name__)

    # Carga de configuración según entorno
    env = os.getenv("FLASK_ENV", "development")
    app.config.from_object(config.config[env])

    db.init_app(app)
    migrate.init_app(app, db)

    login_manager.init_app(app)
    login_manager.login_view = "auth.login" # Correctly points to the blueprint's login endpoint
    login_manager.login_message = "Por favor, inicia sesión para acceder."
    login_manager.login_message_category = "warning"

    logging.basicConfig(level=logging.DEBUG)

    app.register_blueprint(auth_bp)

    # Initialize your main application routes AFTER the blueprint
    # This ensures that any `url_for` calls within 'routes' for 'auth.login' work correctly.
    routes.init_app(app)

    # Registra el comando que lee de .env
    app.cli.add_command(init_admin_env)

    # Flask-Admin
    admin = Admin(app, name="Panel Admin", template_mode="bootstrap3", url="/admin", endpoint="flask_admin")
    admin.add_view(SecureModelView(User, db.session, name="Usuarios"))

    # imprime todas las rutas ya registradas
    for rule in app.url_map.iter_rules():
        app.logger.debug(f"{rule.endpoint:30}   {rule}")

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5002, debug=True)
