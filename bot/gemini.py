import os
import httpx
import db

URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

SYSTEM = (
    "تو «ساجده» هستی، مشاور فروش حرفه‌ای و باتجربه‌ی تبلیغات پیج اینستاگرام «درباره اصفهان»، و تو تلگرام با مشتری‌ها چت می‌کنی. "
    "مثل یه آدم واقعی، خوش‌صحبت و فروشنده‌ی کاربلد حرف بزن: لحن دوستانه و خودمونی ولی محترمانه، جمله‌های کوتاه، بدون رسمی‌بازی و بدون لیست و فرمت ربات‌گونه. "
    "حداکثر ۳ جمله، و هر بار فقط یه سؤال یا یه قدم بعدی جلوی پای مشتری بذار تا گفتگو به سمت ثبت سفارش بره. "
    "اول نیاز مشتری رو بفهم (چه کسب‌وکاری داره، چی می‌خواد)، بعد مناسب‌ترین سرویس رو پیشنهاد بده و مزیتش رو خیلی کوتاه بگو. "
    "اگه مشتری مردد بود یا گفت گرونه، با ارزش کار و قیمت ویژه جواب بده، ولی هیچ‌وقت قیمت رو کم یا تخفیف نده و چیزی از خودت نساز. "
    "فقط بر اساس اطلاعات داده‌شده جواب بده؛ اگه جوابش رو نداری بگو «از ادمین می‌پرسم و بهت خبر می‌دم». "
    "سلام و احوال‌پرسی فقط یک‌بار: اگه تو تاریخچه‌ی گفتگو قبلاً سلام شده، هرگز دوباره سلام نکن و مستقیم برو سراغ جواب. "
    "هیچ وعده‌ی نتیجه یا آماری نده (مثل «هزینه‌تون برمی‌گرده» یا «فروشتون بالا می‌ره»). ترتیب کار: پرداخت و ارسال رسید، بعد رزرو تایم و اعلام تاریخ؛ هرگز نگو پرداخت بعد از ساخت ویدیوئه. "
    "ایموجی خیلی کم (حداکثر یکی).\n"
    "قوانین:\n{rules}"
)


async def reply(chat_id, user_text):
    chunks = db.retrieve(user_text)
    info = "\n".join(f"[{c['title']}] {c['content']}" for c in chunks)
    paid = "مشتری پرداخت کرده (رسید تأیید شده)." if db.is_paid(chat_id) else "مشتری هنوز پرداخت تأیید‌شده‌ای ندارد."
    system = SYSTEM.format(rules=db.rules_text()) + f"\n\nوضعیت: {paid}\n\nاطلاعات مرتبط:\n{info}"

    contents = [{"role": "user" if h["role"] == "user" else "model", "parts": [{"text": h["text"]}]}
                for h in db.history(chat_id)]
    contents.append({"role": "user", "parts": [{"text": user_text}]})

    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": contents,
        "generationConfig": {"temperature": 0.4, "maxOutputTokens": 300},
    }
    model = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=20) as cli:
                r = await cli.post(URL.format(model=model), json=body,
                                   headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]})
            if r.status_code < 500:
                break
        except httpx.TimeoutException:
            if attempt == 2:
                raise
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
