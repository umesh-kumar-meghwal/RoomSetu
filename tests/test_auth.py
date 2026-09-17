"""
tests/test_auth.py
Unit tests for user registration, authentication, and session handling.
"""
import pytest
from app import create_app
from config import TestConfig
from utils.validators import validate_registration_payload


@pytest.fixture
def client():
    """Constructs test client."""
    app = create_app(TestConfig)
    with app.test_client() as test_client:
        with app.app_context():
            yield test_client


def test_registration_validation():
    """Validates registration input verification helper."""
    # Valid Student Payload
    valid_payload = {
        "email": "student@example.com",
        "password": "StrongPassword123",
        "full_name": "Aman Verma",
        "phone": "9876543210",
        "role": "STUDENT"
    }
    is_valid, msg = validate_registration_payload(valid_payload)
    assert is_valid is True
    assert msg == ""

    # Invalid Indian Phone
    invalid_phone = dict(valid_payload, phone="123456")
    is_valid, msg = validate_registration_payload(invalid_phone)
    assert is_valid is False
    assert "Invalid mobile number" in msg

    # Disallowed ADMIN self-registration
    invalid_role = dict(valid_payload, role="ADMIN")
    is_valid, msg = validate_registration_payload(invalid_role)
    assert is_valid is False
    assert "Role must be STUDENT or LANDLORD" in msg


def test_login_page_renders(client):
    """Ensures login endpoint is publicly accessible."""
    response = client.get("/auth/login")
    assert response.status_code == 200
    assert b"Welcome Back" in response.data


def test_logout_clears_session(client):
    """Ensures logout endpoint clears user session variables."""
    with client.session_transaction() as sess:
        sess["user_id"] = "test-user-uuid"
        sess["role"] = "STUDENT"
        sess["access_token"] = "mock-jwt"

    response = client.get("/auth/logout", follow_redirects=True)
    assert response.status_code == 200
    assert b"signed out successfully" in response.data

    with client.session_transaction() as sess:
        assert "user_id" not in sess
        assert "role" not in sess