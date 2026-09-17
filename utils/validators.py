"""
utils/validators.py
Input validators for sanitizing form submissions and API payloads.
"""
import re
from typing import Tuple, Dict, Any
import bleach

EMAIL_REGEX = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
PINCODE_REGEX = re.compile(r"^[1-9][0-9]{5}$")
PHONE_REGEX = re.compile(r"^[6-9]\d{9}$")  # Standard Indian 10-digit mobile format


def sanitize_string(input_str: str | None) -> str:
    """Sanitizes user input string using bleach to protect against XSS."""
    if not input_str:
        return ""
    cleaned = bleach.clean(input_str.strip(), tags=[], strip=True)
    return cleaned


def validate_registration_payload(form_data: Dict[str, Any]) -> Tuple[bool, str]:
    """Validates registration input fields."""
    email = form_data.get("email", "").strip()
    password = form_data.get("password", "")
    full_name = form_data.get("full_name", "").strip()
    phone = form_data.get("phone", "").strip()
    role = form_data.get("role", "").strip()

    if not EMAIL_REGEX.match(email):
        return False, "Invalid email address format."
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if len(full_name) < 2 or len(full_name) > 100:
        return False, "Full name must be between 2 and 100 characters."
    if phone and not PHONE_REGEX.match(phone):
        return False, "Invalid mobile number. Please provide a valid 10-digit Indian phone number."
    if role not in ("STUDENT", "LANDLORD"):
        return False, "Role must be STUDENT or LANDLORD."

    return True, ""


def validate_coordinates(lat: Any, lon: Any) -> Tuple[bool, float, float]:
    """Validates latitude and longitude values."""
    try:
        lat_val = float(lat)
        lon_val = float(lon)
    except (ValueError, TypeError):
        return False, 0.0, 0.0

    if -90.0 <= lat_val <= 90.0 and -180.0 <= lon_val <= 180.0:
        return True, lat_val, lon_val
    return False, 0.0, 0.0