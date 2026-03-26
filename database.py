#!/usr/bin/env python3
"""
SQLite database for persisting match results.
"""

from __future__ import annotations
import json
import os
import sqlite3
import uuid
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")


def _load_or_create_config() -> dict:
    """Wczytaj config lub utwórz nowy z unikalnym ID instancji."""
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    
    # Generuj nową konfigurację z unikalnym ID
    instance_id = str(uuid.uuid4())[:8]  # Pierwsze 8 znaków UUID
    config = {"instance_id": instance_id, "created_at": datetime.now().isoformat()}
    
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)
    
    return config


# Wczytaj konfigurację przy imporcie
CONFIG = _load_or_create_config()
INSTANCE_ID = CONFIG["instance_id"]
DB_PATH = os.path.join(DATA_DIR, f"{INSTANCE_ID}.db")


def get_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """Create tables if they don't exist."""
    try:
        conn = get_db()
        
        # Utwórz tabelę users
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                username    TEXT    UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
            )
        """)
        
        # Utwórz tabelę matches
        conn.execute("""
            CREATE TABLE IF NOT EXISTS matches (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    NOT NULL,
                date        TEXT,
                level       INTEGER DEFAULT 1,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
                data_json   TEXT    NOT NULL
            )
        """)
        
        conn.commit()
        conn.close()
        
        print(f"✓ Baza danych zainicjalizowana: {DB_PATH}")
        
        # Dodaj domyślnego użytkownika jeśli baza jest nowa
        if not list_users():
            import hashlib
            default_hash = hashlib.sha256(b"IP$c2023").hexdigest()
            add_user("bartek", default_hash)
            print(f"✓ Domyślny użytkownik 'bartek' utworzony")
    
    except Exception as e:
        print(f"✗ Błąd inicjalizacji bazy: {e}")
        raise


def save_match(result: dict) -> int:
    """Save processed match result to DB. Returns match id."""
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO matches (name, date, level, data_json) VALUES (?, ?, ?, ?)",
        (
            result["match"]["name"],
            result["match"]["date"],
            result["match"]["level"],
            json.dumps(result, ensure_ascii=False),
        ),
    )
    match_id = cur.lastrowid
    conn.commit()
    conn.close()
    return match_id


def list_matches() -> list[dict]:
    """Return all saved matches (without full data)."""
    conn = get_db()
    rows = conn.execute(
        "SELECT id, name, date, level, created_at FROM matches ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_match(match_id: int) -> dict | None:
    """Load a saved match by id."""
    conn = get_db()
    row = conn.execute(
        "SELECT data_json FROM matches WHERE id = ?", (match_id,)
    ).fetchone()
    conn.close()
    if row is None:
        return None
    return json.loads(row["data_json"])


def delete_match(match_id: int) -> bool:
    """Delete a match by id. Returns True if deleted."""
    conn = get_db()
    cur = conn.execute("DELETE FROM matches WHERE id = ?", (match_id,))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted


# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------

def add_user(username: str, password_hash: str) -> int:
    """Add a new user. Returns user id."""
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO users (username, password_hash) VALUES (?, ?)",
        (username, password_hash),
    )
    user_id = cur.lastrowid
    conn.commit()
    conn.close()
    return user_id


def verify_user(username: str, password_hash: str) -> bool:
    """Verify if username/password matches. Uses timing-safe comparison."""
    import hmac
    conn = get_db()
    row = conn.execute(
        "SELECT password_hash FROM users WHERE username = ?", (username,)
    ).fetchone()
    conn.close()
    if row is None:
        return False
    stored_hash = row["password_hash"]
    return hmac.compare_digest(password_hash, stored_hash)


def list_users() -> list[dict]:
    """Return all users (without password hashes)."""
    conn = get_db()
    rows = conn.execute(
        "SELECT id, username, created_at FROM users ORDER BY username"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_user(user_id: int) -> bool:
    """Delete a user by id. Returns True if deleted. Refuses if only 1 user."""
    conn = get_db()
    count = conn.execute("SELECT COUNT(*) as c FROM users").fetchone()["c"]
    if count <= 1:
        conn.close()
        return False  # Prevent deleting last user
    cur = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted


def change_password(user_id: int, password_hash: str) -> bool:
    """Change user's password. Returns True if successful."""
    conn = get_db()
    cur = conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id))
    conn.commit()
    updated = cur.rowcount > 0
    conn.close()
    return updated

