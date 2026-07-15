"""Player data access and mutations."""

from datetime import datetime, timedelta, timezone

from one_piece_rpg.data import (
    CHARACTERS,
    DAILY_REWARD_BASE,
    DAILY_REWARD_STREAK_BONUS,
    ENERGY_REGEN_MINS,
    ISLANDS,
    LEVEL_XP,
    MARINE_RANKS,
    MAX_DAILY_STREAK,
    MAX_ENERGY,
    PIRATE_RANKS,
    STARTER_CHARACTERS,
)
from one_piece_rpg.database import _now, _parse_dt, get_db, json_load, row_to_dict


def get_player(user_id: int) -> dict | None:
    with get_db() as conn:
        row = conn.execute("SELECT * FROM players WHERE user_id = ?", (user_id,)).fetchone()
    player = row_to_dict(row)
    if player:
        player["haki"] = json_load(player.get("haki"), {})
        player["titles"] = json_load(player.get("titles"), [])
    return player


def create_player(user_id: int, username: str | None, faction: str, age: int = 0, height: int = 0, weight: int = 0) -> dict:
    now = _now()
    with get_db() as conn:
        conn.execute(
            """INSERT INTO players
               (user_id, username, faction, energy, last_energy_at, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, username, faction, MAX_ENERGY, now, now, now),
        )
        # ذخیره اطلاعات اضافی در جدول players اگه ستون وجود داشت، در غیر این صورت ignore
        try:
            conn.execute(
                "UPDATE players SET age=?, height=?, weight=? WHERE user_id=?",
                (age, height, weight, user_id)
            )
        except Exception:
            pass
    return get_player(user_id)


def grant_starter_character(user_id: int, char_id: str) -> None:
    now = _now()
    with get_db() as conn:
        conn.execute(
            """INSERT INTO owned_characters (user_id, char_id, level, xp)
               VALUES (?, ?, 1, 0)""",
            (user_id, char_id),
        )
        conn.execute(
            "UPDATE players SET active_character = ?, updated_at = ? WHERE user_id = ?",
            (char_id, now, user_id),
        )


def get_owned_characters(user_id: int) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM owned_characters WHERE user_id = ?",
            (user_id,),
        ).fetchall()
    return [row_to_dict(r) for r in rows]


def get_character_stats(char_row: dict) -> dict:
    base = CHARACTERS[char_row["char_id"]]
    level = char_row["level"]
    mult = 1 + (level - 1) * 0.08
    atk = int(base["base_atk"] * mult)
    defense = int(base["base_def"] * mult)
    hp = int(base["base_hp"] * mult)

    if char_row.get("devil_fruit"):
        from one_piece_rpg.data import DEVIL_FRUITS

        fruit = DEVIL_FRUITS.get(char_row["devil_fruit"], {})
        atk += fruit.get("atk_bonus", 0)
        defense += fruit.get("def_bonus", 0)
        hp += fruit.get("hp_bonus", 0)

    equipment = json_load(char_row.get("equipment"), {})
    for item_id in equipment.values():
        if item_id:
            from one_piece_rpg.data import ITEMS

            item = ITEMS.get(item_id, {})
            atk += item.get("atk", 0)
            defense += item.get("def", 0)

    return {"atk": atk, "def": defense, "hp": hp, "name": base["name"], "level": level}


def sync_energy(player: dict) -> dict:
    now = datetime.now(timezone.utc)
    last = _parse_dt(player.get("last_energy_at"))
    if not last:
        return player

    elapsed_mins = (now - last).total_seconds() / 60
    regen = int(elapsed_mins // ENERGY_REGEN_MINS)
    if regen <= 0:
        return player

    new_energy = min(MAX_ENERGY, player["energy"] + regen)
    if new_energy != player["energy"]:
        with get_db() as conn:
            conn.execute(
                "UPDATE players SET energy = ?, last_energy_at = ?, updated_at = ? WHERE user_id = ?",
                (new_energy, now.isoformat(), _now(), player["user_id"]),
            )
        player["energy"] = new_energy
        player["last_energy_at"] = now.isoformat()
    return player


def spend_energy(user_id: int, amount: int) -> bool:
    player = get_player(user_id)
    if not player:
        return False
    player = sync_energy(player)
    if player["energy"] < amount:
        return False
    now = _now()
    with get_db() as conn:
        conn.execute(
            "UPDATE players SET energy = energy - ?, last_energy_at = ?, updated_at = ? WHERE user_id = ?",
            (amount, now, now, user_id),
        )
    return True


def add_beli(user_id: int, amount: int) -> None:
    with get_db() as conn:
        conn.execute(
            "UPDATE players SET beli = MAX(0, beli + ?), updated_at = ? WHERE user_id = ?",
            (amount, _now(), user_id),
        )


def add_xp(user_id: int, char_id: str | None, xp_amount: int) -> dict:
    """Add XP to character and player. Returns level-up info."""
    result = {"char_level_up": False, "player_level_up": False, "new_char_level": 1, "new_player_level": 1}
    with get_db() as conn:
        if char_id:
            char = conn.execute(
                "SELECT * FROM owned_characters WHERE user_id = ? AND char_id = ?",
                (user_id, char_id),
            ).fetchone()
            if char:
                char = dict(char)
                new_xp = char["xp"] + xp_amount
                new_level = char["level"]
                while new_level < 100 and new_xp >= LEVEL_XP[new_level + 1]:
                    new_level += 1
                    result["char_level_up"] = True
                conn.execute(
                    "UPDATE owned_characters SET xp = ?, level = ? WHERE user_id = ? AND char_id = ?",
                    (new_xp, new_level, user_id, char_id),
                )
                result["new_char_level"] = new_level

        player = conn.execute("SELECT * FROM players WHERE user_id = ?", (user_id,)).fetchone()
        player = dict(player)
        p_xp = player["xp"] + xp_amount
        p_level = player["level"]
        while p_level < 100 and p_xp >= LEVEL_XP[p_level + 1]:
            p_level += 1
            result["player_level_up"] = True

        conn.execute(
            "UPDATE players SET xp = ?, level = ?, updated_at = ? WHERE user_id = ?",
            (p_xp, p_level, _now(), user_id),
        )
        result["new_player_level"] = p_level

        if player["faction"] == "pirate":
            bounty_gain = max(1, xp_amount // 5)
            conn.execute(
                "UPDATE players SET bounty = bounty + ? WHERE user_id = ?",
                (bounty_gain, user_id),
            )

    return result


def get_rank(player: dict) -> str:
    level = player["level"]
    ranks = PIRATE_RANKS if player["faction"] == "pirate" else MARINE_RANKS
    current = ranks[0][1]
    for min_lvl, rank_name, _ in ranks:
        if level >= min_lvl:
            current = rank_name
    return current


def get_island(player: dict) -> dict:
    for island in ISLANDS:
        if island["id"] == player["current_island"]:
            return island
    return ISLANDS[0]


def can_access_island(player: dict, island_id: str) -> bool:
    for island in ISLANDS:
        if island["id"] == island_id:
            return player["level"] >= island["min_level"]
    return False


def set_island(user_id: int, island_id: str) -> bool:
    player = get_player(user_id)
    if not player or not can_access_island(player, island_id):
        return False
    with get_db() as conn:
        conn.execute(
            "UPDATE players SET current_island = ?, updated_at = ? WHERE user_id = ?",
            (island_id, _now(), user_id),
        )
    return True


def is_dead(player: dict) -> bool:
    death_until = _parse_dt(player.get("death_until"))
    if not death_until:
        return False
    return datetime.now(timezone.utc) < death_until


def set_death_cooldown(user_id: int, minutes: int = 30) -> None:
    until = (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()
    with get_db() as conn:
        conn.execute(
            "UPDATE players SET death_until = ?, updated_at = ? WHERE user_id = ?",
            (until, _now(), user_id),
        )


def claim_daily(user_id: int) -> dict | None:
    player = get_player(user_id)
    if not player:
        return None

    now = datetime.now(timezone.utc)
    last = _parse_dt(player.get("last_daily"))
    if last and (now - last).days < 1:
        return None

    streak = player.get("daily_streak", 0)
    if last and (now - last).days == 1:
        streak = min(MAX_DAILY_STREAK, streak + 1)
    else:
        streak = 1

    reward = DAILY_REWARD_BASE + (streak - 1) * DAILY_REWARD_STREAK_BONUS
    with get_db() as conn:
        conn.execute(
            """UPDATE players SET beli = beli + ?, daily_streak = ?,
               last_daily = ?, updated_at = ? WHERE user_id = ?""",
            (reward, streak, now.isoformat(), _now(), user_id),
        )
    return {"beli": reward, "streak": streak}


def buy_character(user_id: int, char_id: str) -> str | None:
    """Returns error message or None on success."""
    char = CHARACTERS.get(char_id)
    if not char:
        return "شخصیت یافت نشد."

    player = get_player(user_id)
    if not player:
        return "بازیکن یافت نشد."

    if char["faction"] != player["faction"]:
        return "این شخصیت با فکشن تو سازگار نیست."

    owned = {c["char_id"] for c in get_owned_characters(user_id)}
    if char_id in owned:
        return "این شخصیت را قبلاً داری."

    if player["beli"] < char["price"]:
        return f"Beli کافی نیست. نیاز: {char['price']:,}"

    with get_db() as conn:
        conn.execute(
            "UPDATE players SET beli = beli - ?, updated_at = ? WHERE user_id = ?",
            (char["price"], _now(), user_id),
        )
        conn.execute(
            "INSERT INTO owned_characters (user_id, char_id, level, xp) VALUES (?, ?, 1, 0)",
            (user_id, char_id),
        )
    return None


def update_player_info(user_id: int, name: str = None, age: int = None, height: int = None, weight: int = None, photo_id: str = None, race: str = None) -> None:
    fields = []
    values = []
    if name is not None:
        fields.append("username = ?"); values.append(name)
    if age is not None:
        fields.append("age = ?"); values.append(age)
    if height is not None:
        fields.append("height = ?"); values.append(height)
    if weight is not None:
        fields.append("weight = ?"); values.append(weight)
    if photo_id is not None:
        fields.append("photo_id = ?"); values.append(photo_id)
    if race is not None:
        fields.append("race = ?"); values.append(race)
    if not fields:
        return
    values.extend([_now(), user_id])
    with get_db() as conn:
        conn.execute(
            f"UPDATE players SET {', '.join(fields)}, updated_at = ? WHERE user_id = ?",
            values
        )


TRAIN_LEVELS = [
    {"key": "light",  "name": "تمرین سبک",   "cooldown_mins": 10,  "energy": 10, "xp_gain": 30,  "power_gain": (1, 3)},
    {"key": "medium", "name": "تمرین متوسط", "cooldown_mins": 30,  "energy": 20, "xp_gain": 80,  "power_gain": (3, 7)},
    {"key": "hard",   "name": "تمرین سنگین", "cooldown_mins": 120, "energy": 40, "xp_gain": 200, "power_gain": (7, 15)},
]


def get_train_status(user_id: int, level_key: str) -> dict:
    """وضعیت تمرین: not_started / in_progress / completed"""
    t = next((x for x in TRAIN_LEVELS if x["key"] == level_key), None)
    if not t:
        return {"status": "not_started"}
    cooldown_key = f"train_{level_key}"
    with get_db() as conn:
        row = conn.execute(
            "SELECT metadata FROM inventory WHERE user_id=? AND item_type='train_cd' AND item_id=?",
            (user_id, cooldown_key)
        ).fetchone()
    if not row:
        return {"status": "not_started"}
    start_time = _parse_dt(row["metadata"])
    if not start_time:
        return {"status": "not_started"}
    now = datetime.now(timezone.utc)
    elapsed_mins = (now - start_time).total_seconds() / 60
    remaining = t["cooldown_mins"] - elapsed_mins
    if remaining <= 0:
        return {"status": "completed", "level": t}
    mins = int(remaining)
    secs = int((remaining - mins) * 60)
    return {"status": "in_progress", "mins": mins, "secs": secs, "level": t}


def start_train(user_id: int, level_key: str) -> dict:
    """شروع تمرین — cooldown را ست می‌کند."""
    t = next((x for x in TRAIN_LEVELS if x["key"] == level_key), None)
    if not t:
        return {"ok": False, "msg": "تمرین نامعتبر"}
    player = get_player(user_id)
    if not player:
        return {"ok": False, "msg": "بازیکن یافت نشد"}
    if player["energy"] < t["energy"]:
        return {"ok": False, "msg": f"⚡ انرژی کافی نیست. نیاز: {t['energy']}"}

    status = get_train_status(user_id, level_key)
    if status["status"] == "in_progress":
        return {"ok": False, "msg": f"⏳ {status['mins']}:{status['secs']:02d} دیگه تموم میشه"}

    if status["status"] == "completed":
        return {"ok": False, "msg": "تمرین تموم شده، نتیجه رو بگیر!"}

    # شروع تمرین
    spend_energy(user_id, t["energy"])
    now = datetime.now(timezone.utc)
    cooldown_key = f"train_{level_key}"
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM inventory WHERE user_id=? AND item_type='train_cd' AND item_id=?",
            (user_id, cooldown_key)
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE inventory SET metadata=? WHERE user_id=? AND item_type='train_cd' AND item_id=?",
                (now.isoformat(), user_id, cooldown_key)
            )
        else:
            conn.execute(
                "INSERT INTO inventory (user_id, item_type, item_id, quantity, metadata) VALUES (?,?,?,1,?)",
                (user_id, "train_cd", cooldown_key, now.isoformat())
            )
    return {"ok": True, "cooldown_mins": t["cooldown_mins"]}


def claim_train(user_id: int, level_key: str) -> dict:
    """گرفتن جایزه تمرین تموم‌شده."""
    status = get_train_status(user_id, level_key)
    if status["status"] != "completed":
        return {"ok": False, "msg": "تمرین هنوز تموم نشده"}
    t = status["level"]
    import random
    power_gain = random.randint(*t["power_gain"])
    level_info = add_xp(user_id, None, t["xp_gain"])
    # پاک کردن cooldown تا بتونه دوباره شروع کنه
    with get_db() as conn:
        conn.execute(
            "DELETE FROM inventory WHERE user_id=? AND item_type='train_cd' AND item_id=?",
            (user_id, f"train_{level_key}")
        )
    return {"ok": True, "xp": t["xp_gain"], "power_gain": power_gain, "level_info": level_info}



