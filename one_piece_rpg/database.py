"""SQLite database layer."""

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _db_path() -> str:
    return os.getenv(
        "DATABASE_PATH",
        str(Path(__file__).resolve().parent / "game.db"),
    )

_SCHEMA = """
CREATE TABLE IF NOT EXISTS players (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    faction TEXT,
    beli INTEGER DEFAULT 0,
    xp INTEGER DEFAULT 0,
    level INTEGER DEFAULT 1,
    energy INTEGER DEFAULT 100,
    last_energy_at TEXT,
    current_island TEXT DEFAULT 'east_blue',
    active_character TEXT,
    bounty INTEGER DEFAULT 0,
    ship_id TEXT,
    crew_id INTEGER,
    haki TEXT DEFAULT '{}',
    titles TEXT DEFAULT '[]',
    daily_streak INTEGER DEFAULT 0,
    last_daily TEXT,
    last_wheel TEXT,
    death_until TEXT,
    age INTEGER DEFAULT 0,
    height INTEGER DEFAULT 0,
    weight INTEGER DEFAULT 0,
    photo_id TEXT,
    race TEXT,
    food INTEGER DEFAULT 100,
    last_food_at TEXT,
    battle_items TEXT DEFAULT NULL,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS owned_characters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    char_id TEXT NOT NULL,
    level INTEGER DEFAULT 1,
    xp INTEGER DEFAULT 0,
    devil_fruit TEXT,
    equipment TEXT DEFAULT '{}',
    UNIQUE(user_id, char_id),
    FOREIGN KEY (user_id) REFERENCES players(user_id)
);

CREATE TABLE IF NOT EXISTS inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    item_type TEXT NOT NULL,
    item_id TEXT NOT NULL,
    quantity INTEGER DEFAULT 1,
    metadata TEXT DEFAULT '{}',
    FOREIGN KEY (user_id) REFERENCES players(user_id)
);

CREATE TABLE IF NOT EXISTS crews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    leader_id INTEGER NOT NULL,
    level INTEGER DEFAULT 1,
    bank INTEGER DEFAULT 0,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS crew_members (
    crew_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    role TEXT DEFAULT 'member',
    joined_at TEXT,
    PRIMARY KEY (crew_id, user_id)
);

CREATE TABLE IF NOT EXISTS world_boss_state (
    boss_id TEXT PRIMARY KEY,
    current_hp INTEGER,
    started_at TEXT,
    ends_at TEXT
);

CREATE TABLE IF NOT EXISTS black_market (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    seller_id INTEGER NOT NULL,
    seller_name TEXT,
    item_type TEXT NOT NULL,
    item_id TEXT NOT NULL,
    price INTEGER NOT NULL,
    listed_at TEXT,
    FOREIGN KEY (seller_id) REFERENCES players(user_id)
);

CREATE TABLE IF NOT EXISTS fight_cooldowns (
    user_id INTEGER PRIMARY KEY,
    last_fight REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS cooking_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    fish_id TEXT NOT NULL,
    chef_id TEXT NOT NULL,
    started_at TEXT NOT NULL,
    done_at TEXT NOT NULL,
    claimed INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS ship_crew (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    captain_id INTEGER NOT NULL,
    member_id INTEGER NOT NULL,
    title TEXT DEFAULT NULL,
    joined_at TEXT,
    UNIQUE(captain_id, member_id)
);

CREATE TABLE IF NOT EXISTS achievements (
    user_id INTEGER NOT NULL,
    achievement_id TEXT NOT NULL,
    unlocked_at TEXT,
    PRIMARY KEY (user_id, achievement_id)
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


@contextmanager
def get_db():
    conn = sqlite3.connect(_db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with get_db() as conn:
        conn.executescript(_SCHEMA)


def row_to_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(row)


def json_load(value: str | None, default: Any) -> Any:
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default
