"""
Google Maps / Places integration for Suwwah.
"""

import time
from typing import List, Dict, Optional
import requests
from app.config import GOOGLE_MAPS_KEY, ENVIRONMENT, ENABLE_MAPS

BASE_URL = "https://maps.googleapis.com/maps/api/place/textsearch/json"

# -----------------------
# SIMPLE IN-MEMORY CACHE
# -----------------------
_CACHE = {}
CACHE_TTL_SECONDS = 300   # 5 minutes

# reuse HTTP connections
_SESSION = requests.Session()

def _log(msg: str) -> None:
    if ENVIRONMENT == "development":
        print(f"[MAPS] {msg}")

def search_pois(query: str, city: str, limit: int = 8, lang: Optional[str] = None) -> List[Dict]:
    """
    Query Google Places for POIs that match a text query in a specific city.
    Returns a list of simplified place dictionaries (name, type, rating).
    """

    if not GOOGLE_MAPS_KEY or not ENABLE_MAPS:
        print("Google Maps key is missing; returning an empty POI list.")
        _log("[MAPS] GOOGLE_MAPS_KEY missing; returning empty POI list.")
        return []
    
    q = (query or "").strip()
    c = (city or "").strip()

    if not q or not c:
        return []
    
    # -----------------------
    # CACHE CHECK
    # -----------------------
    cache_lang = lang or "auto"
    key = (q.lower(), c.lower(), limit, cache_lang)
    now = time.time()

    if key in _CACHE:
        ts, cached = _CACHE[key]
        if now - ts < CACHE_TTL_SECONDS:
            _log(f"[MAPS] Cache HIT for key: {key}")
            return cached
        _CACHE.pop(key, None)

    # -----------------------
    # CALL GOOGLE API
    # -----------------------
    full_query = f"{q} in {c}"
    params = {
        "query": full_query,
        "key": GOOGLE_MAPS_KEY,
        "region": "sa",
    }

    # Let Google Maps handle language auto-detection if lang is None
    if lang in ("en", "ar"):
        params["language"] = lang

    try:
        response = _SESSION.get(BASE_URL, params=params, timeout=6)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        print("Google Maps request error:", repr(e))
        _log(f"[MAPS] Request error for key: {key} - {repr(e)}")
        return []

    status = data.get("status", "")
    if status not in ("OK", "ZERO_RESULTS"):
        print("Google Maps API status:", status, data.get("error_message"))
        _log(f"[MAPS] API error for key: {key} - status: {status} | message: {data.get('error_message')}")
        return []

    results = []
    for r in data.get("results", [])[:limit]:
        results.append(
            {
                "name": r.get("name", "Unknown place"),
                "type": ", ".join((r.get("types") or [])[:3]),
                "rating": r.get("rating", "N/A"),
                "address": r.get("formatted_address", ""),
                "place_id": r.get("place_id", ""),
            }
        )

    # -----------------------
    # SAVE TO CACHE
    # -----------------------
    _CACHE[key] = (time.time(), results)
    print(f"[MAPS] Saved new result to cache for key: {key}")
    _log(f"[MAPS] Cached: {key}")

    return results