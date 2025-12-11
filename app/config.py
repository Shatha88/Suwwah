"""
Configuration loader: reads API keys and environment settings from .env file.
"""

import os


try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    # In production (e.g., Pella), env vars should be set in the host settings.
    pass

# Telegram bot API token
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# OpenAI API key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
OPENAI_TIMEOUT = int(os.getenv("OPENAI_TIMEOUT", "20"))  # seconds

# Google Maps API key
GOOGLE_MAPS_KEY = os.getenv("GOOGLE_MAPS_KEY", "")

# Application environment: "development" or "production"
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Feature toggles
ENABLE_MAPS = os.getenv("ENABLE_MAPS", "1") == "1"
ENABLE_VISION = os.getenv("ENABLE_VISION", "1") == "1"

MAX_ITINERARY_TOKENS = int(os.getenv("MAX_ITINERARY_TOKENS", "450"))
MAX_QA_TOKENS = int(os.getenv("MAX_QA_TOKENS", "200"))

# Optional RAG mode for itinerary generation: "off" | "tfidf" | "embeddings"
SAND_RAG_MODE = os.getenv("SAND_RAG_MODE", "tfidf").lower()