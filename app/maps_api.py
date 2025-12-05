import time
from typing import List, Dict
import requests
from app.config import GOOGLE_MAPS_KEY

BASE_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"

# -----------------------
# SIMPLE IN-MEMORY CACHE
# -----------------------
_CACHE = {}
CACHE_TTL_SECONDS = 300   # 5 minutes


def search_pois(query: str, city: str, limit: int = 8) -> List[Dict]:
    """
    Query Google Places for POIs that match a text query in a specific city.
    Returns a list of simplified place dictionaries (name, type, rating).
    """

    if not GOOGLE_MAPS_KEY:
        print("Google Maps key is missing; returning an empty POI list.")
        return []

    # -----------------------
    # CACHE CHECK
    # -----------------------
    key = (query.strip().lower(), city.strip().lower(), limit)
    now = time.time()

    print(f"[MAPS] Checking cache for key: {key}")

    if key in _CACHE:
        ts, cached = _CACHE[key]
        age = now - ts
        print(f"[MAPS] Cache entry FOUND. Age = {age:.1f}s")

        if age < CACHE_TTL_SECONDS:
            print(f"[MAPS] >>> CACHE HIT <<< Returning cached results.")
            return cached
        else:
            print(f"[MAPS] Cache EXPIRED. Removing old entry.")
            _CACHE.pop(key, None)
    else:
        print(f"[MAPS] No cache entry found.")

    # -----------------------
    # CALL GOOGLE API
    # -----------------------
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

    results = []
    for r in data.get("results", [])[:limit]:
        results.append(
            {
                "name": r.get("name", "Unknown place"),
                "type": ", ".join(r.get("types", [])[:3]),
                "rating": r.get("rating", "N/A")
            }
        )

    # -----------------------
    # SAVE TO CACHE
    # -----------------------
    _CACHE[key] = (time.time(), results)
    print(f"[MAPS] Saved new result to cache for key: {key}")

    return results