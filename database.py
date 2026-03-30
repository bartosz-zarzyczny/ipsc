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
                multiplier  REAL    DEFAULT 1.0,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
                data_json   TEXT    NOT NULL
            )
        """)

        # Utwórz tabelę rankings
        conn.execute("""
            CREATE TABLE IF NOT EXISTS rankings (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                name        TEXT    UNIQUE NOT NULL,
                top_matches_count INTEGER DEFAULT 0,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
                updated_at  TEXT    NOT NULL DEFAULT (datetime('now'))
            )
        """)

        # Powiązanie rankingów z zawodami (grupy rankingowe)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ranking_matches (
                ranking_id  INTEGER NOT NULL,
                match_id    INTEGER NOT NULL,
                created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
                PRIMARY KEY (ranking_id, match_id),
                FOREIGN KEY (ranking_id) REFERENCES rankings(id) ON DELETE RESTRICT,
                FOREIGN KEY (match_id) REFERENCES matches(id) ON DELETE CASCADE
            )
        """)

        # Tabela mapowania dywizji (mapowanie między dywizjami z importu a standardowymi)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS standard_divisions (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        
        # Tabela mapowania dywizji (mapowanie między dywizjami z importu a standardowymi)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS division_mappings (
                source_division TEXT PRIMARY KEY,
                mapped_division_id INTEGER NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (mapped_division_id) REFERENCES standard_divisions(id)
            )
        """)
        
        # Migrate: dodaj kolumnę top_matches_count jeśli nie istnieje
        try:
            conn.execute("ALTER TABLE rankings ADD COLUMN top_matches_count INTEGER DEFAULT 0")
        except sqlite3.OperationalError:
            pass  # Kolumna już istnieje
        
        # Migrate: dodaj kolumnę multiplier jeśli nie istnieje
        try:
            conn.execute("ALTER TABLE matches ADD COLUMN multiplier REAL DEFAULT 1.0")
        except sqlite3.OperationalError:
            pass  # Kolumna już istnieje
        
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
    # Pobierz metadane zawodów z rankingami
    rows = conn.execute(
        """
        SELECT
            m.id,
            m.name,
            m.date,
            m.level,
            m.multiplier,
            m.created_at,
            COALESCE(GROUP_CONCAT(r.name, ' || '), '') AS ranking_names,
            COALESCE(GROUP_CONCAT(rm.ranking_id, ','), '') AS ranking_ids_str
        FROM matches m
        LEFT JOIN ranking_matches rm ON rm.match_id = m.id
        LEFT JOIN rankings r ON r.id = rm.ranking_id
        GROUP BY m.id
        ORDER BY m.created_at DESC
        """
    ).fetchall()
    conn.close()
    
    result = []
    for r in rows:
        d = dict(r)
        # Konwertuj ranking_ids_str na listę liczb
        d["ranking_ids"] = [int(x) for x in d["ranking_ids_str"].split(",") if x.strip()]
        del d["ranking_ids_str"]
        result.append(d)
    return result


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


def get_match_with_multiplier(match_id: int) -> dict | None:
    """Load a saved match by id with multiplier metadata."""
    conn = get_db()
    row = conn.execute(
        "SELECT data_json, multiplier FROM matches WHERE id = ?", (match_id,)
    ).fetchone()
    conn.close()
    if row is None:
        return None
    data = json.loads(row["data_json"])
    data["match"]["multiplier"] = row["multiplier"] or 1.0
    return data


def delete_match(match_id: int) -> bool:
    """Delete a match by id. Returns True if deleted."""
    conn = get_db()
    cur = conn.execute("DELETE FROM matches WHERE id = ?", (match_id,))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted


# ---------------------------------------------------------------------------
# Rankings
# ---------------------------------------------------------------------------

def _normalize_match_ids(match_ids: list[str] | list[int] | None) -> list[int]:
    values: list[int] = []
    if not match_ids:
        return values
    for value in match_ids:
        try:
            values.append(int(value))
        except (TypeError, ValueError):
            continue
    return list(dict.fromkeys(values))


def list_rankings() -> list[dict]:
    """Return all rankings with attached match counts and names."""
    conn = get_db()
    rows = conn.execute(
        """
        SELECT
            r.id,
            r.name,
            r.top_matches_count,
            r.created_at,
            r.updated_at,
            COUNT(rm.match_id) AS match_count,
            COALESCE(GROUP_CONCAT(m.name, ' || '), '') AS match_names
        FROM rankings r
        LEFT JOIN ranking_matches rm ON rm.ranking_id = r.id
        LEFT JOIN matches m ON m.id = rm.match_id
        GROUP BY r.id
        ORDER BY r.created_at DESC, r.name COLLATE NOCASE
        """
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_ranking(ranking_id: int) -> dict | None:
    """Load a ranking together with assigned match ids."""
    conn = get_db()
    ranking_row = conn.execute(
        "SELECT id, name, top_matches_count, created_at, updated_at FROM rankings WHERE id = ?",
        (ranking_id,),
    ).fetchone()
    if ranking_row is None:
        conn.close()
        return None

    match_rows = conn.execute(
        "SELECT match_id FROM ranking_matches WHERE ranking_id = ? ORDER BY created_at, match_id",
        (ranking_id,),
    ).fetchall()
    conn.close()

    result = dict(ranking_row)
    result["match_ids"] = [row["match_id"] for row in match_rows]
    result["match_count"] = len(result["match_ids"])
    return result


def add_ranking(name: str, match_ids: list[str] | list[int] | None = None, top_matches_count: int = 0) -> int:
    """Create a ranking and attach selected matches."""
    normalized_match_ids = _normalize_match_ids(match_ids)
    conn = get_db()
    cur = conn.execute("INSERT INTO rankings (name, top_matches_count) VALUES (?, ?)", (name, top_matches_count))
    ranking_id = cur.lastrowid
    if normalized_match_ids:
        conn.executemany(
            "INSERT OR IGNORE INTO ranking_matches (ranking_id, match_id) VALUES (?, ?)",
            [(ranking_id, match_id) for match_id in normalized_match_ids],
        )
    conn.execute(
        "UPDATE rankings SET updated_at = datetime('now') WHERE id = ?",
        (ranking_id,),
    )
    conn.commit()
    conn.close()
    return ranking_id


def update_ranking(ranking_id: int, name: str, match_ids: list[str] | list[int] | None = None, top_matches_count: int = 0) -> bool:
    """Update ranking details and replace match assignments."""
    normalized_match_ids = _normalize_match_ids(match_ids)
    conn = get_db()
    cur = conn.execute(
        "UPDATE rankings SET name = ?, top_matches_count = ?, updated_at = datetime('now') WHERE id = ?",
        (name, top_matches_count, ranking_id),
    )
    if cur.rowcount == 0:
        conn.close()
        return False

    conn.execute("DELETE FROM ranking_matches WHERE ranking_id = ?", (ranking_id,))
    if normalized_match_ids:
        conn.executemany(
            "INSERT OR IGNORE INTO ranking_matches (ranking_id, match_id) VALUES (?, ?)",
            [(ranking_id, match_id) for match_id in normalized_match_ids],
        )
    conn.commit()
    conn.close()
    return True


def ranking_match_count(ranking_id: int) -> int:
    """Return number of matches assigned to a ranking."""
    conn = get_db()
    row = conn.execute(
        "SELECT COUNT(*) AS c FROM ranking_matches WHERE ranking_id = ?",
        (ranking_id,),
    ).fetchone()
    conn.close()
    return int(row["c"]) if row else 0


def delete_ranking(ranking_id: int) -> bool:
    """Delete a ranking only when it has no assigned matches."""
    if ranking_match_count(ranking_id) > 0:
        return False

    conn = get_db()
    cur = conn.execute("DELETE FROM rankings WHERE id = ?", (ranking_id,))
    conn.commit()
    deleted = cur.rowcount > 0
    conn.close()
    return deleted


def add_match_to_ranking(ranking_id: int, match_id: int) -> bool:
    """Add a match to a ranking. Returns True if added (or if already assigned)."""
    conn = get_db()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO ranking_matches (ranking_id, match_id) VALUES (?, ?)",
            (ranking_id, match_id),
        )
        conn.execute(
            "UPDATE rankings SET updated_at = datetime('now') WHERE id = ?",
            (ranking_id,),
        )
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def update_match_rankings(match_id: int, ranking_ids: list[str] | list[int] | None = None) -> bool:
    """Replace all ranking assignments for a match with new ones."""
    normalized_ranking_ids = _normalize_match_ids(ranking_ids)
    conn = get_db()
    try:
        # Usuń wszystkie stare przypisania tego meczu
        conn.execute("DELETE FROM ranking_matches WHERE match_id = ?", (match_id,))
        
        # Dodaj nowe przypisania
        if normalized_ranking_ids:
            conn.executemany(
                "INSERT OR IGNORE INTO ranking_matches (ranking_id, match_id) VALUES (?, ?)",
                [(ranking_id, match_id) for ranking_id in normalized_ranking_ids],
            )
        
        # Zaktualizuj timestamp dla wszystkich rankingów
        for ranking_id in normalized_ranking_ids:
            conn.execute(
                "UPDATE rankings SET updated_at = datetime('now') WHERE id = ?",
                (ranking_id,),
            )
        
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def update_match_multiplier(match_id: int, multiplier: float = 1.0) -> bool:
    """Update multiplier for a match (used only in rankings)."""
    conn = get_db()
    try:
        conn.execute(
            "UPDATE matches SET multiplier = ? WHERE id = ?",
            (max(0.0, multiplier), match_id),
        )
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


def update_match_level(match_id: int, level: int = 1) -> bool:
    """Update level for a match."""
    conn = get_db()
    try:
        conn.execute(
            "UPDATE matches SET level = ? WHERE id = ?",
            (max(0, level), match_id),
        )
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()



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


def verify_user(username: str, password_hash: str) -> int | None:
    """Verify if username/password matches. Returns user_id if valid, None otherwise. Uses timing-safe comparison."""
    import hmac
    conn = get_db()
    row = conn.execute(
        "SELECT id, password_hash FROM users WHERE username = ?", (username,)
    ).fetchone()
    conn.close()
    if row is None:
        return None
    stored_hash = row["password_hash"]
    if hmac.compare_digest(password_hash, stored_hash):
        return row["id"]
    return None


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


# ---------------------------------------------------------------------------
# Competitor management
# ---------------------------------------------------------------------------

def update_competitor_name(match_id: int, comp_id: str, firstname: str, lastname: str, category: str = None) -> bool:
    """Update competitor's first name, last name, and optionally category in a match. Returns True if successful."""
    conn = get_db()
    try:
        # Pobierz dane meczu
        row = conn.execute(
            "SELECT data_json FROM matches WHERE id = ?", (match_id,)
        ).fetchone()
        
        if row is None:
            return False
        
        # Załaduj JSON
        data = json.loads(row["data_json"])
        
        # Znajdź i zaktualizuj zawodnika
        found = False
        for competitor in data.get("competitors", []):
            if str(competitor.get("comp_id")) == str(comp_id):
                competitor["firstname"] = firstname.strip()
                competitor["lastname"] = lastname.strip()
                # Zaktualizuj połączone imię i nazwisko
                competitor["name"] = f"{competitor['lastname']} {competitor['firstname']}"
                # Zaktualizuj kategorię jeśli podana
                if category is not None:
                    competitor["category"] = category.strip()
                found = True
                break
        
        if not found:
            return False
        
        # Zapisz zmieniony JSON
        conn.execute(
            "UPDATE matches SET data_json = ? WHERE id = ?",
            (json.dumps(data, ensure_ascii=False), match_id),
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Błąd aktualizacji zawodnika: {e}")
        conn.close()
        return False


def delete_competitor_from_match(match_id: int, comp_id: str) -> bool:
    """Delete a competitor from a match. Returns True if successful."""
    conn = get_db()
    try:
        # Pobierz dane meczu
        row = conn.execute(
            "SELECT data_json FROM matches WHERE id = ?", (match_id,)
        ).fetchone()
        
        if row is None:
            return False
        
        # Załaduj JSON
        data = json.loads(row["data_json"])
        
        # Znajdź i usuń zawodnika
        original_count = len(data.get("competitors", []))
        data["competitors"] = [
            c for c in data.get("competitors", [])
            if str(c.get("comp_id")) != str(comp_id)
        ]
        
        if len(data["competitors"]) == original_count:
            # Zawodnik nie znaleziony
            return False
        
        # Zapisz zmieniony JSON
        conn.execute(
            "UPDATE matches SET data_json = ? WHERE id = ?",
            (json.dumps(data, ensure_ascii=False), match_id),
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Błąd usuwania zawodnika: {e}")
        conn.close()
        return False


# ---------------------------------------------------------------------------
# Division Mappings
# ---------------------------------------------------------------------------

def get_division_mapping(source_division: str) -> int | None:
    """Get the mapped standard division ID for a source division. Returns division ID or None."""
    conn = get_db()
    row = conn.execute(
        "SELECT mapped_division_id FROM division_mappings WHERE source_division = ?",
        (source_division,)
    ).fetchone()
    conn.close()
    return int(row["mapped_division_id"]) if row else None


def set_division_mapping(source_division: str, mapped_division_id: int | None) -> bool:
    """Set or update a division mapping. If mapped_division_id is None, removes the mapping."""
    conn = get_db()
    try:
        if mapped_division_id is None:
            # Usuń mapowanie
            conn.execute(
                "DELETE FROM division_mappings WHERE source_division = ?",
                (source_division,)
            )
        else:
            # Dodaj lub zaktualizuj mapowanie
            conn.execute(
                """
                INSERT OR REPLACE INTO division_mappings (source_division, mapped_division_id, updated_at)
                VALUES (?, ?, datetime('now'))
                """,
                (source_division, mapped_division_id)
            )
        conn.commit()
        return True
    except Exception as e:
        print(f"Błąd mapowania dywizji: {e}")
        return False
    finally:
        conn.close()


def get_all_division_mappings() -> dict[str, int]:
    """Get all division mappings as a dictionary {source_division: mapped_division_id}."""
    conn = get_db()
    rows = conn.execute(
        "SELECT source_division, mapped_division_id FROM division_mappings"
    ).fetchall()
    conn.close()
    return {row["source_division"]: int(row["mapped_division_id"]) for row in rows}


def get_imported_divisions() -> list[str]:
    """Get all source divisions that have been imported from matches. Returns sorted list."""
    conn = get_db()
    try:
        # Zbierz wszystkie unikalne dywizje ze wszystkich zawodów
        rows = conn.execute(
            """
            SELECT DISTINCT json_extract(value, '$.division') as division
            FROM matches, json_each(matches.data_json, '$.competitors')
            WHERE json_extract(value, '$.division') IS NOT NULL
            ORDER BY division COLLATE NOCASE
            """
        ).fetchall()
        
        divisions = [row["division"] for row in rows if row["division"]]
        return sorted(list(set(divisions)))
    except Exception as e:
        print(f"Błąd pobierania dywizji: {e}")
        return []
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Standard Divisions Management
# ---------------------------------------------------------------------------

def get_standard_divisions() -> list[dict]:
    """Get all standard divisions."""
    conn = get_db()
    rows = conn.execute(
        "SELECT id, name, description FROM standard_divisions ORDER BY id"
    ).fetchall()
    conn.close()
    return [{"id": row["id"], "name": row["name"], "description": row["description"]} for row in rows]


def get_standard_division(division_id: int) -> dict | None:
    """Get a specific standard division by ID."""
    conn = get_db()
    row = conn.execute(
        "SELECT id, name, description FROM standard_divisions WHERE id = ?",
        (division_id,)
    ).fetchone()
    conn.close()
    if row:
        return {"id": row["id"], "name": row["name"], "description": row["description"]}
    return None


def add_standard_division(division_id: int, name: str, description: str = "") -> bool:
    """Add a new standard division."""
    conn = get_db()
    try:
        conn.execute(
            """
            INSERT INTO standard_divisions (id, name, description)
            VALUES (?, ?, ?)
            """,
            (division_id, name, description)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False  # Already exists or name is not unique
    except Exception as e:
        print(f"Błąd dodawania dywizji: {e}")
        return False
    finally:
        conn.close()


def update_standard_division(division_id: int, name: str, description: str = "") -> bool:
    """Update an existing standard division."""
    conn = get_db()
    try:
        conn.execute(
            """
            UPDATE standard_divisions
            SET name = ?, description = ?, updated_at = datetime('now')
            WHERE id = ?
            """,
            (name, description, division_id)
        )
        conn.commit()
        return conn.total_changes > 0
    except Exception as e:
        print(f"Błąd aktualizacji dywizji: {e}")
        return False
    finally:
        conn.close()


def delete_standard_division(division_id: int) -> bool:
    """Delete a standard division (if no mappings reference it)."""
    conn = get_db()
    try:
        # Sprawdź czy jest mapowanie
        mapping = conn.execute(
            "SELECT COUNT(*) as count FROM division_mappings WHERE mapped_division_id = ?",
            (division_id,)
        ).fetchone()
        
        if mapping["count"] > 0:
            # Nie możesz usunąć jeśli jest do niej mapowanie
            return False
        
        conn.execute("DELETE FROM standard_divisions WHERE id = ?", (division_id,))
        conn.commit()
        return conn.total_changes > 0
    except Exception as e:
        print(f"Błąd usuwania dywizji: {e}")
        return False
    finally:
        conn.close()


def init_standard_divisions_from_json(divisions_list: list[dict]) -> bool:
    """Initialize/update standard_divisions table from a list of divisions (from JSON)."""
    conn = get_db()
    try:
        # Dodaj lub zaktualizuj każdą dywizję
        for div in divisions_list:
            div_id = div.get("id")
            div_name = div.get("name")
            div_description = div.get("description", "")
            
            if not div_id or not div_name:
                continue
            
            # Sprawdź czy istnieje
            exists = conn.execute(
                "SELECT id FROM standard_divisions WHERE id = ?",
                (div_id,)
            ).fetchone()
            
            if exists:
                # Zaktualizuj
                conn.execute(
                    """
                    UPDATE standard_divisions
                    SET name = ?, description = ?, updated_at = datetime('now')
                    WHERE id = ?
                    """,
                    (div_name, div_description, div_id)
                )
            else:
                # Dodaj nową
                conn.execute(
                    """
                    INSERT INTO standard_divisions (id, name, description)
                    VALUES (?, ?, ?)
                    """,
                    (div_id, div_name, div_description)
                )
        
        conn.commit()
        count = len(divisions_list)
        print(f"✓ Załadowano/Zaktualizowano {count} standardowych dywizji w bazie")
        return True
    except Exception as e:
        print(f"Błąd inicjalizacji dywizji: {e}")
        return False
    finally:
        conn.close()


def apply_division_mappings(match_data: dict) -> dict:
    """Apply division mappings to competitors in match data. Returns modified data."""
    try:
        data = json.loads(json.dumps(match_data))  # Deep copy
        mappings = get_all_division_mappings()
        
        if not mappings:
            return data  # Brak mapowań
        
        # Aplikuj mapowania do każdego zawodnika
        for competitor in data.get("competitors", []):
            original_division = competitor.get("division")
            if original_division and original_division in mappings:
                mapped_division_id = mappings[original_division]
                # Pobierz nazwę zmapowanej dywizji
                mapped_div = get_standard_division(mapped_division_id)
                if mapped_div:
                    competitor["division"] = mapped_div["name"]
                    competitor["_original_division"] = original_division  # Zapisz oryginał dla referencji
        
        return data
    except Exception as e:
        print(f"Błąd stosowania mapowań dywizji: {e}")
        return match_data

