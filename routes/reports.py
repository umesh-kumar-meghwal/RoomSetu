"""
routes/reports.py
Allows users to file reports regarding misleading pricing, fake photos, or fraud.
"""
import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from middleware.auth_guard import login_required
from services.supabase_client import get_service_client
from utils.validators import sanitize_string

logger = logging.getLogger(__name__)

reports_bp = Blueprint("reports_bp", __name__, url_prefix="/reports")


@reports_bp.route("/new", methods=["GET", "POST"])
@login_required
def submit_report():
    """
    Renders and processes listing complaint submissions.
    Accepts property_id and/or room_id via query parameters.
    """
    reporter_id = session.get("user_id")
    property_id = request.args.get("property_id") or request.form.get("property_id")
    room_id = request.args.get("room_id") or request.form.get("room_id")

    if request.method == "POST":
        reason = sanitize_string(request.form.get("reason"))
        description = sanitize_string(request.form.get("description"))

        valid_reasons = (
            "MISLEADING_PRICING", "FAKE_PHOTOS", "INACCURATE_LOCATION",
            "HARASSMENT", "ILLEGAL_RESTRICTIONS", "ALREADY_OCCUPIED", "OTHER"
        )

        if reason not in valid_reasons:
            flash("Please choose a valid reason for this report.", "warning")
            return render_template("reports/new.html", property_id=property_id, room_id=room_id)

        if not description or len(description) < 10:
            flash("Please provide a detailed description of the issue (at least 10 characters).", "warning")
            return render_template("reports/new.html", property_id=property_id, room_id=room_id)

        service = get_service_client()
        try:
            payload = {
                "reporter_id": reporter_id,
                "property_id": property_id if property_id else None,
                "room_id": room_id if room_id else None,
                "reason": reason,
                "description": description,
                "status": "PENDING"
            }
            res = service.table("reports").insert(payload).execute()

            if res.data:
                flash("Thank you. Your report has been submitted for administrative review.", "success")
                return redirect(url_for("properties_bp.browse"))
            else:
                flash("Failed to record report.", "danger")
        except Exception as exc:
            logger.error(f"Error filing report: {exc}")
            flash(f"Submission error: {exc}", "danger")

    return render_template("reports/new.html", property_id=property_id, room_id=room_id)