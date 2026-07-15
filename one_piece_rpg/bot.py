"""One Piece Telegram RPG - Bot entry point."""

import asyncio
import logging

from telegram import Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from one_piece_rpg.config import TELEGRAM_TOKEN
from one_piece_rpg.database import init_db
from one_piece_rpg.handlers import callback_handler, dice_handler, invite_command, menu_command, name_input_handler, photo_handler, profile_command, skip_command, start_command, group_trigger_handler

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def main() -> None:
    init_db()
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # ست کردن دستورات برای menu button
    from telegram import BotCommand
    commands = [
        BotCommand("start", "شروع بازی"),
        BotCommand("menu", "منوی اصلی"),
        BotCommand("profile", "پروفایل من"),
        BotCommand("invite", "دعوت به خدمه"),
        BotCommand("skip", "رد کردن عکس"),
    ]
    try:
        await app.bot.set_my_commands(commands)
    except Exception:
        pass  # اگه اینترنت نبود crash نکنه

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("menu", menu_command))
    app.add_handler(CommandHandler("profile", profile_command))
    app.add_handler(CommandHandler("skip", skip_command))
    app.add_handler(CommandHandler("invite", invite_command))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(
        filters.Dice.SLOT_MACHINE & filters.ChatType.PRIVATE,
        dice_handler
    ))
    app.add_handler(MessageHandler(
        filters.PHOTO & filters.ChatType.PRIVATE,
        photo_handler
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE,
        name_input_handler
    ))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & (filters.ChatType.GROUPS | filters.ChatType.SUPERGROUP),
        group_trigger_handler
    ))

    logger.info("One Piece RPG Bot started!")
    await app.initialize()
    await app.start()
    await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    try:
        await asyncio.Event().wait()
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
