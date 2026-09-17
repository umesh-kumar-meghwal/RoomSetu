"""
routes/inquiries.py
Endpoints for students to initiate and manage room rental inquiries.
"""
import logging
from flask import Blueprint, request, redirect, url_for, flash, session
from middleware.auth_guard import login_required
from middleware.role_guard import role_required
from services.inquiry_service import InquiryService
from utils.validators import sanitize_string

logger = logging.getLogger(__name__)

inquiries_bp = Blueprint("inquiries_bp", __name__, url_prefix="/inquiries")


@inquiries_bp.route("/submit/<room_id>", methods=["POST"])
@login_required
@role_required("STUDENT")
def submit(room_id: str):
    """
    Submits a student inquiry for a specific room.
    Validates message content and schedules notifications to the landlord.
    """
    student_id = session.get("user_id")
    access_token = session.get("access_token")
    message = sanitize_string(request.form.get("message"))
    move_in_date = request.form.get("move_in_date")

    if not message or len(message) < 5:
        flash("Please provide a descriptive inquiry message (at least 5 characters).", "warning")
        return redirect(url_for("properties_bp.room_detail", room_id=room_id))

    success, msg = InquiryService.create_inquiry(
        student_id=student_id,
        room_id=room_id,
        message=message,
        move_in_date=move_in_date,
        access_token=access_token
    )

    if success:
        flash(msg, "success")
        return redirect(url_for("student_bp.inquiries"))
    else:
        flash(msg, "danger")
        return redirect(url_for("properties_bp.room_detail", room_id=room_id))