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
SYSTEM_PROMPT = ("""
You are Suwwah, a bilingual (Arabic/English) smart tourism assistant for
Saudi Arabia. You speak with the tone of a helpful local tour guide.

Core abilities:
- Design detailed, day-by-day travel itineraries for cities in Saudi Arabia.
- Answer tourism questions about landmarks, neighborhoods, and activities.
- Suggest realistic POIs based on Google Maps / Places data when available.

Hard rules:
1) Always reply in the same language as the user's last message.
2) When the user asks you to PLAN or ORGANIZE a trip, you MUST provide
   a concrete, structured itinerary. Do NOT say that you cannot plan.
   If some information is missing, make reasonable assumptions and state them.
3) Avoid generic apologies like “I cannot do that” or “Sorry, I can’t”.
   Instead, give your best helpful answer and clearly mention any limits
   (for example: prices may change, opening hours may differ, etc.).
4) Follow user constraints (days, family/adventure, budget, city) whenever
   they are mentioned. Do not ignore them.
5) Keep answers concise but practically useful: day-by-day, morning/afternoon/
   evening where applicable, with short justifications.
"""
)

# Internal function to call model
def _call_model(prompt: str, user_text: Optional[str] = None) -> str:

    lang_source = user_text or prompt

    if client is None:        
        return get_error_message(lang_source, "no_client")

    # Detect language from user text if available
    lang = detect_language(lang_source)
    lang_instruction = "Arabic" if lang == "ar" else "English"

    # lan_system_prompt = (
    #     SYSTEM_PROMPT
    #     + " Hard rules: "
    #       f"1) Respond ONLY in {lang_instruction}. Never switch languages. "
    #       "2) If the user specifies city or duration, you MUST follow it. "
    #       "3) Use stored profile values only when the user does not specify them."
    #       "4) Keep answers practical for real tourists."
    #       "5) Be friendly and helpful."
    # )
    
    try:
        completion = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content":  SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            # temperature means creativity level (0 = deterministic, 1 = creative)
            temperature=0.6,
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
        "Answer the user's question directly in 2-4 sentences unless the user asks for a plan, schedule, tour or count of days/weeks. "
        "If helpful, add at most 2 brief suggestions. "
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

    lang = detect_language(user_text)
    lang_name = "Arabic" if lang == "ar" else "English"

    if sand_ctx.strip():
        context_block = (
            "CONTEXT FROM SAUDI TOURISM POSTS (SAND)\n"
            "These snippets are BACKGROUND MATERIAL ONLY.\n"
            "- They are NOT written by the user.\n"
            "- Use them only to enrich descriptions and cultural details.\n"
            "- Do NOT quote them at length or talk about them directly.\n"
            "- Ignore their language; your answer must be in "
            f"{lang_name}.\n\n"
            f"{sand_ctx}\n"
            "END OF CONTEXT\n\n")

    if poi_list:
        poi_lines = "\n".join(
            f"- {p.get('name', 'Unknown place')} "
            f"({p.get('type', 'place')}, rating {p.get('rating', 'N/A')})"
            for p in poi_list
        )
        poi_part = ("CANDIDATE PLACES FROM GOOGLE MAPS\n"
            "Use these where appropriate, but you may add others.\n"
            f"{poi_lines}\n\n")
    else:
        poi_part = (
            "No candidate places were returned from Maps. "
            "You must still propose realistic places and activities "
            "in Saudi Arabia based on your own knowledge.\n\n"
        )

    prompt = (
        f"{context_block if sand_ctx.strip() else ''}"
        "USER TRIP REQUEST (this is what you must answer):\n"
        f"\"\"\"{user_text}\"\"\"\n\n"
        f"Create a detailed {days}-day itinerary for {city} in Saudi Arabia.\n"
        f"Traveler type: {traveler_type}. Interests: {interests}.\n\n"
        f"{poi_part}"
        "The itinerary MUST:\n"
        "- Be day-by-day.\n"
        "- Include morning, afternoon, and evening sections.\n"
        "- Provide short practical justifications.\n"
        "- Be realistic for tourists in Saudi Arabia.\n"
        "- Keep the response compact and well-structured.\n"
        "- Respond ONLY to the user request above, treating the CONTEXT and\n"
        "  CANDIDATE PLACES as helper information, not as questions.\n"
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
