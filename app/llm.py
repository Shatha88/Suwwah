"""
LLM integration: connects Suwwah to GPT-4o for itineraries and landmark summaries.
This module uses the OpenAI Python SDK to call GPT-4o.
"""

from typing import List, Dict, Optional
from openai import OpenAI
from app.config import OPENAI_API_KEY

# Language Detection 
import re

def detect_language(text: str) -> str:
    """Detect Arabic vs English using Unicode range."""
    return "ar" if re.search(r"[\u0600-\u06FF]", text) else "en"

# Error Messages 
ERROR_MESSAGES = {
    "no_client": {
        "ar": "سُوّاح ما قدر يتصل بخدمة الذكاء الاصطناعي حالياً. حاول مرة أخرى لاحقاً.",
        "en": "Suwwah couldn't connect to the AI service. Please try again later."
    },
    "exception": {
        "ar": "سُوّاح واجه مشكلة تقنية بسيطة أثناء الاتصال بالخدمة. حاول مرة أخرى قريباً.",
        "en": "Suwwah had a small technical issue while contacting the AI service. Please try again soon."
    }
}

def get_error_message(user_text: str, error_type: str) -> str:
    lang = detect_language(user_text)
    return ERROR_MESSAGES[error_type][lang]

# Initialize OpenAI client
if OPENAI_API_KEY:
    client = OpenAI(api_key=OPENAI_API_KEY, timeout=20)
else:
    client = None

# System prompt for GPT-4o
SYSTEM_PROMPT = (
    "You are Suwwah, a smart tourism assistant for Saudi Arabia. "
    "You help users with itineraries, landmarks, and city information. "
    "Be accurate, concise, and honest. "
    "Hard rule: Always reply in the same language as the user's last message."
)

# Internal function to call GPT-4o
def _call_model(prompt: str, user_text: Optional[str] = None) -> str:
    """
    Send a prompt to GPT-4o and return the reply.
    If the model is not available or an error occurs, return a user-friendly message.
    """
    if client is None:        
        return get_error_message(user_text or prompt, "no_client")

    # Detect language from user text if available
    lang_source = user_text if user_text else prompt
    lang = detect_language(lang_source)
    lang_instruction = "Arabic" if lang == "ar" else "English"

    lan_system_prompt = (
        SYSTEM_PROMPT
        + " Hard rules: "
          f"1) Respond ONLY in {lang_instruction}. Never switch languages. "
          "2) If the user specifies city or duration, you MUST follow it. "
          "3) Use stored profile values only when the user does not specify them."
    )
    
    try:
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content":  lan_system_prompt},
                {"role": "user", "content": prompt},
            ],
        )
        return completion.choices[0].message.content
        
    except Exception as e:
        print("OpenAI error in _call_model:", repr(e))
        return get_error_message(lang_source, "exception")

# generate itinerary function
def generate_itinerary(user_profile: dict, poi_list: List[Dict], user_text:str) -> str:
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
        f"Create a detailed {days}-day itinerary for {city}.\n"
    f"The traveler type: {traveler_type}. Interests: {interests}.\n\n"
    f"{poi_part}"
    "The itinerary MUST:\n"
    "- Be day-by-day.\n"
    "- Include morning, afternoon, and evening sections.\n"
    "- Provide short practical justifications.\n"
    "- Be realistic for tourists in Saudi Arabia.\n"
    )

    return _call_model(prompt, user_text=user_text)

# prompt for landmark cultural summary
def summarize_landmark(landmark_name: str, user_text: str, city: str | None = None) -> str:
    if city:
        prompt = (
            f"Explain the landmark '{landmark_name}' in {city}, Saudi Arabia. "
            "Give a short (1–2 sentences) tourist-friendly cultural and historical summary."
        )
    else:
        prompt = (
            f"Explain the landmark '{landmark_name}' in Saudi Arabia. "
            "Give a short (1–2 sentences) tourist-friendly cultural and historical summary."
        )

    return _call_model(prompt, user_text=user_text)
