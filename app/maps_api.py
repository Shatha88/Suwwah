"""
Google Maps / Places integration for Suwwah.
"""

from typing import List, Dict
import requests
from app.config import GOOGLE_MAPS_KEY

# Google Places Text Search endpoint
BASE_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"

# Search for POIs function
def search_pois(query: str, city: str, limit: int = 8) -> List[Dict]:
    """
    Query Google Places for POIs that match a text query in a specific city.
    Returns a list of simplified place dictionaries (name, type, rating).
    """
    if not GOOGLE_MAPS_KEY:
        print("Google Maps key is missing; returning an empty POI list.")
        return []

    full_query = f"{query} in {city}"
    params = {"query": full_query, "key": GOOGLE_MAPS_KEY}

    try:
        response = requests.get(BASE_URL, params=params, timeout=5)
        data = response.json()
    except Exception as e:
        print("Google Maps request error:", repr(e))
        return []

    status = data.get("status", "")
    if status not in ("OK", "ZERO_RESULTS"):
        print("Google Maps API status:", status, data.get("error_message"))
        return []

    results: List[Dict] = []
    for r in data.get("results", [])[:limit]:
        results.append(
            {
                "name": r.get("name", "Unknown place"),
                "type": ", ".join(r.get("types", [])[:3]),
                "rating": r.get("rating", "N/A"),
            }
        )

    return results


# === IGNORE ===
# def _dummy_pois(city: str) -> List[Dict]:
    # """
    # Simple dummy data to keep the rest of the system testable.
    # """
    # return [
    #     {"name": f"Heritage Site in {city}", "type": "tourist_attraction", "rating": 4.7},
    #     {"name": f"Popular Mall in {city}", "type": "shopping_mall", "rating": 4.5},
    #     {"name": f"Family Park in {city}", "type": "park", "rating": 4.3},
    # ]


# def search_pois(query: str, city: str, limit: int = 8) -> List[Dict]:
    # """
    # Search for POIs relevant to the query in a given city.

    # Later:
    # - Use the Google Places Text Search / Nearby Search APIs.
    # - Return real results from the API.

    # For now:
    # - Return a fixed dummy list based on the city only.
    # """
    # # TODO: integrate real Google Maps / Places API here.
    # return _dummy_pois(city)[:limit]