"""
routes/api.py
Public REST API endpoints for geolocation searches and nearby room lookups.
"""
import logging
from flask import Blueprint, request, jsonify
from services.supabase_client import get_service_client
from services.location_service import LocationService
from utils.validators import validate_coordinates
from config import Config

logger = logging.getLogger(__name__)

api_bp = Blueprint("api_bp", __name__, url_prefix="/api")


@api_bp.route("/nearby-rooms", methods=["GET"])
def get_nearby_rooms():
    """
    GET /api/nearby-rooms
    Query Parameters:
        - latitude: float (required)
        - longitude: float (required)
        - radius: float (optional, default 5.0, max 25.0)
        - room_type: string (optional: SINGLE, DOUBLE_SHARING, etc.)
        - min_rent: float (optional)
        - max_rent: float (optional)

    Returns:
        JSON response with list of available rooms inside radius, sorted by distance.
    """
    lat_param = request.args.get("latitude")
    lon_param = request.args.get("longitude")
    radius_param = request.args.get("radius", str(Config.DEFAULT_SEARCH_RADIUS_KM))
    room_type_param = request.args.get("room_type")
    min_rent_param = request.args.get("min_rent")
    max_rent_param = request.args.get("max_rent")

    # 1. Validate coordinates
    is_valid_coords, lat, lon = validate_coordinates(lat_param, lon_param)
    if not is_valid_coords:
        return jsonify({
            "success": False,
            "error": "Invalid coordinates. Latitude must be between -90 and 90, Longitude between -180 and 180."
        }), 400

    # 2. Validate radius
    try:
        radius = float(radius_param)
        if radius <= 0 or radius > Config.MAX_SEARCH_RADIUS_KM:
            radius = Config.DEFAULT_SEARCH_RADIUS_KM
    except (ValueError, TypeError):
        radius = Config.DEFAULT_SEARCH_RADIUS_KM

    service = get_service_client()

    try:
        # 3. Query PostgreSQL via Supabase
        # Filter strictly: room is AVAILABLE and property is PUBLISHED
        query = service.table("rooms").select(
            "id, room_name, room_type, monthly_rent, security_deposit, availability_status, "
            "properties!inner(id, title, property_type, locality, city, latitude, longitude, publishing_status), "
            "room_images(storage_path, is_primary)"
        ).eq("availability_status", "AVAILABLE").eq("properties.publishing_status", "PUBLISHED")

        if room_type_param:
            query = query.eq("room_type", room_type_param)
        if min_rent_param:
            try:
                query = query.gte("monthly_rent", float(min_rent_param))
            except ValueError:
                pass
        if max_rent_param:
            try:
                query = query.lte("monthly_rent", float(max_rent_param))
            except ValueError:
                pass

        res = query.limit(100).execute()
        raw_rooms = res.data or []

        # 4. Geodesic Distance Calculation & Sorting
        nearby_rooms = LocationService.filter_and_sort_by_distance(
            user_lat=lat,
            user_lon=lon,
            rooms_data=raw_rooms,
            max_radius_km=radius
        )

        # 5. Sanitize payload: never leak private owner info
        sanitized_results = []
        for r in nearby_rooms:
            prop = r.get("properties", {})
            images = r.get("room_images", [])
            primary_img = images[0]["storage_path"] if images else None

            sanitized_results.append({
                "id": r["id"],
                "room_name": r["room_name"],
                "room_type": r["room_type"],
                "monthly_rent": float(r["monthly_rent"]),
                "security_deposit": float(r.get("security_deposit", 0)),
                "distance_km": r["distance_km"],
                "property_id": prop.get("id"),
                "property_title": prop.get("title"),
                "locality": prop.get("locality"),
                "city": prop.get("city"),
                "latitude": float(prop.get("latitude")),
                "longitude": float(prop.get("longitude")),
                "thumbnail_path": primary_img
            })

        return jsonify({
            "success": True,
            "center": {"latitude": lat, "longitude": lon},
            "radius_km": radius,
            "count": len(sanitized_results),
            "rooms": sanitized_results
        }), 200

    except Exception as exc:
        logger.error(f"Error executing nearby-rooms query: {exc}")
        return jsonify({
            "success": False,
            "error": "Failed to process location lookup due to an internal error."
        }), 500