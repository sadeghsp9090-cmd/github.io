import logging
import os

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (Application, CommandHandler, ContextTypes, MessageHandler, filters)

load_dotenv()
import db  # noqa: E402
import gemini  # noqa: E402

logging.basicConfig(level=logging.INFO)
ADMIN_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))
FALLBACK = "ببخشید یه مشکل فنی پیش اومد 🌹 ادمین به‌زودی پاسخ می‌ده."


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    db.upsert_customer(update.effective_chat.id, u.full_name)
    await update.message.reply_text(
        "سلام 🌹 به پیج «درباره اصفهان» خوش اومدید. برای تبلیغ پست دائمی، استوری گویشی یا استوری بنری راهنماییتون کنم؟")


async def on_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id, text = update.effective_chat.id, update.message.text
    db.upsert_customer(chat_id, update.effective_user.full_name)
    await ctx.bot.send_chat_action(chat_id, "typing")
    try:
        answer = await gemini.reply(chat_id, text)
    except Exception:
        logging.exception("gemini failed")
        answer = FALLBACK
    db.add_message(chat_id, "user", text)
    db.add_message(chat_id, "model", answer)
    await update.message.reply_text(answer)


async def on_media(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Photos/docs are treated as receipts: forwarded to admin, who confirms with /paid."""
    chat_id = update.effective_chat.id
    await update.message.reply_text("رسید دریافت شد 🌹 بعد از تأیید، اولین تایم خالی رو رزرو و تاریخ انتشار رو اعلام می‌کنم.")
    if ADMIN_ID:
        await update.message.forward(ADMIN_ID)
        await ctx.bot.send_message(
            ADMIN_ID, f"رسید/فایل از {update.effective_user.full_name}\nبرای تأیید پرداخت: /paid {chat_id}")


async def paid(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != ADMIN_ID or not ctx.args:
        return
    cid = int(ctx.args[0])
    db.set_paid(cid)
    await update.message.reply_text(f"پرداخت {cid} ثبت شد.")
    await ctx.bot.send_message(cid, "پرداخت شما تأیید شد 🌹 اولین تایم خالی رو رزرو می‌کنم و تاریخ دقیق انتشار رو بهتون اعلام می‌کنم.")


def main():
    db.seed()
    app = Application.builder().token(os.environ["TELEGRAM_BOT_TOKEN"]).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("paid", paid))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, on_media))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.run_polling()


if __name__ == "__main__":
    main()
