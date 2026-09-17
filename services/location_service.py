"""
services/location_service.py
Mathematical calculations for geodesic distances using the Haversine equation.
Zero external proprietary dependencies.
"""
import math
from typing import List, Dict, Any

# Mean radius of Earth in kilometers
EARTH_RADIUS_KM = 6371.0088


class LocationService:
    """Computes great-circle distances between points on a sphere."""

    @staticmethod
    def calculate_haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """
        Calculates the great-circle distance between two points in kilometers.
        Formula:
            a = sin²(Δφ/2) + cos(φ1) * cos(φ2) * sin²(Δλ/2)
            c = 2 * atan2(√a, √(1−a))
            d = R * c
        """
        # Convert decimal degrees to radians
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = (
            math.sin(delta_phi / 2.0) ** 2
            + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
        )
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        distance = EARTH_RADIUS_KM * c

        return round(distance, 2)

    @classmethod
    def filter_and_sort_by_distance(
        cls,
        user_lat: float,
        user_lon: float,
        rooms_data: List[Dict[str, Any]],
        max_radius_km: float
    ) -> List[Dict[str, Any]]:
        """
        Filters room records to only those within max_radius_km of (user_lat, user_lon)
        and sorts them in ascending order of distance.
        """
        nearby = []
        for room in rooms_data:
            prop = room.get("properties")
            if not prop or prop.get("latitude") is None or prop.get("longitude") is None:
                continue

            dist = cls.calculate_haversine_distance(
                user_lat,
                user_lon,
                float(prop["latitude"]),
                float(prop["longitude"])
            )

            if dist <= max_radius_km:
                room_copy = dict(room)
                room_copy["distance_km"] = dist
                nearby.append(room_copy)

        nearby.sort(key=lambda x: x["distance_km"])
        return nearby