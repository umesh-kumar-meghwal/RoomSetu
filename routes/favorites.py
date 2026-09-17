"""
routes/favorites.py
Endpoints for managing student saved rooms (favorites).
"""
import logging
from flask import Blueprint, request, redirect, url_for, flash, session, jsonify
from middleware.auth_guard import login_required
from middleware.role_guard import role_required
from services.supabase_client import get_service_client

logger = logging.getLogger(__name__)

favorites_bp = Blueprint("favorites_bp", __name__, url_prefix="/favorites")


@favorites_bp.route("/toggle/<room_id>", methods=["POST"])
@login_required
@role_required("STUDENT")
def toggle(room_id: str):
    """
    Toggles bookmark status of a room for the authenticated student.
    Adds if not present; removes if already favorited.
    """
    student_id = session.get("user_id")
    service = get_service_client()

    try:
        # Check if already in favorites
        existing = service.table("favorites").select("id").eq("student_id", student_id).eq("room_id", room_id).execute()

        if existing.data:
            # Remove favorite
            fav_id = existing.data[0]["id"]
            service.table("favorites").delete().eq("id", fav_id).execute()
            msg = "Room removed from your saved list."
            is_favorited = False
        else:
            # Insert favorite
            service.table("favorites").insert({
                "student_id": student_id,
                "room_id": room_id
            }).execute()
            msg = "Room saved to your favorites!"
            is_favorited = True

        # Support both AJAX and standard POST redirect
        if request.headers.get("X-Requested-With") == "XMLHttpRequest" or request.is_json:
            return jsonify({"success": True, "favorited": is_favorited, "message": msg})

        flash(msg, "info" if not is_favorited else "success")
        return redirect(request.referrer or url_for("student_bp.favorites"))

    except Exception as exc:
        logger.error(f"Error toggling favorite for room {room_id}: {exc}")
        if request.headers.get("X-Requested-With") == "XMLHttpRequest":
            return jsonify({"success": False, "error": str(exc)}), 500
        flash("Could not update saved status.", "danger")
        return redirect(request.referrer or url_for("student_bp.favorites"))