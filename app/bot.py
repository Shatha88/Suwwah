"""
Telegram interface: receives user messages/photos and forwards them to the controller
"""

import os, re
# from dotenv import load_dotenv
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
# load_dotenv()
# TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN") or config.TELEGRAM_TOKEN


# Lightweight language detection
def detect_tg_lang(update: Update) -> str:
    """
    Lightweight language detection for /start and fallback errors.
    Uses Telegram language_code when available, otherwise checks Arabic chars.
    """
    code = (update.effective_user.language_code or "").lower()
    if code.startswith("ar"):
        return "ar"

    # Fallback heuristic based on name/text (rarely used)
    name = (update.effective_user.first_name or "") + (update.effective_user.last_name or "")
    if re.search(r"[\u0600-\u06FF]", name):
        return "ar"

    return "en"

# Safe reply function with Markdown fallback
async def safe_reply(update: Update, text: str) -> None:
    """
    Tries Markdown first, falls back to plain text if Markdown fails.
    """
    try:
        await update.message.reply_text(text, parse_mode="Markdown")
    except Exception:
        await update.message.reply_text(text)


# /start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    /start command: send a short introduction and usage hints.
    """
    lang = detect_tg_lang(update)
    user_first_name = update.effective_user.first_name or "there"
    if lang == "ar":
        text = (
            f"مرحباً {user_first_name} 👋\n\n"
            "سُوّاح هو مساعد سياحي ذكي للمملكة العربية السعودية.\n"
            "يمكنك:\n"
            "• طلب خطة رحلة، مثلاً: “خطط لي رحلة عائلية لمدة يومين في الرياض”.\n"
            "• الاستفسار عن أي مدينة أو معلم سياحي في السعودية.\n"
            "• إرسال صورة لمعلم سياحي للحصول على وصف مختصر.\n"
        )
    else:    
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
        await safe_reply(update, reply)

    except Exception as e:
        print("Error in handle_text:", repr(e))
        lang = detect_tg_lang(update)

        err = (
            "واجهنا خطأ داخلي بسيط أثناء معالجة رسالتك. حاول مرة أخرى بعد قليل."
            if lang == "ar"
            else
            "We as a team ran into an internal error while processing your message. Please try again shortly."
        )
        await update.message.reply_text(err)

# Photo message handler
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle photo messages and delegate to the controller for landmark recognition.
    """
    try:
        user_id = update.effective_user.id

        if not update.message.photo:
            lang = detect_tg_lang(update)
            msg = "لم نستلم صورة واضحة. حاول إرسال صورة أخرى." if lang == "ar" else "We didn't receive a clear photo. Please try again."
            await update.message.reply_text(msg)
            return

        photo_file = await update.message.photo[-1].get_file()
        image_bytes = await photo_file.download_as_bytearray()

        reply = await controller.handle_image_message(user_id, image_bytes)
        await safe_reply(update, reply)

    except Exception as e:
        print("Error in handle_photo:", repr(e))
        lang = detect_tg_lang(update)

        err = (
            "واجهنا مشكلة أثناء معالجة الصورة. حاول إرسال صورة أوضح أو اكتب اسم المكان نصاً."
            if lang == "ar"
            else
            "We ran into an error while processing your photo. Please try a clearer image or send the place name as text."
        )
        await update.message.reply_text(err)

# Main function to start the bot
def main() -> None:
    """
    Entry point: start the Telegram bot and begin polling.
    """
    TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN") or config.TELEGRAM_TOKEN

    if not TELEGRAM_TOKEN:
        print("ERROR: TELEGRAM_TOKEN is not set in the environment.")
        return

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    print("Suwwah Telegram bot is running. Press Ctrl+C to stop.")
    app.run_polling()


if __name__ == "__main__":
    main()