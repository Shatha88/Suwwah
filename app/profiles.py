"""
User profile management for Suwwah.

Each user has a small profile:
- city
- days
- traveler_type
- interests

This module uses lightweight rule-based extraction from user text.
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple, List
import re

def detect_language(text: str) -> str:
    return "ar" if re.search(r"[\u0600-\u06FF]", text) else "en"

# Mapping: user_id -> profile dictionary
USER_PROFILES: Dict[int, dict] = {}


def get_default_profile() -> dict:
    """Return a fresh default profile object."""
    return {
        "city": "Riyadh",
        "days": 2,
        "traveler_type": "family",
        "interests": "culture, malls, parks",
    }


def get_profile(user_id: int) -> dict:
    """
    Fetch the profile for a user_id.
    Returns a stored profile or a fresh default one.
    """
    profile = USER_PROFILES.get(user_id)
    return profile.copy() if profile else get_default_profile()


def save_profile(user_id: int, profile: dict) -> None:
    """Store or update the profile for a user_id."""
    USER_PROFILES[user_id] = profile


# ----------------------------
# Internal helpers
# ----------------------------

def _detect_days(text: str) -> Optional[int]:
    t = text.strip()
    lower = t.lower()

    # 1) English numeric patterns: "2 days", "3 day", "2-day"
    m = re.search(r"\b([1-7])\s*[- ]?\s*(day|days)\b", lower)
    if m:
        return int(m.group(1))

    # 2) English word patterns
    word_days = {
        "one day": 1,
        "two days": 2,
        "three days": 3,
        "four days": 4,
        "five days": 5,
        "six days": 6,
        "seven days": 7,
    }
    for k, v in word_days.items():
        if k in lower:
            return v

    # 3) Arabic patterns
    arabic_patterns: List[Tuple[str, int]] = [
        (r"يوم\s*واحد", 1),
        (r"يومين", 2),
        (r"ثلاث(ة)?\s*أيام", 3),
        (r"أربع(ة)?\s*أيام", 4),
        (r"خمس(ة)?\s*أيام", 5),
        (r"ست(ة)?\s*أيام", 6),
        (r"سبع(ة)?\s*أيام", 7),
    ]
    for pattern, val in arabic_patterns:
        if re.search(pattern, t):
            return val

    # 4) Week patterns -> assume 7
    if "week" in lower or "أسبوع" in t or "اسبوع" in t:
        return 7

    # 5) Weekend hint -> assume 2 (optional, safe)
    if "weekend" in lower or "عطلة نهاية الأسبوع" in t:
        return 2

    return None


def _detect_city(text: str) -> Optional[str]:
    t = text.strip()
    lower = t.lower()

    # Ordered: first match wins
    if re.search(r"\briyadh\b", lower) or "الرياض" in t:
        return "Riyadh"
    if re.search(r"\balula\b", lower) or "العلا" in t:
        return "AlUla"
    if re.search(r"\bjeddah\b", lower) or "جدة" in t or "جده" in t:
        return "Jeddah"

    return None


def _detect_traveler_type(text: str) -> Optional[str]:
    t = text.strip()
    lower = t.lower()

    if "family" in lower or "عائلة" in t or "kids" in lower or "children" in lower:
        return "family"
    if "culture" in lower or "cultural" in lower or "heritage" in lower or "ثقافة" in t or "تراث" in t:
        return "cultural"
    if "adventure" in lower or "adventur" in lower or "hiking" in lower or "مغامر" in t or "مغامرة" in t:
        return "adventurer"

    return None


def _detect_interests(text: str) -> Optional[str]:
    """
    Optional interest enrichment.
    Returns a comma-separated interest string if something is detected.
    """
    t = text.strip()
    lower = t.lower()

    interests: List[str] = []

    # English
    if any(k in lower for k in ["history", "heritage", "museum", "culture"]):
        interests.append("culture")
    if any(k in lower for k in ["mall", "shopping"]):
        interests.append("malls")
    if any(k in lower for k in ["park", "garden"]):
        interests.append("parks")
    if any(k in lower for k in ["food", "restaurant", "cafe"]):
        interests.append("food")
    if any(k in lower for k in ["nature", "mountain", "desert"]):
        interests.append("nature")
    if any(k in lower for k in ["beach", "sea"]):
        interests.append("beaches")

    # Arabic
    if any(k in t for k in ["تاريخ", "تراث", "متحف", "ثقافة"]):
        interests.append("culture")
    if any(k in t for k in ["مول", "تسوق", "أسواق"]):
        interests.append("malls")
    if any(k in t for k in ["حديقة", "منتزه"]):
        interests.append("parks")
    if any(k in t for k in ["مطاعم", "قهوة", "كافيه"]):
        interests.append("food")
    if any(k in t for k in ["طبيعة", "جبال", "صحراء"]):
        interests.append("nature")
    if any(k in t for k in ["شاطئ", "البحر"]):
        interests.append("beaches")

    if not interests:
        return None

    # de-duplicate while preserving order
    unique: List[str] = []
    for i in interests:
        if i not in unique:
            unique.append(i)

    return ", ".join(unique)


# ----------------------------
# Public API
# ----------------------------

def update_profile_from_text(user_id: int, text: str) -> dict:
    """
    Update a profile using lightweight keyword rules extracted from user text.
    """
    profile = get_profile(user_id)

    profile["last_lang"] = detect_language(text)
    
    days = _detect_days(text)
    if days is not None:
        profile["days"] = days

    city = _detect_city(text)
    if city:
        profile["city"] = city

    traveler = _detect_traveler_type(text)
    if traveler:
        profile["traveler_type"] = traveler

    # Optional interest enrichment (safe override)
    interests = _detect_interests(text)
    if interests:
        profile["interests"] = interests

    save_profile(user_id, profile)
    return profile
