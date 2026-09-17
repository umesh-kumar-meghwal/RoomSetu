"""
services/inquiry_service.py
Service handling student inquiries, message threads, and inquiry lifecycle.
"""
import logging
from typing import Dict, Any, List, Optional
from services.supabase_client import get_service_client, get_user_client

logger = logging.getLogger(__name__)


class InquiryService:
    """Encapsulates student-landlord inquiry workflows."""

    @staticmethod
    def create_inquiry(
        student_id: str,
        room_id: str,
        message: str,
        move_in_date: Optional[str] = None,
        access_token: Optional[str] = None
    ) -> tuple[bool, str]:
        """
        Creates a new inquiry from a student for a specific room.
        Resolves property_id and landlord_id automatically.
        """
        service = get_service_client()
        try:
            # 1. Fetch room and parent property to locate landlord
            room_res = service.table("rooms").select(
                "id, property_id, properties(id, owner_id, publishing_status)"
            ).eq("id", room_id).execute()

            if not room_res.data:
                return False, "Selected room does not exist."

            room_data = room_res.data[0]
            prop_data = room_data.get("properties")
            if not prop_data or prop_data.get("publishing_status") != "PUBLISHED":
                return False, "This listing is currently unavailable for inquiries."

            landlord_id = prop_data.get("owner_id")
            property_id = prop_data.get("id")

            if student_id == landlord_id:
                return False, "Property owners cannot send inquiries to their own listings."

            payload = {
                "student_id": student_id,
                "landlord_id": landlord_id,
                "property_id": property_id,
                "room_id": room_id,
                "message": message.strip(),
                "move_in_date": move_in_date if move_in_date else None,
                "status": "PENDING"
            }

            # Use user-scoped client if token available, else fallback to service
            client = get_user_client(access_token) if access_token else service
            res = client.table("inquiries").insert(payload).execute()

            if res.data:
                # Trigger a notification to the landlord
                service.table("notifications").insert({
                    "recipient_id": landlord_id,
                    "title": "New Room Inquiry Received",
                    "message": f"A student has sent an inquiry regarding your property.",
                    "notification_type": "INQUIRY_RECEIVED",
                    "action_url": f"/landlord/inquiries"
                }).execute()

                return True, "Inquiry sent successfully to the property owner."
            return False, "Failed to record inquiry."

        except Exception as exc:
            logger.error(f"Failed to submit inquiry: {exc}")
            return False, str(exc)

    @staticmethod
    def get_student_inquiries(student_id: str) -> List[Dict[str, Any]]:
        """Retrieves all inquiries submitted by a student with joined listing details."""
        service = get_service_client()
        try:
            res = service.table("inquiries").select(
                "id, message, move_in_date, landlord_response, status, created_at, "
                "rooms(id, room_name, monthly_rent, room_type), "
                "properties(id, title, locality, city), "
                "landlord:profiles!inquiries_landlord_id_fkey(full_name, phone, email)"
            ).eq("student_id", student_id).order("created_at", desc=True).execute()

            return res.data or []
        except Exception as exc:
            logger.error(f"Error fetching inquiries for student {student_id}: {exc}")
            return []

    @staticmethod
    def cancel_inquiry(inquiry_id: str, student_id: str) -> tuple[bool, str]:
        """Allows a student to cancel a pending inquiry."""
        service = get_service_client()
        try:
            res = service.table("inquiries").update(
                {"status": "CANCELLED_BY_STUDENT"}
            ).eq("id", inquiry_id).eq("student_id", student_id).eq("status", "PENDING").execute()

            if res.data:
                return True, "Inquiry cancelled."
            return False, "Could not cancel inquiry. It may have already been resolved."
        except Exception as exc:
            logger.error(f"Error cancelling inquiry {inquiry_id}: {exc}")
            return False, str(exc)