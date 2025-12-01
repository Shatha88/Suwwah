"""
Telegram interface: receives user messages/photos and forwards them to the controller
"""

import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from app import controller, config

# Read TELEGRAM_TOKEN from .env or config
load_dotenv()
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN") or config.TELEGRAM_TOKEN

# /start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /start command: send a short introduction and usage hints.
    """
    user_first_name = update.effective_user.first_name or "there"
    text = (
        f"Welcome {user_first_name} 👋\n\n"
        "We built Suwwah as a smart tourism assistant for Saudi Arabia.\n"
        "You can:\n"
        "• Ask for a plan, e.g. “Plan a 2-day family trip in Riyadh”.\n"
        "• Ask about any Saudi city or landmark.\n"
        "• Send a photo of a landmark to get a brief description.\n"
    )
    await update.message.reply_text(text)

# Text message handler
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle regular text messages and delegate to the controller.
    """
    try:
        user_text = update.message.text or ""
        user_id = update.effective_user.id
        reply = await controller.handle_text_message(user_id, user_text)
        await update.message.reply_text(reply, parse_mode="Markdown")
    except Exception as e:
        print("Error in handle_text:", repr(e))
        await update.message.reply_text(
            "We as a team ran into an internal error while processing your message. "
            "Please try again in a moment."
        )

# Photo message handler
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle photo messages and delegate to the controller for landmark recognition.
    """
    try:
        user_id = update.effective_user.id
        photo_file = await update.message.photo[-1].get_file()
        image_bytes = await photo_file.download_as_bytearray()
        reply = await controller.handle_image_message(user_id, image_bytes)
        await update.message.reply_text(reply, parse_mode="Markdown")
    except Exception as e:
        print("Error in handle_photo:", repr(e))
        await update.message.reply_text(
            "We ran into an error while processing your photo. "
            "Please try again with a clearer image or send the place name as text."
        )

# Main function to start the bot
def main() -> None:
    """
    Entry point: start the Telegram bot and begin polling.
    """
    if not TELEGRAM_TOKEN:
        print("ERROR: TELEGRAM_TOKEN is not set in the environment or .env file.")
        return

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("Suwwah Telegram bot is running. Press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()