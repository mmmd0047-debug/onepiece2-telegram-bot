"""Rotating shop — refreshes every 6 hours, items return after 2-5 days."""

import random
import time
from one_piece_rpg.data import ITEMS

# state در حافظه — هر ۶ ساعت یه بار reset میشه
_shop_state = {
    "items": [],          # لیست item_id های فعلی
    "next_refresh": 0.0,  # timestamp بعدی refresh
    "item_timers": {},    # item_id -> timestamp که برمیگرده
}

SHOP_REFRESH_SECS = 6 * 3600   # ۶ ساعت
ITEM_RETURN_MIN = 2 * 86400    # ۲ روز
ITEM_RETURN_MAX = 5 * 86400    # ۵ روز
SHOP_SLOT_COUNT = 4            # تعداد آیتم‌های همزمان


def _refresh_shop():
    now = time.time()
    if now < _shop_state["next_refresh"] and _shop_state["items"]:
        return

    # آیتم‌هایی که هنوز cooldown دارن رو رد کن
    available = [
        item_id for item_id in ITEMS
        if now >= _shop_state["item_timers"].get(item_id, 0)
    ]

    # آیتم‌های فعلی رو cooldown بده
    for item_id in _shop_state["items"]:
        cooldown = random.uniform(ITEM_RETURN_MIN, ITEM_RETURN_MAX)
        _shop_state["item_timers"][item_id] = now + cooldown

    # انتخاب آیتم‌های جدید
    count = min(SHOP_SLOT_COUNT, len(available))
    # وزن‌دار: common بیشتر، legendary کمتر
    rarity_weights = {"common": 50, "rare": 30, "epic": 15, "legendary": 4, "mythic": 1}
    weights = [rarity_weights.get(ITEMS[i]["rarity"], 10) for i in available]
    if available:
        chosen = random.choices(available, weights=weights, k=min(count, len(available)))
        # حذف تکراری
        seen = set()
        _shop_state["items"] = [x for x in chosen if not (x in seen or seen.add(x))]
    else:
        _shop_state["items"] = list(ITEMS.keys())[:SHOP_SLOT_COUNT]

    _shop_state["next_refresh"] = now + SHOP_REFRESH_SECS


def get_shop_items() -> list[dict]:
    """لیست آیتم‌های فعلی تاجر."""
    _refresh_shop()
    result = []
    for item_id in _shop_state["items"]:
        if item_id in ITEMS:
            item = ITEMS[item_id].copy()
            item["id"] = item_id
            item["price"] = item["sell_price"] * 3
            result.append(item)
    return result


def time_until_refresh() -> int:
    """ثانیه تا refresh بعدی."""
    return max(0, int(_shop_state["next_refresh"] - time.time()))
