"""
LLM integration: connects Suwwah to GPT-4o for itineraries and landmark summaries.
This module uses the OpenAI Python SDK to call GPT-4o.
"""

from typing import List, Dict, Optional
from openai import OpenAI
from app.config import (
    OPENAI_API_KEY,
    OPENAI_MODEL,
    OPENAI_TIMEOUT,
    MAX_ITINERARY_TOKENS,
    MAX_QA_TOKENS,
    SAND_RAG_MODE,
)
# Language Detection 
import re
from app.profiles import detect_language
from app.sand_rag import get_sand_rag

try:
    from app.sand_rag_embeddings import get_sand_rag_embeddings
except Exception:
    get_sand_rag_embeddings = None


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


# Client Initialization
client = OpenAI(api_key=OPENAI_API_KEY, timeout=OPENAI_TIMEOUT) if OPENAI_API_KEY else None

# System prompt with language enforcement
SYSTEM_PROMPT = (
    "You are Suwwah, a smart tourism assistant for Saudi Arabia. "
    "You help users with itineraries, landmarks, and city information. "
    "Be accurate, concise, and honest. "
    "Hard rule: Always reply in the same language as the user's last message."
    "Hard rule: Answer the user's exact question first."
    "Do NOT provide an itinerary unless the user explicitly asks for a plan, schedule, or عدد الأيام. "
    "If the user asks a general question, give a direct answer and at most 2 short suggestions."

)

# Internal function to call model
def _call_model(prompt: str, user_text: Optional[str] = None) -> str:

    lang_source = user_text or prompt

    if client is None:        
        return get_error_message(lang_source, "no_client")

    # Detect language from user text if available
    lang = detect_language(lang_source)
    lang_instruction = "Arabic" if lang == "ar" else "English"

    lan_system_prompt = (
        SYSTEM_PROMPT
        + " Hard rules: "
          f"1) Respond ONLY in {lang_instruction}. Never switch languages. "
          "2) If the user specifies city or duration, you MUST follow it. "
          "3) Use stored profile values only when the user does not specify them."
          "4) Keep answers practical for real tourists."
    )
    
    try:
        completion = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content":  lan_system_prompt},
                {"role": "user", "content": prompt},
            ],
            # temperature means creativity level (0 = deterministic, 1 = creative)
            temperature=0.4,
        )
        return completion.choices[0].message.content
        
    except Exception as e:
        print("OpenAI error in _call_model:", repr(e))
        return get_error_message(lang_source, "exception")

# -----------------------
# SAND context builder
# -----------------------

def build_sand_context(user_text: str) -> str:
    if SAND_RAG_MODE == "off":
        return ""

    lang = detect_language(user_text)

    if SAND_RAG_MODE == "embeddings" and get_sand_rag_embeddings:
        rag = get_sand_rag_embeddings()
        docs = rag.search(user_text, lang=lang, k=3)
    else:
        rag = get_sand_rag(use_mock_if_missing=True)
        docs = rag.search(user_text, lang=lang, k=3)

    if not docs:
        return ""

    lines = [f"- {d.text}" for d in docs]
    return "Relevant Saudi tourism narrative snippets (SAND):\n" + "\n".join(lines) + "\n\n"

# -----------------------
# Public helpers
# -----------------------

def answer_question(user_text: str) -> str:
    sand_ctx = build_sand_context(user_text)

    prompt = (
        f"{sand_ctx}"
        "Answer the user's question directly in 2-4 sentences. "
        "If helpful, add at most 2 brief suggestions. "
        "Do not create a full itinerary unless asked.\n\n"
        f"User message: {user_text}"
    )
    return _call_model(prompt, user_text=user_text)

# generate itinerary function
def generate_itinerary(user_profile: dict, poi_list: List[Dict], user_text:str) -> str:

    city: str = user_profile.get("city", "Unknown city")
    days: int = int(user_profile.get("days", 1))
    traveler_type: str = user_profile.get("traveler_type", "general")
    interests: str = user_profile.get("interests", "general")

    sand_ctx = build_sand_context(user_text)

    if poi_list:
        poi_lines = "\n".join(
            f"- {p.get('name', 'Unknown place')} "
            f"({p.get('type', 'place')}, rating {p.get('rating', 'N/A')})"
            for p in poi_list
        )
        poi_part = f"Use the following candidate places where possible:\n{poi_lines}\n\n"
    else:
        poi_part = (
            "Google Maps did not return specific places. "
            "Focus on important and realistic attractions in that city.\n\n"
        )

    prompt = (
        f"{sand_ctx}"
        f"Create a detailed {days}-day itinerary for {city} in Saudi Arabia.\n"
        f"The traveler type: {traveler_type}. Interests: {interests}.\n\n"
        f"{poi_part}"
        "The itinerary MUST:\n"
        "- Be day-by-day.\n"
        "- Include morning, afternoon, and evening sections.\n"
        "- Provide short practical justifications.\n"
        "- Be realistic for tourists in Saudi Arabia.\n"
        "- Keep the response compact and well-structured.\n"
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
    
    sand_ctx = build_sand_context(user_text)
    final_prompt = (
        f"{sand_ctx}"
        f"{prompt}"
        " Keep the answer short concise and engaging for tourists."
        )


    return _call_model(final_prompt, user_text=user_text)
