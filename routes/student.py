"""
routes/student.py
Student portal endpoints: dashboard, inquiries, saved listings, and profile settings.
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from middleware.auth_guard import login_required
from middleware.role_guard import role_required
from services.supabase_client import get_service_client, get_user_client
from services.inquiry_service import InquiryService
from utils.validators import sanitize_string, PHONE_REGEX

student_bp = Blueprint("student_bp", __name__, url_prefix="/student")


@student_bp.route("/dashboard")
@login_required
@role_required("STUDENT")
def dashboard():
    """Renders the main student dashboard with high-level stats and recent activity."""
    student_id = session.get("user_id")
    service = get_service_client()

    # 1. Total Favorites Count
    favs_res = service.table("favorites").select("id", count="exact").eq("student_id", student_id).execute()
    total_favorites = favs_res.count or 0

    # 2. Total Inquiries Count
    inq_res = service.table("inquiries").select("id", count="exact").eq("student_id", student_id).execute()
    total_inquiries = inq_res.count or 0

    # 3. Recent 3 inquiries
    recent_inquiries = InquiryService.get_student_inquiries(student_id)[:3]

    # 4. Recent saved rooms (limit 4)
    saved_res = service.table("favorites").select(
        "id, room_id, rooms(id, room_name, monthly_rent, room_type, availability_status, "
        "properties(id, title, locality, city, publishing_status), "
        "room_images(storage_path, is_primary))"
    ).eq("student_id", student_id).limit(4).execute()

    saved_rooms = []
    if saved_res.data:
        for item in saved_res.data:
            room = item.get("rooms")
            if room:
                saved_rooms.append(room)

    return render_template(
        "student/dashboard.html",
        total_favorites=total_favorites,
        total_inquiries=total_inquiries,
        recent_inquiries=recent_inquiries,
        saved_rooms=saved_rooms
    )


@student_bp.route("/inquiries")
@login_required
@role_required("STUDENT")
def inquiries():
    """Displays full history of inquiries submitted by the student."""
    student_id = session.get("user_id")
    all_inquiries = InquiryService.get_student_inquiries(student_id)
    return render_template("student/inquiries.html", inquiries=all_inquiries)


@student_bp.route("/inquiries/<inquiry_id>/cancel", methods=["POST"])
@login_required
@role_required("STUDENT")
def cancel_inquiry(inquiry_id: str):
    """Cancels a pending inquiry."""
    student_id = session.get("user_id")
    success, msg = InquiryService.cancel_inquiry(inquiry_id, student_id)
    flash(msg, "info" if success else "danger")
    return redirect(url_for("student_bp.inquiries"))


@student_bp.route("/favorites")
@login_required
@role_required("STUDENT")
def favorites():
    """Displays all bookmarked/saved rooms for the student."""
    student_id = session.get("user_id")
    service = get_service_client()

    fav_res = service.table("favorites").select(
        "id, room_id, created_at, "
        "rooms(id, room_name, monthly_rent, security_deposit, room_type, availability_status, "
        "properties(id, title, locality, city, publishing_status), "
        "room_images(storage_path, is_primary))"
    ).eq("student_id", student_id).order("created_at", desc=True).execute()

    favorites_list = []
    if fav_res.data:
        for f in fav_res.data:
            room = f.get("rooms")
            if room:
                room["favorite_id"] = f["id"]
                favorites_list.append(room)

    return render_template("student/favorites.html", favorites=favorites_list)


@student_bp.route("/profile", methods=["GET", "POST"])
@login_required
@role_required("STUDENT")
def profile():
    """Allows student to view and update contact details."""
    student_id = session.get("user_id")
    service = get_service_client()

    if request.method == "POST":
        full_name = sanitize_string(request.form.get("full_name"))
        phone = sanitize_string(request.form.get("phone"))

        if len(full_name) < 2:
            flash("Full name must be at least 2 characters.", "danger")
        elif phone and not PHONE_REGEX.match(phone):
            flash("Please enter a valid 10-digit Indian phone number.", "danger")
        else:
            try:
                service.table("profiles").update({
                    "full_name": full_name,
                    "phone": phone
                }).eq("id", student_id).execute()

                session["full_name"] = full_name
                flash("Profile updated successfully.", "success")
                return redirect(url_for("student_bp.profile"))
            except Exception as exc:
                flash(f"Failed to update profile: {exc}", "danger")

    # GET Request
    res = service.table("profiles").select("*").eq("id", student_id).execute()
    profile_data = res.data[0] if res.data else {}

    return render_template("student/profile.html", profile=profile_data)


@student_bp.route("/nearby-rooms")
def nearby_rooms():
    """Serves the interactive Leaflet map interface for nearby room searches."""
    return render_template("student/nearby_rooms.html")