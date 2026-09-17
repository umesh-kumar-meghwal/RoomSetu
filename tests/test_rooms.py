"""
tests/test_rooms.py
Tests Haversine distance calculations and location API constraints.
"""
import pytest
from app import create_app
from config import TestConfig
from services.location_service import LocationService


@pytest.fixture
def client():
    app = create_app(TestConfig)
    with app.test_client() as test_client:
        yield test_client


def test_haversine_accuracy():
    """
    Tests Haversine distance calculation.
    Distance between Connaught Place (28.6315, 77.2167)
    and India Gate (28.6129, 77.2295) in New Delhi is ~2.39 km.
    """
    lat1, lon1 = 28.6315, 77.2167
    lat2, lon2 = 28.6129, 77.2295

    dist = LocationService.calculate_haversine_distance(lat1, lon1, lat2, lon2)
    assert 2.2 <= dist <= 2.6


def test_nearby_rooms_api_invalid_coords(client):
    """Verifies that invalid coordinates return a 400 Bad Request error."""
    # Latitude out of bounds (> 90)
    response = client.get("/api/nearby-rooms?latitude=105.0&longitude=77.0")
    assert response.status_code == 400
    json_data = response.get_json()
    assert json_data["success"] is False
    assert "Invalid coordinates" in json_data["error"]


def test_nearby_rooms_api_missing_coords(client):
    """Verifies that missing coordinates return a 400 Bad Request error."""
    response = client.get("/api/nearby-rooms")
    assert response.status_code == 400
    json_data = response.get_json()
    assert json_data["success"] is False