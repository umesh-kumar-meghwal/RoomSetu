"""
tests/test_permissions.py
Validates role guards and tests against privilege escalation.
"""
import pytest
from app import create_app
from config import TestConfig


@pytest.fixture
def client():
    app = create_app(TestConfig)
    with app.test_client() as test_client:
        yield test_client


def test_student_cannot_access_admin_dashboard(client):
    """Ensures a student session cannot access the admin panel."""
    with client.session_transaction() as sess:
        sess["user_id"] = "student-uuid"
        sess["role"] = "STUDENT"
        sess["access_token"] = "valid-token"

    response = client.get("/admin/dashboard")
    assert response.status_code == 403


def test_unauthenticated_user_redirected(client):
    """Ensures unauthenticated access to student dashboard redirects to login."""
    response = client.get("/student/dashboard")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_student_cannot_access_landlord_routes(client):
    """Ensures a student cannot access landlord property management."""
    with client.session_transaction() as sess:
        sess["user_id"] = "student-uuid"
        sess["role"] = "STUDENT"
        sess["access_token"] = "valid-token"

    response = client.get("/landlord/properties")
    assert response.status_code == 403