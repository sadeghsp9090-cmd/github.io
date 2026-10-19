"""SQLite store: small knowledge chunks + chat history. Only a few matching chunks go to Gemini."""
import json
import re
import sqlite3
import time
from pathlib import Path

DB_PATH = Path(__file__).with_name("bot.db")
KB_PATH = Path(__file__).with_name("kb.json")
HISTORY_LIMIT = 6   # messages sent to Gemini
TOP_K = 3           # chunks sent to Gemini

_conn = None


def conn():
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(DB_PATH)
        _conn.row_factory = sqlite3.Row
        _conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS rules  (id INTEGER PRIMARY KEY, text TEXT);
            CREATE TABLE IF NOT EXISTS chunks (id INTEGER PRIMARY KEY, topic TEXT, title TEXT,
                                               keywords TEXT, content TEXT);
            CREATE TABLE IF NOT EXISTS customers (chat_id INTEGER PRIMARY KEY, name TEXT,
                                               paid INTEGER DEFAULT 0, created REAL);
            CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY, chat_id INTEGER,
                                               role TEXT, text TEXT, ts REAL);
            CREATE INDEX IF NOT EXISTS idx_msg ON messages(chat_id, id);
            """
        )
    return _conn


def seed():
    """Reload knowledge from kb.json (edit the file, restart the bot)."""
    c = conn()
    data = json.loads(KB_PATH.read_text(encoding="utf-8"))
    c.execute("DELETE FROM rules")
    c.execute("DELETE FROM chunks")
    c.executemany("INSERT INTO rules(text) VALUES (?)", [(r,) for r in data["rules"]])
    c.executemany(
        "INSERT INTO chunks(topic,title,keywords,content) VALUES (?,?,?,?)",
        [(k["topic"], k["title"], k["keywords"], k["content"]) for k in data["chunks"]],
    )
    c.commit()


def _norm(s):
    s = s.replace("ي", "ی").replace("ك", "ک").replace("‌", " ")
    return re.findall(r"\w+", s.lower())


def rules_text():
    return "\n".join("- " + r["text"] for r in conn().execute("SELECT text FROM rules"))


def retrieve(query):
    """Score chunks by keyword overlap; fall back to overview."""
    words = set(_norm(query))
    scored = []
    for r in conn().execute("SELECT * FROM chunks"):
        kws = set(_norm(r["keywords"] + " " + r["title"]))
        score = len(words & kws)
        if score:
            scored.append((score, r))
    scored.sort(key=lambda x: -x[0])
    picked = [r for _, r in scored[:TOP_K]]
    if not picked:
        picked = list(conn().execute("SELECT * FROM chunks WHERE topic='overview'"))
    return picked


def add_message(chat_id, role, text):
    c = conn()
    c.execute("INSERT INTO messages(chat_id,role,text,ts) VALUES (?,?,?,?)",
              (chat_id, role, text, time.time()))
    c.commit()


def history(chat_id):
    rows = conn().execute(
        "SELECT role,text FROM messages WHERE chat_id=? ORDER BY id DESC LIMIT ?",
        (chat_id, HISTORY_LIMIT)).fetchall()
    return list(reversed(rows))


def upsert_customer(chat_id, name):
    c = conn()
    c.execute("INSERT OR IGNORE INTO customers(chat_id,name,created) VALUES (?,?,?)",
              (chat_id, name, time.time()))
    c.commit()


def is_paid(chat_id):
    r = conn().execute("SELECT paid FROM customers WHERE chat_id=?", (chat_id,)).fetchone()
    return bool(r and r["paid"])


def set_paid(chat_id, paid=True):
    c = conn()
    c.execute("UPDATE customers SET paid=? WHERE chat_id=?", (int(paid), chat_id))
    c.commit()
