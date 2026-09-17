"""
services/room_service.py
Handles room inventory, amenity matrices, and availability status updates.
"""
import logging
from typing import Dict, Any, Tuple
from services.supabase_client import get_service_client

logger = logging.getLogger(__name__)


class RoomService:
    """Manages individual rooms within a property."""
    @staticmethod
    def delete_room(room_id: str, owner_id: str) -> Tuple[bool, str]:
        """
        Room delete karta hai aur ensures ki sirf property owner hi delete kar sake.
        Cascade delete se amenities aur room_images auto-delete ho jayenge.
        """
        service = get_service_client()
        try:
            # Check ownership
            check_res = service.table("rooms").select(
                "id, properties!inner(owner_id)"
            ).eq("id", room_id).eq("properties.owner_id", owner_id).execute()

            if not check_res.data:
                return False, "Unauthorized: Aap is room ke owner nahi hain."

            # Delete room
            service.table("rooms").delete().eq("id", room_id).execute()
            return True, "Room safalta-purvak delete ho gaya."
        except Exception as exc:
            logger.error(f"Failed to delete room {room_id}: {exc}")
            return False, str(exc)

    @staticmethod
    def delete_room_image(image_id: str, owner_id: str) -> Tuple[bool, str]:
        """Specific room image ko delete karta hai."""
        service = get_service_client()
        try:
            # Verify owner via rooms -> properties
            img_res = service.table("room_images").select(
                "id, storage_path, rooms!inner(properties!inner(owner_id))"
            ).eq("id", image_id).execute()

            if not img_res.data:
                return False, "Image nahi mili ya aap unauthorized hain."

            # Ownership check
            img_data = img_res.data[0]
            prop_owner = img_data.get("rooms", {}).get("properties", {}).get("owner_id")
            if prop_owner != owner_id:
                return False, "Unauthorized action."

            # Supabase storage se file remove karein
            storage_path = img_data.get("storage_path")
            if storage_path:
                try:
                    service.storage.from_(Config.STORAGE_BUCKET_PROPERTY_MEDIA).remove([storage_path])
                except Exception as st_err:
                    logger.warning(f"Storage file delete warning: {st_err}")

            # Database record delete karein
            service.table("room_images").delete().eq("id", image_id).execute()
            return True, "Image delete ho gayi."
        except Exception as exc:
            logger.error(f"Error deleting room image {image_id}: {exc}")
            return False, str(exc)

    @staticmethod
    def add_room(property_id: str, owner_id: str, room_data: Dict[str, Any], amenities_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Adds a new room to a landlord's property and configures its amenities."""
        service = get_service_client()
        try:
            # Confirm property ownership before insertion
            prop_res = service.table("properties").select("id").eq("id", property_id).eq("owner_id", owner_id).execute()
            if not prop_res.data:
                return False, "Property ownership validation failed."

            room_payload = {
                "property_id": property_id,
                "room_name": room_data["room_name"],
                "room_type": room_data["room_type"],
                "monthly_rent": float(room_data["monthly_rent"]),
                "security_deposit": float(room_data.get("security_deposit", 0.0)),
                "advance_rent": float(room_data.get("advance_rent", 0.0)),
                "availability_status": room_data.get("availability_status", "AVAILABLE"),
                "electricity_policy": room_data.get("electricity_policy", "METER_SEPARATE"),
                "water_policy": room_data.get("water_policy", "INCLUDED"),
                "cooler_charges": float(room_data.get("cooler_charges", 0.0))
            }

            room_res = service.table("rooms").insert(room_payload).execute()
            if not room_res.data:
                return False, "Failed to insert room record."

            room_id = room_res.data[0]["id"]

            # Attach amenities record
            amenities_data["room_id"] = room_id
            service.table("amenities").insert(amenities_data).execute()

            return True, room_id
        except Exception as exc:
            logger.error(f"Room creation error: {exc}")
            return False, str(exc)
        
    @staticmethod
    def update_room(room_id: str, owner_id: str, room_data: Dict[str, Any], amenities_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Updates room details and amenities."""
        service = get_service_client()
        try:
            # Verify ownership via join with properties
            check_res = service.table("rooms").select("id, properties!inner(owner_id)").eq("id", room_id).eq("properties.owner_id", owner_id).execute()
            if not check_res.data:
                return False, "Unauthorized access to this room."

            room_payload = {
                "room_name": room_data["room_name"],
                "room_type": room_data["room_type"],
                "monthly_rent": float(room_data["monthly_rent"]),
                "security_deposit": float(room_data.get("security_deposit", 0.0)),
                "advance_rent": float(room_data.get("advance_rent", 0.0)),
                "availability_status": room_data.get("availability_status", "AVAILABLE"),
                "electricity_policy": room_data.get("electricity_policy", "METER_SEPARATE"),
                "water_policy": room_data.get("water_policy", "INCLUDED"),
                "cooler_charges": float(room_data.get("cooler_charges", 0.0))
            }

            service.table("rooms").update(room_payload).eq("id", room_id).execute()
            service.table("amenities").update(amenities_data).eq("room_id", room_id).execute()

            return True, "Room updated successfully."
        except Exception as exc:
            logger.error(f"Room update error for {room_id}: {exc}")
            return False, str(exc)

    @staticmethod
    def set_availability(room_id: str, owner_id: str, new_status: str) -> Tuple[bool, str]:
        """
        Toggles room status between AVAILABLE, OCCUPIED, and INACTIVE.
        Changing to OCCUPIED removes it immediately from public searches.
        """
        if new_status not in ("AVAILABLE", "OCCUPIED", "INACTIVE"):
            return False, "Invalid status choice."

        service = get_service_client()
        try:
            check_res = service.table("rooms").select("id, properties!inner(owner_id)").eq("id", room_id).eq("properties.owner_id", owner_id).execute()
            if not check_res.data:
                return False, "Unauthorized room state modification."

            service.table("rooms").update({"availability_status": new_status}).eq("id", room_id).execute()
            return True, f"Room status updated to {new_status}."
        except Exception as exc:
            logger.error(f"Failed to update room availability: {exc}")
            return False, str(exc)