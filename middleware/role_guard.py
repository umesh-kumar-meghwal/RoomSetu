"""
middleware/role_guard.py
Role-based access control (RBAC) decorators.
"""
from functools import wraps
from flask import session, abort, flash, redirect, url_for
from services.supabase_client import get_service_client


def role_required(*allowed_roles: str):
    """
    Ensures that only users with one of the specified roles can access the endpoint.
    Aborts with 403 Forbidden if the user's role does not match.
    """
    def decorator(view_func):
        @wraps(view_func)
        def decorated_function(*args, **kwargs):
            if not session.get("user_id"):
                flash("Please log in to continue.", "warning")
                return redirect(url_for("auth_bp.login"))

            user_role = session.get("role")
            if user_role not in allowed_roles:
                abort(403)
            return view_func(*args, **kwargs)
        return decorated_function
    return decorator


def landlord_approved_required(view_func):
    """
    Ensures that a landlord's KYC verification has been APPROVED
    before allowing access to listing management.
    """
    @wraps(view_func)
    def decorated_function(*args, **kwargs):
        user_id = session.get("user_id")
        user_role = session.get("role")

        if not user_id or user_role != "LANDLORD":
            abort(403)

        service = get_service_client()
        res = service.table("landlord_verifications").select("verification_status").eq("user_id", user_id).execute()

        if not res.data or res.data[0].get("verification_status") != "APPROVED":
            flash("Access Restricted: Your landlord identity verification is pending admin review.", "info")
            return redirect(url_for("landlord_bp.verification_status"))

        return view_func(*args, **kwargs)
    return decorated_function