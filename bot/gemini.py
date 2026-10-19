import os
import httpx
import db

URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

SYSTEM = (
    "تو دستیار فروش پیج اینستاگرام «درباره اصفهان» هستی و در تلگرام با مشتری‌ها چت می‌کنی. "
    "فارسی، صمیمی، کوتاه (حداکثر ۴ جمله) و محترمانه جواب بده. فقط بر اساس اطلاعات داده‌شده جواب بده؛ "
    "اگه جوابش رو نداری بگو ادمین بهش پاسخ می‌ده. چیزی از خودت اختراع نکن.\n"
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
    async with httpx.AsyncClient(timeout=30) as cli:
        r = await cli.post(URL.format(model=model), json=body,
                           headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]})
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"].strip()
