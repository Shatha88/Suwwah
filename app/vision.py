"""
Vision integration: optional landmark recognition using Google Cloud Vision.
If Vision is not configured or fails, detect_landmark returns None.
"""

from typing import Optional

# Import Google Cloud Vision only if available
try:
    from google.cloud import vision

    # Shared Vision client (uses GOOGLE_APPLICATION_CREDENTIALS)
    vision_client: Optional["vision.ImageAnnotatorClient"] = vision.ImageAnnotatorClient()
except Exception as e:
    print("Vision client initialization error:", repr(e))
    vision_client = None


# handle landmark detection
def detect_landmark(image_bytes: bytes) -> Optional[str]:
    """
    Run landmark detection on an image and return the top landmark name,
    or None if nothing is detected or an error occurs.
    """
    if vision_client is None:
        return None

    try:
        image = vision.Image(content=image_bytes)
        response = vision_client.landmark_detection(image=image)

        if response.error.message:
            print("Vision API error:", response.error.message)
            return None

        if not response.landmark_annotations:
            return None

        top = response.landmark_annotations[0]
        return top.description
    except Exception as e:
        print("Vision detection error:", repr(e))
        return None