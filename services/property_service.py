"""
services/property_service.py
Handles landlord property lifecycle, relational constraints, and policies.
"""
import logging
from typing import Dict, Any, List, Tuple
from services.supabase_client import get_service_client

logger = logging.getLogger(__name__)


class PropertyService:
    """Coordinates property entities, images, and rental policies."""

    @staticmethod
    def get_landlord_properties(owner_id: str) -> List[Dict[str, Any]]:
        """Retrieves all properties owned by a specific landlord with room statistics."""
        service = get_service_client()
        try:
            res = service.table("properties").select(
                "id, title, property_type, address_line, locality, city, state, "
                "pincode, latitude, longitude, publishing_status, created_at, "
                "rooms(id, room_name, availability_status, monthly_rent), "
                "property_images(id, storage_path, image_type)"
            ).eq("owner_id", owner_id).order("created_at", desc=True).execute()

            return res.data or []
        except Exception as exc:
            logger.error(f"Failed to fetch properties for landlord {owner_id}: {exc}")
            return []

    @staticmethod
    def get_property_by_id(property_id: str, owner_id: str | None = None) -> Dict[str, Any] | None:
        """Fetches a single property record, optionally confirming ownership."""
        service = get_service_client()
        try:
            query = service.table("properties").select(
                "*, rental_policies(*), property_images(*), rooms(*, amenities(*), room_images(*))"
            ).eq("id", property_id)

            if owner_id:
                query = query.eq("owner_id", owner_id)

            res = query.execute()
            return res.data[0] if res.data else None
        except Exception as exc:
            logger.error(f"Error fetching property {property_id}: {exc}")
            return None

    @staticmethod
    def create_property(owner_id: str, data: Dict[str, Any], policies_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Creates a property along with its initial rental policies record."""
        service = get_service_client()
        try:
            prop_payload = {
                "owner_id": owner_id,
                "title": data["title"],
                "description": data["description"],
                "property_type": data["property_type"],
                "address_line": data["address_line"],
                "locality": data["locality"],
                "city": data["city"],
                "state": data["state"],
                "pincode": data["pincode"],
                "latitude": float(data["latitude"]),
                "longitude": float(data["longitude"]),
                "publishing_status": "PUBLISHED"
            }

            res = service.table("properties").insert(prop_payload).execute()
            if not res.data:
                return False, "Failed to insert property record."

            property_id = res.data[0]["id"]

            # Insert 1:1 Rental Policies
            policies_data["property_id"] = property_id
            service.table("rental_policies").insert(policies_data).execute()

            return True, property_id
        except Exception as exc:
            logger.error(f"Property creation error: {exc}")
            return False, str(exc)

    @staticmethod
    def update_property(property_id: str, owner_id: str, data: Dict[str, Any], policies_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Updates property metadata and its corresponding rental policies."""
        service = get_service_client()
        try:
            prop_payload = {
                "title": data["title"],
                "description": data["description"],
                "property_type": data["property_type"],
                "address_line": data["address_line"],
                "locality": data["locality"],
                "city": data["city"],
                "state": data["state"],
                "pincode": data["pincode"],
                "latitude": float(data["latitude"]),
                "longitude": float(data["longitude"]),
                "publishing_status": data.get("publishing_status", "PUBLISHED")
            }

            res = service.table("properties").update(prop_payload).eq("id", property_id).eq("owner_id", owner_id).execute()
            if not res.data:
                return False, "Unauthorized or property record not found."

            service.table("rental_policies").update(policies_data).eq("property_id", property_id).execute()
            return True, "Property updated successfully."
        except Exception as exc:
            logger.error(f"Failed to update property {property_id}: {exc}")
            return False, str(exc)