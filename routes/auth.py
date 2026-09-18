"""
routes/auth.py
Handles user signup, email verification, session creation, and signout.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from services.auth_service import AuthService
from utils.validators import validate_registration_payload, sanitize_string
from services.supabase_client import get_anon_client, get_service_client


auth_bp = Blueprint("auth_bp", __name__, url_prefix="/auth")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """Renders registration form and creates new user accounts."""
    if session.get("user_id"):
        return _redirect_by_role(session.get("role"))

    if request.method == "POST":
        payload = {
            "email": sanitize_string(request.form.get("email")),
            "password": request.form.get("password", ""),
            "full_name": sanitize_string(request.form.get("full_name")),
            "phone": sanitize_string(request.form.get("phone")),
            "role": sanitize_string(request.form.get("role"))
        }

        valid, error_msg = validate_registration_payload(payload)
        if not valid:
            flash(error_msg, "danger")
            return render_template("auth/register.html", form_data=payload)

        success, msg = AuthService.register_user(
            email=payload["email"],
            password=payload["password"],
            full_name=payload["full_name"],
            phone=payload["phone"],
            role=payload["role"]
        )

        if success:
            flash(msg, "success")
            return redirect(url_for("auth_bp.verify_otp", email=payload["email"]))
        else:
            flash(msg, "danger")
            return render_template("auth/register.html", form_data=payload)

    return render_template("auth/register.html", form_data={})


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """Authenticates existing users and initializes the session."""
    if session.get("user_id"):
        return _redirect_by_role(session.get("role"))

    if request.method == "POST":
        email = sanitize_string(request.form.get("email"))
        password = request.form.get("password", "")

        if not email or not password:
            flash("Please enter both email and password.", "warning")
            return render_template("auth/login.html")

        success, user_data, msg = AuthService.authenticate_user(email, password)

        if success and user_data:
            session.clear()
            session.permanent = True
            session["user_id"] = user_data["user_id"]
            session["email"] = user_data["email"]
            session["role"] = user_data["role"]
            session["full_name"] = user_data["full_name"]
            session["access_token"] = user_data["access_token"]
            session["account_status"] = user_data["account_status"]

            flash(f"Welcome back, {user_data['full_name']}!", "success")
            next_url = request.args.get("next")
            if next_url and next_url.startswith("/"):
                return redirect(next_url)
            return _redirect_by_role(user_data["role"])
        else:
            flash(msg, "danger")

    return render_template("auth/login.html")


@auth_bp.route("/verify-otp", methods=["GET", "POST"])
def verify_otp():
    """Validates the 6-digit confirmation token sent via email."""
    email = sanitize_string(request.args.get("email", ""))

    if request.method == "POST":
        email = sanitize_string(request.form.get("email"))
        token = sanitize_string(request.form.get("token"))

        if not email or not token:
            flash("Email and verification code are required.", "warning")
            return render_template("auth/verify_otp.html", email=email)

        success, msg = AuthService.verify_otp(email, token, otp_type="signup")
        if success:
            flash(msg, "success")
            return redirect(url_for("auth_bp.login"))
        else:
            flash(msg, "danger")

    return render_template("auth/verify_otp.html", email=email)

@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    """Initiates a password recovery request."""
    if request.method == "POST":
        email = sanitize_string(request.form.get("email"))
        if not email:
            flash("Please enter your registered email address.", "warning")
        else:
            client = get_anon_client()
            try:
                # User ko Flask ke reset-password route par bhejein
                redirect_target = f"{Config.APP_BASE_URL.rstrip('/')}/auth/reset-password"
                client.auth.reset_password_for_email(
                    email, 
                    options={"redirect_to": redirect_target}
                )
                flash("Password reset link aapke email par bhej diya gaya hai. Apna inbox check karein!", "info")
                return redirect(url_for("auth_bp.login"))
            except Exception as exc:
                flash(f"Error: {exc}", "danger")

    return render_template("auth/forgot_password.html")

@auth_bp.route("/reset-password", methods=["GET", "POST"])
def reset_password():
    """Renders the form to set a new password and updates it in Supabase."""
    if request.method == "POST":
        new_password = request.form.get("password", "")
        confirm_password = request.form.get("confirm_password", "")
        access_token = request.form.get("access_token", "")

        if len(new_password) < 8:
            flash("Password kam se kam 8 characters ka hona chahiye.", "warning")
            return render_template("auth/reset_password.html")

        if new_password != confirm_password:
            flash("Dono password match nahi ho rahe.", "warning")
            return render_template("auth/reset_password.html")

        try:
            # Supabase user client se password update karein
            user_client = get_user_client(access_token)
            user_client.auth.update_user({"password": new_password})

            flash("Aapka password safalta-purvak badal gaya hai! Ab naye password se login karein.", "success")
            return redirect(url_for("auth_bp.login"))
        except Exception as exc:
            flash(f"Password update fail ho gaya: {exc}", "danger")

    return render_template("auth/reset_password.html")


@auth_bp.route("/logout")
def logout():
    """Clears the session and logs the user out."""
    session.clear()
    flash("You have been signed out successfully.", "info")
    return redirect(url_for("auth_bp.login"))


def _redirect_by_role(role: str | None):
    """Helper to route users to their role-specific dashboard."""
    if role == "ADMIN":
        return redirect(url_for("admin_bp.dashboard"))
    elif role == "LANDLORD":
        return redirect(url_for("landlord_bp.dashboard"))
    return redirect(url_for("student_bp.dashboard"))