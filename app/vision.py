"""
Vision integration: optional landmark recognition using Google Cloud Vision.
If Vision is not configured or fails, detect_landmark returns None.
"""

from typing import Optional
import base64
from openai import OpenAI
from app.config import OPENAI_API_KEY, OPENAI_TIMEOUT, ENABLE_VISION

VISION_MODEL = "gpt-4o-mini"

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

def detect_landmark(image_bytes: bytes) -> Optional[str]:
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

        prompt = (
            "Identify the landmark in this image.\n"
            "Prioritize Saudi Arabia landmarks when relevant.\n"
            "Return ONLY the most likely official place/landmark name.\n"
            "If you are not confident, return exactly: unknown"
        )

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
            temperature=0,
            max_tokens=30,
        )

        # Extract response text
        result = (response.choices[0].message.content or "").strip()
        print("Vision (raw):", repr(result))

        if not result or result.lower() == "unknown":
            return None

        return result.strip(".!:\n")

    except Exception as e:
        print("Vision detection error:", repr(e))
        return None