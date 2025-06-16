from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, current_user, login_required
from models import User, db
from flask_wtf import CSRFProtect, FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo
from datetime import datetime, timedelta
import secrets
import smtplib
from email.mime.text import MIMEText
from urllib.parse import urlparse, urljoin

csrf = CSRFProtect()

def init_app(app):
    csrf.init_app(app)
    app.register_blueprint(auth_bp)

class LoginForm(FlaskForm):
    username = StringField('Usuario', validators=[DataRequired()])
    password = PasswordField('Contraseña', validators=[DataRequired()])
    submit = SubmitField('Entrar')

class ResetPasswordRequestForm(FlaskForm):
    email = StringField('Correo electrónico', validators=[DataRequired(), Email()])
    submit = SubmitField('Enviar enlace de restablecimiento')

class ResetPasswordForm(FlaskForm):
    password = PasswordField('Nueva contraseña', validators=[DataRequired()])
    confirm_password = PasswordField('Confirmar nueva contraseña', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Restablecer contraseña')

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form["username"]
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]
        email = request.form.get("email")

        if password != confirm_password:
            flash("Las contraseñas no coinciden.", "error")
            return redirect(url_for("auth.register"))

        if User.query.filter_by(username=username).first():
            flash("El usuario ya existe.", "error")
            return redirect(url_for("auth.register"))

        if not email:
            flash("El campo de correo electrónico es obligatorio.", "error")
            return redirect(url_for("auth.register"))

        user = User(username=username, email=email)
        user.set_password(password)
        user.is_approved = False
        db.session.add(user)
        db.session.commit()
        flash("Usuario registrado. Espera aprobación del administrador.", "success")
        return redirect(url_for("auth.login"))
    return render_template("register.html")

def is_safe_url(target):
    host_url = request.host_url
    test_url = urljoin(host_url, target)
    return test_url.startswith(host_url)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        user = User.query.filter_by(username=username).first()

        if user is None or not user.check_password(password):
            flash("Credenciales inválidas", "error")
            return redirect(url_for("auth.login"))

        if not user.is_approved:
            flash("Tu cuenta aún no ha sido aprobada por un administrador.", "warning")
            return redirect(url_for("auth.login"))

        login_user(user)
        flash("Bienvenido", "success")
        next_page = request.form.get('next') or request.args.get('next')
        if next_page and is_safe_url(next_page):
            return redirect(next_page)
        else:
            return redirect(url_for("index"))
    return render_template('login.html', form=form)

@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    flash('Has cerrado sesión.', 'info')
    return redirect(url_for('auth.login'))

def send_email(subject, recipient, body):
    app = current_app._get_current_object()
    msg = MIMEText(body, "html")
    msg["Subject"] = subject
    msg["From"] = app.config["MAIL_USERNAME"]
    msg["To"] = recipient

    try:
        if app.config["MAIL_USE_SSL"]:
            server = smtplib.SMTP_SSL(app.config["MAIL_SERVER"], app.config["MAIL_PORT"])
        else:
            server = smtplib.SMTP(app.config["MAIL_SERVER"], app.config["MAIL_PORT"])
            if app.config["MAIL_USE_TLS"]:
                server.starttls()
        server.login(app.config["MAIL_USERNAME"], app.config["MAIL_PASSWORD"])
        server.sendmail(app.config["MAIL_USERNAME"], [recipient], msg.as_string())
        server.quit()
    except Exception as e:
        app.logger.error(f"Error enviando correo: {e}")

@auth_bp.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = secrets.token_urlsafe(32)
            user.reset_token = token
            user.reset_token_expiration = datetime.utcnow() + timedelta(hours=1)
            db.session.commit()
            reset_url = url_for('auth.reset_password', token=token, _external=True)
            html_body = f"""
            <p>Para restablecer tu contraseña, haz clic en el siguiente enlace:</p>
            <p><a href="{reset_url}">{reset_url}</a></p>
            <p>Si no solicitaste este cambio, ignora este correo.</p>
            """
            send_email("Restablecimiento de contraseña", user.email, html_body)
        # Mostrar mensaje genérico para no revelar si el email existe
        flash('Si el correo está registrado, recibirás un enlace para restablecer la contraseña.', 'info')
        return redirect(url_for('auth.login'))
    return render_template('reset_password_request.html', form=form)

@auth_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    user = User.query.filter_by(reset_token=token).first()
    if user is None or user.reset_token_expiration is None or user.reset_token_expiration < datetime.utcnow():
        flash('El enlace de restablecimiento no es válido o ha expirado.', 'error')
        return redirect(url_for('auth.reset_password_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        user.reset_token = None
        user.reset_token_expiration = None
        db.session.commit()
        flash('Tu contraseña ha sido restablecida. Ya puedes iniciar sesión.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('reset_password.html', form=form)
