"""
tests/test_properties.py
Tests public room search filters and query parameters.
"""
import pytest
from app import create_app
from config import TestConfig


@pytest.fixture
def client():
    app = create_app(TestConfig)
    with app.test_client() as test_client:
        yield test_client


def test_browse_properties_view(client):
    """Validates that public room exploration loads successfully."""
    response = client.get("/properties/browse")
    assert response.status_code == 200
    assert b"Find Verified Student Rooms" in response.data


def test_browse_properties_filters(client):
    """Validates that filter query parameters are handled without errors."""
    response = client.get("/properties/browse?city=Kota&room_type=SINGLE&max_rent=8000&has_wifi=1")
    assert response.status_code == 200