"""
middleware/auth_guard.py
Route guard verifying presence of an active authenticated session.
"""
from functools import wraps
from flask import session, redirect, url_for, flash, request


def login_required(view_func):
    """Decorator ensuring that a route can only be accessed by authenticated users."""
    @wraps(view_func)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id") or not session.get("access_token"):
            flash("Please sign in to access this page.", "warning")
            return redirect(url_for("auth_bp.login", next=request.url))
        return view_func(*args, **kwargs)
    return decorated_function