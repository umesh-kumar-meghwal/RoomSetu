"""
services/auth_service.py
Encapsulates Supabase Auth operations: registration, session exchange, and user profiles.
"""
import logging
from typing import Dict, Any, Tuple
from services.supabase_client import get_anon_client, get_service_client

logger = logging.getLogger(__name__)


class AuthService:
    """Service class for authentication and identity provisioning."""

    @staticmethod
    def register_user(email: str, password: str, full_name: str, phone: str, role: str) -> Tuple[bool, str]:
        """
        Signs up a user with Supabase Auth and registers profile metadata.
        Public registration permits only STUDENT or LANDLORD roles.
        """
        if role not in ["STUDENT", "LANDLORD"]:
            return False, "Invalid role selected during registration."

        client = get_anon_client()
        try:
            response = client.auth.sign_up({
                "email": email,
                "password": password,
                "options": {
                    "data": {
                        "full_name": full_name,
                        "phone": phone,
                        "role": role
                    }
                }
            })
            if response.user:
                return True, "Registration successful. Please verify your email to continue."
            return False, "User registration failed with no error returned."
        except Exception as exc:
            logger.error(f"Error during registration for {email}: {exc}")
            return False, str(exc)

    @staticmethod
    def authenticate_user(email: str, password: str) -> Tuple[bool, Dict[str, Any] | None, str]:
        """
        Authenticates a user via email and password.
        Returns a tuple: (success_bool, auth_payload_dict, error_message).
        """
        client = get_anon_client()
        try:
            response = client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })

            if not response.user or not response.session:
                return False, None, "Invalid authentication credentials."

            # Fetch authoritative profile from database using the service client
            service = get_service_client()
            profile_res = service.table("profiles").select("*").eq("id", response.user.id).execute()

            if not profile_res.data:
                return False, None, "User profile record not found in system database."

            profile = profile_res.data[0]

            if profile.get("account_status") == "SUSPENDED":
                return False, None, "Your account is suspended. Please contact platform support."

            session_payload = {
                "user_id": response.user.id,
                "email": response.user.email,
                "role": profile.get("role"),
                "full_name": profile.get("full_name"),
                "account_status": profile.get("account_status"),
                "access_token": response.session.access_token,
                "refresh_token": response.session.refresh_token
            }
            return True, session_payload, "Authentication successful."
        except Exception as exc:
            logger.error(f"Sign-in error for {email}: {exc}")
            return False, None, str(exc)

    @staticmethod
    def verify_otp(email: str, token: str, otp_type: str = "signup") -> Tuple[bool, str]:
        """
        Verifies an OTP code for email confirmation or password recovery.
        otp_type can be 'signup', 'recovery', or 'magiclink'.
        """
        client = get_anon_client()
        try:
            response = client.auth.verify_otp({
                "email": email,
                "token": token,
                "type": otp_type
            })
            if response.user:
                return True, "Email successfully verified. You may now log in."
            return False, "Invalid or expired verification token."
        except Exception as exc:
            logger.error(f"OTP verification error for {email}: {exc}")
            return False, str(exc)

    @staticmethod
    def initiate_password_reset(email: str) -> Tuple[bool, str]:
        """Triggers a password recovery email."""
        client = get_anon_client()
        try:
            client.auth.reset_password_for_email(email)
            return True, "If an account matches that email, a password recovery link has been sent."
        except Exception as exc:
            logger.error(f"Password reset error for {email}: {exc}")
            return False, str(exc)

    @staticmethod
    def get_profile(user_id: str) -> Dict[str, Any] | None:
        """Fetches the user profile by user UUID."""
        service = get_service_client()
        res = service.table("profiles").select("*").eq("id", user_id).execute()
        return res.data[0] if res.data else None