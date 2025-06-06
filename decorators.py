from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("Acceso denegado. Se requieren permisos de administrador.")
            return redirect(url_for("auth.login")) # Assuming your login route is 'auth.login'
        return f(*args, **kwargs)
    return decorated_function