
"""Battle system."""
import random
from one_piece_rpg.data import (
    CHEST_TYPES, DEFAULT_ENEMIES, DEVIL_FRUIT_DROP_RATES, DEVIL_FRUITS,
    ENEMIES, FIGHT_ENERGY_COST, ITEMS, RARITY_ORDER, SEA_ENEMIES, SHIPS,
)
from one_piece_rpg.database import _now, get_db
from one_piece_rpg.services.player import (
    add_beli, add_xp, get_player, is_dead, set_death_cooldown,
    spend_energy, sync_energy,
)


def _player_atk(player):
    base = 10 + player["level"] * 2
    with get_db() as conn:
        rows = conn.execute(
            "SELECT item_id, quantity FROM inventory WHERE user_id=? AND item_type='item'",
            (player["user_id"],)
        ).fetchall()
    for row in rows:
        item = ITEMS.get(row["item_id"], {})
        base += item.get("atk", 0) * min(row["quantity"], 1)
    return base


def _player_def(player):
    base = 5 + player["level"]
    with get_db() as conn:
        rows = conn.execute(
            "SELECT item_id, quantity FROM inventory WHERE user_id=? AND item_type='item'",
            (player["user_id"],)
        ).fetchall()
    for row in rows:
        item = ITEMS.get(row["item_id"], {})
        base += item.get("def", 0) * min(row["quantity"], 1)
    return base


def calc_power(atk, defense, hp):
    return atk * 1.5 + defense + hp * 0.3 + random.uniform(-10, 10)


def get_island_enemies(island_id):
    return ENEMIES.get(island_id, DEFAULT_ENEMIES)


def pick_enemy(island_id, player_level):
    enemies = get_island_enemies(island_id)
    suitable = [e for e in enemies if e["lvl"] <= player_level + 5]
    if not suitable:
        suitable = enemies[:1]
    weights = [3 if not e.get("boss") else 1 for e in suitable]
    return random.choices(suitable, weights=weights, k=1)[0]


def fight(user_id):
    player = get_player(user_id)
    if not player:
        return {"ok": False, "message": "بازیکن یافت نشد."}
    player = sync_energy(player)
    if is_dead(player):
        return {"ok": False, "message": "در حال بهبودی هستی. کمی صبر کن..."}
    if player["energy"] < FIGHT_ENERGY_COST:
        return {"ok": False, "message": f"انرژی کافی نیست! ({player['energy']}/100)"}
    if not spend_energy(user_id, FIGHT_ENERGY_COST):
        return {"ok": False, "message": "انرژی کافی نیست!"}

    atk = _player_atk(player)
    defense = _player_def(player)
    hp = 100 + player["level"] * 5
    enemy = pick_enemy(player["current_island"], player["level"])
    player_power = calc_power(atk, defense, hp)
    enemy_power = calc_power(enemy["atk"], enemy.get("def", enemy["atk"] // 2), enemy["hp"])

    result = {
        "ok": True, "enemy": enemy,
        "player_name": player.get("username") or "تو",
        "won": False, "died": False,
        "xp": 0, "beli": 0,
        "item": None, "chest": None, "devil_fruit": None, "level_info": {},
    }

    if player_power >= enemy_power:
        result["won"] = True
        add_beli(user_id, enemy["beli"])
        result["xp"] = enemy["xp"]
        result["beli"] = enemy["beli"]
        result["level_info"] = add_xp(user_id, None, enemy["xp"])
        if random.random() < enemy.get("item_chance", 0.05):
            result["item"] = _roll_item()
        if random.random() < 0.03:
            result["chest"] = random.choice(list(CHEST_TYPES.keys()))
        if random.random() < 0.001:
            result["devil_fruit"] = _roll_devil_fruit()
        if result["item"]:
            _add_inventory(user_id, "item", result["item"])
        if result["chest"]:
            _add_inventory(user_id, "chest", result["chest"])
        if result["devil_fruit"]:
            _add_inventory(user_id, "devil_fruit", result["devil_fruit"])
    else:
        if random.random() < enemy.get("death_chance", 0.03):
            result["died"] = True
            set_death_cooldown(user_id)
            penalty = max(0, int(player["beli"] * 0.05))
            if penalty:
                add_beli(user_id, -penalty)
            result["beli"] = -penalty
    return result


def sea_fight(user_id):
    player = get_player(user_id)
    if not player:
        return {"ok": False, "message": "بازیکن یافت نشد."}
    if not player.get("ship_id"):
        return {"ok": False, "message": "برای مبارزه دریایی باید کشتی داشته باشی!"}
    if player["energy"] < FIGHT_ENERGY_COST:
        return {"ok": False, "message": "انرژی کافی نیست!"}
    spend_energy(user_id, FIGHT_ENERGY_COST)
    ship = SHIPS[player["ship_id"]]
    suitable = [e for e in SEA_ENEMIES if e["lvl"] <= player["level"] + 5]
    if not suitable:
        suitable = SEA_ENEMIES[:1]
    enemy = random.choice(suitable)
    player_power = ship["defense"] * 2 + ship["hp"] * 0.1 + player["level"] * 3 + random.uniform(-20, 20)
    enemy_power = enemy["atk"] * 1.5 + enemy["ship_hp"] * 0.1 + random.uniform(-20, 20)
    result = {"ok": True, "enemy": enemy, "ship": ship, "won": player_power >= enemy_power, "xp": 0, "beli": 0}
    if result["won"]:
        result["xp"] = enemy["xp"]
        result["beli"] = enemy["beli"]
        add_beli(user_id, enemy["beli"])
        add_xp(user_id, None, enemy["xp"])
    else:
        penalty = max(0, int(player["beli"] * 0.03))
        add_beli(user_id, -penalty)
        result["beli"] = -penalty
    return result


def fish(user_id):
    from one_piece_rpg.data import FISH_TYPES, FISHING_RODS, FISH_COOLDOWN_MINS
    import time
    player = get_player(user_id)
    if not player:
        return {"ok": False, "message": "بازیکن یافت نشد."}

    # چک cooldown
    with get_db() as conn:
        cd_row = conn.execute(
            "SELECT metadata FROM inventory WHERE user_id=? AND item_type='fish_cd' AND item_id='last'",
            (user_id,)
        ).fetchone()
    if cd_row and cd_row["metadata"]:
        from one_piece_rpg.database import _parse_dt
        from datetime import datetime, timezone
        last_fish = _parse_dt(cd_row["metadata"])
        if last_fish:
            elapsed = (datetime.now(timezone.utc) - last_fish).total_seconds() / 60
            remaining = FISH_COOLDOWN_MINS - elapsed
            if remaining > 0:
                mins = int(remaining); secs = int((remaining - mins) * 60)
                return {"ok": False, "message": f"⏳ {mins}:{secs:02d} دیگه می‌تونی ماهی بگیری!"}

    with get_db() as conn:
        rod_row = conn.execute(
            "SELECT id, item_id FROM inventory WHERE user_id=? AND item_type='rod' LIMIT 1",
            (user_id,)
        ).fetchone()
    if not rod_row:
        return {"ok": False, "message": "برای ماهیگیری به قلاب نیاز داری! از تاجر بخر."}

    rod_id = rod_row["item_id"]
    rod = FISHING_RODS.get(rod_id, FISHING_RODS["simple_rod"])

    fish_list = list(FISH_TYPES.items())
    weights = [max(0.01, f["chance"]) for _, f in fish_list]
    fish_id, fish_info = random.choices(fish_list, weights=weights, k=1)[0]

    # ذخیره زمان آخرین ماهیگیری
    from one_piece_rpg.database import _now
    from datetime import datetime, timezone
    now_str = datetime.now(timezone.utc).isoformat()
    with get_db() as conn:
        ex = conn.execute(
            "SELECT id FROM inventory WHERE user_id=? AND item_type='fish_cd' AND item_id='last'",
            (user_id,)
        ).fetchone()
        if ex:
            conn.execute("UPDATE inventory SET metadata=? WHERE id=?", (now_str, ex["id"]))
        else:
            conn.execute(
                "INSERT INTO inventory (user_id,item_type,item_id,quantity,metadata) VALUES (?,?,?,1,?)",
                (user_id, "fish_cd", "last", now_str)
            )

    rod_broke = False
    break_chance = fish_info.get("rod_break", 0)
    if break_chance > 0:
        rod_strength = {"simple_rod": 1, "pro_rod": 2, "legendary_rod": 4}.get(rod_id, 1)
        if random.random() < (break_chance / rod_strength) * 0.1:
            rod_broke = True
            with get_db() as conn:
                conn.execute("DELETE FROM inventory WHERE user_id=? AND item_type='rod'", (user_id,))

    _add_inventory(user_id, "fish", fish_id)
    return {"ok": True, "fish_id": fish_id, "fish": fish_info, "rod_broke": rod_broke}


def _roll_item():
    items_by_rarity = {}
    for item_id, item in ITEMS.items():
        items_by_rarity.setdefault(item["rarity"], []).append(item_id)
    rarity = random.choices(["common", "rare", "epic", "legendary"], weights=[60, 25, 12, 3], k=1)[0]
    pool = items_by_rarity.get(rarity, list(ITEMS.keys()))
    return random.choice(pool)


def _roll_devil_fruit():
    for rarity in reversed(RARITY_ORDER):
        rate = DEVIL_FRUIT_DROP_RATES[rarity]
        if random.random() < rate:
            pool = [fid for fid, f in DEVIL_FRUITS.items() if f["rarity"] == rarity]
            if pool:
                return random.choice(pool)
    return None


def _add_inventory(user_id, item_type, item_id):
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id, quantity FROM inventory WHERE user_id=? AND item_type=? AND item_id=?",
            (user_id, item_type, item_id),
        ).fetchone()
        if existing:
            conn.execute("UPDATE inventory SET quantity=quantity+1 WHERE id=?", (existing["id"],))
        else:
            conn.execute(
                "INSERT INTO inventory (user_id, item_type, item_id, quantity) VALUES (?,?,?,1)",
                (user_id, item_type, item_id),
            )


def get_inventory(user_id):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM inventory WHERE user_id=? ORDER BY item_type, item_id",
            (user_id,),
        ).fetchall()
    return [dict(r) for r in rows]
