import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")
load_dotenv(Path(__file__).resolve().parent / ".env")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
DATABASE_PATH = os.getenv(
    "DATABASE_PATH",
    str(Path(__file__).resolve().parent / "game.db"),
)

if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN یافت نشد. فایل .env را بررسی کنید.")
