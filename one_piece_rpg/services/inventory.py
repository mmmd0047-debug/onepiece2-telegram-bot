"""Inventory, devil fruit, and item helpers."""

from one_piece_rpg.data import DEVIL_FRUITS, ITEMS, RARITY_EMOJI
from one_piece_rpg.database import _now, get_db
from one_piece_rpg.services.battle import get_inventory
from one_piece_rpg.services.player import get_owned_characters, get_player


def format_inventory(user_id: int) -> str:
    items = get_inventory(user_id)
    if not items:
        return "🎒 انبار خالی است."

    lines = ["🎒 *انبار تو:*", ""]
    for entry in items:
        qty = entry["quantity"]
        item_type = entry["item_type"]
        item_id = entry["item_id"]

        if item_type == "train_cd" or item_type == "fish_cd":
            continue  # سیستمی، تو انبار نمیاد
        elif item_type == "fish":
            from one_piece_rpg.data import FISH_TYPES
            fi = FISH_TYPES.get(item_id, {"name": item_id, "emoji": "🐟", "sell": 0})
            lines.append(f"{fi['emoji']} {fi['name']} x{qty}")
        elif item_type == "item":
            info = ITEMS.get(item_id, {"name": item_id, "rarity": "common"})
            emoji = RARITY_EMOJI.get(info["rarity"], "⚪")
            lines.append(f"{emoji} {info['name']} x{qty}")
        elif item_type == "devil_fruit":
            info = DEVIL_FRUITS.get(item_id, {"name": item_id, "rarity": "common"})
            emoji = RARITY_EMOJI.get(info["rarity"], "⚪")
            lines.append(f"🍎 {emoji} {info['name']} x{qty}")
        elif item_type == "chest":
            from one_piece_rpg.data import CHEST_TYPES
            chest_info = CHEST_TYPES.get(item_id, {"name": item_id.title(), "emoji": "📦"})
            lines.append(f"{chest_info['emoji']} {chest_info['name']} x{qty}")
        elif item_type == "fish":
            pass  # قبلاً handle شد
        else:
            lines.append(f"• {item_id} x{qty}")

    return "\n".join(lines)


def feed_devil_fruit(user_id: int, fruit_id: str, char_id: str) -> str | None:
    """Feed devil fruit to character. Returns error or None."""
    player = get_player(user_id)
    if not player:
        return "بازیکن یافت نشد."

    owned = {c["char_id"]: c for c in get_owned_characters(user_id)}
    if char_id not in owned:
        return "این شخصیت را نداری."

    char = owned[char_id]
    if char.get("devil_fruit"):
        return "این شخصیت قبلاً Devil Fruit خورده."

    with get_db() as conn:
        inv = conn.execute(
            """SELECT id, quantity FROM inventory
               WHERE user_id = ? AND item_type = 'devil_fruit' AND item_id = ?""",
            (user_id, fruit_id),
        ).fetchone()
        if not inv or inv["quantity"] < 1:
            return "این Devil Fruit را نداری."

        if inv["quantity"] <= 1:
            conn.execute("DELETE FROM inventory WHERE id = ?", (inv["id"],))
        else:
            conn.execute(
                "UPDATE inventory SET quantity = quantity - 1 WHERE id = ?",
                (inv["id"],),
            )

        conn.execute(
            "UPDATE owned_characters SET devil_fruit = ? WHERE user_id = ? AND char_id = ?",
            (fruit_id, user_id, char_id),
        )

    return None


def sell_item(user_id: int, item_type: str, item_id: str) -> tuple[int | None, str | None]:
    """Sell one item. Returns (beli_gained, error)."""
    if item_type == "devil_fruit":
        return None, "Devil Fruit قابل فروش نیست (مگر قبل از خوردن)."

    sell_price = 0
    if item_type == "item":
        sell_price = ITEMS.get(item_id, {}).get("sell_price", 10)
    elif item_type == "chest":
        from one_piece_rpg.data import CHEST_TYPES

        prices = {"wooden": 30, "silver": 100, "gold": 300, "diamond": 800, "legendary": 2000, "mythic": 5000}
        sell_price = prices.get(item_id, 50)
    else:
        return None, "آیتم ناشناخته."

    with get_db() as conn:
        inv = conn.execute(
            "SELECT id, quantity FROM inventory WHERE user_id = ? AND item_type = ? AND item_id = ?",
            (user_id, item_type, item_id),
        ).fetchone()
        if not inv:
            return None, "این آیتم را نداری."

        if inv["quantity"] <= 1:
            conn.execute("DELETE FROM inventory WHERE id = ?", (inv["id"],))
        else:
            conn.execute(
                "UPDATE inventory SET quantity = quantity - 1 WHERE id = ?",
                (inv["id"],),
            )
        conn.execute(
            "UPDATE players SET beli = beli + ?, updated_at = ? WHERE user_id = ?",
            (sell_price, _now(), user_id),
        )
    return sell_price, None
