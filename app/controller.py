"""
Application controller: connects text/photos from Telegram to profiles,
Google Maps, the LLM, and the Vision module.
This file contains the main application logic for Suwwah.
"""

from app import llm, maps_api, vision, profiles


def is_itinerary_request(text: str) -> bool:
    """
    Heuristic to detect if the user is asking for an itinerary or trip plan.
    """
    keywords = [
        "plan a trip",
        "itinerary",
        "day trip",
        "days in",
        "what to do",
        "where to go",
        "رحلة",
        "جدول",
        "برنامج",
        "خطط لي",
        "وين اروح",
        "ما هي المعالم",
        "فعاليات",
        "أماكن سياحية",
    ]
    lower = text.lower()
    return any(k in lower for k in keywords)

def is_profile_reset_request(text: str) -> bool:
    """
    Lightweight detection for explicit preference changes/resets.
    This helps allow the LLM fallback to re-run when the user clearly wants changes.
    """
    lower = text.lower()
    arabic = text

    patterns = [
        "change my plan",
        "change my preferences",
        "update my preferences",
        "reset my preferences",
        "new plan",

        "غير خطتي",
        "غير التفضيلات",
        "حدث تفضيلاتي",
        "ابغى خطة جديدة",
        "خطة جديدة",
        "ابدأ من جديد",
    ]
    return any(p in lower or p in arabic for p in patterns)

async def handle_text_message(user_id: int, text: str) -> str:
    """
    Main entry point for text messages from Telegram.
    Updates the profile and either generates an itinerary or answers a question.
    """
    # If user explicitly asks to change/reset preferences,
    # allow LLM enrichment to run again by resetting the flag.
    if is_profile_reset_request(text):
        profile = profiles.get_profile(user_id)
        profile["llm_enriched"] = False
        profiles.save_profile(user_id, profile)

    # 1) Update profile FIRST (rules -> optional LLM fallback)
    profile = profiles.update_profile_from_text(user_id, text)

    # 2) Itinerary path
    if is_itinerary_request(text):
        traveler_type = profile.get("traveler_type", "general")

        if traveler_type == "family":
            query = "family attractions and parks"
        elif traveler_type == "cultural":
            query = "museums and heritage sites"
        elif traveler_type == "adventurer":
            query = "outdoor and adventure activities"
        else:
            query = "tourist attractions"

        pois = maps_api.search_pois(query, profile["city"], limit=8)

        # IMPORTANT: pass user_text so LLM locks language correctly
        return llm.generate_itinerary(profile, pois, user_text=text)

    # 3) General tourism Q&A (fast path)
    return llm.answer_question(text)


async def handle_image_message(user_id: int, image_bytes: bytes, caption: str | None = None) -> str:
    """
    Main entry point for photo messages from Telegram.
    Attempts landmark recognition and then requests an LLM summary.
    """
    # Detect landmark from image
    landmark_name = vision.detect_landmark(bytes(image_bytes), caption=caption)

    # Fetch profile early to get last_lang safely
    profile = profiles.get_profile(user_id)
    last_lang = profile.get("last_lang", "en")


    if not landmark_name:
        if last_lang == "ar":
            return (
                "وصلتنا صورتك، لكن لم نتمكن من التعرف على معلم محدد بثقة. "
                "قد يحدث ذلك إذا لم يكن المعلم ضمن نطاق التعرف أو كانت جودة الصورة منخفضة.\n\n"
                "يمكنك كتابة اسم الموقع في رسالة نصية."
            )
        return (
            "We received your photo, but we could not confidently recognize a specific landmark. "
            "This may happen if the landmark is out of scope or if image quality is low.\n\n"
            "You can still ask about the location by name in a text message."
        )
        
    user_text = caption if caption else ("اكتب الرد بالعربية" if last_lang == "ar" else "Reply in English")
    summary = llm.summarize_landmark(landmark_name, user_text=user_text)

    return summary
