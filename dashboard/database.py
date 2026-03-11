import sqlite3
from config import DB_PATH

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute('''CREATE TABLE IF NOT EXISTS emails (
        id INTEGER PRIMARY KEY,
        message_id TEXT UNIQUE,
        sender TEXT,
        subject TEXT,
        date TEXT,
        body TEXT,
        category TEXT,
        priority TEXT,
        summary TEXT,
        action_required INTEGER,
        manually_classified INTEGER DEFAULT 0,
        processed_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    return conn
