"""
Configuration loader: reads API keys and environment settings from .env file.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env (if it exists)
load_dotenv()

# Telegram bot API token
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# OpenAI API key
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Google Maps API key
GOOGLE_MAPS_KEY = os.getenv("GOOGLE_MAPS_KEY")

# Application environment: "development" or "production"
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Vision API key (if you use a separate vision service)
# VISION_API_KEY = os.getenv("VISION_API_KEY")
