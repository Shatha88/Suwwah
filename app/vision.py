"""
Vision integration: optional landmark recognition using Google Cloud Vision.
If Vision is not configured or fails, detect_landmark returns None.
"""

from typing import Optional, List, Dict
import base64
from openai import OpenAI
from app.config import OPENAI_API_KEY, OPENAI_TIMEOUT, ENABLE_VISION, VISION_MODEL

SAUDI_LANDMARK_FEATURES: dict[str, str] = {
    # Riyadh
    "Kingdom Centre Tower": (
        "Very tall blue-glass skyscraper with a huge inverted arch / U-shaped cutout "
        "near the top and a skybridge connecting the two sides of the opening."
    ),
    "Al Faisaliah Tower": (
        "Tall, slender tower shaped like a tapered pyramid with a visible metal frame "
        "and a large glass sphere (ball) near the top."
    ),
    "Al Masmak Palace": (
        "Low, rectangular mud-brick fortress with thick beige walls, wooden gates, "
        "and round corner towers in traditional Najdi style."
    ),
    "Riyadh Water Tower": (
        "Mushroom-shaped concrete water tower with a wide circular top and a narrow stem, "
        "often painted in light colors and standing alone against the skyline."
    ),
    "Diriyah (At-Turaif)": (
        "Historic adobe settlement with clusters of brown mud-brick houses, palaces, and "
        "fortified walls on a hillside overlooking a palm-filled wadi."
    ),

    # AlUla / Madain Saleh
    "Hegra (Madain Saleh)": (
        "Large rock-cut Nabataean tomb carved into a sandstone cliff, with an ornate "
        "facade, stepped top, and a single doorway in the center."
    ),
    "Jabal AlFil (Elephant Rock)": (
        "Isolated sandstone rock in the desert shaped like an elephant with a distinct "
        "arched 'trunk' touching the ground."
    ),
    "Maraya": (
        "Massive rectangular building fully covered in mirrored panels reflecting the "
        "surrounding desert mountains."
    ),

    # Jeddah
    "Al Rahmah Mosque": (
        "White seaside mosque built on pillars above the water, giving a 'floating' effect, "
        "with a domed roof and minaret extending over the sea."
    ),
    "Nassif House Museum": (
        "Traditional multi-story Hijazi house with wooden rawashin (latticed balconies) "
        "and decorative brown-and-white façade in Jeddah's old town."
    ),
    "King Abdullah Financial District (KAFD)": (
        "Cluster of modern angular glass-and-steel skyscrapers with faceted, futuristic "
        "designs forming a dense business district skyline."
    ),

    # Makkah & Madinah
    "The Clock Towers (Abraj Al Bait)": (
        "Enormous tower complex overlooking the Grand Mosque with a giant green clock "
        "face near the top and an ornate spire above it."
    ),
    "The Kaaba": (
        "Cubical structure draped in a black cloth with a golden embroidered band and door, "
        "located at the center of a large white marble courtyard filled with pilgrims."
    ),
    "Quba Mosque": (
        "White mosque complex with multiple small domes and minarets, simple clean lines, "
        "and a bright courtyard, often photographed from ground level."
    ),

    # Eastern Province
    "Ithra (King Abdulaziz Center for World Culture)": (
        "Distinctive cluster of smooth, metallic, pebble-like towers leaning and wrapping "
        "around each other with horizontal stripe texture."
    ),

    # Generic extras
    "Jeddah Corniche": (
        "Long seafront promenade along the Red Sea with walking paths, palm trees, modern "
        "sculptures, and sometimes views of the sea and city skyline."
    ),
    "Jeddah Waterfront": (
        "Developed coastal area with wide pedestrian walkways, landscaped parks, play "
        "areas, and sea views, often showing families and recreational spaces."
    ),
}

def build_landmark_hint_text() -> str:
    """Return a human-readable list for the Vision prompt."""
    lines = []
    for name, desc in SAUDI_LANDMARK_FEATURES.items():
        lines.append(f"- {name}: {desc}")
    return "\n".join(lines)

# Client Initialization
client = OpenAI(api_key=OPENAI_API_KEY, timeout=OPENAI_TIMEOUT) if OPENAI_API_KEY else None
# Mime type guessing (minimal)
def _guess_mime(image_bytes: bytes) -> str:
    """
    Minimal header-based mime guess.
    """
    if image_bytes.startswith(b"\x89PNG"):
        return "image/png"
    if image_bytes.startswith(b"\xff\xd8"):
        return "image/jpeg"
    return "image/jpeg"

def detect_landmark(image_bytes: bytes, caption: str | None = None) -> Optional[str]:
    """
    Uses OpenAI Vision to analyze a landmark in the image.
    Returns the landmark name as text, or None if not recognized.
    """
    if not ENABLE_VISION:
        print("Vision is disabled in config.")
        return None
    
    if client is None:
        print("OpenAI client is None")
        return None

    try:
        mime_type = _guess_mime(image_bytes)
        b64_image = base64.b64encode(image_bytes).decode("utf-8")

        # prompt = (
        #     "You are an expert in identifying world landmarks mainly Saudi Arabia landmarks.\n"
        #     "Look at the image and reply ONLY with the landmark name.\n"
        #     "Prioritize Saudi Arabia landmarks when relevant.\n"
        #     "Hard rule:If you are not confident, return exactly: unknown"
        # )
    
        # feature_lines = "\n".join(
        #     f"- {name}: {desc}" for name, desc in SAUDI_LANDMARK_FEATURES.items())
        landmark_hints = build_landmark_hint_text()

        caption_hint = ""
        if caption:
            caption_hint = (
                f"\nUser caption (may contain place name or city): '{caption}'. "
                "Use this ONLY as a hint and ignore it if it conflicts with the visual evidence.\n"
            )

        prompt = (
            "You are an expert in identifying worldwide landmarks, with a focus on Saudi Arabia.\n"
            "Here is a list of key Saudi landmarks and how they usually look:\n"
            f"{landmark_hints}\n"
            f"{caption_hint}\n"
            "Task:\n"
            "1) Look only at the image.\n"
            "2) Choose the SINGLE best-matching landmark name from the list above.\n"
            "3) Reply ONLY with that canonical name.\n"
            "4) If none are a reasonable match, reply exactly: unknown."
        )
            # "You are a VERY careful expert in identifying landmarks, with a focus on "
            # "Saudi Arabian tourist attractions.\n\n"
            # "Here are some important landmarks with their distinctive visual features:\n"
            # f"{feature_lines}\n\n"
            # "Look at the image and identify the SINGLE main landmark.\n"
            # "Output STRICT JSON ONLY in this format:\n"
            # '{"name": "<landmark name or \'unknown\'>", "confidence": 0.xx}\n\n'
            # "Rules:\n"
            # "1) If the image clearly matches one of the described Saudi landmarks, "
            # "return EXACTLY that canonical name.\n"
            # "2) Never mix up Kingdom Centre Tower and Al Faisaliah Tower:\n"
            # "   - If you see a big inverted arch with a skybridge → 'Kingdom Centre Tower'.\n"
            # "   - If you see a tapered tower with a ball near the top → 'Al Faisaliah Tower'.\n"
            # "3) Do NOT include city names in the 'name' field.\n"
            # "4) If you are not at least 80% confident, set name='unknown' and confidence<=0.5.\n"
            # "5) Respond with ONLY the JSON object, no explanation."

        response = client.chat.completions.create(
            model=VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{b64_image}"
                            },
                        },
                    ],
                }
            ],
        )

        print(response)
        # Extract response text
        result = (response.choices[0].message.content or "").strip()
        print("Vision (raw):", repr(result))

        if not result or result.lower() == "unknown":
            return None

        # Snap noisy output to our canonical label if possible
        # canonical = normalize_landmark_name(result)
        return result

    except Exception as e:
        print("Vision detection error:", repr(e))
        return None