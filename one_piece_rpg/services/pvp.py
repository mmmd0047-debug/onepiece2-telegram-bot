"""PvP Battle System — 1v1, 2v2, team battles in groups."""
import random
import time
from datetime import datetime, timezone
from one_piece_rpg.data import ITEMS, FISH_TYPES
from one_piece_rpg.database import get_db, _now

BATTLE_TURN_TIMEOUT = 60      # ثانیه برای هر نوبت
BATTLE_JOIN_TIMEOUT = 60      # ثانیه برای پیوستن
BATTLE_COOLDOWN_MINS = 15     # cooldown بعد از مبارزه

# حافظه battle sessions
_sessions: dict[str, dict] = {}  # battle_id -> session


def get_user_active_battle(user_id: int) -> dict | None:
    """پیدا کردن جنگ فعال کاربر."""
    for bid, s in _sessions.items():
        if s["status"] in ("waiting", "active"):
            if user_id in s["team1"] or user_id in s["team2"]:
                return s
    return None


def create_battle(chat_id: int, creator_id: int, mode: str) -> str:
    """mode: '1v1', '2v2', '3v3'"""
    import uuid
    bid = str(uuid.uuid4())[:8]
    teams = int(mode[0])
    _sessions[bid] = {
        "battle_id": bid,
        "chat_id": chat_id,
        "mode": mode,
        "team_size": teams,
        "team1": [],
        "team2": [],
        "status": "waiting",  # waiting -> active -> ended
        "created_at": time.time(),
        "current_turn": None,
        "turn_started": 0.0,
        "round": 1,
        "log": [],
    }
    return bid


def join_battle(bid: str, user_id: int, team: int) -> dict:
    """team: 1 یا 2"""
    s = _sessions.get(bid)
    if not s:
        return {"ok": False, "msg": "مبارزه پیدا نشد!"}
    if s["status"] != "waiting":
        return {"ok": False, "msg": "مبارزه شروع شده!"}
    if time.time() - s["created_at"] > BATTLE_JOIN_TIMEOUT:
        s["status"] = "expired"
        return {"ok": False, "msg": "وقت پیوستن تموم شد!"}

    t1, t2 = s["team1"], s["team2"]
    # چک اینکه کاربر قبلاً تیمی نداشته باشه
    if user_id in t1 or user_id in t2:
        return {"ok": False, "msg": "قبلاً پیوستی!"}

    target = t1 if team == 1 else t2
    if len(target) >= s["team_size"]:
        return {"ok": False, "msg": f"تیم {team} پر شده!"}

    target.append(user_id)
    return {"ok": True}


def is_battle_full(bid: str) -> bool:
    s = _sessions.get(bid)
    if not s:
        return False
    return len(s["team1"]) == s["team_size"] and len(s["team2"]) == s["team_size"]


def get_battle(bid: str) -> dict | None:
    return _sessions.get(bid)


def start_battle(bid: str) -> dict:
    s = _sessions.get(bid)
    if not s:
        return {"ok": False, "msg": "مبارزه پیدا نشد!"}
    if not is_battle_full(bid):
        return {"ok": False, "msg": "هنوز همه نپیوستن!"}

    # ساخت state بازیکنان
    with get_db() as conn:
        all_ids = s["team1"] + s["team2"]
        players_data = {}
        for uid in all_ids:
            row = conn.execute("SELECT * FROM players WHERE user_id=?", (uid,)).fetchone()
            if row:
                p = dict(row)
                # آیتم‌های انتخاب شده برای جنگ
                import json
                selected_items = []
                if p.get("battle_items"):
                    try:
                        selected_items = json.loads(p["battle_items"])
                    except Exception:
                        selected_items = []

                items_row = conn.execute(
                    "SELECT item_id, quantity FROM inventory WHERE user_id=? AND item_type='item'",
                    (uid,)
                ).fetchall()
                fish_row = conn.execute(
                    "SELECT item_id, quantity FROM inventory WHERE user_id=? AND item_type='fish'",
                    (uid,)
                ).fetchall()

                p["battle_hp"] = 100 + p["level"] * 5
                p["battle_atk"] = 10 + p["level"] * 2
                p["battle_def"] = 5 + p["level"]

                # اعمال آمار آیتم‌ها
                for ir in items_row:
                    item = ITEMS.get(ir["item_id"], {})
                    p["battle_atk"] += item.get("atk", 0) * min(ir["quantity"], 1)
                    p["battle_def"] += item.get("def", 0) * min(ir["quantity"], 1)

                # آیتم‌های قابل استفاده در جنگ (از selected_items)
                all_inv = {r["item_id"]: r["quantity"] for r in items_row}
                all_inv.update({r["item_id"]: r["quantity"] for r in fish_row})

                if selected_items:
                    # فقط آیتم‌های انتخاب شده
                    p["items_available"] = {k: v for k, v in all_inv.items() if k in selected_items}
                else:
                    p["items_available"] = all_inv

                players_data[uid] = p

    s["players"] = players_data
    # ترتیب نوبت: تیم 1 اول، تیم 2 بعد، ردیفی
    turn_order = []
    for i in range(s["team_size"]):
        if i < len(s["team1"]):
            turn_order.append(s["team1"][i])
        if i < len(s["team2"]):
            turn_order.append(s["team2"][i])
    s["turn_order"] = turn_order
    s["turn_index"] = 0
    s["current_turn"] = turn_order[0]
    s["turn_started"] = time.time()
    s["turn_id"] = 1
    s["status"] = "active"
    return {"ok": True}


def do_attack(bid: str, attacker_id: int, action: str, target_id: int | None = None, item_id: str | None = None) -> dict:
    """
    action: 'punch' | 'sword' | 'use_item'
    """
    s = _sessions.get(bid)
    if not s or s["status"] != "active":
        return {"ok": False, "msg": "مبارزه‌ای فعال نیست!"}
    if s["current_turn"] != attacker_id:
        return {"ok": False, "msg": "نوبت تو نیست!"}
    if time.time() - s["turn_started"] > BATTLE_TURN_TIMEOUT:
        return kick_from_battle(bid, attacker_id)

    attacker = s["players"][attacker_id]
    # پیدا کردن هدف پیش‌فرض (اولین دشمن زنده)
    if target_id is None:
        enemy_team = s["team2"] if attacker_id in s["team1"] else s["team1"]
        alive_enemies = [uid for uid in enemy_team if s["players"][uid]["battle_hp"] > 0]
        if not alive_enemies:
            return check_battle_end(bid)
        target_id = alive_enemies[0]

    target = s["players"].get(target_id)
    if not target or target["battle_hp"] <= 0:
        return {"ok": False, "msg": "هدف معتبر نیست!"}

    log_line = ""
    result = {"ok": True, "action": action, "attacker": attacker_id, "target": target_id}

    if action == "punch":
        dmg = max(1, attacker["battle_atk"] - target["battle_def"] // 2 + random.randint(-5, 5))
        target["battle_hp"] = max(0, target["battle_hp"] - dmg)
        log_line = f"👊 {attacker['username']} به {target['username']} {dmg} ضربه زد!"
        result["dmg"] = dmg

    elif action == "sword":
        # شمشیر ۵۰٪ بیشتر ضربه میزنه
        sword_items = [k for k in attacker["items_available"] if "sword" in k or "axe" in k]
        if not sword_items:
            return {"ok": False, "msg": "شمشیری نداری! مشت بزن."}
        dmg = max(1, int(attacker["battle_atk"] * 1.5) - target["battle_def"] // 2 + random.randint(-3, 8))
        target["battle_hp"] = max(0, target["battle_hp"] - dmg)
        log_line = f"⚔️ {attacker['username']} با شمشیر به {target['username']} {dmg} ضربه زد!"
        result["dmg"] = dmg

    elif action == "use_item" and item_id:
        # خوردن غذا = ریکاوری جون
        if item_id.startswith("cooked_") or item_id in FISH_TYPES or item_id in ("meat", "simple_food", "seafood", "special_food"):
            heal = random.randint(15, 40)
            attacker["battle_hp"] = min(100 + attacker["level"] * 5, attacker["battle_hp"] + heal)
            # کم کردن از session
            if item_id in attacker["items_available"]:
                attacker["items_available"][item_id] -= 1
                if attacker["items_available"][item_id] <= 0:
                    del attacker["items_available"][item_id]
            # کم کردن از db
            with get_db() as conn:
                item_type = "fish" if item_id in FISH_TYPES else "item"
                row = conn.execute(
                    "SELECT id, quantity FROM inventory WHERE user_id=? AND item_type=? AND item_id=?",
                    (attacker_id, item_type, item_id)
                ).fetchone()
                if row:
                    if row["quantity"] <= 1:
                        conn.execute("DELETE FROM inventory WHERE id=?", (row["id"],))
                    else:
                        conn.execute("UPDATE inventory SET quantity=quantity-1 WHERE id=?", (row["id"],))
            log_line = f"🍖 {attacker['username']} غذا خورد و {heal} جون گرفت!"
            result["heal"] = heal
        else:
            return {"ok": False, "msg": "این آیتم در مبارزه قابل استفاده نیست!"}

    s["log"].append(log_line)

    # چک پایان مبارزه
    end = check_battle_end(bid)
    if end.get("ended"):
        return {**result, **end}

    # نوبت بعدی
    _advance_turn(bid)
    result["next_turn"] = s["current_turn"]
    return result


def _advance_turn(bid: str):
    s = _sessions[bid]
    order = s["turn_order"]
    idx = s["turn_index"]
    for i in range(1, len(order) + 1):
        next_idx = (idx + i) % len(order)
        next_uid = order[next_idx]
        if s["players"][next_uid]["battle_hp"] > 0:
            s["turn_index"] = next_idx
            s["current_turn"] = next_uid
            s["turn_started"] = time.time()
            s["turn_id"] = s.get("turn_id", 0) + 1  # هر نوبت یه ID جدید
            return
    s["status"] = "ended"


def check_battle_end(bid: str) -> dict:
    s = _sessions.get(bid)
    if not s:
        return {"ended": False}
    t1_alive = any(s["players"][uid]["battle_hp"] > 0 for uid in s["team1"])
    t2_alive = any(s["players"][uid]["battle_hp"] > 0 for uid in s["team2"])
    if not t1_alive or not t2_alive:
        s["status"] = "ended"
        winner_team = s["team1"] if t1_alive else s["team2"]
        loser_team = s["team2"] if t1_alive else s["team1"]
        # جایزه
        xp_reward = 50 * s["team_size"]
        beli_reward = 200 * s["team_size"]
        with get_db() as conn:
            for uid in winner_team:
                conn.execute("UPDATE players SET xp=xp+?, beli=beli+? WHERE user_id=?",
                             (xp_reward, beli_reward, uid))
        # cooldown برای همه
        _set_battle_cooldowns(s["team1"] + s["team2"])
        return {
            "ended": True,
            "winner_team": winner_team,
            "loser_team": loser_team,
            "xp_reward": xp_reward,
            "beli_reward": beli_reward,
        }
    return {"ended": False}


def kick_from_battle(bid: str, user_id: int) -> dict:
    """اخراج بازیکن به دلیل timeout نوبت."""
    s = _sessions.get(bid)
    if not s:
        return {"ok": False, "msg": "مبارزه پیدا نشد!"}
    p = s["players"].get(user_id)
    if p:
        p["battle_hp"] = 0
    s["log"].append(f"⏰ {p['username'] if p else user_id} به دلیل عدم پاسخ از مبارزه اخراج شد!")
    _advance_turn(bid)
    end = check_battle_end(bid)
    if end.get("ended"):
        return end
    return {"ok": True, "kicked": user_id, "next_turn": s["current_turn"]}


def _set_battle_cooldowns(user_ids: list[int]):
    now = time.time()
    with get_db() as conn:
        for uid in user_ids:
            conn.execute(
                """INSERT OR REPLACE INTO fight_cooldowns (user_id, last_fight) VALUES (?,?)""",
                (uid, now)
            )


def get_fight_cooldown(user_id: int) -> int:
    """ثانیه تا cooldown تموم بشه. 0 = آزاد."""
    with get_db() as conn:
        try:
            row = conn.execute("SELECT last_fight FROM fight_cooldowns WHERE user_id=?", (user_id,)).fetchone()
        except Exception:
            return 0
    if not row:
        return 0
    elapsed = (time.time() - row["last_fight"]) / 60
    remaining = BATTLE_COOLDOWN_MINS - elapsed
    return max(0, int(remaining * 60))


def get_battle_status(bid: str) -> dict | None:
    return _sessions.get(bid)


def format_battle_state(bid: str) -> str:
    s = _sessions.get(bid)
    if not s:
        return "مبارزه‌ای وجود نداره!"
    lines = [f"⚔️ *مبارزه {s['mode']}*\n"]
    for team_num, team in [(1, s["team1"]), (2, s["team2"])]:
        lines.append(f"تیم {team_num}:")
        for uid in team:
            p = s["players"].get(uid, {})
            hp = p.get("battle_hp", 0)
            max_hp = 100 + p.get("level", 1) * 5
            bar = "█" * (hp * 10 // max_hp) + "░" * (10 - hp * 10 // max_hp)
            marker = "👉 " if uid == s.get("current_turn") else "    "
            lines.append(f"{marker}{p.get('username','?')} ❤️{hp}/{max_hp} [{bar}]")
    return "\n".join(lines)
