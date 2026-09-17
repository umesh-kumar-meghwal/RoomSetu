"""
routes/properties.py
Public endpoints for searching and viewing student rooms and properties.
"""
import logging
from flask import Blueprint, render_template, request, abort
from services.supabase_client import get_service_client

logger = logging.getLogger(__name__)

properties_bp = Blueprint("properties_bp", __name__, url_prefix="/properties")


@properties_bp.route("/")
@properties_bp.route("/browse")
def browse():
    """
    Search and filter public room listings across India.
    Only returns AVAILABLE rooms from PUBLISHED properties.
    """
    service = get_service_client()

    # Query Parameters
    city = request.args.get("city", "").strip()
    locality = request.args.get("locality", "").strip()
    room_type = request.args.get("room_type", "").strip()
    max_rent = request.args.get("max_rent", "").strip()
    has_wifi = request.args.get("has_wifi") == "1"
    has_ac = request.args.get("has_ac") == "1"
    has_attached_bathroom = request.args.get("has_attached_bathroom") == "1"

    try:
        # Base query joining room details, property details, and images
        query = service.table("rooms").select(
            "id, room_name, room_type, monthly_rent, security_deposit, availability_status, "
            "properties!inner(id, title, property_type, address_line, locality, city, state, publishing_status), "
            "amenities!inner(*), "
            "room_images(storage_path, is_primary)"
        ).eq("availability_status", "AVAILABLE").eq("properties.publishing_status", "PUBLISHED")

        # Apply Filters
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

    except Exception as exc:
        logger.error(f"Error querying properties/browse: {exc}")
        rooms = []

    return render_template(
        "properties/listing.html",
        rooms=rooms,
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
    """
    Renders comprehensive details for a property, including
    rental policies, exterior images, and all associated rooms.
    """
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

        # Enforce publication visibility
        if property_data.get("publishing_status") != "PUBLISHED":
            abort(404)

        # Filter only AVAILABLE rooms for public view
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

        return render_template("properties/detail.html", property=property_data)

    except Exception as exc:
        logger.error(f"Error fetching property detail for {property_id}: {exc}")
        abort(404)


@properties_bp.route("/rooms/<room_id>")
def room_detail(room_id: str):
    """
    Renders detailed room specifications, including utility
    pricing, amenities matrix, and inquiry submission panel.
    """
    service = get_service_client()

    try:
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

        amenities = room_data.get("amenities")
        if isinstance(amenities, list) and amenities:
            room_data["amenities"] = amenities[0]
        elif not isinstance(amenities, dict):
            room_data["amenities"] = {}

        policies = property_data.get("rental_policies")
        if isinstance(policies, list) and policies:
            property_data["rental_policies"] = policies[0]
        elif not isinstance(policies, dict):
            property_data["rental_policies"] = {}

        return render_template("properties/room_detail.html", room=room_data, property=property_data)

    except Exception as exc:
        logger.error(f"Error fetching room detail for {room_id}: {exc}")
        abort(404)