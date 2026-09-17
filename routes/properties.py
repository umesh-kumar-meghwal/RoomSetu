"""
routes/properties.py
Public endpoints for searching and viewing student rooms and properties.
"""
import logging
from flask import Blueprint, render_template, request, abort, redirect, url_for, flash, session
from middleware.auth_guard import login_required
from middleware.role_guard import role_required
from utils.validators import sanitize_string
from services.supabase_client import get_service_client

logger = logging.getLogger(__name__)

properties_bp = Blueprint("properties_bp", __name__, url_prefix="/properties")


@properties_bp.route("/")
@properties_bp.route("/browse")
def browse():
    service = get_service_client()

    city = request.args.get("city", "").strip()
    locality = request.args.get("locality", "").strip()
    room_type = request.args.get("room_type", "").strip()
    max_rent = request.args.get("max_rent", "").strip()
    has_wifi = request.args.get("has_wifi") == "1"
    has_ac = request.args.get("has_ac") == "1"
    has_attached_bathroom = request.args.get("has_attached_bathroom") == "1"

    try:
        query = service.table("rooms").select(
            "id, room_name, room_type, monthly_rent, security_deposit, availability_status, "
            "properties!inner(id, title, property_type, address_line, locality, city, state, publishing_status), "
            "amenities!inner(*), "
            "room_images(storage_path, is_primary)"
        ).eq("availability_status", "AVAILABLE").eq("properties.publishing_status", "PUBLISHED")

        if city:
            query = query.ilike("properties.city", f"%{city}%")
        if locality:
            query = query.ilike("properties.locality", f"%{locality}%")
        if room_type:
            query = query.eq("room_type", room_type)
        if max_rent:
            try:
                rent_val = float(max_rent)
                query = query.lte("monthly_rent", rent_val)
            except ValueError:
                pass

        if has_wifi:
            query = query.eq("amenities.has_wifi", True)
        if has_ac:
            query = query.eq("amenities.has_ac", True)
        if has_attached_bathroom:
            query = query.eq("amenities.has_attached_bathroom", True)

        res = query.order("monthly_rent", desc=False).limit(40).execute()
        rooms = res.data or []

        # ================= NAYA: Recent 10 Verified Student Reviews Fetch Karein =================
        reviews_res = service.table("reviews").select(
            "id, rating, comment, created_at, "
            "student:profiles!reviews_student_id_fkey(full_name), "
            "property:properties!reviews_property_id_fkey(title, city, locality)"
        ).order("created_at", desc=True).limit(10).execute()

        public_reviews = reviews_res.data or []

    except Exception as exc:
        logger.error(f"Error querying properties/browse: {exc}")
        rooms = []
        public_reviews = []

    return render_template(
        "properties/listing.html",
        rooms=rooms,
        public_reviews=public_reviews,  # <-- Passed to Template
        filters={
            "city": city,
            "locality": locality,
            "room_type": room_type,
            "max_rent": max_rent,
            "has_wifi": has_wifi,
            "has_ac": has_ac,
            "has_attached_bathroom": has_attached_bathroom
        }
    )
@properties_bp.route("/<property_id>")
def property_detail(property_id: str):
    service = get_service_client()

    try:
        res = service.table("properties").select(
            "*, rental_policies(*), property_images(*), "
            "owner:profiles!properties_owner_id_fkey(full_name, phone, email), "
            "rooms(*, amenities(*), room_images(*))"
        ).eq("id", property_id).execute()

        if not res.data:
            abort(404)

        property_data = res.data[0]

        if property_data.get("publishing_status") != "PUBLISHED":
            abort(404)

        available_rooms = [
            r for r in property_data.get("rooms", [])
            if r.get("availability_status") == "AVAILABLE"
        ]
        property_data["rooms"] = available_rooms

        policies = property_data.get("rental_policies")
        if isinstance(policies, list) and policies:
            property_data["rental_policies"] = policies[0]
        elif not isinstance(policies, dict):
            property_data["rental_policies"] = {}

        # NAYA: Reviews aur Student profiles fetch karein
        reviews_res = service.table("reviews").select(
            "id, rating, comment, created_at, student:profiles!reviews_student_id_fkey(full_name, avatar_url)"
        ).eq("property_id", property_id).order("created_at", desc=True).execute()

        reviews = reviews_res.data or []
        
        # Calculate Average Rating
        if reviews:
            avg_rating = round(sum(r["rating"] for r in reviews) / len(reviews), 1)
        else:
            avg_rating = 0.0

        return render_template(
            "properties/detail.html", 
            property=property_data, 
            reviews=reviews, 
            avg_rating=avg_rating,
            total_reviews=len(reviews)
        )

    except Exception as exc:
        logger.error(f"Error fetching property detail for {property_id}: {exc}")
        abort(404)
        
        
@properties_bp.route("/<property_id>/reviews", methods=["POST"])
@login_required
@role_required("STUDENT")
def add_review(property_id: str):
    """Student feedback aur rating submit karta hai."""
    student_id = session.get("user_id")
    service = get_service_client()

    try:
        rating = int(request.form.get("rating", 5))
        comment = sanitize_string(request.form.get("comment"))

        if rating < 1 or rating > 5:
            flash("Rating 1 se 5 stars ke beech honi chahiye.", "warning")
            return redirect(url_for("properties_bp.property_detail", property_id=property_id))

        if not comment or len(comment) < 5:
            flash("Please feedback mein kam se kam 5 characters likhein.", "warning")
            return redirect(url_for("properties_bp.property_detail", property_id=property_id))

        # Check agar student ne pehle se review de rakha hai
        existing = service.table("reviews").select("id").eq("property_id", property_id).eq("student_id", student_id).execute()

        if existing.data:
            # Update existing review
            service.table("reviews").update({
                "rating": rating,
                "comment": comment,
                "updated_at": "now()"
            }).eq("id", existing.data[0]["id"]).execute()
            flash("Aapka review update ho gaya hai!", "success")
        else:
            # Insert new review
            service.table("reviews").insert({
                "property_id": property_id,
                "student_id": student_id,
                "rating": rating,
                "comment": comment
            }).execute()
            flash("Thank you! Aapka feedback submit ho gaya hai.", "success")

    except Exception as exc:
        logger.error(f"Error saving review: {exc}")
        flash("Feedback save karne mein dikkat aayi. Please dubara try karein.", "danger")

    return redirect(url_for("properties_bp.property_detail", property_id=property_id))
@properties_bp.route("/rooms/<room_id>")
def room_detail(room_id: str):
    """
    Renders detailed room specifications, including utility
    pricing, amenities matrix, reviews, and inquiry submission panel.
    """
    service = get_service_client()

    try:
        # 1. Fetch Room, Amenities, Images, Property, and Owner Details
        res = service.table("rooms").select(
            "*, amenities(*), room_images(*), "
            "properties!inner(*, rental_policies(*), property_images(*), "
            "owner:profiles!properties_owner_id_fkey(full_name, phone, email))"
        ).eq("id", room_id).execute()

        if not res.data:
            abort(404)

        room_data = res.data[0]
        property_data = room_data.get("properties")

        # Security check: Room must be available and property published
        if room_data.get("availability_status") != "AVAILABLE" or property_data.get("publishing_status") != "PUBLISHED":
            abort(404)

        # Normalize Amenities Dict
        amenities = room_data.get("amenities")
        if isinstance(amenities, list) and amenities:
            room_data["amenities"] = amenities[0]
        elif not isinstance(amenities, dict):
            room_data["amenities"] = {}

        # Normalize Rental Policies Dict
        policies = property_data.get("rental_policies")
        if isinstance(policies, list) and policies:
            property_data["rental_policies"] = policies[0]
        elif not isinstance(policies, dict):
            property_data["rental_policies"] = {}

        # 2. Fetch All Student Reviews for this Property
        reviews_res = service.table("reviews").select(
            "id, rating, comment, created_at, student:profiles!reviews_student_id_fkey(full_name, avatar_url)"
        ).eq("property_id", property_data["id"]).order("created_at", desc=True).execute()

        reviews = reviews_res.data or []
        
        # Calculate Average Rating
        if reviews:
            avg_rating = round(sum(r["rating"] for r in reviews) / len(reviews), 1)
        else:
            avg_rating = 0.0

        # 3. Check if CURRENT logged-in student has already reviewed this property
        user_review = None
        user_id = session.get("user_id")
        user_role = session.get("role")
        
        if user_id and user_role == "STUDENT":
            u_check = service.table("reviews").select("*").eq("property_id", property_data["id"]).eq("student_id", user_id).execute()
            if u_check.data:
                user_review = u_check.data[0]

        return render_template(
            "properties/room_detail.html",
            room=room_data,
            property=property_data,
            reviews=reviews,
            avg_rating=avg_rating,
            total_reviews=len(reviews),
            user_review=user_review
        )

    except Exception as exc:
        logger.error(f"Error fetching room detail for {room_id}: {exc}")
        abort(404)