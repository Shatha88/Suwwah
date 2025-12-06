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


async def handle_text_message(user_id: int, text: str) -> str:
    """
    Main entry point for text messages from Telegram.
    Updates the profile and either generates an itinerary or answers a question.
    """
    # 1) Update profile FIRST
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

    # 3) General tourism Q&A
    # IMPORTANT: pass user_text so LLM locks language correctly
    return llm._call_model(text, user_text=text)


async def handle_image_message(user_id: int, image_bytes: bytes) -> str:
    """
    Main entry point for photo messages from Telegram.
    Attempts landmark recognition and then requests an LLM summary.
    """
    landmark_name = vision.detect_landmark(bytes(image_bytes))

    if not landmark_name:
        # With images there is no user text to detect language from.
        # This is a safe neutral message; you can localize later if needed.
        return (
            "We received your photo, but we could not confidently "
            "recognize a specific landmark. This may happen if the place is "
            "not in the vision model or if image quality is low.\n\n"
            "You can still ask about the location by name in a text message."
        )

    profile = profiles.get_profile(user_id)
    city = profile.get("city")

    # We don't have a user-written text here, so pass a small hint string
    # based on the profile city language is not reliable.
    # Best approach later: store last_lang in profile.
    summary = llm.summarize_landmark(landmark_name, user_text=landmark_name, city=city)

    return f"I think this is **{landmark_name}**.\n\n{summary}"
