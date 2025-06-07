from functools import wraps
from flask import flash, redirect, request, url_for, abort
from flask_login import current_user

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Si no estás logueado, te enviamos al login con el next
        if not current_user.is_authenticated:
            flash("Debes iniciar sesión para acceder a esta sección.", "warning")
            return redirect(url_for("auth.login", next=request.path))
        # Si estás logueado pero no eres admin, 403
        if not current_user.is_admin:
            flash("No tienes permisos para acceder a esta sección.", "error")
            return abort(403)
        return f(*args, **kwargs)
    return decorated_function