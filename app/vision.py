"""
Vision integration: optional landmark recognition using Google Cloud Vision.
If Vision is not configured or fails, detect_landmark returns None.
"""

from typing import Optional
import base64
from openai import OpenAI

# Initialize OpenAI Vision client
try:
    client = OpenAI()  # Uses OPENAI_API_KEY from .env
except Exception as e:
    print("OpenAI client initialization error:", repr(e))
    client = None


def detect_landmark(image_bytes: bytes) -> Optional[str]:
    """
    Uses OpenAI Vision to analyze a landmark in the image.
    Returns the landmark name as text, or None if not recognized.
    """

    if client is None:
        print("OpenAI client is None")
        return None

    try:
        # Convert image to Base64
        b64_image = base64.b64encode(image_bytes).decode("utf-8")

        # Send image to OpenAI Vision
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "You are an expert in identifying world landmarks. "
                                "Look at the image and reply ONLY with the landmark name. "
                                "If you are not sure, reply exactly: unknown."
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{b64_image}"
                            },
                        },
                    ],
                }
            ],
            temperature=0,
        )

        # Extract response text
        result = response.choices[0].message.content.strip()
        print("Vision (raw):", repr(result))

        if not result or result.lower() == "unknown":
            return None

        return result

    except Exception as e:
        print("Vision detection error:", repr(e))
        return None