"""
User profile management for Suwwah.

Each user has a small profile:
- city
- days
- traveler_type
- interests

"""

from typing import Dict

# Mapping: user_id -> profile dictionar
USER_PROFILES: Dict[int, dict] = {}

# Default profile values
def get_default_profile() -> dict:
    """Return a default profile when the user has not provided preferences yet."""
    return {
        "city": "Riyadh",
        "days": 2,
        "traveler_type": "family",
        "interests": "culture, malls, parks",
    }

# Profile management functions
def get_profile(user_id: int) -> dict:
    """Fetch the profile for a user_id or a default one if none exists."""
    return USER_PROFILES.get(user_id, get_default_profile())


def save_profile(user_id: int, profile: dict) -> None:
    """Store or update the profile for a user_id."""
    USER_PROFILES[user_id] = profile


def update_profile_from_text(user_id: int, text: str) -> dict:
    """
    Update a profile using simple keyword rules extracted from user text
    (city names and traveler type).
    """
    profile = get_profile(user_id)

    # Add days handling Here
    if "1 day" in text or "يوم واحد" in text:
        profile["days"] = 1
    if "3 days" in text or "3 أيام" in text or "ثلاثة أيام" in text:
        profile["days"] = 3
    if "4 days" in text or "4 أيام" in text or "أربعة أيام" in text:
        profile["days"] = 4
    if "5 days" in text or "5 أيام" in text or "خمسة أيام" in text:
        profile["days"] = 5
    if "6 days" in text or "6 أيام" in text or "ستة أيام" in text:
        profile["days"] = 6
    if "7 days" in text or "7 أيام" in text or "سبعة أيام" in text:
        profile["days"] = 7
    if "1 week" in text or "اسبوع 1" in text or "اسبوع واحد" in text:
        profile["days"] = 7

    # City detection (Arabic and English)
    if "Riyadh" in text or "الرياض" in text:
        profile["city"] = "Riyadh"
    if "AlUla" in text or "العلا" in text:
        profile["city"] = "AlUla"
    if "Jeddah" in text or "جدة" in text or "جده" in text:
        profile["city"] = "Jeddah"

    # Traveler type detection
    lower = text.lower()
    if "family" in lower or "عائلة" in text:
        profile["traveler_type"] = "family"
    if "culture" in lower or "ثقافة" in text:
        profile["traveler_type"] = "cultural"
    if "adventure" in lower or "مغامر" in text or "مغامرة" in text:
        profile["traveler_type"] = "adventurer"

    save_profile(user_id, profile)
    return profile
