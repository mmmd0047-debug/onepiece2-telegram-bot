"""Telegram command and callback handlers."""

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

from telegram import Update
from telegram.ext import ContextTypes

from one_piece_rpg.data import (
    CHARACTERS,
    DEVIL_FRUITS,
    ITEMS,
    RARITY_EMOJI,
    SHIPS,
    STORY_INTRO,
    WORLD_BOSSES,
)
from one_piece_rpg.keyboards import (
    back_to_menu,
    faction_keyboard,
    group_menu_keyboard,
    island_keyboard,
    main_menu_keyboard,
    ship_keyboard,
    shop_keyboard,
    shop_items_keyboard,
    starter_keyboard,
)
from one_piece_rpg.services.battle import fight
from one_piece_rpg.services.inventory import format_inventory
from one_piece_rpg.services.player import (
    buy_character,
    claim_daily,
    claim_train,
    create_player,
    get_character_stats,
    get_island,
    get_owned_characters,
    get_player,
    get_rank,
    get_train_status,
    grant_starter_character,
    start_train,
    sync_energy,
    update_player_info,
)
from one_piece_rpg.services.travel import buy_ship, spin_wheel, travel_to_island


async def dice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """هندل dice message — برای چرخ شانس."""
    user = update.effective_user
    logger.warning(f"dice_handler called by {user.id}, reply={update.message.reply_to_message is not None}, wheel_msg={context.user_data.get('wheel_msg_id')}")
    if not update.message.reply_to_message:
        return
    wheel_msg_id = context.user_data.get("wheel_msg_id")
    wheel_time = context.user_data.get("wheel_time", 0)
    if not wheel_msg_id:
        return
    if update.message.reply_to_message.message_id != wheel_msg_id:
        return

    # چک 60 ثانیه منقضی
    import time
    if time.time() - wheel_time > 60:
        context.user_data.pop("wheel_msg_id", None)
        context.user_data.pop("wheel_time", None)
        await update.message.reply_text("⏰ وقت تموم شد! دوباره از منو چرخ شانس رو بزن.")
        return

    from one_piece_rpg.services.travel import spin_wheel
    from one_piece_rpg.data import WHEEL_COOLDOWN_MINS
    from datetime import datetime, timezone
    from one_piece_rpg.database import _parse_dt
    import asyncio

    p = get_player(user.id)
    last = _parse_dt(p.get("last_wheel"))
    now_dt = datetime.now(timezone.utc)
    if last:
        elapsed_mins = (now_dt - last).total_seconds() / 60
        if elapsed_mins < WHEEL_COOLDOWN_MINS:
            remaining = WHEEL_COOLDOWN_MINS - elapsed_mins
            mins = int(remaining); secs = int((remaining - mins) * 60)
            await update.message.reply_text(f"⏳ {mins}:{secs:02d} دیگه می‌تونی بچرخونی!")
            return

    context.user_data.pop("wheel_msg_id", None)
    context.user_data.pop("wheel_time", None)

    # dice value 1-64 یا 1-6
    dice_value = update.message.dice.value
    await asyncio.sleep(3)  # صبر برای انیمیشن

    reward = spin_wheel(user.id)
    if not reward or reward.get("error"):
        await update.message.reply_text("خطا! دوباره امتحان کن.")
        return

    label = reward["label"]
    if reward["type"] == "beli" and reward.get("amount", 0) < 0:
        txt = f"😱 بدشانس!\n{label}"
    elif reward["type"] == "nothing":
        txt = f"😐 {label}"
    else:
        txt = f"🎉 {label}"

    p2 = sync_energy(get_player(user.id))
    await update.message.reply_text(
        f"🎰 *نتیجه چرخ شانس*\n\n{txt}\n\n💰 Beli: {p2['beli']:,}",
        parse_mode="Markdown"
    )


async def name_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """دریافت اطلاعات بازیکن مرحله به مرحله."""
    user = update.effective_user
    text = (update.message.text or "").strip()

    # چرخ شانس — ریپلای با ایموجی 🎰 (slot machine)
    if update.message.reply_to_message:
        wheel_msg_id = context.user_data.get("wheel_msg_id")
        if wheel_msg_id and update.message.reply_to_message.message_id == wheel_msg_id:
            # بررسی که ایموجی 🎰 فرستاده یا dice
            msg_text = text
            if "🎰" in msg_text or (update.message.sticker is None and not msg_text):
                pass
            elif "🎰" not in msg_text:
                await update.message.reply_text("برای چرخوندن چرخ، ایموجی 🎰 رو ریپلای کن!")
                return

            from one_piece_rpg.services.travel import spin_wheel
            from one_piece_rpg.data import WHEEL_COOLDOWN_MINS
            from datetime import datetime, timezone
            from one_piece_rpg.database import _parse_dt
            p = get_player(user.id)
            last = _parse_dt(p.get("last_wheel"))
            now_dt = datetime.now(timezone.utc)
            if last:
                elapsed_mins = (now_dt - last).total_seconds() / 60
                if elapsed_mins < WHEEL_COOLDOWN_MINS:
                    remaining = WHEEL_COOLDOWN_MINS - elapsed_mins
                    mins = int(remaining); secs = int((remaining - mins) * 60)
                    await update.message.reply_text(f"⏳ {mins}:{secs:02d} دیگه!")
                    return

            # ارسال dice انیمیشن تلگرام
            import asyncio
            dice_msg = await update.message.reply_dice(emoji="🎰")
            dice_value = dice_msg.dice.value  # 1-64
            await asyncio.sleep(3)  # صبر برای انیمیشن

            reward = spin_wheel(user.id)
            if reward and not reward.get("error"):
                label = reward["label"]
                if reward["type"] == "beli" and reward.get("amount", 0) < 0:
                    txt = f"😱 بدشانس! {label}"
                elif reward["type"] == "nothing":
                    txt = f"😐 {label}"
                else:
                    txt = f"🎉 {label}"
                p2 = sync_energy(get_player(user.id))
                await update.message.reply_text(
                    f"🎰 *نتیجه:* {dice_value}/64\n\n{txt}\n\n💰 Beli: {p2['beli']:,}",
                    parse_mode="Markdown"
                )
            context.user_data.pop("wheel_msg_id", None)
            return

    step = context.user_data.get("reg_step")
    market_step = context.user_data.get("market_step")

    # لقب خدمه
    if context.user_data.get("crew_title_step"):
        member_id = context.user_data.pop("crew_title_for", None)
        context.user_data.pop("crew_title_step", None)
        if member_id:
            from one_piece_rpg.services.crew import set_title
            result = set_title(user.id, member_id, text)
            if result["ok"]:
                await update.message.reply_text(f"\u2705 \u0644\u0642\u0628 \u00ab{text}\u00bb \u062b\u0628\u062a \u0634\u062f!")
            else:
                await update.message.reply_text(f"\u274c {result['msg']}")
        return

    # قیمت‌گذاری بلک مارکت
    if market_step == "price":
        if not text.isdigit() or int(text) < 1:
            await update.message.reply_text("یه عدد معتبر بنویس (حداقل ۱):")
            return
        sell_info = context.user_data.pop("market_sell", {})
        context.user_data.pop("market_step", None)
        price = int(text)
        from one_piece_rpg.services.market import list_item, format_item_name
        p = get_player(user.id)
        result = list_item(user.id, p.get("username") or user.first_name,
                           sell_info["item_type"], sell_info["item_id"], price)
        if not result["ok"]:
            await update.message.reply_text(f"❌ {result['msg']}")
        else:
            name = format_item_name(sell_info["item_type"], sell_info["item_id"])
            await update.message.reply_text(f"✅ *{name}* با قیمت {price:,} Beli در بلک مارکت ثبت شد!",
                                            parse_mode="Markdown")
        return

    if not step:
        return

    if step == "name":
        if not text or len(text) > 20:
            await update.message.reply_text("اسم باید بین ۱ تا ۲۰ کاراکتر باشه. دوباره بنویس:")
            return
        context.user_data["reg_name"] = text
        context.user_data["reg_step"] = "age"
        await update.message.reply_text("سنت چنده؟ (عدد بنویس)")
        return

    if step == "age":
        if not text.isdigit() or not (1 <= int(text) <= 120):
            await update.message.reply_text("سن معتبر وارد کن (بین ۱ تا ۱۲۰):")
            return
        context.user_data["reg_age"] = int(text)
        context.user_data["reg_step"] = "race"
        # نمایش نژادها
        from one_piece_rpg.data import RACES
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        buttons = [[InlineKeyboardButton(f"{r['emoji']} {r['name']}", callback_data=f"reg_race:{key}")]
                   for key, r in RACES.items()]
        await update.message.reply_text(
            "نژادت رو انتخاب کن:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    if step == "height":
        from one_piece_rpg.data import RACES
        race_key = context.user_data.get("reg_race", "human")
        race = RACES.get(race_key, RACES["human"])
        h_min, h_max = race["height_cm"]
        if not text.isdigit() or not (1 <= int(text) <= 10000):
            await update.message.reply_text(f"قد معتبر وارد کن ({h_min} تا {h_max} سانت):")
            return
        height = int(text)
        if not (h_min <= height <= h_max):
            note = race.get("note", f"{h_min} تا {h_max} سانت")
            await update.message.reply_text(
                f"برای نژاد *{race['name']}* قد باید {note} باشه!\nدوباره وارد کن:",
                parse_mode="Markdown"
            )
            return
        context.user_data["reg_height"] = height
        context.user_data["reg_step"] = "weight"
        await update.message.reply_text("وزنت چنده؟ (کیلوگرم)")
        return

    if step == "weight":
        if not text.isdigit() or not (20 <= int(text) <= 500):
            await update.message.reply_text("وزن معتبر وارد کن (بین ۲۰ تا ۵۰۰ کیلو):")
            return
        context.user_data["reg_weight"] = int(text)
        context.user_data["reg_step"] = "photo"
        await update.message.reply_text(
            "عالیه! حالا یه عکس از خودت بفرست تا رو پروفایلت بذاریم 📸\n"
            "یا /skip بزن تا بعداً بذاری."
        )
        return


async def _finish_registration(update, context, user, photo_id=None):
    """تکمیل ثبت‌نام و ورود به بازی."""
    faction = context.user_data.pop("pending_faction", None)
    name = context.user_data.pop("reg_name", user.first_name)
    age = context.user_data.pop("reg_age", 0)
    height = context.user_data.pop("reg_height", 0)
    weight = context.user_data.pop("reg_weight", 0)
    race = context.user_data.pop("reg_race", "human")
    update_only = context.user_data.pop("update_only", False)
    context.user_data.pop("reg_step", None)

    if update_only:
        update_player_info(user.id, name=name, age=age, height=height, weight=weight, photo_id=photo_id, race=race)
        player = sync_energy(get_player(user.id))
        await update.message.reply_text(
            f"\u2705 پروفایلت آپدیت شد!\n\n"
            f"اسم: *{name}* | سن: {age} | قد: {height}cm | وزن: {weight}kg",
            parse_mode="Markdown",
        )
    else:
        if not faction:
            await update.message.reply_text("لطفاً دوباره /start بزن.")
            return
        try:
            create_player(user.id, name, faction, age=age, height=height, weight=weight)
        except Exception:
            update_player_info(user.id, name=name, age=age, height=height, weight=weight)
        if photo_id:
            update_player_info(user.id, photo_id=photo_id)
        if race:
            update_player_info(user.id, race=race)
        player = sync_energy(get_player(user.id))
        faction_emoji = "\U0001f3f4\u200d\u2620\ufe0f" if faction == "pirate" else "\u2693"
        from one_piece_rpg.data import RACES
        race_info = RACES.get(race, RACES["human"])
        await update.message.reply_text(
            f"{faction_emoji} *{name}*، سفرت شروع شد!\n\n"
            f"نژاد: {race_info['emoji']} {race_info['name']} | سن: {age}\n"
            f"قد: {height}cm | وزن: {weight}kg\n"
            f"فکشن: *{faction.upper()}*\n\n"
            "از East Blue شروع می‌کنی — دنیا منتظرته.",
            parse_mode="Markdown",
        )

    await update.message.reply_text(
        _main_menu_text(player),
        parse_mode="Markdown",
        reply_markup=main_menu_keyboard(),
    )


async def photo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """دریافت عکس پروفایل."""
    user = update.effective_user
    step = context.user_data.get("reg_step")

    if step == "photo":
        photo = update.message.photo[-1]  # بزرگترین سایز
        photo_id = photo.file_id
        await update.message.reply_text("📸 عکست ثبت شد!")
        await _finish_registration(update, context, user, photo_id=photo_id)
    elif get_player(user.id):
        # آپدیت عکس بدون ثبت‌نام
        photo = update.message.photo[-1]
        update_player_info(user.id, photo_id=photo.file_id)
        await update.message.reply_text("📸 عکس پروفایلت آپدیت شد!")


async def skip_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """رد کردن عکس."""
    user = update.effective_user
    step = context.user_data.get("reg_step")
    if step == "photo":
        await update.message.reply_text("باشه، بعداً می‌تونی عکس بفرستی.")
        await _finish_registration(update, context, user, photo_id=None)


async def invite_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """دعوت به خدمه با /invite @username یا /invite username"""
    user = update.effective_user
    player = get_player(user.id)
    if not player:
        await update.message.reply_text("اول /start بزن.")
        return
    if not player.get("ship_id"):
        await update.message.reply_text("اول باید کشتی داشته باشی!")
        return

    args = context.args
    if not args:
        await update.message.reply_text("استفاده: /invite @username یا /invite username")
        return

    target_username = args[0].lstrip("@").lower()
    # پیدا کردن بازیکن با username
    from one_piece_rpg.database import get_db
    with get_db() as conn:
        row = conn.execute(
            "SELECT user_id, username FROM players WHERE LOWER(username)=?",
            (target_username,)
        ).fetchone()

    if not row:
        await update.message.reply_text(f"بازیکن «{target_username}» پیدا نشد. باید تو بازی باشه.")
        return

    from one_piece_rpg.services.crew import invite_to_crew
    result = invite_to_crew(user.id, row["user_id"])
    if not result["ok"]:
        await update.message.reply_text(f"❌ {result['msg']}")
        return

    from one_piece_rpg.data import SHIPS
    ship = SHIPS[player["ship_id"]]
    await update.message.reply_text(
        f"✅ *{row['username']}* به خدمه کشتی {ship['name']} اضافه شد!\n"
        f"👥 خدمه: {result['current']}/{result['cap']}",
        parse_mode="Markdown"
    )


async def group_trigger_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = update.message.text or ""
    user = update.effective_user
    chat_id = update.effective_chat.id

    # تریگر جنگ PvP — "جنگ 1v1", "جنگ 2v2", "جنگ 3v3"
    pvp_triggers = {"جنگ 1v1": "1v1", "جنگ 2v2": "2v2", "جنگ 3v3": "3v3",
                    "fight 1v1": "1v1", "fight 2v2": "2v2"}
    pvp_mode = None
    for trigger, mode in pvp_triggers.items():
        if trigger.lower() in text.lower():
            pvp_mode = mode
            break

    if pvp_mode:
        player = get_player(user.id)
        if not player:
            await update.message.reply_text("برای شرکت باید /start زده باشی!")
            return
        from one_piece_rpg.services.pvp import create_battle, join_battle, get_fight_cooldown, get_user_active_battle
        cd = get_fight_cooldown(user.id)
        if cd > 0:
            mins = cd // 60; secs = cd % 60
            await update.message.reply_text(f"⏳ {mins}:{secs:02d} دیگه می‌تونی بجنگی!")
            return
        # چک جنگ فعال
        active = get_user_active_battle(user.id)
        if active:
            if active["status"] == "active":
                await update.message.reply_text("⚠️ هنوز تو یه جنگ فعال هستی! اول اون رو تموم کن.")
                return
            elif active["status"] == "waiting":
                import time as _pt
                elapsed = _pt.time() - active["created_at"]
                if elapsed < 60:
                    remaining = int(60 - elapsed)
                    await update.message.reply_text(f"⚠️ جنگ قبلیت هنوز منقضی نشده! {remaining} ثانیه دیگه.")
                    return
        bid = create_battle(chat_id, user.id, pvp_mode)
        join_battle(bid, user.id, 1)
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        team_size = int(pvp_mode[0])
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"🔴 پیوستن به تیم ۱", callback_data=f"pvp:join:{bid}:1")],
            [InlineKeyboardButton(f"🔵 پیوستن به تیم ۲", callback_data=f"pvp:join:{bid}:2")],
            [InlineKeyboardButton(f"🚀 شروع مبارزه!", callback_data=f"pvp:start:{bid}")],
        ])
        msg = await update.message.reply_text(
            f"⚔️ *مبارزه {pvp_mode} شروع شد!*\n\n"
            f"🔴 تیم ۱: {player.get('username','؟')} ({1}/{team_size})\n"
            f"🔵 تیم ۲: — (0/{team_size})\n\n"
            f"⏳ {60} ثانیه برای پیوستن",
            parse_mode="Markdown",
            reply_markup=kb
        )
        # ذخیره message_id برای آپدیت
        context.bot_data[f"pvp_msg_{bid}"] = msg.message_id
        # تایمر انقضا
        import asyncio
        async def expire_battle():
            await asyncio.sleep(60)
            from one_piece_rpg.services.pvp import get_battle_status
            s = get_battle_status(bid)
            if s and s["status"] == "waiting":
                s["status"] = "expired"
                try:
                    await context.bot.edit_message_text(
                        "⏰ مبارزه منقضی شد — کسی نپیوست!",
                        chat_id=chat_id,
                        message_id=msg.message_id
                    )
                except Exception:
                    pass
        asyncio.get_event_loop().create_task(expire_battle())
        return

    # تریگر منوی شخصی — فقط برای کسی که اسمش صدا زده شده
    own_name = user.first_name or ""
    if own_name and own_name.lower() in text.lower():
        player = get_player(user.id)
        if not player:
            try:
                await context.bot.send_message(
                    chat_id=user.id,
                    text="سلام! برای بازی باید /start بزنی و ثبت‌نام کنی 👋"
                )
                await update.message.reply_text(f"{own_name}، پیام خصوصی برات فرستادم!")
            except Exception:
                await update.message.reply_text(f"{own_name}، اول به ربات /start بزن!")
            return
        player = sync_energy(player)
        await update.message.reply_text(
            _main_menu_text(player),
            parse_mode="Markdown",
            reply_markup=group_menu_keyboard(chat_id, user.id),
        )
        return

    # تریگر عمومی وان پیس
    triggers = ["وان پیس", "one piece", "onepiece", "One Piece"]
    if any(t.lower() in text.lower() for t in triggers):
        player = get_player(user.id)
        if not player:
            await update.message.reply_text(
                "🏴\u200d☠️ *ONE PIECE RPG*\n\nبرای شروع بازی به ربات پیام بده و /start بزن!",
                parse_mode="Markdown",
            )
            return
        player = sync_energy(player)
        await update.message.reply_text(
            _main_menu_text(player),
            parse_mode="Markdown",
            reply_markup=group_menu_keyboard(chat_id, user.id),
        )


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat_type = update.effective_chat.type

    # اگه تو گروه /start زده شده
    if chat_type in ("group", "supergroup"):
        await update.message.reply_text(
            "🏴\u200d☠️ *ONE PIECE RPG*\n\n"
            "برای بازی تو گروه:\n"
            "۱. اسمت رو بنویس تا منوت بیاد\n"
            "۲. «وان پیس» بنویس\n"
            "۳. «جنگ 1v1» یا «جنگ 2v2» برای مبارزه\n\n"
            "⚠️ ربات باید *ادمین گروه* باشه تا پیام‌ها رو بخونه!",
            parse_mode="Markdown"
        )
        return
    player = get_player(user.id)

    if player:
        player = sync_energy(player)
        # کاربر قدیمی بدون اطلاعات کامل
        if not player.get("age") or not player.get("race"):
            context.user_data["reg_step"] = "name"
            context.user_data["pending_faction"] = player["faction"]
            context.user_data["update_only"] = True
            await update.message.reply_text(
                "سلام! برای تکمیل پروفایلت اطلاعات زیر رو وارد کن.\n\nاسمت رو بنویس:"
            )
            return
        # کاربر قدیمی بدون عکس
        if not player.get("photo_id"):
            context.user_data["reg_step"] = "photo"
            context.user_data["update_only"] = True
            await update.message.reply_text(
                "سلام! یه عکس از خودت بفرست تا رو پروفایلت بذاریم 📸\n"
                "یا /skip بزن تا بعداً بذاری."
            )
            return
        await _send_main_menu(update, player)
        return

    await update.message.reply_text(
        STORY_INTRO,
        parse_mode="Markdown",
        reply_markup=faction_keyboard(),
    )


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    player = get_player(user.id)
    if not player:
        await update.message.reply_text("ابتدا /start بزن و بازی را شروع کن.")
        return
    player = sync_energy(player)
    await _send_main_menu(update, player)


async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    player = get_player(user.id)
    if not player:
        await update.message.reply_text("ابتدا /start بزن.")
        return
    player = sync_energy(player)
    text = _format_profile(player)
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=back_to_menu())


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    data = query.data
    user = query.from_user

    try:
        await _handle_callback(query, data, user, context)
    except Exception as e:
        logger.error(f"callback error [{data}]: {e}", exc_info=True)
        try:
            await query.answer(f"خطا: {str(e)[:50]}", show_alert=True)
        except Exception:
            pass


_solo_sessions: dict[int, dict] = {}


def _solo_fight_keyboard(user_id: int) -> "InlineKeyboardMarkup":
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    from one_piece_rpg.data import ITEMS, FISH_TYPES
    s = _solo_sessions.get(user_id, {})
    buttons = [
        [InlineKeyboardButton("👊 مشت", callback_data="solo:punch")],
    ]
    # چک شمشیر/تبر در آیتم‌های جنگ
    for iid in s.get("battle_items", []):
        item = ITEMS.get(iid, {})
        if item.get("atk", 0) > 0:
            buttons.append([InlineKeyboardButton(f"⚔️ {item['name']}", callback_data=f"solo:sword:{iid}")])
            break
    # غذا/ماهی
    for iid in s.get("battle_items", []):
        fish = FISH_TYPES.get(iid)
        if fish:
            buttons.append([InlineKeyboardButton(f"🍖 {fish['name']}", callback_data=f"solo:eat_battle:{iid}")])
        from one_piece_rpg.data import FOOD_ITEMS
        food = FOOD_ITEMS.get(iid)
        if food:
            buttons.append([InlineKeyboardButton(f"🍱 {food['name']}", callback_data=f"solo:eat_battle:{iid}")])
    buttons.append([InlineKeyboardButton("🔙 فرار!", callback_data="menu:fight")])
    return InlineKeyboardMarkup(buttons)


def _pvp_turn_keyboard(bid: str, user_id: int) -> "InlineKeyboardMarkup":
    """Keyboard نوبت PvP بر اساس آیتم‌های کاربر."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    from one_piece_rpg.services.pvp import get_battle_status
    from one_piece_rpg.data import ITEMS, FISH_TYPES

    s = get_battle_status(bid)
    buttons = [[InlineKeyboardButton("👊 مشت", callback_data=f"pvp:punch:{bid}")]]

    if s and s.get("players") and user_id in s["players"]:
        p_data = s["players"][user_id]
        items_avail = p_data.get("items_available", {})

        # شمشیر/تبر — با اسم
        weapon_btns = []
        for k, qty in items_avail.items():
            item = ITEMS.get(k, {})
            if item.get("atk", 0) > 0:
                weapon_btns.append(
                    InlineKeyboardButton(f"⚔️ {item.get('name', k)}", callback_data=f"pvp:sword:{bid}")
                )
                break  # فقط اولی

        if weapon_btns:
            buttons.append(weapon_btns)

        # غذا/ماهی — هر کدوم جداگانه
        food_btns = []
        for k, qty in items_avail.items():
            fish = FISH_TYPES.get(k)
            if fish:
                food_btns.append(
                    InlineKeyboardButton(f"🍖 {fish['name']}", callback_data=f"pvp:useitem:{bid}:{k}")
                )
            # غذای معمولی
            from one_piece_rpg.data import FOOD_ITEMS
            food = FOOD_ITEMS.get(k)
            if food:
                food_btns.append(
                    InlineKeyboardButton(f"🍱 {food['name']}", callback_data=f"pvp:useitem:{bid}:{k}")
                )
        if food_btns:
            buttons.extend([[btn] for btn in food_btns[:3]])  # max 3 غذا نشون بده

    return InlineKeyboardMarkup(buttons)


async def _safe_edit(query, text: str, **kwargs) -> None:
    """Edit message text safely — handles photo messages too."""
    try:
        await query.edit_message_text(text, **kwargs)
    except Exception:
        try:
            await query.edit_message_caption(caption=text, **kwargs)
        except Exception:
            pass


async def _handle_callback(query, data: str, user, context) -> None:

    if data.startswith("race:upgrade:"):
        from one_piece_rpg.data import RACE_UPGRADES, RACES
        race_key = data.split(":")[2]
        upgrade = RACE_UPGRADES.get(race_key)
        if not upgrade:
            await query.answer("ارتقا ممکن نیست!", show_alert=True)
            return
        p = get_player(user.id)
        if p.get("race") != race_key:
            await query.answer("نژادت با این ارتقا مطابقت نداره!", show_alert=True)
            return
        if p["beli"] < upgrade["cost"]:
            await query.answer(
                f"Beli کافی نیست! نیاز: {upgrade['cost']:,}",
                show_alert=True
            )
            return
        # انجام ارتقا
        from one_piece_rpg.database import get_db, _now
        with get_db() as conn:
            conn.execute(
                "UPDATE players SET beli=beli-?, race=?, updated_at=? WHERE user_id=?",
                (upgrade["cost"], upgrade["to"], _now(), user.id)
            )
        race_info = RACES.get(race_key, {})
        await _safe_edit(query,
            f"🏔 *ارتقای نژاد موفق!*\n\n"
            f"{race_info.get('emoji','🏔')} غول ← {upgrade['emoji']} *{upgrade['name']}*\n\n"
            f"+{upgrade['atk_bonus']} قدرت حمله\n"
            f"+{upgrade['def_bonus']} قدرت دفاع\n\n"
            f"💰 -{upgrade['cost']:,} Beli",
            parse_mode="Markdown",
            reply_markup=back_to_menu()
        )
        return

    if data.startswith("reg_race:"):
        race_key = data.split(":")[1]
        from one_piece_rpg.data import RACES
        race = RACES.get(race_key)
        if not race:
            await query.answer("نژاد نامعتبر!", show_alert=True)
            return
        await query.answer()
        context.user_data["reg_race"] = race_key
        context.user_data["reg_step"] = "height"
        h_min, h_max = race["height_cm"]
        note = race.get("note", f"{h_min} تا {h_max} سانت")
        await query.edit_message_text(
            f"{race['emoji']} نژاد *{race['name']}* انتخاب شد!\n\nقدت رو بنویس ({note}):",
            parse_mode="Markdown"
        )
        return

    if data.startswith("faction:"):
        faction = data.split(":")[1]
        emoji = "🏴\u200d☠️ Pirate" if faction == "pirate" else "⚓ Marine"
        await _safe_edit(query, 
            f"{emoji} انتخاب شد!\n\n"
            "حالا اسم دزد دریاییت رو بنویس:\n"
            "(فقط یک پیام متنی بفرست)",
        )
        context.user_data["pending_faction"] = faction
        context.user_data["reg_step"] = "name"
        return
    if data.startswith("starter:"):
        char_id = data.split(":")[1]
        faction = context.user_data.get("pending_faction")
        if not faction:
            await _safe_edit(query, "لطفاً دوباره /start بزن.")
            return
        create_player(user.id, user.username, faction)
        grant_starter_character(user.id, char_id)
        player = sync_energy(get_player(user.id))
        char_name = CHARACTERS[char_id]["name"]
        await _safe_edit(query, 
            f"🎉 *{char_name}* به ماجراجویی پیوست!\n\n"
            f"{'🏴‍☠️' if faction == 'pirate' else '⚓'} فکشن: *{faction.upper()}*\n"
            "سفر تو آغاز شد...",
            parse_mode="Markdown",
        )
        await query.message.reply_text(
            _main_menu_text(player),
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard(),
        )
        return

    player = get_player(user.id)
    if not player:
        await _safe_edit(query, "ابتدا /start بزن.")
        return
    player = sync_energy(player)

    if data == "menu:main":
        await _safe_edit(query, _main_menu_text(player),
                         parse_mode="Markdown", reply_markup=main_menu_keyboard())
        return
    if data == "menu:train":
        player = sync_energy(get_player(user.id))
        from one_piece_rpg.services.player import TRAIN_LEVELS
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        buttons = []
        for t in TRAIN_LEVELS:
            status = get_train_status(user.id, t["key"])
            if status["status"] == "in_progress":
                label = f"⏳ {t['name']} — {status['mins']}:{status['secs']:02d} مونده"
            elif status["status"] == "completed":
                label = f"✅ {t['name']} — تموم شد! بگیر"
            else:
                label = f"{'🏃' if t['key']=='light' else '🏋️' if t['key']=='medium' else '💪'} {t['name']} ({t['cooldown_mins']} دقیقه)"
            buttons.append([InlineKeyboardButton(label, callback_data=f"train:{t['key']}")])
        buttons.append([InlineKeyboardButton("🔙 بازگشت", callback_data="menu:main")])
        kb = InlineKeyboardMarkup(buttons)
        await _safe_edit(query, 
            f"🏋️ *تمرین*\n\n⚡ انرژی: {player['energy']}/100\n\nیه تمرین انتخاب کن:",
            parse_mode="Markdown",
            reply_markup=kb
        )
        return

    if data.startswith("train:"):
        level_key = data.split(":")[1]
        status = get_train_status(user.id, level_key)

        if status["status"] == "completed":
            result = claim_train(user.id, level_key)
            player = sync_energy(get_player(user.id))
            lines = [
                "✅ *تمرین با موفقیت تموم شد!*\n",
                f"⭐ +{result['xp']} XP",
                f"💪 +{result['power_gain']} قدرت",
                f"⚡ انرژی: {player['energy']}/100",
            ]
            if result["level_info"].get("player_level_up"):
                lines.append(f"🎉 Level {result['level_info']['new_player_level']} شدی!")
            await _safe_edit(query, "\n".join(lines), parse_mode="Markdown", reply_markup=back_to_menu())
            return

        if status["status"] == "in_progress":
            await query.answer(
                f"⏳ {status['mins']}:{status['secs']:02d} دیگه تموم میشه",
                show_alert=True
            )
            return

        # چک: آیا تمرین دیگه‌ای در جریانه؟
        from one_piece_rpg.services.player import TRAIN_LEVELS
        for t_check in TRAIN_LEVELS:
            if t_check["key"] == level_key:
                continue
            s = get_train_status(user.id, t_check["key"])
            if s["status"] == "in_progress":
                await query.answer(
                    f"⏳ اول تمرین {t_check['name']} رو تموم کن! ({s['mins']}:{s['secs']:02d} مونده)",
                    show_alert=True
                )
                return
            if s["status"] == "completed":
                await query.answer(
                    f"اول نتیجه تمرین {t_check['name']} رو بگیر!",
                    show_alert=True
                )
                return

        result = start_train(user.id, level_key)
        if not result["ok"]:
            await query.answer(result["msg"], show_alert=True)
            return

        t = next(x for x in TRAIN_LEVELS if x["key"] == level_key)
        await _safe_edit(query,
            f"🏋️ *در حال تمرین...*\n\n"
            f"نوع: {t['name']}\n"
            f"⏳ زمان: {t['cooldown_mins']} دقیقه\n\n"
            "وقتی تموم شد برگرد و نتیجه رو بگیر!",
            parse_mode="Markdown",
            reply_markup=back_to_menu()
        )
        return

    if data.startswith("chest:open:"):
        chest_id = data.split(":")[2]
        from one_piece_rpg.data import CHEST_TYPES, ITEMS, RARITY_EMOJI
        from one_piece_rpg.database import get_db
        from one_piece_rpg.database import _now
        import random

        chest_info = CHEST_TYPES.get(chest_id)
        if not chest_info:
            await query.answer("صندوق نامعتبر!", show_alert=True)
            return

        # چک کردن وجود صندوق
        with get_db() as conn:
            row = conn.execute(
                "SELECT id, quantity FROM inventory WHERE user_id=? AND item_type='chest' AND item_id=?",
                (user.id, chest_id)
            ).fetchone()
            if not row or row["quantity"] < 1:
                await query.answer("این صندوق رو نداری!", show_alert=True)
                return
            # کم کردن صندوق
            if row["quantity"] <= 1:
                conn.execute("DELETE FROM inventory WHERE id=?", (row["id"],))
            else:
                conn.execute("UPDATE inventory SET quantity=quantity-1 WHERE id=?", (row["id"],))

        # باز کردن و دادن جوایز
        drops = chest_info["drops"]
        items_by_rarity = {}
        for item_id, item in ITEMS.items():
            items_by_rarity.setdefault(item["rarity"], []).append(item_id)

        rewards = []
        for rarity in drops:
            pool = items_by_rarity.get(rarity, [])
            if pool:
                won_item = random.choice(pool)
                item_info = ITEMS[won_item]
                emoji = RARITY_EMOJI.get(item_info["rarity"], "⚪")
                rewards.append(f"{emoji} {item_info['name']}")
                # اضافه کردن به inventory
                with get_db() as conn:
                    ex = conn.execute(
                        "SELECT id FROM inventory WHERE user_id=? AND item_type='item' AND item_id=?",
                        (user.id, won_item)
                    ).fetchone()
                    if ex:
                        conn.execute("UPDATE inventory SET quantity=quantity+1 WHERE id=?", (ex["id"],))
                    else:
                        conn.execute(
                            "INSERT INTO inventory (user_id,item_type,item_id,quantity) VALUES (?,?,?,1)",
                            (user.id, "item", won_item)
                        )

        lines = [f"{chest_info['emoji']} *{chest_info['name']} باز شد!*\n", "جوایز:"]
        lines.extend([f"• {r}" for r in rewards])
        await _safe_edit(query, "\n".join(lines), parse_mode="Markdown", reply_markup=back_to_menu())
        return

    if data.startswith("fish:"):
        parts = data.split(":")
        action = parts[1]
        fish_id = parts[2]
        from one_piece_rpg.data import FISH_TYPES, COOK_MULTIPLIER
        from one_piece_rpg.database import get_db, _now
        fish_info = FISH_TYPES.get(fish_id)
        if not fish_info:
            await query.answer("ماهی پیدا نشد!", show_alert=True)
            return
        # چک وجود ماهی در انبار
        with get_db() as conn:
            row = conn.execute(
                "SELECT id, quantity FROM inventory WHERE user_id=? AND item_type='fish' AND item_id=?",
                (user.id, fish_id)
            ).fetchone()
        if not row or row["quantity"] < 1:
            await query.answer("این ماهی رو نداری!", show_alert=True)
            return
        # حذف یک ماهی
        with get_db() as conn:
            if row["quantity"] <= 1:
                conn.execute("DELETE FROM inventory WHERE id=?", (row["id"],))
            else:
                conn.execute("UPDATE inventory SET quantity=quantity-1 WHERE id=?", (row["id"],))

        if action == "eat":
            await query.answer(f"🍖 +{fish_info['food']} غذا خوردی!", show_alert=True)
            # TODO: سیستم غذا کامل
            await _safe_edit(query, f"🍖 *{fish_info['name']}* رو خوردی!\n\n+{fish_info['food']} غذا",
                             parse_mode="Markdown", reply_markup=back_to_menu())

        elif action == "sell":
            price = fish_info["sell"]
            with get_db() as conn:
                conn.execute("UPDATE players SET beli=beli+?, updated_at=? WHERE user_id=?",
                             (price, _now(), user.id))
            await _safe_edit(query, f"💰 *{fish_info['name']}* فروختی!\n\n+{price:,} Beli",
                             parse_mode="Markdown", reply_markup=back_to_menu())

        elif action == "cook":
            from one_piece_rpg.data import FISH_COOK_SECS, CHEFS
            from one_piece_rpg.database import get_db as _gdb2, _now as _n2
            from datetime import datetime, timezone, timedelta
            # چک داشتن آشپز
            with _gdb2() as conn:
                chef_row = conn.execute(
                    "SELECT item_id FROM inventory WHERE user_id=? AND item_type='chef' LIMIT 1",
                    (user.id,)
                ).fetchone()
            if not chef_row:
                await _safe_edit(query,
                    "👨‍🍳 آشپز نداری! از تاجر یه آشپز بخر.",
                    reply_markup=back_to_menu())
                return
            chef = CHEFS.get(chef_row["item_id"], CHEFS["novice_chef"])
            cook_secs = int(FISH_COOK_SECS.get(fish_id, 300) / chef["speed"])
            now = datetime.now(timezone.utc)
            done_at = (now + timedelta(seconds=cook_secs)).isoformat()
            # ثبت در صف پخت
            with _gdb2() as conn:
                conn.execute(
                    "INSERT INTO cooking_queue (user_id, fish_id, chef_id, started_at, done_at) VALUES (?,?,?,?,?)",
                    (user.id, fish_id, chef_row["item_id"], now.isoformat(), done_at)
                )
            mins = cook_secs // 60; secs2 = cook_secs % 60
            await _safe_edit(query,
                f"🍳 *{chef['name']}* داره {fish_info['name']} رو آماده می‌کنه!\n\n"
                f"⏳ زمان: {mins}:{secs2:02d}\n"
                f"بعد از پخت از انبار می‌تونی بگیریش.",
                parse_mode="Markdown", reply_markup=back_to_menu())
        return

    if data.startswith("solo:"):
        from one_piece_rpg.services.battle import (
            pick_enemy, _player_atk, _player_def, calc_power,
            _add_inventory, _roll_item, _roll_devil_fruit, get_island_enemies
        )
        from one_piece_rpg.data import (
            CHEST_TYPES, FIGHT_ENERGY_COST, ENEMIES, DEFAULT_ENEMIES, ITEMS as _ITEMS
        )
        from one_piece_rpg.services.pvp import _set_battle_cooldowns
        from one_piece_rpg.services.player import (
            spend_energy, add_beli, add_xp, is_dead, set_death_cooldown, sync_energy as _sync
        )
        import random as _r

        parts = data.split(":")
        s_action = parts[1]
        enemy_id = parts[2] if len(parts) > 2 else ""

        player = _sync(get_player(user.id))

        if s_action == "item_menu":
            from one_piece_rpg.database import get_db as _gdb
            with _gdb() as conn:
                rows = conn.execute(
                    "SELECT item_id, quantity FROM inventory WHERE user_id=? AND item_type IN ('item','fish')",
                    (user.id,)
                ).fetchall()
            from one_piece_rpg.data import FISH_TYPES as _FT
            usable = []
            for row in rows:
                item = _ITEMS.get(row["item_id"]) or _FT.get(row["item_id"])
                if item and "food" in item:
                    usable.append((row["item_id"], item, row["quantity"]))
            if not usable:
                await query.answer("آیتم درمانی نداری!", show_alert=True)
                return
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            btns = [[InlineKeyboardButton(
                f"🍖 {item['name']} x{qty}",
                callback_data=f"solo:eat:{item_id}:{enemy_id}"
            )] for item_id, item, qty in usable]
            btns.append([InlineKeyboardButton("🔙 برگشت", callback_data=f"solo:back:{enemy_id}")])
            await _safe_edit(query, "کدوم آیتم بخوری؟", reply_markup=InlineKeyboardMarkup(btns))
            return

        if s_action == "eat":
            item_id = parts[2]
            enemy_id = parts[3] if len(parts) > 3 else ""
            from one_piece_rpg.database import get_db as _gdb, _now as _n
            from one_piece_rpg.data import FISH_TYPES as _FT
            item = _ITEMS.get(item_id) or _FT.get(item_id)
            if item:
                heal = item.get("food", 20)
                with _gdb() as conn:
                    row = conn.execute(
                        "SELECT id, quantity FROM inventory WHERE user_id=? AND item_id=?",
                        (user.id, item_id)
                    ).fetchone()
                    if row:
                        if row["quantity"] <= 1:
                            conn.execute("DELETE FROM inventory WHERE id=?", (row["id"],))
                        else:
                            conn.execute("UPDATE inventory SET quantity=quantity-1 WHERE id=?", (row["id"],))
                await query.answer(f"🍖 +{heal} جون گرفتی!", show_alert=True)
            # برگرد به انتخاب حمله
            enemies = ENEMIES.get(player["current_island"], DEFAULT_ENEMIES)
            enemy = next((e for e in enemies if e["id"] == enemy_id), enemies[0])
            atk = _player_atk(player)
            defense = _player_def(player)
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            await _safe_edit(query,
                f"⚔️ *{enemy['name']}* منتظرته!\n\nحمله رو انتخاب کن:",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("👊 مشت", callback_data=f"solo:punch:{enemy_id}")],
                    [InlineKeyboardButton("⚔️ شمشیر", callback_data=f"solo:sword:{enemy_id}")],
                    [InlineKeyboardButton("🍖 آیتم", callback_data=f"solo:item_menu:{enemy_id}")],
                ])
            )
            return

        if s_action in ("punch", "sword", "eat_battle", "back"):
            if s_action == "back":
                _solo_sessions.pop(user.id, None)
                await _handle_fight(query, user.id, player)
                return

            sess = _solo_sessions.get(user.id)
            if not sess:
                await _safe_edit(query, "جنگ پیدا نشد! دوباره شروع کن.", reply_markup=back_to_menu())
                return

            enemy = sess["enemy"]
            enemy_hp = sess["enemy_hp"]
            player_hp = sess["player_hp"]

            def hp_bar(hp, max_hp):
                filled = max(0, hp * 10 // max_hp)
                return "█" * filled + "░" * (10 - filled)

            import asyncio as _aio

            if s_action == "eat_battle":
                # خوردن آیتم — هیچ ضربه‌ای نمیزنه ولی جون میگیره
                iid = parts[2] if len(parts) > 2 else ""
                from one_piece_rpg.data import FISH_TYPES as _FT, FOOD_ITEMS as _FI
                item_info = _FT.get(iid) or _FI.get(iid)
                if item_info:
                    heal = _r.randint(item_info.get("food",15), item_info.get("food",15) + 10)
                    player_hp = min(sess["player_max_hp"], player_hp + heal)
                    sess["player_hp"] = player_hp
                    from one_piece_rpg.database import get_db as _gdb4
                    with _gdb4() as conn:
                        itype = "fish" if iid in _FT else "item"
                        row = conn.execute(
                            "SELECT id, quantity FROM inventory WHERE user_id=? AND item_type=? AND item_id=?",
                            (user.id, itype, iid)
                        ).fetchone()
                        if row:
                            if row["quantity"] <= 1:
                                conn.execute("DELETE FROM inventory WHERE id=?", (row["id"],))
                            else:
                                conn.execute("UPDATE inventory SET quantity=quantity-1 WHERE id=?", (row["id"],))
                    # آیتم رو از session هم حذف کن
                    if iid in sess.get("battle_items", []):
                        sess["battle_items"].remove(iid)
                    log = f"🍖 +{heal} جون گرفتی!"
                else:
                    log = ""
                # دشمن هم ضربه میزنه
                enemy_dmg = max(1, enemy["atk"] - sess["player_def"] // 2 + _r.randint(-3, 3))
                player_hp = max(0, player_hp - enemy_dmg)
                sess["player_hp"] = player_hp
                log += f"\n👹 {enemy['name']} {enemy_dmg} ضربه زد!"
            else:
                # محاسبه ضربه
                atk = sess["player_atk"]
                if s_action == "sword":
                    sword_id = parts[2] if len(parts) > 2 else ""
                    if sword_id:
                        extra = _ITEMS.get(sword_id, {}).get("atk", 0)
                        atk = int((atk + extra) * 1.5)
                    else:
                        atk = int(atk * 1.5)

                player_dmg = max(1, atk - enemy.get("def", enemy["atk"] // 3) + _r.randint(-5, 5))
                enemy_hp = max(0, enemy_hp - player_dmg)
                sess["enemy_hp"] = enemy_hp

                # دشمن جواب میده
                if enemy_hp > 0:
                    enemy_dmg = max(1, enemy["atk"] - sess["player_def"] // 2 + _r.randint(-3, 3))
                    player_hp = max(0, player_hp - enemy_dmg)
                    sess["player_hp"] = player_hp
                    log = f"{'⚔️' if s_action == 'sword' else '👊'} {player_dmg} ضربه زدی!\n👹 {enemy['name']} {enemy_dmg} ضربه زد!"
                else:
                    log = f"{'⚔️' if s_action == 'sword' else '👊'} {player_dmg} ضربه زدی! حریف کشته شد!"

            # چک پایان
            if player_hp <= 0:
                _solo_sessions.pop(user.id, None)
                from one_piece_rpg.services.player import is_dead as _id2, set_death_cooldown as _sdc
                if _r.random() < enemy.get("death_chance", 0.03):
                    _sdc(user.id)
                    penalty = max(0, int(player["beli"] * 0.05))
                    if penalty:
                        add_beli(user.id, -penalty)
                    await _safe_edit(query,
                        f"⚔️ *{enemy['name']}* vs تو\n\n{log}\n\n"
                        f"💀 *مُردی!*\n۳۰ دقیقه استراحت...\n💸 -{penalty:,} Beli",
                        parse_mode="Markdown", reply_markup=back_to_menu())
                else:
                    await _safe_edit(query,
                        f"⚔️ *{enemy['name']}* vs تو\n\n{log}\n\n❌ *شکست!*",
                        parse_mode="Markdown", reply_markup=back_to_menu())
                return

            if enemy_hp <= 0:
                _solo_sessions.pop(user.id, None)
                _set_battle_cooldowns([user.id])
                add_beli(user.id, enemy["beli"])
                level_info = add_xp(user.id, None, enemy["xp"])
                item_won = None
                if _r.random() < enemy.get("item_chance", 0.05):
                    item_won = _roll_item()
                    _add_inventory(user.id, "item", item_won)
                lines = [
                    f"⚔️ *{enemy['name']}* vs تو\n\n{log}\n",
                    "🏆 *پیروزی!*\n",
                    f"⭐ +{enemy['xp']} XP | 💰 +{enemy['beli']:,} Beli",
                ]
                if level_info.get("player_level_up"):
                    lines.append(f"🎉 Level {level_info['new_player_level']}!")
                if item_won:
                    lines.append(f"🎁 {_ITEMS.get(item_won,{}).get('name', item_won)}")
                await _safe_edit(query, "\n".join(lines), parse_mode="Markdown", reply_markup=back_to_menu())
                return

            # ادامه جنگ — نمایش HP
            p_bar = hp_bar(player_hp, sess["player_max_hp"])
            e_bar = hp_bar(enemy_hp, sess["enemy_max_hp"])
            status = (
                f"👹 *{enemy['name']}*\n❤️ {enemy_hp}/{sess['enemy_max_hp']} [{e_bar}]\n\n"
                f"👤 *تو*\n❤️ {player_hp}/{sess['player_max_hp']} [{p_bar}]\n\n"
                f"{log}\n\nحمله رو انتخاب کن:"
            )
            await _safe_edit(query, status, parse_mode="Markdown", reply_markup=_solo_fight_keyboard(user.id))
            return
        return

    if data.startswith("grp:"):
        parts = data.split(":")
        grp_action = parts[1]

        # چک owner — فقط کسی که منو رو باز کرده
        if grp_action in ("fight", "seafight", "profile", "fishing"):
            try:
                owner_id = int(parts[-1])
            except (ValueError, IndexError):
                owner_id = None
            if owner_id and user.id != owner_id:
                await query.answer("این منو مال تو نیست! اسمت رو تو گروه بنویس.", show_alert=True)
                return

        if grp_action == "back":
            try:
                owner_id_back = int(parts[2])
            except (ValueError, IndexError):
                owner_id_back = user.id
            if user.id != owner_id_back:
                await query.answer("این منو مال تو نیست!", show_alert=True)
                return
            p2 = get_player(user.id)
            p2 = sync_energy(p2)
            chat_id_back = query.message.chat_id
            await query.answer()
            await query.message.reply_text(
                _main_menu_text(p2),
                parse_mode="Markdown",
                reply_markup=group_menu_keyboard(chat_id_back, user.id)
            )
            return

        if grp_action == "fight":
            mode = parts[2]
            from one_piece_rpg.services.pvp import create_battle, join_battle, get_fight_cooldown, get_user_active_battle
            import time as _time
            cd = get_fight_cooldown(user.id)
            if cd > 0:
                mins = cd // 60; secs = cd % 60
                await query.answer(f"⏳ {mins}:{secs:02d} دیگه می‌تونی بجنگی!", show_alert=True)
                return
            active = get_user_active_battle(user.id)
            if active:
                if active["status"] == "active":
                    await query.answer("⚠️ هنوز تو یه جنگ فعال هستی!", show_alert=True)
                    return
                elif active["status"] == "waiting":
                    elapsed = _time.time() - active["created_at"]
                    if elapsed < 60:
                        await query.answer(f"⚠️ جنگ قبلیت هنوز منقضی نشده!", show_alert=True)
                        return
            chat_id = query.message.chat_id
            bid = create_battle(chat_id, user.id, mode)
            join_battle(bid, user.id, 1)
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            team_size = int(mode[0])
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"🔴 پیوستن به تیم ۱ (1/{team_size})", callback_data=f"pvp:join:{bid}:1")],
                [InlineKeyboardButton(f"🔵 پیوستن به تیم ۲ (0/{team_size})", callback_data=f"pvp:join:{bid}:2")],
                [InlineKeyboardButton("🚀 شروع مبارزه!", callback_data=f"pvp:start:{bid}")],
            ])
            await query.edit_message_text(
                f"⚔️ *مبارزه {mode}!*\n\n"
                f"🔴 تیم ۱: {player.get('username','؟')}\n"
                f"🔵 تیم ۲: —\n\n"
                "⏳ ۶۰ ثانیه برای پیوستن",
                parse_mode="Markdown",
                reply_markup=kb
            )
            import asyncio
            async def expire():
                await asyncio.sleep(60)
                from one_piece_rpg.services.pvp import get_battle_status
                s = get_battle_status(bid)
                if s and s["status"] == "waiting":
                    s["status"] = "expired"
                    try:
                        await query.edit_message_text("⏰ مبارزه منقضی شد!")
                    except Exception:
                        pass
            asyncio.get_event_loop().create_task(expire())
            return

        if grp_action == "profile":
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            p = get_player(user.id)
            txt = _format_profile(p)
            if p.get("photo_id"):
                await query.answer()
                await query.message.reply_photo(photo=p["photo_id"], caption=txt, parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 منو", callback_data=f"grp:back:{owner_id}")]]))
            else:
                await query.answer()
                await query.message.reply_text(txt, parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 منو", callback_data=f"grp:back:{owner_id}")]]))
            return

        if grp_action == "top":
            from one_piece_rpg.database import get_db
            with get_db() as conn:
                rows = conn.execute(
                    "SELECT username, level, xp FROM players ORDER BY xp DESC LIMIT 10"
                ).fetchall()
            medals = ["🥇", "🥈", "🥉"]
            lines = ["📊 *برترین بازیکنان:*\n"]
            for i, row in enumerate(rows):
                m = medals[i] if i < 3 else f"{i+1}."
                lines.append(f"{m} {row['username'] or '؟'} — Level {row['level']}")
            await query.answer()
            await query.message.reply_text("\n".join(lines), parse_mode="Markdown")
            return

        if grp_action == "fishing":
            await query.answer()
            await _handle_fishing(query, user.id, player)
            return

        if grp_action == "seafight":
            await query.answer()
            await _handle_sea_fight(query, user.id, player)
            return
        return

    if data.startswith("pvp:"):
        from one_piece_rpg.services.pvp import (
            join_battle, start_battle, do_attack, get_battle_status,
            is_battle_full, format_battle_state, kick_from_battle
        )
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        parts = data.split(":")
        pvp_action = parts[1]
        bid = parts[2]
        s = get_battle_status(bid)

        if not s:
            await query.answer("مبارزه پیدا نشد!", show_alert=True)
            return

        if pvp_action == "join":
            team = int(parts[3])
            # چک استارت
            if not get_player(user.id):
                try:
                    await context.bot.send_message(
                        chat_id=user.id,
                        text="🏴\u200d☠️ برای شرکت در جنگ باید اول /start بزنی!\n\nبعد از ثبت‌نام برگرد به گروه."
                    )
                except Exception:
                    pass
                await query.answer("ابتدا به ربات /start بزن! پیام خصوصی برات فرستادم.", show_alert=True)
                return
            result = join_battle(bid, user.id, team)
            if not result["ok"]:
                await query.answer(result["msg"], show_alert=True)
                return
            await query.answer(f"✅ به تیم {team} پیوستی!")
            # آپدیت پیام
            team_size = s["team_size"]
            t1_names = [get_player(uid).get("username","؟") for uid in s["team1"] if get_player(uid)]
            t2_names = [get_player(uid).get("username","؟") for uid in s["team2"] if get_player(uid)]
            kb = InlineKeyboardMarkup([
                [InlineKeyboardButton(f"🔴 تیم ۱ ({len(s['team1'])}/{team_size})", callback_data=f"pvp:join:{bid}:1")],
                [InlineKeyboardButton(f"🔵 تیم ۲ ({len(s['team2'])}/{team_size})", callback_data=f"pvp:join:{bid}:2")],
                [InlineKeyboardButton("🚀 شروع!", callback_data=f"pvp:start:{bid}")],
            ])
            t1_str = ", ".join(t1_names) or "—"
            t2_str = ", ".join(t2_names) or "—"
            await _safe_edit(query,
                f"⚔️ *مبارزه {s['mode']}*\n\n"
                f"🔴 تیم ۱: {t1_str}\n"
                f"🔵 تیم ۲: {t2_str}\n\n"
                "وقتی آماده شدید شروع کنید!",
                parse_mode="Markdown",
                reply_markup=kb
            )
            return

        if pvp_action == "start":
            # فقط سازنده می‌تونه شروع کنه
            if user.id != s["team1"][0] if s["team1"] else True:
                await query.answer("فقط سازنده می‌تونه شروع کنه!", show_alert=True)
                return
            result = start_battle(bid)
            if not result["ok"]:
                await query.answer(result["msg"], show_alert=True)
                return
            await query.answer()

            # نمایش عکس‌های پروفایل همه بازیکنان
            all_ids = s["team1"] + s["team2"]
            chat_id = s["chat_id"]
            profile_lines = ["⚔️ *مبارزه شروع شد!*\n"]
            for uid in all_ids:
                p = get_player(uid)
                if p:
                    team_emoji = "🔴" if uid in s["team1"] else "🔵"
                    profile_lines.append(f"{team_emoji} {p.get('username','؟')} — Level {p['level']}")
                    if p.get("photo_id"):
                        try:
                            await context.bot.send_photo(
                                chat_id=chat_id,
                                photo=p["photo_id"],
                                caption=f"{team_emoji} {p.get('username','؟')}"
                            )
                        except Exception:
                            pass

            current = get_player(s["current_turn"])
            battle_txt = format_battle_state(bid)
            turn_kb = _pvp_turn_keyboard(bid, s["current_turn"])
            await _safe_edit(query,
                f"{battle_txt}\n\n👉 نوبت: *{current.get('username','؟') if current else '?'}* ⏳60s",
                parse_mode="Markdown",
                reply_markup=turn_kb
            )

            # تایمر نوبت اول
            import asyncio
            first_turn_id = s.get("turn_id", 1)
            first_turn_uid = s["current_turn"]

            async def first_turn_timeout():
                await asyncio.sleep(60)
                s2 = get_battle_status(bid)
                if (s2 and s2["status"] == "active"
                        and s2.get("turn_id") == first_turn_id
                        and s2["current_turn"] == first_turn_uid):
                    kick_from_battle(bid, s2["current_turn"])
                    try:
                        kicked_p = get_player(first_turn_uid)
                        name = kicked_p.get("username","؟") if kicked_p else "؟"
                        s3 = get_battle_status(bid)
                        bt2 = format_battle_state(bid) if s3 else ""
                        next_uid = s3["current_turn"] if s3 and s3.get("current_turn") else None
                        next2 = get_player(next_uid) if next_uid else None
                        next_name = next2.get("username","؟") if next2 else "؟"
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text=f"⏰ *{name}* وقت نزد — اخراج!\n\n{bt2}\n\n👉 نوبت: *{next_name}* ⏳60s",
                            parse_mode="Markdown"
                        )
                    except Exception:
                        pass
            asyncio.get_event_loop().create_task(first_turn_timeout())
            return

        if pvp_action in ("punch", "sword"):
            if s["status"] != "active":
                await query.answer("مبارزه فعال نیست!", show_alert=True)
                return
            if s["current_turn"] != user.id:
                await query.answer("نوبت تو نیست!", show_alert=True)
                return
            res = do_attack(bid, user.id, pvp_action)
            if not res.get("ok", True) and "msg" in res:
                await query.answer(res["msg"], show_alert=True)
                return

            if res.get("ended"):
                w_names = [get_player(uid).get("username","؟") for uid in res["winner_team"] if get_player(uid)]
                # تشخیص گروه یا خصوصی برای دکمه بازگشت
                try:
                    is_grp = query.message.chat.type in ("group", "supergroup")
                    end_kb = InlineKeyboardMarkup([
                        [InlineKeyboardButton("🔙 منو گروه", callback_data=f"grp:back:{user.id}")]
                    ]) if is_grp else back_to_menu()
                except Exception:
                    end_kb = back_to_menu()
                await _safe_edit(query,
                    f"🏆 *مبارزه تموم شد!*\n\n"
                    f"برنده: {', '.join(w_names)}\n"
                    f"🎁 +{res['xp_reward']} XP | +{res['beli_reward']:,} Beli",
                    parse_mode="Markdown",
                    reply_markup=end_kb
                )
                return

            curr_s = get_battle_status(bid)
            next_p = get_player(curr_s["current_turn"]) if curr_s else None
            bt = format_battle_state(bid)
            last_log = curr_s["log"][-1] if curr_s["log"] else ""
            turn_kb = _pvp_turn_keyboard(bid, curr_s["current_turn"]) if curr_s else back_to_menu()
            await _safe_edit(query,
                f"{bt}\n\n{last_log}\n\n👉 نوبت: *{next_p.get('username','؟') if next_p else '?'}* ⏳60s",
                parse_mode="Markdown",
                reply_markup=turn_kb
            )
            # تایمر نوبت جدید — با turn_id چک می‌کنه
            import asyncio
            current_turn_id = curr_s.get("turn_id", 0)
            current_turn_uid = curr_s["current_turn"]
            chat_id_for_timer = query.message.chat_id

            async def turn_timeout_after_action():
                await asyncio.sleep(60)
                s2 = get_battle_status(bid)
                # فقط اگه همون turn هنوز فعاله
                if (s2 and s2["status"] == "active"
                        and s2.get("turn_id") == current_turn_id
                        and s2["current_turn"] == current_turn_uid):
                    kick_from_battle(bid, s2["current_turn"])
                    try:
                        kicked_p = get_player(current_turn_uid)
                        name = kicked_p.get("username","؟") if kicked_p else "؟"
                        s3 = get_battle_status(bid)
                        bt2 = format_battle_state(bid) if s3 else ""
                        next_uid = s3["current_turn"] if s3 and s3.get("current_turn") else None
                        next2 = get_player(next_uid) if next_uid else None
                        next_name = next2.get("username","؟") if next2 else "؟"
                        await context.bot.send_message(
                            chat_id=chat_id_for_timer,
                            text=f"⏰ *{name}* وقت نزد — اخراج!\n\n{bt2}\n\n👉 نوبت: *{next_name}* ⏳60s",
                            parse_mode="Markdown"
                        )
                    except Exception:
                        pass
            asyncio.get_event_loop().create_task(turn_timeout_after_action())
            return

        if pvp_action == "item_menu":
            if s["current_turn"] != user.id:
                await query.answer("نوبت تو نیست!", show_alert=True)
                return
            p_data = s["players"].get(user.id, {})
            items = p_data.get("items_available", {})
            usable = {k: v for k, v in items.items()
                      if any(f in k for f in ["food", "meat", "fish", "cooked"])}
            if not usable:
                await query.answer("آیتم درمانی نداری!", show_alert=True)
                return
            btns = [[InlineKeyboardButton(f"🍖 {k} x{v}", callback_data=f"pvp:useitem:{bid}:{k}")]
                    for k, v in usable.items()]
            btns.append([InlineKeyboardButton("🔙 لغو", callback_data=f"pvp:punch:{bid}")])
            await _safe_edit(query, "کدوم آیتم استفاده کنی?", reply_markup=InlineKeyboardMarkup(btns))
            return

        if pvp_action == "useitem":
            item_id = parts[3]
            if s["current_turn"] != user.id:
                await query.answer("نوبت تو نیست!", show_alert=True)
                return
            res = do_attack(bid, user.id, "use_item", item_id=item_id)
            if not res.get("ok", True) and "msg" in res:
                await query.answer(res["msg"], show_alert=True)
                return
            curr_s = get_battle_status(bid)
            next_p = get_player(curr_s["current_turn"]) if curr_s else None
            bt = format_battle_state(bid)
            turn_kb = _pvp_turn_keyboard(bid, curr_s["current_turn"]) if curr_s else back_to_menu()
            await _safe_edit(query,
                f"{bt}\n\n{curr_s['log'][-1] if curr_s['log'] else ''}\n\n👉 نوبت: *{next_p.get('username','؟') if next_p else '?'}* ⏳60s",
                parse_mode="Markdown",
                reply_markup=turn_kb
            )
            return
        return

    if data == "menu:battle_items":
        from one_piece_rpg.services.battle import get_inventory
        from one_piece_rpg.data import ITEMS, FISH_TYPES
        from one_piece_rpg.database import get_db, json_load
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        import json

        # آیتم‌های موجود (فقط قابل استفاده در جنگ)
        inv = get_inventory(user.id)
        usable = []
        for item in inv:
            if item["item_type"] == "item":
                it = ITEMS.get(item["item_id"], {})
                usable.append({"id": item["item_id"], "name": it.get("name", item["item_id"]),
                               "type": "weapon" if it.get("atk", 0) > 0 else "armor", "qty": item["quantity"]})
            elif item["item_type"] == "fish":
                fi = FISH_TYPES.get(item["item_id"], {})
                usable.append({"id": item["item_id"], "name": fi.get("name", item["item_id"]),
                               "type": "food", "qty": item["quantity"]})

        # آیتم‌های فعلاً انتخاب شده — فقط اونایی که هنوز تو انبار هستن
        with get_db() as conn:
            row = conn.execute("SELECT battle_items FROM players WHERE user_id=?", (user.id,)).fetchone()
        selected_raw = json_load(row["battle_items"] if row else None, [])
        available_ids = {item["id"] for item in usable}
        # پاک کردن آیتم‌هایی که دیگه نیستن
        selected = [s for s in selected_raw if s in available_ids]
        if len(selected) != len(selected_raw):
            # آپدیت db
            with get_db() as conn:
                conn.execute("UPDATE players SET battle_items=? WHERE user_id=?",
                             (json.dumps(selected), user.id))

        if not usable:
            await _safe_edit(query, "🎒 آیتمی برای انتخاب نداری!\nاز تاجر یا ماهیگیری آیتم بگیر.",
                             reply_markup=back_to_menu())
            return

        lines = [f"⚔️ *آیتم‌های جنگ* (حداکثر ۵)\n\n✅ انتخاب شده: {len(selected)}/5\n"]
        buttons = []
        for item in usable:
            is_sel = item["id"] in selected
            emoji = "✅" if is_sel else "◻️"
            type_emoji = "⚔️" if item["type"] == "weapon" else "🛡" if item["type"] == "armor" else "🍖"
            label = f"{emoji} {type_emoji} {item['name']} x{item['qty']}"
            cb = f"bitems:toggle:{item['id']}"
            buttons.append([InlineKeyboardButton(label, callback_data=cb)])
        buttons.append([InlineKeyboardButton("💾 ذخیره", callback_data="bitems:save"),
                        InlineKeyboardButton("🔙 برگشت", callback_data="menu:main")])
        await _safe_edit(query, "\n".join(lines), parse_mode="Markdown",
                         reply_markup=InlineKeyboardMarkup(buttons))
        return

    if data.startswith("bitems:"):
        from one_piece_rpg.database import get_db, json_load, _now
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        import json
        action = data.split(":")[1]

        with get_db() as conn:
            row = conn.execute("SELECT battle_items FROM players WHERE user_id=?", (user.id,)).fetchone()
        selected = json_load(row["battle_items"] if row else None, [])

        if action == "toggle":
            item_id = data.split(":")[2]
            if item_id in selected:
                selected.remove(item_id)
            elif len(selected) < 5:
                selected.append(item_id)
            else:
                await query.answer("حداکثر ۵ آیتم می‌تونی انتخاب کنی!", show_alert=True)
                return
            with get_db() as conn:
                conn.execute("UPDATE players SET battle_items=?, updated_at=? WHERE user_id=?",
                             (json.dumps(selected), _now(), user.id))
            # refresh منو
            from one_piece_rpg.services.battle import get_inventory
            from one_piece_rpg.data import ITEMS, FISH_TYPES
            inv = get_inventory(user.id)
            usable = []
            for item in inv:
                if item["item_type"] == "item":
                    it = ITEMS.get(item["item_id"], {})
                    usable.append({"id": item["item_id"], "name": it.get("name", item["item_id"]),
                                   "type": "weapon" if it.get("atk", 0) > 0 else "armor", "qty": item["quantity"]})
                elif item["item_type"] == "fish":
                    fi = FISH_TYPES.get(item["item_id"], {})
                    usable.append({"id": item["item_id"], "name": fi.get("name", item["item_id"]),
                                   "type": "food", "qty": item["quantity"]})
            buttons = []
            for item in usable:
                is_sel = item["id"] in selected
                emoji = "✅" if is_sel else "◻️"
                type_emoji = "⚔️" if item["type"] == "weapon" else "🛡" if item["type"] == "armor" else "🍖"
                label = f"{emoji} {type_emoji} {item['name']} x{item['qty']}"
                buttons.append([InlineKeyboardButton(label, callback_data=f"bitems:toggle:{item['id']}")])
            buttons.append([InlineKeyboardButton("💾 ذخیره", callback_data="bitems:save"),
                            InlineKeyboardButton("🔙 برگشت", callback_data="menu:main")])
            await _safe_edit(query, f"⚔️ *آیتم‌های جنگ*\n\n✅ انتخاب شده: {len(selected)}/5",
                             parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))

        elif action == "save":
            await query.answer(f"✅ {len(selected)} آیتم ذخیره شد!", show_alert=True)
        return

    if data == "menu:fight":
        from one_piece_rpg.services.pvp import get_fight_cooldown
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        cd = get_fight_cooldown(user.id)
        if cd > 0:
            m, s2 = divmod(cd // 60, 60)
            mins = cd // 60; secs = cd % 60
            await _safe_edit(query,
                f"⚔️ *مبارزه*\n\n⏳ کولداون: {mins}:{secs:02d} دیگه می‌تونی بجنگی!",
                parse_mode="Markdown", reply_markup=back_to_menu())
            return
        await _safe_edit(query,
            "⚔️ *مبارزه*\n\nنوع مبارزه رو انتخاب کن:",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⚔️ مبارزه جزیره‌ای", callback_data="fight:island")],
                [InlineKeyboardButton("🌊 مبارزه دریایی", callback_data="fight:sea")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="menu:main")],
            ])
        )
        return

    if data == "fight:island":
        await _handle_fight(query, user.id, player)
        return

    if data == "fight:sea":
        await _handle_sea_fight(query, user.id, player)
        return

    if data == "menu:fishing":
        await _handle_fishing(query, user.id, player)
        return

    if data == "menu:shop":
        await _safe_edit(query,
            f"🏪 *فروشگاه*\n💰 Beli: {player['beli']:,}\n\nچی می‌خوای بخری؟",
            parse_mode="Markdown",
            reply_markup=shop_keyboard(player["beli"]),
        )
        return

    if data == "shop:cat:items":
        from one_piece_rpg.services.shop import time_until_refresh
        secs = time_until_refresh()
        h, m = divmod(secs // 60, 60)
        refresh_txt = f"🔄 آیتم‌های جدید: {h}:{m:02d} دیگه" if secs > 0 else "🔄 آیتم‌های جدید آماده‌ست!"
        await _safe_edit(query,
            f"⚔️ *آیتم‌های تاجر*\n💰 Beli: {player['beli']:,}\n{refresh_txt}",
            parse_mode="Markdown",
            reply_markup=shop_items_keyboard(player["beli"]),
        )
        return

    if data == "shop:cat:chefs":
        from one_piece_rpg.data import CHEFS
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        from one_piece_rpg.database import get_db
        with get_db() as conn:
            owned_chef = conn.execute(
                "SELECT item_id FROM inventory WHERE user_id=? AND item_type='chef' LIMIT 1",
                (user.id,)
            ).fetchone()
        buttons = []
        for chef_id, chef in CHEFS.items():
            owned = owned_chef and owned_chef["item_id"] == chef_id
            lock = "✅" if owned else ("🔒" if player["beli"] < chef["price"] else "")
            label = f"{chef['emoji']} {chef['name']} — {chef['price']:,} Beli {lock}"
            buttons.append([InlineKeyboardButton(label, callback_data=f"shop:buy_chef:{chef_id}")])
        buttons.append([InlineKeyboardButton("🔙 تاجر", callback_data="menu:shop")])
        current = f"\n👨‍🍳 آشپز فعلی: {CHEFS[owned_chef['item_id']]['name']}" if owned_chef else ""
        await _safe_edit(query,
            f"👨‍🍳 *آشپزها*\n💰 Beli: {player['beli']:,}{current}",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if data.startswith("shop:buy_chef:"):
        chef_id = data.split(":")[2]
        from one_piece_rpg.data import CHEFS
        from one_piece_rpg.database import get_db, _now
        chef = CHEFS.get(chef_id)
        if not chef:
            await query.answer("آشپز پیدا نشد!", show_alert=True)
            return
        if player["beli"] < chef["price"]:
            await query.answer(f"Beli کافی نیست! نیاز: {chef['price']:,}", show_alert=True)
            return
        with get_db() as conn:
            conn.execute("UPDATE players SET beli=beli-?, updated_at=? WHERE user_id=?",
                         (chef["price"], _now(), user.id))
            conn.execute("DELETE FROM inventory WHERE user_id=? AND item_type='chef'", (user.id,))
            conn.execute("INSERT INTO inventory (user_id,item_type,item_id,quantity) VALUES (?,?,?,1)",
                         (user.id, "chef", chef_id))
        await query.answer(f"✅ {chef['name']} استخدام شد!")
        player = get_player(user.id)
        await _safe_edit(query,
            f"👨‍🍳 *{chef['name']}* استخدام شد!\n\nسرعت پخت: x{chef['speed']}\nکیفیت: x{chef['quality']}",
            parse_mode="Markdown", reply_markup=back_to_menu())
        return

    if data == "shop:cat:rods":
        from one_piece_rpg.data import FISHING_RODS
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        from one_piece_rpg.database import get_db
        with get_db() as conn:
            owned_rod = conn.execute(
                "SELECT item_id FROM inventory WHERE user_id=? AND item_type='rod' LIMIT 1",
                (user.id,)
            ).fetchone()
        buttons = []
        for rod_id, rod in FISHING_RODS.items():
            owned = owned_rod and owned_rod["item_id"] == rod_id
            lock = "✅" if owned else ("🔒" if player["beli"] < rod["price"] else "")
            label = f"{rod['emoji']} {rod['name']} — {rod['price']:,} Beli {lock}"
            buttons.append([InlineKeyboardButton(label, callback_data=f"shop:buy_rod:{rod_id}")])
        buttons.append([InlineKeyboardButton("🔙 تاجر", callback_data="menu:shop")])
        await _safe_edit(query, f"🎣 *قلاب‌های ماهیگیری*\n💰 Beli: {player['beli']:,}",
                         parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if data.startswith("shop:buy_rod:"):
        rod_id = data.split(":")[2]
        from one_piece_rpg.data import FISHING_RODS
        from one_piece_rpg.database import get_db, _now
        rod = FISHING_RODS.get(rod_id)
        if not rod:
            await query.answer("قلاب پیدا نشد!", show_alert=True)
            return
        if player["beli"] < rod["price"]:
            await query.answer(f"Beli کافی نیست! نیاز: {rod['price']:,}", show_alert=True)
            return
        with get_db() as conn:
            conn.execute("UPDATE players SET beli=beli-?, updated_at=? WHERE user_id=?",
                         (rod["price"], _now(), user.id))
            # فقط یه قلاب داریم — جایگزین کن
            conn.execute("DELETE FROM inventory WHERE user_id=? AND item_type='rod'", (user.id,))
            conn.execute("INSERT INTO inventory (user_id,item_type,item_id,quantity) VALUES (?,?,?,1)",
                         (user.id, "rod", rod_id))
        await query.answer(f"✅ {rod['name']} خریده شد!")
        player = get_player(user.id)
        await _safe_edit(query, f"🎣 *قلاب‌های ماهیگیری*\n💰 Beli: {player['beli']:,}",
                         parse_mode="Markdown",
                         reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 تاجر", callback_data="menu:shop")]]))
        return

    if data == "shop:cat:ships":
        ship_name = SHIPS[player["ship_id"]]["name"] if player.get("ship_id") else "نداری"
        await _safe_edit(query,
            f"🚢 *کشتی‌ها*\nکشتی فعلی: {ship_name}\n💰 Beli: {player['beli']:,}",
            parse_mode="Markdown",
            reply_markup=ship_keyboard(player.get("ship_id"), player["beli"]),
        )
        return

    if data.startswith("shop:buy_item:"):
        item_id = data.split(":")[2]
        from one_piece_rpg.data import ITEMS
        from one_piece_rpg.services.shop import get_shop_items
        from one_piece_rpg.database import get_db, _now
        # چک که آیتم الان تو shop باشه
        shop_items = {i["id"]: i for i in get_shop_items()}
        if item_id not in shop_items:
            await query.answer("این آیتم دیگه تو تاجر نیست!", show_alert=True)
            return
        item = shop_items[item_id]
        price = item["price"]
        if player["beli"] < price:
            await query.answer(f"Beli کافی نیست! نیاز: {price:,}", show_alert=True)
            return
        with get_db() as conn:
            conn.execute("UPDATE players SET beli=beli-?, updated_at=? WHERE user_id=?",
                         (price, _now(), user.id))
            ex = conn.execute("SELECT id FROM inventory WHERE user_id=? AND item_type='item' AND item_id=?",
                              (user.id, item_id)).fetchone()
            if ex:
                conn.execute("UPDATE inventory SET quantity=quantity+1 WHERE id=?", (ex["id"],))
            else:
                conn.execute("INSERT INTO inventory (user_id,item_type,item_id,quantity) VALUES (?,?,?,1)",
                             (user.id, "item", item_id))
        await query.answer(f"✅ {item['name']} خریده شد!")
        player = get_player(user.id)
        from one_piece_rpg.services.shop import time_until_refresh
        secs = time_until_refresh()
        h, m = divmod(secs // 60, 60)
        await _safe_edit(query,
            f"⚔️ *آیتم‌های تاجر*\n💰 Beli: {player['beli']:,}\n🔄 آیتم‌های جدید: {h}:{m:02d} دیگه",
            parse_mode="Markdown",
            reply_markup=shop_items_keyboard(player["beli"]),
        )
        return

    if data.startswith("shop:buy:"):
        # قدیمی - شخصیت (دیگه استفاده نمیشه)
        await query.answer("فروشگاه شخصیت حذف شده.", show_alert=True)
        return

    if data == "menu:profile":
        p = get_player(user.id)
        text_profile = _format_profile(player)
        from one_piece_rpg.data import RACE_UPGRADES, RACES
        race = p.get("race", "human")
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        buttons = []
        # دکمه ارتقای نژاد فقط برای غول
        if race in RACE_UPGRADES:
            upgrade = RACE_UPGRADES[race]
            buttons.append([InlineKeyboardButton(
                f"⬆️ ارتقای نژاد → {upgrade['name']} ({upgrade['cost']:,} Beli)",
                callback_data=f"race:upgrade:{race}"
            )])
        buttons.append([InlineKeyboardButton("🔙 منوی اصلی", callback_data="menu:main")])
        kb = InlineKeyboardMarkup(buttons)
        if p.get("photo_id"):
            await query.answer()
            await query.message.reply_photo(
                photo=p["photo_id"],
                caption=text_profile,
                parse_mode="Markdown",
            )
        else:
            await _safe_edit(query, text_profile, parse_mode="Markdown", reply_markup=kb)
        return

    if data == "menu:inventory":
        from one_piece_rpg.services.battle import get_inventory
        from one_piece_rpg.data import CHEST_TYPES, FISH_TYPES, ITEMS, CHEFS
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        items = get_inventory(user.id)
        # فیلتر آیتم‌های سیستمی
        visible = [i for i in items if i["item_type"] not in ("train_cd", "fish_cd")]
        if not visible:
            await _safe_edit(query, "🎒 *انبار خالیه!*", parse_mode="Markdown", reply_markup=back_to_menu())
            return
        buttons = []
        for item in visible:
            itype = item["item_type"]
            iid = item["item_id"]
            qty = item["quantity"]
            if itype == "fish":
                fi = FISH_TYPES.get(iid, {})
                label = f"{fi.get('emoji','🐟')} {fi.get('name', iid)} x{qty}"
            elif itype == "item":
                it = ITEMS.get(iid, {})
                label = f"⚔️ {it.get('name', iid)} x{qty}"
            elif itype == "chest":
                ct = CHEST_TYPES.get(iid, {})
                label = f"{ct.get('emoji','📦')} {ct.get('name', iid)} x{qty}"
            elif itype == "chef":
                ch = CHEFS.get(iid, {})
                label = f"{ch.get('emoji','👨‍🍳')} {ch.get('name', iid)}"
            elif itype == "rod":
                from one_piece_rpg.data import FISHING_RODS
                r = FISHING_RODS.get(iid, {})
                label = f"🎣 {r.get('name', iid)}"
            else:
                label = f"• {iid} x{qty}"
            buttons.append([InlineKeyboardButton(label, callback_data=f"inv:item:{itype}:{iid}")])
        buttons.append([InlineKeyboardButton("🔙 منوی اصلی", callback_data="menu:main")])
        await _safe_edit(query, "🎒 *انبار:*\nروی هر آیتم بزن تا گزینه‌هاش بیاد:",
                         parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if data.startswith("inv:item:"):
        parts = data.split(":")
        itype = parts[2]
        iid = parts[3]
        from one_piece_rpg.data import CHEST_TYPES, FISH_TYPES, ITEMS, CHEFS
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        buttons = []
        if itype == "fish":
            fi = FISH_TYPES.get(iid, {})
            name = fi.get("name", iid)
            txt = (f"{fi.get('emoji','🐟')} *{name}*\n\n"
                   f"🍖 ارزش غذایی: {fi.get('food',0)}\n"
                   f"💰 فروش خام: {fi.get('sell',0):,} Beli\n"
                   f"🍳 فروش پخته: {fi.get('sell',0)*3:,} Beli")
            buttons = [
                [InlineKeyboardButton(f"🍖 بخور", callback_data=f"fish:eat:{iid}")],
                [InlineKeyboardButton(f"💰 بفروش ({fi.get('sell',0):,})", callback_data=f"fish:sell:{iid}")],
                [InlineKeyboardButton(f"🍳 بده به آشپز", callback_data=f"fish:cook:{iid}")],
            ]
        elif itype == "item":
            it = ITEMS.get(iid, {})
            name = it.get("name", iid)
            txt = (f"⚔️ *{name}*\n\n"
                   f"⚔️ ATK: +{it.get('atk',0)}\n"
                   f"🛡 DEF: +{it.get('def',0)}\n"
                   f"💰 فروش: {it.get('sell_price',0):,} Beli")
            buttons = [[InlineKeyboardButton("💰 بفروش", callback_data=f"inv:sell_item:{iid}")]]
        elif itype == "chest":
            ct = CHEST_TYPES.get(iid, {})
            name = ct.get("name", iid)
            txt = f"📦 *{name}*\n\nمحتوا: {', '.join(ct.get('drops',[]))}"
            buttons = [[InlineKeyboardButton("🔓 باز کن", callback_data=f"chest:open:{iid}")]]
        elif itype == "chef":
            ch = CHEFS.get(iid, {})
            name = ch.get("name", iid)
            txt = (f"{ch.get('emoji','👨‍🍳')} *{name}*\n\n"
                   f"⚡ سرعت پخت: x{ch.get('speed',1)}\n"
                   f"✨ کیفیت: x{ch.get('quality',1)}\n\n"
                   "برای پختن ماهی روی ماهی‌ات بزن و آشپز رو انتخاب کن.")
        elif itype == "rod":
            from one_piece_rpg.data import FISHING_RODS
            r = FISHING_RODS.get(iid, {})
            name = r.get("name", iid)
            txt = (f"🎣 *{name}*\n\n"
                   f"🌟 شانس ماهی کمیاب: +{r.get('rare_bonus',0)}%\n"
                   f"⚡ سرعت: +{r.get('speed_bonus',0)}%")
        else:
            txt = f"• {iid}"

        buttons.append([InlineKeyboardButton("🔙 انبار", callback_data="menu:inventory")])
        await _safe_edit(query, txt if txt else f"*{iid}*",
                         parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))
        return

    if data.startswith("inv:sell_item:"):
        iid = data.split(":")[2]
        from one_piece_rpg.data import ITEMS
        from one_piece_rpg.database import get_db, _now
        item = ITEMS.get(iid)
        if not item:
            await query.answer("آیتم پیدا نشد!", show_alert=True)
            return
        price = item.get("sell_price", 0)
        with get_db() as conn:
            row = conn.execute("SELECT id, quantity FROM inventory WHERE user_id=? AND item_type='item' AND item_id=?",
                               (user.id, iid)).fetchone()
            if not row:
                await query.answer("این آیتم رو نداری!", show_alert=True)
                return
            if row["quantity"] <= 1:
                conn.execute("DELETE FROM inventory WHERE id=?", (row["id"],))
            else:
                conn.execute("UPDATE inventory SET quantity=quantity-1 WHERE id=?", (row["id"],))
            conn.execute("UPDATE players SET beli=beli+?, updated_at=? WHERE user_id=?",
                         (price, _now(), user.id))
        await query.answer(f"✅ {item['name']} فروخته شد! +{price:,} Beli", show_alert=True)
        return

    if data == "menu:island":
        await _safe_edit(query, 
            f"🗺 *جزایر Grand Line*\n📍 فعلی: {get_island(player)['name']}",
            parse_mode="Markdown",
            reply_markup=island_keyboard(player["level"], player["current_island"]),
        )
        return

    if data.startswith("island:travel:"):
        island_id = data.split(":")[2]
        result = travel_to_island(user.id, island_id)
        if not result["ok"]:
            await query.answer(result["message"], show_alert=True)
            return
        events_text = ""
        if result["events"]:
            events_text = "\n\n*رویدادهای سفر:*\n" + "\n".join(e["name"] for e in result["events"])
        await _safe_edit(query, 
            f"⛵ به *{result['island']['name']}* رسیدی!{events_text}",
            parse_mode="Markdown",
            reply_markup=back_to_menu(),
        )
        return

    if data.startswith("island:locked:"):
        await query.answer("هنوز Level کافی نداری!", show_alert=True)
        return

    if data == "menu:ship":
        ship_name = SHIPS[player["ship_id"]]["name"] if player.get("ship_id") else "نداری"
        await _safe_edit(query, 
            f"🚢 *کشتی‌ها*\nکشتی فعلی: {ship_name}\n💰 Beli: {player['beli']:,}",
            parse_mode="Markdown",
            reply_markup=ship_keyboard(player.get("ship_id"), player["beli"]),
        )
        return

    if data.startswith("ship:buy:"):
        ship_id = data.split(":")[2]
        err = buy_ship(user.id, ship_id)
        if err:
            await query.answer(err, show_alert=True)
            return
        ship = SHIPS[ship_id]
        await query.answer(f"✅ {ship['name']} خریده شد!")
        player = get_player(user.id)
        await _safe_edit(query, 
            f"🚢 *{ship['name']}* اکنون کشتی توست!",
            parse_mode="Markdown",
            reply_markup=back_to_menu(),
        )
        return

    if data == "menu:daily":
        from datetime import datetime, timedelta, timezone
        from one_piece_rpg.database import _parse_dt
        p = get_player(user.id)
        last = _parse_dt(p.get("last_daily"))
        now_dt = datetime.now(timezone.utc)
        if last and (now_dt - last).total_seconds() < 86400:
            remaining = 86400 - (now_dt - last).total_seconds()
            h = int(remaining // 3600)
            m = int((remaining % 3600) // 60)
            await _safe_edit(query, 
                f"🎁 *جایزه روزانه*\n\n⏳ {h} ساعت و {m} دقیقه دیگه جایزه داری!",
                parse_mode="Markdown",
                reply_markup=back_to_menu(),
            )
            return
        reward = claim_daily(user.id)
        if not reward:
            await query.answer("خطا!", show_alert=True)
            return
        await _safe_edit(query, 
            f"🎁 *جایزه روزانه!*\n\n"
            f"💰 +{reward['beli']:,} Beli\n"
            f"🔥 Streak: {reward['streak']} روز",
            parse_mode="Markdown",
            reply_markup=back_to_menu(),
        )
        return

    if data == "menu:wheel":
        from datetime import datetime, timezone
        from one_piece_rpg.database import _parse_dt
        from one_piece_rpg.data import WHEEL_COOLDOWN_MINS
        p = get_player(user.id)
        last = _parse_dt(p.get("last_wheel"))
        now_dt = datetime.now(timezone.utc)
        if last:
            elapsed_mins = (now_dt - last).total_seconds() / 60
            remaining = WHEEL_COOLDOWN_MINS - elapsed_mins
            if remaining > 0:
                mins = int(remaining)
                secs = int((remaining - mins) * 60)
                await _safe_edit(query,
                    f"🎰 *چرخ شانس*\n\n⏳ {mins}:{secs:02d} دیگه می‌تونی بچرخونی!\n\n"
                    "وقتی آماده شد، رو این پیام ریپلای کن و 🎰 بفرست!",
                    parse_mode="Markdown",
                    reply_markup=back_to_menu(),
                )
                return
        import time
        context.user_data["wheel_msg_id"] = query.message.message_id
        context.user_data["wheel_time"] = time.time()
        await _safe_edit(query,
            "🎰 *چرخ شانس آماده‌ست!*\n\n"
            "رو این پیام ریپلای کن و ایموجی 🎰 بفرست!\n\n"
            "_هرچی بالاتر بیاد جایزه بهتر، هرچی پایین‌تر ممکنه سکه کم بشه!_",
            parse_mode="Markdown",
            reply_markup=back_to_menu(),
        )
        return

    if data.startswith("market:"):
        from one_piece_rpg.services.market import (
            get_listings, get_listing_count, buy_listing,
            cancel_listing, list_item, format_item_name
        )
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup

        parts = data.split(":")
        action = parts[1]

        if action == "browse":
            page = int(parts[2]) if len(parts) > 2 else 0
            listings = get_listings(page=page)
            total = get_listing_count()
            lines = [f"🕶 *بلک مارکت* ({total} آگهی)\n"]
            buttons = []
            if not listings:
                lines.append("هیچ آیتمی برای فروش نیست.")
            for L in listings:
                name = format_item_name(L["item_type"], L["item_id"])
                lines.append(f"• {name} — {L['price']:,} Beli ({L['seller_name']})")
                buttons.append([InlineKeyboardButton(
                    f"🛒 بخر: {name[:20]} — {L['price']:,}",
                    callback_data=f"market:buy:{L['id']}"
                )])
            nav = []
            if page > 0:
                nav.append(InlineKeyboardButton("◀️", callback_data=f"market:browse:{page-1}"))
            if (page + 1) * 8 < total:
                nav.append(InlineKeyboardButton("▶️", callback_data=f"market:browse:{page+1}"))
            if nav:
                buttons.append(nav)
            buttons.append([InlineKeyboardButton("➕ آیتم بفروش", callback_data="market:sell_menu")])
            buttons.append([InlineKeyboardButton("📋 آگهی‌های من", callback_data="market:mylist")])
            buttons.append([InlineKeyboardButton("🔙 منو", callback_data="menu:main")])
            await _safe_edit(query, "\n".join(lines), parse_mode="Markdown",
                                          reply_markup=InlineKeyboardMarkup(buttons))
            return

        if action == "buy":
            lid = int(parts[2])
            result = buy_listing(user.id, lid)
            if not result["ok"]:
                await query.answer(result["msg"], show_alert=True)
                return
            name = format_item_name(result["item_type"], result["item_id"])
            await query.answer(f"✅ {name} خریدی!", show_alert=True)
            # برگرد به لیست
            listings = get_listings()
            total = get_listing_count()
            lines = [f"🕶 *بلک مارکت* ({total} آگهی)\n"]
            buttons = []
            for L in listings:
                n = format_item_name(L["item_type"], L["item_id"])
                lines.append(f"• {n} — {L['price']:,} Beli ({L['seller_name']})")
                buttons.append([InlineKeyboardButton(f"🛒 {n[:20]} — {L['price']:,}", callback_data=f"market:buy:{L['id']}")])
            buttons.append([InlineKeyboardButton("➕ آیتم بفروش", callback_data="market:sell_menu")])
            buttons.append([InlineKeyboardButton("🔙 منو", callback_data="menu:main")])
            await _safe_edit(query, "\n".join(lines), parse_mode="Markdown",
                                          reply_markup=InlineKeyboardMarkup(buttons))
            return

        if action == "sell_menu":
            from one_piece_rpg.services.battle import get_inventory
            items = [i for i in get_inventory(user.id) if i["item_type"] != "train_cd"]
            if not items:
                await query.answer("انبارت خالیه!", show_alert=True)
                return
            buttons = []
            for i in items:
                name = format_item_name(i["item_type"], i["item_id"])
                buttons.append([InlineKeyboardButton(
                    f"{name} x{i['quantity']}",
                    callback_data=f"market:set_price:{i['item_type']}:{i['item_id']}"
                )])
            buttons.append([InlineKeyboardButton("🔙 بلک مارکت", callback_data="market:browse:0")])
            await _safe_edit(query, "کدوم آیتم رو می‌خوای بفروشی?",
                                          reply_markup=InlineKeyboardMarkup(buttons))
            return

        if action == "set_price":
            item_type = parts[2]
            item_id = parts[3]
            name = format_item_name(item_type, item_id)
            context.user_data["market_sell"] = {"item_type": item_type, "item_id": item_id}
            context.user_data["market_step"] = "price"
            await _safe_edit(query, 
                f"قیمت *{name}* رو بنویس (Beli):",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 لغو", callback_data="market:browse:0")]])
            )
            return

        if action == "mylist":
            with get_db() as conn:
                my = conn.execute("SELECT * FROM black_market WHERE seller_id=?", (user.id,)).fetchall()
            if not my:
                await query.answer("آگهی فعالی نداری!", show_alert=True)
                return
            buttons = []
            lines = ["📋 *آگهی‌های من:*\n"]
            for L in my:
                n = format_item_name(L["item_type"], L["item_id"])
                lines.append(f"• {n} — {L['price']:,} Beli")
                buttons.append([InlineKeyboardButton(f"❌ لغو: {n[:20]}", callback_data=f"market:cancel:{L['id']}")])
            buttons.append([InlineKeyboardButton("🔙 بلک مارکت", callback_data="market:browse:0")])
            await _safe_edit(query, "\n".join(lines), parse_mode="Markdown",
                                          reply_markup=InlineKeyboardMarkup(buttons))
            return

        if action == "cancel":
            lid = int(parts[2])
            result = cancel_listing(user.id, lid)
            if not result["ok"]:
                await query.answer(result["msg"], show_alert=True)
            else:
                await query.answer("✅ آگهی لغو شد!", show_alert=True)
            return

    if data == "menu:crew":
        from one_piece_rpg.services.crew import get_crew, get_crew_cap, get_captain
        p = get_player(user.id)
        ship_id = p.get("ship_id")

        # ببین کاپیتان کشتیه یا خدمه
        captain_info = get_captain(user.id)
        crew_list = get_crew(user.id)

        lines = ["👥 *خدمه کشتی*\n"]
        if ship_id:
            ship = SHIPS[ship_id]
            cap = get_crew_cap(ship_id)
            lines.append(f"🚢 کشتی: {ship['name']}\n👥 خدمه: {len(crew_list)}/{cap}\n")
            if crew_list:
                for m in crew_list:
                    title = f" [{m['title']}]" if m.get("title") else ""
                    lines.append(f"• {m['name'] or m['member_id']}{title}")
            else:
                lines.append("هنوز خدمه‌ای نداری.")
        elif captain_info:
            lines.append(f"تو خدمه کشتی *{captain_info['name']}* هستی!")
        else:
            lines.append("نه کشتی داری نه توی خدمه‌ای!")

        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        buttons = []
        if ship_id and crew_list:
            buttons.append([InlineKeyboardButton("🏷 لقب بزار", callback_data="crew:title_menu")])
            buttons.append([InlineKeyboardButton("🚫 اخراج", callback_data="crew:kick_menu")])
        if captain_info:
            buttons.append([InlineKeyboardButton("🚪 ترک خدمه", callback_data="crew:leave")])
        buttons.append([InlineKeyboardButton("🔙 منو", callback_data="menu:main")])
        await _safe_edit(query, "\n".join(lines), parse_mode="Markdown",
                         reply_markup=InlineKeyboardMarkup(buttons))
        return

    if data.startswith("crew:"):
        from one_piece_rpg.services.crew import get_crew, invite_to_crew, set_title, kick_from_crew, leave_crew, get_captain
        parts = data.split(":")
        action = parts[1]

        if action == "leave":
            leave_crew(user.id)
            await query.answer("از خدمه خارج شدی!", show_alert=True)
            return

        if action == "kick_menu":
            crew = get_crew(user.id)
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            buttons = [[InlineKeyboardButton(
                f"❌ {m['name'] or m['member_id']}",
                callback_data=f"crew:kick:{m['member_id']}"
            )] for m in crew]
            buttons.append([InlineKeyboardButton("🔙", callback_data="menu:crew")])
            await _safe_edit(query, "کی رو اخراج کنی؟", reply_markup=InlineKeyboardMarkup(buttons))
            return

        if action == "kick" and len(parts) > 2:
            kick_from_crew(user.id, int(parts[2]))
            await query.answer("اخراج شد!", show_alert=True)
            return

        if action == "title_menu":
            crew = get_crew(user.id)
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            buttons = [[InlineKeyboardButton(
                f"🏷 {m['name'] or m['member_id']}",
                callback_data=f"crew:set_title:{m['member_id']}"
            )] for m in crew]
            buttons.append([InlineKeyboardButton("🔙", callback_data="menu:crew")])
            await _safe_edit(query, "لقب برای کی؟", reply_markup=InlineKeyboardMarkup(buttons))
            return

        if action == "set_title" and len(parts) > 2:
            context.user_data["crew_title_for"] = int(parts[2])
            context.user_data["crew_title_step"] = True
            await _safe_edit(query, "لقب رو بنویس (حداکثر ۲۰ کاراکتر):",
                             reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 لغو", callback_data="menu:crew")]]))
            return
        return

    if data == "menu:boss":
        bosses = "\n".join(f"• {b['name']} — HP: {b['hp']:,}" for b in WORLD_BOSSES.values())
        await _safe_edit(query, 
            f"🌍 *World Boss*\n\nهر ۱۲ ساعت یک Boss ظاهر می‌شود.\n\n{bosses}\n\n"
            "⏳ سیستم World Boss به زودی فعال می‌شود.",
            parse_mode="Markdown",
            reply_markup=back_to_menu(),
        )
        return


async def _handle_sea_fight(query, user_id: int, player: dict) -> None:
    import asyncio, random as _random
    from one_piece_rpg.services.battle import sea_fight
    result = sea_fight(user_id)
    if not result["ok"]:
        await _safe_edit(query, result["message"], reply_markup=back_to_menu())
        return

    ship = result["ship"]
    enemy = result["enemy"]
    await _safe_edit(query, f"🌊 *{ship['name']}* در حال مبارزه با *{enemy['emoji']} {enemy['name']}*...", parse_mode="Markdown")
    await asyncio.sleep(1)

    if result["won"]:
        lines = [
            f"🌊 *{ship['name']}* vs *{enemy['emoji']} {enemy['name']}*\n",
            "🏆 *پیروزی دریایی!*\n",
            f"⭐ +{result['xp']} XP",
            f"💰 +{result['beli']:,} Beli",
        ]
    else:
        lines = [
            f"🌊 *{ship['name']}* vs *{enemy['emoji']} {enemy['name']}*\n",
            "❌ *شکست دریایی!*\n",
        ]
        if result.get("beli") and result["beli"] < 0:
            lines.append(f"💸 {abs(result['beli']):,} Beli از دست دادی")

    p = sync_energy(get_player(user_id))
    lines.append(f"\n⚡ انرژی: {p['energy']}/100")
    await _safe_edit(query, "\n".join(lines), parse_mode="Markdown", reply_markup=back_to_menu())


async def _handle_fishing(query, user_id: int, player: dict) -> None:
    import asyncio
    from one_piece_rpg.services.battle import fish
    await _safe_edit(query, "🎣 *در حال ماهیگیری...*", parse_mode="Markdown")
    await asyncio.sleep(1.5)
    result = fish(user_id)
    if not result["ok"]:
        await _safe_edit(query, result["message"], reply_markup=back_to_menu())
        return
    f = result["fish"]
    lines = [
        f"🎣 *ماهی گرفتی!*\n",
        f"{f['emoji']} *{f['name']}*",
        f"💰 فروش خام: {f['sell']:,} Beli",
        f"🍳 فروش پخته: {f['sell'] * 3:,} Beli",
    ]
    if result.get("rod_broke"):
        lines.append("\n⚠️ *قلابت شکست!* باید قلاب جدید بخری.")
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    from one_piece_rpg.database import get_db as _gdb3
    fish_id = result["fish_id"]

    # چک داشتن آشپز
    with _gdb3() as conn:
        has_chef = conn.execute(
            "SELECT 1 FROM inventory WHERE user_id=? AND item_type='chef' LIMIT 1",
            (user_id,)
        ).fetchone()

    # تشخیص گروه یا خصوصی
    try:
        chat_type = query.message.chat.type
        is_group = chat_type in ("group", "supergroup")
    except Exception:
        is_group = False

    if is_group:
        back_btn = [InlineKeyboardButton("🔙 منو گروه", callback_data=f"grp:back:{user_id}")]
    else:
        back_btn = [InlineKeyboardButton("🔙 منوی اصلی", callback_data="menu:main")]

    btn_rows = [
        [InlineKeyboardButton(f"🍖 بخور (+{f['food']} غذا)", callback_data=f"fish:eat:{fish_id}")],
        [InlineKeyboardButton(f"💰 بفروش ({f['sell']:,})", callback_data=f"fish:sell:{fish_id}")],
    ]
    if has_chef:
        btn_rows.append([InlineKeyboardButton(f"🍳 به آشپز بده ({f['sell']*3:,})", callback_data=f"fish:cook:{fish_id}")])
    btn_rows.append(back_btn)

    await _safe_edit(query, "\n".join(lines), parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(btn_rows)
    )


async def _handle_fight(query, user_id: int, player: dict) -> None:
    from one_piece_rpg.services.battle import pick_enemy, _player_atk, _player_def
    from one_piece_rpg.data import FIGHT_ENERGY_COST
    from one_piece_rpg.services.player import sync_energy, is_dead, get_player as _gp
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    import json

    player = sync_energy(_gp(user_id))
    if is_dead(player):
        await _safe_edit(query, "💀 در حال بهبودی هستی.", reply_markup=back_to_menu())
        return
    if player["energy"] < FIGHT_ENERGY_COST:
        await _safe_edit(query, f"⚡ انرژی کافی نیست! ({player['energy']}/100)", reply_markup=back_to_menu())
        return

    enemy = pick_enemy(player["current_island"], player["level"])
    atk = _player_atk(player)
    defense = _player_def(player)
    player_hp = 100 + player["level"] * 5
    enemy_hp = enemy["hp"]

    # آیتم‌های battle
    battle_items = []
    if player.get("battle_items"):
        try:
            battle_items = json.loads(player["battle_items"])
        except Exception:
            battle_items = []

    # ذخیره session در context
    _solo_sessions[user_id] = {
        "enemy": enemy,
        "enemy_hp": enemy_hp,
        "enemy_max_hp": enemy_hp,
        "player_hp": player_hp,
        "player_max_hp": player_hp,
        "player_atk": atk,
        "player_def": defense,
        "battle_items": battle_items,
    }

    def hp_bar(hp, max_hp):
        filled = max(0, hp * 10 // max_hp)
        return "█" * filled + "░" * (10 - filled)

    await _safe_edit(query,
        f"⚔️ *مبارزه شروع شد!*\n\n"
        f"👹 *{enemy['name']}* (Lv.{enemy['lvl']})\n"
        f"❤️ {enemy_hp}/{enemy_hp} [{hp_bar(enemy_hp, enemy_hp)}]\n\n"
        f"👤 *تو* (Lv.{player['level']})\n"
        f"❤️ {player_hp}/{player_hp} [{hp_bar(player_hp, player_hp)}]\n\n"
        "حمله رو انتخاب کن:",
        parse_mode="Markdown",
        reply_markup=_solo_fight_keyboard(user_id)
    )


def _format_profile(player: dict) -> str:
    faction_emoji = "🏴‍☠️" if player["faction"] == "pirate" else "⚓"
    rank = get_rank(player)
    island = get_island(player)

    char_text = player.get("username") or "—"
    bio = ""
    if player.get("age"):
        from one_piece_rpg.data import RACES, RACE_UPGRADES
        race_key = player.get("race", "human")
        # چک اگه نژاد ارتقایافته (مثلاً giant_ancient)
        if race_key == "giant_ancient":
            race_info = {"emoji": "🏔", "name": "غول باستانی"}
        else:
            race_info = RACES.get(race_key, RACES["human"])
        bio = (f"{race_info['emoji']} نژاد: {race_info['name']} | "
               f"🎂 سن: {player['age']} | "
               f"📏 قد: {player.get('height',0)}cm | "
               f"⚖️ وزن: {player.get('weight',0)}kg\n")

    ship_text = SHIPS[player["ship_id"]]["name"] if player.get("ship_id") else "ندارد"
    bounty_line = f"💀 Bounty: {player['bounty']:,}\n" if player["faction"] == "pirate" else ""

    return (
        f"👤 *پروفایل*\n\n"
        f"{faction_emoji} فکشن: *{player['faction'].title()}*\n"
        f"🏅 Rank: *{rank}*\n"
        f"📈 Level: {player['level']}\n"
        f"⭐ XP: {player['xp']:,}\n"
        f"💰 Beli: {player['beli']:,}\n"
        f"{bounty_line}"
        f"{bio}"
        f"⚡ Energy: {player['energy']}/100\n"
        f"🗺 جزیره: {island['name']}\n"
        f"🚢 کشتی: {ship_text}"
    )


def _main_menu_text(player: dict) -> str:
    island = get_island(player)
    faction_emoji = "🏴‍☠️" if player["faction"] == "pirate" else "⚓"
    return (
        f"{faction_emoji} *ONE PIECE RPG*\n\n"
        f"📈 Level {player['level']} | 💰 {player['beli']:,} Beli\n"
        f"⚡ {player['energy']}/100 | 🗺 {island['name']}\n\n"
        "یک عملیات انتخاب کن:"
    )


async def _send_main_menu(update: Update, player: dict) -> None:
    msg = update.message or update.callback_query.message
    chat_type = msg.chat.type if msg else "private"
    is_group = chat_type in ("group", "supergroup")
    if is_group:
        kb = group_menu_keyboard(msg.chat.id, player["user_id"])
    else:
        kb = main_menu_keyboard()
    await msg.reply_text(
        _main_menu_text(player),
        parse_mode="Markdown",
        reply_markup=kb,
    )
