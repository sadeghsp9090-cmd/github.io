# Telegram sales bot — «درباره اصفهان»

    pip install -r requirements.txt
    cp .env.example .env   # fill in the keys
    python main.py

- Knowledge lives in `kb.json` (small chunks, keyword-tagged). Edit it and restart; it is reloaded into SQLite.
- Per message only the top 3 matching chunks + last 6 chat messages + short rules go to Gemini.
