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
import json

# language detection helper
def detect_language(text: str) -> str:
    return "ar" if re.search(r"[\u0600-\u06FF]", text) else "en"

# Mapping: user_id -> profile dictionary
USER_PROFILES: Dict[int, dict] = {}

def get_default_profile() -> dict:
    return {
        "city": "Riyadh",
        "days": 2,
        "traveler_type": "family",
        "interests": "culture, malls, parks",
        "last_lang": "en",
        "llm_enriched": False,
    }


def get_profile(user_id: int) -> dict:
    profile = USER_PROFILES.get(user_id)
    return profile.copy() if profile else get_default_profile()

def save_profile(user_id: int, profile: dict) -> None:
    USER_PROFILES[user_id] = profile


# Internal helpers: keyword-based extraction

_ARABIC_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789")

def _normalize_digits(text: str) -> str:
    # Convert Arabic digits to English digits
    return text.translate(_ARABIC_DIGITS)

def _detect_days(text: str) -> Optional[int]:
    t = _normalize_digits(text).strip()
    lower = t.lower()

    # Match patterns like:
    # "2 days", "10 day", "3-day", "٣ أيام" (after normalization), "2 weeks", "أسبوعين"
    # We support number + unit in Arabic/English.

    # Numeric + unit
    m = re.search(
        r"\b(\d{1,2})\s*[- ]?\s*(day|days|night|nights|week|weeks|يوم|أيام|ايام|ليلة|ليله|ليال|اسبوع|أسبوع|أسابيع|اسابيع)\b",
        lower
    )
    if m:
        num = int(m.group(1))
        unit = m.group(2)

        # Convert unit to days
        if unit in {"week", "weeks", "اسبوع", "أسبوع", "أسابيع"}:
            return num * 7

        # Treat nights like days for itinerary length
        return num

    # 2) Special Arabic dual forms (no numbers)
    # These are language features, so it’s ok to handle them explicitly.
    if "يومين" in text:
        return 2
    if "أسبوعين" in text or "اسبوعين" in text:
        return 14

    # 3) Weekend hint
    if ("weekend" in lower or "عطلة نهاية الأسبوع" or "عطلة نهاية الاسبوع" in text):
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

    # duplicate preserving order
    unique: List[str] = []
    for i in interests:
        if i not in unique:
            unique.append(i)

    return ", ".join(unique)

# LLM-based extraction fallback
def _extract_profile_with_llm(user_text: str) -> dict:
    """
    Uses the LLM to extract structured fields when rules fail.
    Import is local to avoid circular dependencies.
    """
    try:
        from app import llm
    except Exception:
        return {}

    prompt = (
        "Extract the user's travel preferences as JSON ONLY.\n"
        "Fields:\n"
        "- city: string or null\n"
        "- days: integer or null\n"
        "- traveler_type: one of [family, cultural, adventurer] or null\n"
        "- interests: short comma-separated string or null\n\n"
        f"User message:\n{user_text}\n\n"
        "Return JSON only, no extra text."
    )

    raw = llm._call_model(prompt, user_text=user_text)

    try:
        data = json.loads(raw)
        if not isinstance(data, dict):
            return {}
        return data
    except Exception:
        return {}
    
# ----------------------------
# Public API
# ----------------------------

def update_profile_from_text(user_id: int, text: str) -> dict:
    """
    Update a profile using lightweight keyword rules extracted from user text.
    """
    profile = get_profile(user_id)

    profile["last_lang"] = detect_language(text)
    
    # Rule-based extraction
    days = _detect_days(text)
    city = _detect_city(text)
    traveler = _detect_traveler_type(text)
    interests = _detect_interests(text)

    # Update from rules if detected
    if days is not None:
        profile["days"] = days
    if city:
        profile["city"] = city
    if traveler:
        profile["traveler_type"] = traveler
    if interests:
        profile["interests"] = interests

    # If rules found nothing new, use LLM fallback once
    rules_found_something = any([
        days is not None,
        bool(city),
        bool(traveler),
        bool(interests),
    ])

    if not rules_found_something and not profile.get("llm_enriched", False):
        llm_data = _extract_profile_with_llm(text)

        # Apply safe updates
        if isinstance(llm_data.get("days"), int):
            profile["days"] = llm_data["days"]
        if isinstance(llm_data.get("city"), str) and llm_data["city"]:
            profile["city"] = llm_data["city"]
        if llm_data.get("traveler_type") in {"family", "cultural", "adventurer"}:
            profile["traveler_type"] = llm_data["traveler_type"]
        if isinstance(llm_data.get("interests"), str) and llm_data["interests"]:
            profile["interests"] = llm_data["interests"]

        profile["llm_enriched"] = True

    save_profile(user_id, profile)
    return profile
