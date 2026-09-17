"""
routes/pages.py
Static & Legal SEO Pages: Contact Us, Privacy Policy, Terms & FAQ.
"""
import logging
from flask import Blueprint, render_template, request, flash, redirect, url_for
from services.supabase_client import get_service_client
from utils.validators import sanitize_string, EMAIL_REGEX, PHONE_REGEX

logger = logging.getLogger(__name__)

pages_bp = Blueprint("pages_bp", __name__)


@pages_bp.route("/contact-us", methods=["GET", "POST"])
def contact_us():
    """Contact & Support page with live message submission."""
    if request.method == "POST":
        full_name = sanitize_string(request.form.get("full_name"))
        email = sanitize_string(request.form.get("email"))
        phone = sanitize_string(request.form.get("phone"))
        subject = sanitize_string(request.form.get("subject"))
        message = sanitize_string(request.form.get("message"))

        # Validations
        if not full_name or len(full_name) < 2:
            flash("Please enter your full name.", "warning")
            return render_template("pages/contact.html", form=request.form)

        if not EMAIL_REGEX.match(email):
            flash("Please provide a valid email address.", "warning")
            return render_template("pages/contact.html", form=request.form)

        if phone and not PHONE_REGEX.match(phone):
            flash("Please enter a valid 10-digit Indian phone number.", "warning")
            return render_template("pages/contact.html", form=request.form)

        if not message or len(message) < 10:
            flash("Please write a descriptive message (at least 10 characters).", "warning")
            return render_template("pages/contact.html", form=request.form)

        try:
            service = get_service_client()
            service.table("contact_messages").insert({
                "full_name": full_name,
                "email": email,
                "phone": phone or None,
                "subject": subject or "General Inquiry",
                "message": message
            }).execute()

            flash("Dhanyawad! Aapka sandesh RoomSetu support team tak pahunch gaya hai. Hum 24 hours ke andar reply karenge.", "success")
            return redirect(url_for("pages_bp.contact_us"))

        except Exception as exc:
            logger.error(f"Error saving contact message: {exc}")
            flash("Message send karne mein dikkat aayi. Please dubara try karein.", "danger")

    return render_template("pages/contact.html", form={})


@pages_bp.route("/privacy-policy")
def privacy_policy():
    """Indian IT Act & SPDI compliant Privacy Policy for RoomSetu."""
    return render_template("pages/privacy.html")


@pages_bp.route("/terms-and-conditions")
def terms_and_conditions():
    """Tenancy and platform rules terms."""
    return render_template("pages/terms.html")