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

from flask import Response, make_response
from datetime import datetime
from config import Config

@pages_bp.route("/sitemap.xml", methods=["GET"])
def sitemap():
    """
    Generates a dynamic XML sitemap for search engines.
    Fetches real published properties and available rooms from Supabase.
    """
    service = get_service_client()
    base_url = Config.APP_BASE_URL.rstrip('/')
    now_date = datetime.utcnow().strftime("%Y-%m-%d")

    # 1. Static Core Pages
    static_urls = [
        {"loc": f"{base_url}/", "changefreq": "daily", "priority": "1.0", "lastmod": now_date},
        {"loc": f"{base_url}/properties/browse", "changefreq": "daily", "priority": "0.9", "lastmod": now_date},
        {"loc": f"{base_url}/student/nearby-rooms", "changefreq": "daily", "priority": "0.9", "lastmod": now_date},
        {"loc": f"{base_url}/contact-us", "changefreq": "monthly", "priority": "0.6", "lastmod": now_date},
        {"loc": f"{base_url}/privacy-policy", "changefreq": "monthly", "priority": "0.4", "lastmod": now_date},
        {"loc": f"{base_url}/terms-and-conditions", "changefreq": "monthly", "priority": "0.4", "lastmod": now_date},
    ]

    # 2. Major Student Hub Cities URLs (High SEO value for search queries like "rooms in kota")
    student_cities = ["Kota", "Pune", "Delhi", "Bengaluru", "Dehradun", "Jaipur", "Indore", "Hyderabad"]
    city_urls = [
        {
            "loc": f"{base_url}/properties/browse?city={city}",
            "changefreq": "daily",
            "priority": "0.8",
            "lastmod": now_date
        }
        for city in student_cities
    ]

    # 3. Dynamic Published Properties URLs
    dynamic_property_urls = []
    try:
        props_res = service.table("properties").select("id, updated_at").eq("publishing_status", "PUBLISHED").execute()
        if props_res.data:
            for p in props_res.data:
                lastmod = p.get("updated_at", now_date)[:10]
                dynamic_property_urls.append({
                    "loc": f"{base_url}/properties/{p['id']}",
                    "changefreq": "weekly",
                    "priority": "0.8",
                    "lastmod": lastmod
                })
    except Exception as e:
        logger.warning(f"Sitemap property fetch warning: {e}")

    # 4. Dynamic Available Rooms URLs
    dynamic_room_urls = []
    try:
        rooms_res = service.table("rooms").select(
            "id, updated_at, properties!inner(publishing_status)"
        ).eq("availability_status", "AVAILABLE").eq("properties.publishing_status", "PUBLISHED").execute()

        if rooms_res.data:
            for r in rooms_res.data:
                lastmod = r.get("updated_at", now_date)[:10]
                dynamic_room_urls.append({
                    "loc": f"{base_url}/properties/rooms/{r['id']}",
                    "changefreq": "weekly",
                    "priority": "0.7",
                    "lastmod": lastmod
                })
    except Exception as e:
        logger.warning(f"Sitemap room fetch warning: {e}")

    # Combine all URLs
    all_urls = static_urls + city_urls + dynamic_property_urls + dynamic_room_urls

    # Render XML Template
    xml_content = render_template("seo/sitemap.xml", urls=all_urls)
    response = make_response(xml_content)
    response.headers["Content-Type"] = "application/xml; charset=utf-8"
    return response


@pages_bp.route("/robots.txt", methods=["GET"])
def robots_txt():
    """Serves standard robots.txt directing search bots to sitemap."""
    base_url = Config.APP_BASE_URL.rstrip('/')
    lines = [
        "User-agent: *",
        "Disallow: /admin/",
        "Disallow: /landlord/",
        "Disallow: /student/dashboard",
        "Disallow: /student/inquiries",
        "Disallow: /student/favorites",
        "Disallow: /student/profile",
        "Disallow: /auth/",
        "Disallow: /api/",
        "Allow: /",
        "Allow: /properties/",
        "Allow: /student/nearby-rooms",
        "Allow: /contact-us",
        "Allow: /privacy-policy",
        f"Sitemap: {base_url}/sitemap.xml"
    ]
    response = make_response("\n".join(lines))
    response.headers["Content-Type"] = "text/plain; charset=utf-8"
    return response



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