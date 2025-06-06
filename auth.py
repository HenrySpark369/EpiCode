# auth.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user, login_required # Add current_user if needed for admin_required
from models import User, db # Import db and User

# If you have an admin_required decorator, it should ideally be in a separate decorators.py
# If it's not, you might need to import it here.
# For simplicity, assuming you moved admin_required to a decorators.py
from decorators import admin_required # Make sure this path is correct

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form["username"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"] # Get the new field
        email = request.form.get("email")

        if password != confirm_password:
                flash("Las contraseñas no coinciden.", "error")
                return redirect(url_for("auth.register"))

        if User.query.filter_by(username=username).first():
            flash("El usuario ya existe.", "error") # Good practice to specify category for flash
            return redirect(url_for("auth.register")) # Use auth.register

        if not email:
            flash("El campo de correo electrónico es obligatorio.", "error")
            return redirect(url_for("auth.register")) # Use auth.register

        user = User(username=username, email=email)
        user.set_password(password)
        user.is_approved = False
        db.session.add(user)
        db.session.commit()
        flash("Usuario registrado. Espera aprobación del administrador.", "success")
        return redirect(url_for("auth.login")) # Use auth.login
    return render_template("register.html")


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated: # Prevent authenticated users from seeing login
        return redirect(url_for('index')) # Assuming 'index' is your main authenticated route

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user is None or not user.check_password(password):
            flash("Credenciales inválidas", "error")
            return redirect(url_for("auth.login"))

        if not user.is_approved:
            flash("Tu cuenta aún no ha sido aprobada por un administrador.", "warning")
            return redirect(url_for("auth.login"))

        login_user(user)
        flash("Bienvenido", "success")
        next_page = request.args.get('next')
        return redirect(next_page or url_for("index")) # Redirect to index or 'next' param
    return render_template('login.html')

@auth_bp.route('/logout', methods=['POST'])
@login_required # Only logged in users can log out
def logout():
    logout_user()
    flash('Has cerrado sesión.', 'info')
    return redirect(url_for('auth.login')) # Redirect to login page after logout

# --- Admin routes related to user approval (if you want them in auth blueprint) ---
@auth_bp.route("/admin/aprobar/<int:user_id>", methods=["POST"])
@login_required
@admin_required
def aprobar_usuario(user_id):
    user = User.query.get_or_404(user_id)
    user.is_approved = True
    db.session.commit()
    flash(f"Usuario {user.username} aprobado.", "success")
    return redirect(url_for("auth.admin_usuarios_pendientes")) # Redirect to the pending users list

@auth_bp.route("/admin/usuarios_pendientes", methods=["GET"])
@login_required
@admin_required
def admin_usuarios_pendientes():
    pendientes = User.query.filter_by(is_approved=False).all()
    return render_template("usuarios_pendientes.html", usuarios=pendientes)