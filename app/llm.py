"""
LLM integration: connects Suwwah to GPT-4o for itineraries and landmark summaries.
This module uses the OpenAI Python SDK to call GPT-4o.
"""

from typing import List, Dict, Optional
from openai import OpenAI
from app.config import OPENAI_API_KEY

# Initialize OpenAI client
if OPENAI_API_KEY:
    client = OpenAI(api_key=OPENAI_API_KEY, timeout=20)
else:
    client = None

# System prompt for GPT-4o
SYSTEM_PROMPT = (
    "You are Suwwah, a bilingual (Arabic/English) smart tourism assistant "
    "for Saudi Arabia. You help users with itineraries, landmarks, and city "
    "information. You always reply in the same language as the user message. "
    "Be accurate, concise, and honest."
)

# Internal function to call GPT-4o
def _call_model(prompt: str) -> str:
    
    """
    Send a prompt to GPT-4o and return the reply.
    If the model is not available or an error occurs, return a user-friendly message.
    """
    if client is None:        
        return (
            "The AI service will be added soon. "
            "Please try again later."
        )

    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini" or "gpt-4o",  # or "gpt-4o" if preferred
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        return completion.choices[0].message.content
    except Exception as e:
        print("OpenAI error in _call_model:", repr(e))
        return (
            "We faced a temporary technical problem while contacting "
            "the AI service. Please try again in a few minutes."
        )

# generate itinerary function
def generate_itinerary(user_profile: dict, poi_list: List[Dict]) -> str:
    """
    Create a prompt for GPT-4o that asks for a multi-day itinerary based on
    the user profile and a list of candidate POIs from Google Maps.

    Or, returns a simple stub text.
    """
    city: str = user_profile.get("city", "Unknown city")
    days: int = int(user_profile.get("days", 1))
    traveler_type: str = user_profile.get("traveler_type", "general")
    interests: str = user_profile.get("interests", "general")

    if poi_list:
        poi_lines = "\n".join(
            f"- {p.get('name', 'Unknown place')} "
            f"({p.get('type', 'place')}, rating {p.get('rating', 'N/A')})"
            for p in poi_list
        )
        poi_part = (
            f"Use the following candidate places where possible:\n{poi_lines}\n\n"
        )
    else:
        poi_part = (
            "Google Maps did not return specific places, so focus on important "
            "and realistic attractions in that city.\n\n"
        )

    prompt = (
        f"Create a practical {days}-day itinerary in {city} for a "
        f"{traveler_type} traveler. Interests: {interests}.\n\n"
        f"{poi_part}"
        "Include morning/afternoon/evening segments and short justifications "
        "for each stop. Ensure the itinerary is realistic for Saudi Arabia."
    )

    return _call_model(prompt)

# prompt for landmark cultural summary
def summarize_landmark(landmark_name: str, city: str | None = None) -> str:
    """
    Ask GPT-4o for a short cultural and historical summary of a landmark.
    """
    if city:
        prompt = (
            f"Explain the landmark '{landmark_name}' in {city}, Saudi Arabia. "
            "Give a short cultural and historical summary that is suitable "
            "for tourists visiting the country."
        )
    else:
        prompt = (
            f"Explain the landmark '{landmark_name}' in Saudi Arabia. "
            "Give a short cultural and historical summary that is suitable "
            "for tourists visiting the country."
        )

    return _call_model(prompt)
