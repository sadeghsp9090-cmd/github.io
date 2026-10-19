import logging
import os

from dotenv import load_dotenv
from telegram import BotCommand, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler, ContextTypes,
                          MessageHandler, filters)

load_dotenv()
import db  # noqa: E402
import gemini  # noqa: E402

logging.basicConfig(level=logging.INFO)
ADMIN_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))
DESCRIPTION = (
    "📢 تبلیغات پیج «درباره اصفهان»\n\n"
    "کسب‌وکارت رو توی اصفهان دیده کن! ویدیوی اختصاصی، استوری گویشی و استوری بنری؛ "
    "همه‌چیز غیرحضوری و توسط تیم ما.\n\n"
    "برای شروع، دکمه‌ی «شروع / Start» پایین رو بزن 👇"
)
SHORT = "تبلیغات حرفه‌ای کسب‌وکار شما در پیج «درباره اصفهان»"
MENU = {
    "price": "تعرفه تبلیغات چنده؟",
    "post": "درباره پست تبلیغاتی دائمی توضیح بدید",
    "story": "استوری گویشی و استوری بنری چیه؟",
    "pay": "میخوام سفارش بدم، پرداخت چطوریه؟",
}
KEYBOARD = InlineKeyboardMarkup([
    [InlineKeyboardButton("💰 تعرفه‌ها", callback_data="price")],
    [InlineKeyboardButton("🎬 پست تبلیغاتی دائمی", callback_data="post"),
     InlineKeyboardButton("📱 استوری", callback_data="story")],
    [InlineKeyboardButton("✅ ثبت سفارش", callback_data="pay")],
])
PRICE_LIST = """تعرفه تبلیغات✅

1️⃣پست با تولید محتوا اختصاصی به صورت دائمی در پیج
🔸۲میلیون تومان (ویژه😍)

2️⃣استوری گویشی و توضیحات کامل ساخت با هوش مصنوعی
🔸۱ میلیون تومان

3️⃣هزینه استوری بنر شما با تگ
🔸۵۰۰هزار تومان"""
FALLBACK = "ببخشید یه مشکل فنی پیش اومد 🌹 ادمین به‌زودی پاسخ می‌ده."


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    u = update.effective_user
    db.upsert_customer(update.effective_chat.id, u.full_name)
    greeting = "سلام 🌹 به پیج «درباره اصفهان» خوش اومدید! کسب‌وکارتون چیه؟ بگید تا بهترین نوع تبلیغ رو بهتون پیشنهاد بدم."
    if not db.history(update.effective_chat.id):
        db.add_message(update.effective_chat.id, "model", greeting)
    await update.message.reply_text(greeting, reply_markup=KEYBOARD)


async def on_button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if q.data == "price":
        cid = q.message.chat_id
        db.upsert_customer(cid, q.from_user.full_name)
        db.add_message(cid, "user", MENU["price"])
        db.add_message(cid, "model", PRICE_LIST)
        await q.message.reply_text(PRICE_LIST)
        return
    await respond(q.message.chat_id, MENU[q.data], q.from_user.full_name, ctx, q.message)


async def on_text(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await respond(update.effective_chat.id, update.message.text, update.effective_user.full_name, ctx, update.message)


async def respond(chat_id, text, name, ctx, message):
    db.upsert_customer(chat_id, name)
    await ctx.bot.send_chat_action(chat_id, "typing")
    try:
        answer = await gemini.reply(chat_id, text)
    except Exception:
        logging.exception("gemini failed")
        answer = FALLBACK
    db.add_message(chat_id, "user", text)
    db.add_message(chat_id, "model", answer)
    await message.reply_text(answer)


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


async def setup(app):
    await app.bot.set_my_description(DESCRIPTION)
    await app.bot.set_my_short_description(SHORT)
    await app.bot.set_my_commands([BotCommand("start", "شروع و منوی اصلی")])


def main():
    db.seed()
    app = Application.builder().token(os.environ["TELEGRAM_BOT_TOKEN"]).post_init(setup).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("paid", paid))
    app.add_handler(CallbackQueryHandler(on_button))
    app.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, on_media))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.run_polling(bootstrap_retries=-1)


if __name__ == "__main__":
    main()
