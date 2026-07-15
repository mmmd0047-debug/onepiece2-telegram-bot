"""Telegram inline keyboards."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from one_piece_rpg.data import CHARACTERS, ISLANDS, RARITY_EMOJI, SHIPS, STARTER_CHARACTERS


def faction_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏴‍☠️ Pirate", callback_data="faction:pirate")],
        [InlineKeyboardButton("⚓ Marine", callback_data="faction:marine")],
    ])


def starter_keyboard(faction: str) -> InlineKeyboardMarkup:
    buttons = []
    for char_id in STARTER_CHARACTERS[faction]:
        char = CHARACTERS[char_id]
        buttons.append([
            InlineKeyboardButton(
                f"{RARITY_EMOJI[char['rarity']]} {char['name']}",
                callback_data=f"starter:{char_id}",
            )
        ])
    return InlineKeyboardMarkup(buttons)


def main_menu_keyboard() -> InlineKeyboardMarkup:
    """منوی چت شخصی — همه امکانات."""
    import os
    bot_username = os.getenv("BOT_USERNAME", "")
    add_to_group_url = f"https://t.me/{bot_username}?startgroup=true" if bot_username else None
    rows = [
        [
            InlineKeyboardButton("⚔️ مبارزه", callback_data="menu:fight"),
            InlineKeyboardButton("🏋️ تمرین", callback_data="menu:train"),
        ],
        [
            InlineKeyboardButton("👤 پروفایل", callback_data="menu:profile"),
            InlineKeyboardButton("🏪 تاجر", callback_data="menu:shop"),
        ],
        [
            InlineKeyboardButton("🎒 انبار", callback_data="menu:inventory"),
            InlineKeyboardButton("🗺 جزیره", callback_data="menu:island"),
        ],
        [
            InlineKeyboardButton("🎣 ماهیگیری", callback_data="menu:fishing"),
            InlineKeyboardButton("👥 Crew", callback_data="menu:crew"),
        ],
        [
            InlineKeyboardButton("⚔️ آیتم‌های جنگ", callback_data="menu:battle_items"),
            InlineKeyboardButton("🕶 ترید", callback_data="market:browse:0"),
        ],
    ]
    if add_to_group_url:
        rows.append([InlineKeyboardButton("➕ اضافه کردن ربات به گروه", url=add_to_group_url)])
    return InlineKeyboardMarkup(rows)


def group_menu_keyboard(chat_id: int, owner_id: int) -> InlineKeyboardMarkup:
    """منوی گروه — بخش‌های اجتماعی."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚔️ جنگ 1v1", callback_data=f"grp:fight:1v1:{owner_id}"),
            InlineKeyboardButton("⚔️ جنگ 2v2", callback_data=f"grp:fight:2v2:{owner_id}"),
        ],
        [
            InlineKeyboardButton("⚔️ جنگ 3v3", callback_data=f"grp:fight:3v3:{owner_id}"),
            InlineKeyboardButton("🌊 جنگ دریایی", callback_data=f"grp:seafight:{owner_id}"),
        ],
        [
            InlineKeyboardButton("👤 پروفایل من", callback_data=f"grp:profile:{owner_id}"),
            InlineKeyboardButton("📊 رتبه‌بندی", callback_data="grp:top"),
        ],
        [
            InlineKeyboardButton("🎣 ماهیگیری", callback_data=f"grp:fishing:{owner_id}"),
        ],
    ])


def shop_keyboard(player_beli: int) -> InlineKeyboardMarkup:
    from one_piece_rpg.data import ITEMS, RARITY_EMOJI, SHIPS
    buttons = []
    buttons.append([InlineKeyboardButton("⚔️ آیتم‌ها", callback_data="shop:cat:items")])
    buttons.append([InlineKeyboardButton("🎣 قلاب ماهیگیری", callback_data="shop:cat:rods")])
    buttons.append([InlineKeyboardButton("👨‍🍳 آشپز", callback_data="shop:cat:chefs")])
    buttons.append([InlineKeyboardButton("🚢 کشتی‌ها", callback_data="shop:cat:ships")])
    buttons.append([InlineKeyboardButton("🔙 بازگشت", callback_data="menu:main")])
    return InlineKeyboardMarkup(buttons)


def shop_items_keyboard(player_beli: int) -> InlineKeyboardMarkup:
    from one_piece_rpg.services.shop import get_shop_items
    from one_piece_rpg.data import RARITY_EMOJI
    buttons = []
    items = get_shop_items()
    for item in items:
        emoji = RARITY_EMOJI.get(item["rarity"], "⚪")
        atk = f"+{item['atk']}atk " if item.get("atk") else ""
        def_ = f"+{item['def']}def" if item.get("def") else ""
        lock = "🔒" if player_beli < item["price"] else ""
        label = f"{emoji} {item['name']} {atk}{def_}— {item['price']:,} {lock}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"shop:buy_item:{item['id']}")])
    buttons.append([InlineKeyboardButton("🔙 تاجر", callback_data="menu:shop")])
    return InlineKeyboardMarkup(buttons)


def island_keyboard(player_level: int, current: str) -> InlineKeyboardMarkup:
    buttons = []
    for island in ISLANDS:
        locked = player_level < island["min_level"]
        prefix = "🔒" if locked else ("📍" if island["id"] == current else island["emoji"])
        label = f"{prefix} {island['name']}"
        if locked:
            label += f" (Lv.{island['min_level']})"
            cb = f"island:locked:{island['id']}"
        else:
            cb = f"island:travel:{island['id']}"
        buttons.append([InlineKeyboardButton(label, callback_data=cb)])
    buttons.append([InlineKeyboardButton("🔙 بازگشت", callback_data="menu:main")])
    return InlineKeyboardMarkup(buttons)


def ship_keyboard(current_ship: str | None, beli: int) -> InlineKeyboardMarkup:
    buttons = []
    for ship_id, ship in SHIPS.items():
        owned = current_ship == ship_id
        prefix = "✅ " if owned else ""
        affordable = beli >= ship["price"]
        suffix = "" if affordable or owned else " 🔒"
        buttons.append([
            InlineKeyboardButton(
                f"{prefix}{ship['name']} — {ship['price']:,}{suffix}",
                callback_data=f"ship:buy:{ship_id}" if not owned else f"ship:owned:{ship_id}",
            )
        ])
    buttons.append([InlineKeyboardButton("🔙 بازگشت", callback_data="menu:main")])
    return InlineKeyboardMarkup(buttons)


def back_to_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 منوی اصلی", callback_data="menu:main")],
    ])
