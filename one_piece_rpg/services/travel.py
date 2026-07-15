"""Daily wheel and travel services."""

import random
from datetime import datetime, timezone

from one_piece_rpg.data import ISLANDS, SEA_EVENTS, SHIPS, WHEEL_REWARDS, WHEEL_COOLDOWN_MINS
from one_piece_rpg.database import _now, _parse_dt, get_db
from one_piece_rpg.services.battle import _add_inventory
from one_piece_rpg.services.player import (
    add_beli,
    add_xp,
    can_access_island,
    get_player,
    set_island,
    sync_energy,
)


def spin_wheel(user_id: int) -> dict | None:
    """چرخش شانسی — هر ساعت یک بار."""
    player = get_player(user_id)
    if not player:
        return None

    now = datetime.now(timezone.utc)
    last = _parse_dt(player.get("last_wheel"))
    if last:
        elapsed_mins = (now - last).total_seconds() / 60
        remaining = WHEEL_COOLDOWN_MINS - elapsed_mins
        if remaining > 0:
            mins = int(remaining)
            secs = int((remaining - mins) * 60)
            return {"error": True, "mins": mins, "secs": secs}

    weights = [r["weight"] for r in WHEEL_REWARDS]
    reward = random.choices(WHEEL_REWARDS, weights=weights, k=1)[0]

    with get_db() as conn:
        conn.execute(
            "UPDATE players SET last_wheel = ?, updated_at = ? WHERE user_id = ?",
            (now.isoformat(), _now(), user_id),
        )

    result = {"error": False, "label": reward["label"], "type": reward["type"]}

    if reward["type"] == "beli":
        amount = reward["amount"]
        add_beli(user_id, amount)
        result["amount"] = amount
    elif reward["type"] == "energy":
        with get_db() as conn:
            conn.execute(
                "UPDATE players SET energy = MIN(100, energy + ?) WHERE user_id = ?",
                (reward["amount"], user_id),
            )
        result["amount"] = reward["amount"]
    elif reward["type"] == "chest":
        _add_inventory(user_id, "chest", reward["chest"])
        result["chest"] = reward["chest"]
    elif reward["type"] == "item":
        _add_inventory(user_id, "item", reward["item"])
    # nothing: هیچ کاری نمیکنیم

    return result


def travel_to_island(user_id: int, island_id: str) -> dict:
    player = get_player(user_id)
    if not player:
        return {"ok": False, "message": "بازیکن یافت نشد."}

    if not can_access_island(player, island_id):
        island = next(i for i in ISLANDS if i["id"] == island_id)
        return {"ok": False, "message": f"برای {island['name']} باید Level {island['min_level']} باشی."}

    if not player.get("ship_id"):
        return {"ok": False, "message": "🚢 برای سفر بین جزایر به کشتی نیاز داری! /ship"}

    events = []
    for event in SEA_EVENTS:
        if random.random() < event["chance"]:
            events.append(event)
            if event["beli"]:
                add_beli(user_id, event["beli"])
            if event["xp"] and player.get("active_character"):
                add_xp(user_id, player["active_character"], event["xp"])

    set_island(user_id, island_id)
    island = next(i for i in ISLANDS if i["id"] == island_id)
    return {"ok": True, "island": island, "events": events}


def buy_ship(user_id: int, ship_id: str) -> str | None:
    ship = SHIPS.get(ship_id)
    if not ship:
        return "کشتی یافت نشد."

    player = get_player(user_id)
    if not player:
        return "بازیکن یافت نشد."

    if player.get("ship_id") == ship_id:
        return "این کشتی را داری."

    if player["beli"] < ship["price"]:
        return f"Beli کافی نیست. نیاز: {ship['price']:,}"

    with get_db() as conn:
        conn.execute(
            "UPDATE players SET beli = beli - ?, ship_id = ?, updated_at = ? WHERE user_id = ?",
            (ship["price"], ship_id, _now(), user_id),
        )
    return None
