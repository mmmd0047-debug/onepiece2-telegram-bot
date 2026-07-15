"""Black Market service."""

from one_piece_rpg.database import _now, get_db
from one_piece_rpg.data import ITEMS, DEVIL_FRUITS, CHEST_TYPES, RARITY_EMOJI


def list_item(seller_id: int, seller_name: str, item_type: str, item_id: str, price: int) -> dict:
    """ثبت آیتم در بلک مارکت."""
    if price < 1:
        return {"ok": False, "msg": "قیمت باید حداقل ۱ Beli باشه"}
    if price > 10_000_000:
        return {"ok": False, "msg": "قیمت خیلی زیاده!"}

    # چک وجود آیتم در inventory
    with get_db() as conn:
        row = conn.execute(
            "SELECT id, quantity FROM inventory WHERE user_id=? AND item_type=? AND item_id=?",
            (seller_id, item_type, item_id)
        ).fetchone()
        if not row or row["quantity"] < 1:
            return {"ok": False, "msg": "این آیتم رو نداری!"}

        # چک تعداد آگهی‌های فعال
        count = conn.execute(
            "SELECT COUNT(*) as c FROM black_market WHERE seller_id=?", (seller_id,)
        ).fetchone()["c"]
        if count >= 5:
            return {"ok": False, "msg": "حداکثر ۵ آگهی می‌تونی داشته باشی"}

        # کم کردن از inventory
        if row["quantity"] <= 1:
            conn.execute("DELETE FROM inventory WHERE id=?", (row["id"],))
        else:
            conn.execute("UPDATE inventory SET quantity=quantity-1 WHERE id=?", (row["id"],))

        # ثبت در بلک مارکت
        conn.execute(
            "INSERT INTO black_market (seller_id, seller_name, item_type, item_id, price, listed_at) VALUES (?,?,?,?,?,?)",
            (seller_id, seller_name, item_type, item_id, price, _now())
        )
    return {"ok": True}


def get_listings(page: int = 0, per_page: int = 8) -> list[dict]:
    """لیست آگهی‌های بلک مارکت."""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM black_market ORDER BY listed_at DESC LIMIT ? OFFSET ?",
            (per_page, page * per_page)
        ).fetchall()
    return [dict(r) for r in rows]


def get_listing_count() -> int:
    with get_db() as conn:
        return conn.execute("SELECT COUNT(*) as c FROM black_market").fetchone()["c"]


def buy_listing(buyer_id: int, listing_id: int) -> dict:
    """خرید آیتم از بلک مارکت."""
    with get_db() as conn:
        listing = conn.execute(
            "SELECT * FROM black_market WHERE id=?", (listing_id,)
        ).fetchone()
        if not listing:
            return {"ok": False, "msg": "آگهی پیدا نشد!"}
        listing = dict(listing)

        if listing["seller_id"] == buyer_id:
            return {"ok": False, "msg": "نمی‌تونی از خودت بخری!"}

        buyer = conn.execute("SELECT beli FROM players WHERE user_id=?", (buyer_id,)).fetchone()
        if not buyer or buyer["beli"] < listing["price"]:
            return {"ok": False, "msg": f"Beli کافی نیست. نیاز: {listing['price']:,}"}

        # انتقال پول
        conn.execute("UPDATE players SET beli=beli-? WHERE user_id=?", (listing["price"], buyer_id))
        conn.execute("UPDATE players SET beli=beli+? WHERE user_id=?", (listing["price"], listing["seller_id"]))

        # دادن آیتم به خریدار
        ex = conn.execute(
            "SELECT id FROM inventory WHERE user_id=? AND item_type=? AND item_id=?",
            (buyer_id, listing["item_type"], listing["item_id"])
        ).fetchone()
        if ex:
            conn.execute("UPDATE inventory SET quantity=quantity+1 WHERE id=?", (ex["id"],))
        else:
            conn.execute(
                "INSERT INTO inventory (user_id,item_type,item_id,quantity) VALUES (?,?,?,1)",
                (buyer_id, listing["item_type"], listing["item_id"])
            )

        # حذف آگهی
        conn.execute("DELETE FROM black_market WHERE id=?", (listing_id,))

    return {"ok": True, "item_id": listing["item_id"], "item_type": listing["item_type"], "price": listing["price"]}


def cancel_listing(seller_id: int, listing_id: int) -> dict:
    """لغو آگهی و برگشت آیتم."""
    with get_db() as conn:
        listing = conn.execute(
            "SELECT * FROM black_market WHERE id=? AND seller_id=?", (listing_id, seller_id)
        ).fetchone()
        if not listing:
            return {"ok": False, "msg": "آگهی پیدا نشد!"}
        listing = dict(listing)
        conn.execute("DELETE FROM black_market WHERE id=?", (listing_id,))
        ex = conn.execute(
            "SELECT id FROM inventory WHERE user_id=? AND item_type=? AND item_id=?",
            (seller_id, listing["item_type"], listing["item_id"])
        ).fetchone()
        if ex:
            conn.execute("UPDATE inventory SET quantity=quantity+1 WHERE id=?", (ex["id"],))
        else:
            conn.execute(
                "INSERT INTO inventory (user_id,item_type,item_id,quantity) VALUES (?,?,?,1)",
                (seller_id, listing["item_type"], listing["item_id"])
            )
    return {"ok": True}


def format_item_name(item_type: str, item_id: str) -> str:
    if item_type == "item":
        info = ITEMS.get(item_id, {})
        emoji = RARITY_EMOJI.get(info.get("rarity", "common"), "⚪")
        return f"{emoji} {info.get('name', item_id)}"
    elif item_type == "devil_fruit":
        info = DEVIL_FRUITS.get(item_id, {})
        emoji = RARITY_EMOJI.get(info.get("rarity", "common"), "⚪")
        return f"🍎{emoji} {info.get('name', item_id)}"
    elif item_type == "chest":
        info = CHEST_TYPES.get(item_id, {})
        return f"{info.get('emoji','📦')} {info.get('name', item_id)}"
    return item_id
