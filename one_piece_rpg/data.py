"""One Piece RPG - Game constants and static data."""

FACTIONS = ("pirate", "marine")

RARITY_EMOJI = {
    "common": "⚪",
    "rare": "🔵",
    "epic": "🟣",
    "legendary": "🟡",
    "mythic": "🔴",
}

RARITY_ORDER = ("common", "rare", "epic", "legendary", "mythic")

# ── Characters ──────────────────────────────────────────────────────────────

CHARACTERS = {
    # Pirate starters & shop
    "luffy": {"name": "Monkey D. Luffy", "faction": "pirate", "rarity": "common", "price": 0, "base_atk": 12, "base_def": 8, "base_hp": 120},
    "zoro": {"name": "Roronoa Zoro", "faction": "pirate", "rarity": "common", "price": 0, "base_atk": 15, "base_def": 6, "base_hp": 110},
    "nami": {"name": "Nami", "faction": "pirate", "rarity": "common", "price": 0, "base_atk": 8, "base_def": 10, "base_hp": 100},
    "usopp": {"name": "Usopp", "faction": "pirate", "rarity": "rare", "price": 800, "base_atk": 10, "base_def": 9, "base_hp": 105},
    "sanji": {"name": "Sanji", "faction": "pirate", "rarity": "rare", "price": 800, "base_atk": 14, "base_def": 8, "base_hp": 115},
    "robin": {"name": "Nico Robin", "faction": "pirate", "rarity": "epic", "price": 3000, "base_atk": 16, "base_def": 12, "base_hp": 130},
    "law": {"name": "Trafalgar Law", "faction": "pirate", "rarity": "epic", "price": 3500, "base_atk": 18, "base_def": 11, "base_hp": 135},
    "shanks": {"name": "Shanks", "faction": "pirate", "rarity": "legendary", "price": 15000, "base_atk": 30, "base_def": 25, "base_hp": 250},
    "mihawk": {"name": "Dracule Mihawk", "faction": "pirate", "rarity": "legendary", "price": 18000, "base_atk": 35, "base_def": 20, "base_hp": 240},
    "dragon": {"name": "Monkey D. Dragon", "faction": "pirate", "rarity": "mythic", "price": 100000, "base_atk": 50, "base_def": 40, "base_hp": 400},
    # Marine starters & shop
    "coby": {"name": "Coby", "faction": "marine", "rarity": "common", "price": 0, "base_atk": 10, "base_def": 10, "base_hp": 110},
    "helmeppo": {"name": "Helmeppo", "faction": "marine", "rarity": "common", "price": 0, "base_atk": 11, "base_def": 9, "base_hp": 108},
    "soldier": {"name": "Marine Soldier", "faction": "marine", "rarity": "common", "price": 0, "base_atk": 9, "base_def": 11, "base_hp": 112},
    "smoker": {"name": "Smoker", "faction": "marine", "rarity": "rare", "price": 800, "base_atk": 13, "base_def": 12, "base_hp": 120},
    "tashigi": {"name": "Tashigi", "faction": "marine", "rarity": "rare", "price": 800, "base_atk": 12, "base_def": 11, "base_hp": 115},
    "hina": {"name": "Hina", "faction": "marine", "rarity": "epic", "price": 3000, "base_atk": 15, "base_def": 14, "base_hp": 125},
    "garp": {"name": "Garp", "faction": "marine", "rarity": "legendary", "price": 20000, "base_atk": 33, "base_def": 28, "base_hp": 280},
    "akainu": {"name": "Akainu", "faction": "marine", "rarity": "legendary", "price": 22000, "base_atk": 32, "base_def": 22, "base_hp": 260},
    "sengoku": {"name": "Sengoku", "faction": "marine", "rarity": "mythic", "price": 100000, "base_atk": 48, "base_def": 38, "base_hp": 390},
}

STARTER_CHARACTERS = {
    "pirate": ("luffy", "zoro", "nami"),
    "marine": ("coby", "helmeppo", "soldier"),
}

# ── Islands ───────────────────────────────────────────────────────────────────

ISLANDS = [
    {"id": "east_blue", "name": "East Blue", "min_level": 1, "emoji": "🌊"},
    {"id": "alabasta", "name": "Alabasta", "min_level": 10, "emoji": "🏜"},
    {"id": "skypiea", "name": "Skypiea", "min_level": 20, "emoji": "☁️"},
    {"id": "water_7", "name": "Water 7", "min_level": 30, "emoji": "🔧"},
    {"id": "enies_lobby", "name": "Enies Lobby", "min_level": 35, "emoji": "⚖️"},
    {"id": "thriller_bark", "name": "Thriller Bark", "min_level": 40, "emoji": "👻"},
    {"id": "marineford", "name": "Marineford", "min_level": 50, "emoji": "⚓"},
    {"id": "dressrosa", "name": "Dressrosa", "min_level": 60, "emoji": "🌹"},
    {"id": "whole_cake", "name": "Whole Cake", "min_level": 70, "emoji": "🍰"},
    {"id": "wano", "name": "Wano", "min_level": 80, "emoji": "⛩"},
    {"id": "egghead", "name": "Egghead", "min_level": 90, "emoji": "🔬"},
    {"id": "laugh_tale", "name": "Laugh Tale", "min_level": 99, "emoji": "👑"},
]

# ── Enemies per island ────────────────────────────────────────────────────────

ENEMIES = {
    "east_blue": [
        {"id": "bandit", "name": "Bandit", "lvl": 1, "hp": 30, "atk": 8, "xp": 12, "beli": 8, "death_chance": 0.02, "item_chance": 0.05},
        {"id": "weak_pirate", "name": "Weak Pirate", "lvl": 3, "hp": 55, "atk": 12, "xp": 22, "beli": 15, "death_chance": 0.03, "item_chance": 0.06},
        {"id": "alvida", "name": "Lady Alvida", "lvl": 5, "hp": 120, "atk": 20, "xp": 55, "beli": 45, "death_chance": 0.05, "item_chance": 0.10, "boss": True},
        {"id": "buggy", "name": "Buggy", "lvl": 8, "hp": 200, "atk": 28, "xp": 95, "beli": 85, "death_chance": 0.06, "item_chance": 0.12, "boss": True},
        {"id": "arlong", "name": "Arlong", "lvl": 15, "hp": 400, "atk": 45, "xp": 200, "beli": 180, "death_chance": 0.08, "item_chance": 0.15, "boss": True},
    ],
    "alabasta": [
        {"id": "sand_bandit", "name": "Sand Bandit", "lvl": 12, "hp": 180, "atk": 30, "xp": 80, "beli": 60, "death_chance": 0.05, "item_chance": 0.08},
        {"id": "crocodile", "name": "Crocodile", "lvl": 20, "hp": 600, "atk": 55, "xp": 350, "beli": 300, "death_chance": 0.10, "item_chance": 0.20, "boss": True},
    ],
    "skypiea": [
        {"id": "skypiean_guard", "name": "Skypiean Guard", "lvl": 22, "hp": 250, "atk": 40, "xp": 120, "beli": 90, "death_chance": 0.06, "item_chance": 0.09},
        {"id": "enel", "name": "Enel", "lvl": 30, "hp": 900, "atk": 70, "xp": 500, "beli": 450, "death_chance": 0.12, "item_chance": 0.22, "boss": True},
    ],
}

# Default enemies for islands without specific data
DEFAULT_ENEMIES = [
    {"id": "island_guard", "name": "Island Guard", "lvl": 10, "hp": 150, "atk": 25, "xp": 60, "beli": 40, "death_chance": 0.05, "item_chance": 0.07},
    {"id": "island_boss", "name": "Island Boss", "lvl": 20, "hp": 500, "atk": 50, "xp": 250, "beli": 200, "death_chance": 0.10, "item_chance": 0.15, "boss": True},
]

# ── Devil Fruits ──────────────────────────────────────────────────────────────

DEVIL_FRUITS = {
    "gomu_gomu": {"name": "Gomu Gomu no Mi", "rarity": "legendary", "atk_bonus": 15, "def_bonus": 10, "hp_bonus": 50},
    "mera_mera": {"name": "Mera Mera no Mi", "rarity": "epic", "atk_bonus": 20, "def_bonus": 5, "hp_bonus": 30},
    "hie_hie": {"name": "Hie Hie no Mi", "rarity": "legendary", "atk_bonus": 18, "def_bonus": 12, "hp_bonus": 40},
    "ope_ope": {"name": "Ope Ope no Mi", "rarity": "mythic", "atk_bonus": 30, "def_bonus": 20, "hp_bonus": 80},
    "gura_gura": {"name": "Gura Gura no Mi", "rarity": "mythic", "atk_bonus": 35, "def_bonus": 15, "hp_bonus": 70},
    "moku_moku": {"name": "Moku Moku no Mi", "rarity": "rare", "atk_bonus": 8, "def_bonus": 6, "hp_bonus": 20},
    "bara_bara": {"name": "Bara Bara no Mi", "rarity": "common", "atk_bonus": 5, "def_bonus": 3, "hp_bonus": 15},
    "suna_suna": {"name": "Suna Suna no Mi", "rarity": "epic", "atk_bonus": 14, "def_bonus": 10, "hp_bonus": 35},
}

DEVIL_FRUIT_DROP_RATES = {
    "common": 0.05,
    "rare": 0.01,
    "epic": 0.002,
    "legendary": 0.0005,
    "mythic": 0.0001,
}

# ── Items ─────────────────────────────────────────────────────────────────────

ITEMS = {
    "wooden_sword": {"name": "Wooden Sword", "type": "sword", "rarity": "common", "atk": 3, "def": 0, "sell_price": 20},
    "iron_sword": {"name": "Iron Sword", "type": "sword", "rarity": "rare", "atk": 8, "def": 2, "sell_price": 100},
    "wado_ichimonji": {"name": "Wado Ichimonji", "type": "sword", "rarity": "legendary", "atk": 25, "def": 5, "sell_price": 5000},
    "leather_armor": {"name": "Leather Armor", "type": "armor", "rarity": "common", "atk": 0, "def": 5, "sell_price": 25},
    "marine_coat": {"name": "Marine Coat", "type": "armor", "rarity": "rare", "atk": 2, "def": 10, "sell_price": 150},
    "straw_hat": {"name": "Straw Hat", "type": "hat", "rarity": "epic", "atk": 5, "def": 8, "sell_price": 800},
    "seastone_necklace": {"name": "Seastone Necklace", "type": "necklace", "rarity": "epic", "atk": 10, "def": 10, "sell_price": 1200},
    "lucky_ring": {"name": "Lucky Ring", "type": "ring", "rarity": "rare", "atk": 4, "def": 4, "sell_price": 200},
}

RACES = {
    "human":    {"name": "انسان",          "height_cm": (150, 580),   "emoji": "👤"},
    "giant":    {"name": "غول",            "height_cm": (1000, 2000), "emoji": "🏔", "note": "۱۰ تا ۲۰ متر", "upgradable": True},
    "buccaneer": {"name": "باکانیر",        "height_cm": (400, 850),   "emoji": "⚓"},
    "mink":     {"name": "مینک",           "height_cm": (130, 550),   "emoji": "🐾"},
    "fishman":  {"name": "آدم ماهی",       "height_cm": (190, 520),   "emoji": "🐟"},
    "cyborg":   {"name": "سایبورگ",        "height_cm": (200, 800),   "emoji": "🤖"},
    "celestial_dragon": {"name": "اژدهای افلاکی", "height_cm": (130, 250), "emoji": "🐉"},
    "dwarf":    {"name": "آدم کوچیک",      "height_cm": (20, 35),     "emoji": "🌱", "note": "۲۰ تا ۳۵ سانت"},
    "skypiean": {"name": "اسکای پیا",      "height_cm": (150, 340),   "emoji": "☁️"},
}

RACE_UPGRADES = {
    "giant": {
        "to": "giant_ancient",
        "name": "غول باستانی",
        "cost": 10_000_000_000,
        "height_cm": (3000, 5500),
        "note": "۳۰ تا ۵۵ متر",
        "emoji": "🏔",
        "atk_bonus": 50,
        "def_bonus": 40,
    }
}

CHEST_TYPES = {
    "wooden": {"name": "Wooden Chest", "emoji": "📦", "open_hours": 1, "drops": ["common", "common", "rare"]},
    "silver": {"name": "Silver Chest", "emoji": "🥈", "open_hours": 4, "drops": ["rare", "rare", "epic"]},
    "gold": {"name": "Gold Chest", "emoji": "🥇", "open_hours": 12, "drops": ["epic", "epic", "legendary"]},
    "diamond": {"name": "Diamond Chest", "emoji": "💎", "open_hours": 24, "drops": ["legendary", "legendary", "mythic"]},
    "legendary": {"name": "Legendary Chest", "emoji": "🟡", "open_hours": 48, "drops": ["legendary", "mythic"]},
    "mythic": {"name": "Mythic Chest", "emoji": "🔴", "open_hours": 72, "drops": ["mythic", "mythic", "legendary"]},
}

# ── Ships ─────────────────────────────────────────────────────────────────────

SHIPS = {
    "dinghy":      {"name": "قایق ساده",       "price": 1_000_000,   "hp": 200,  "speed": 5,  "defense": 5,   "cargo": 10,  "crew_cap": 2,  "sea_resist": 5,  "emoji": "🛶"},
    "small_ship":  {"name": "کشتی کوچک",       "price": 5_000_000,   "hp": 600,  "speed": 12, "defense": 15,  "cargo": 30,  "crew_cap": 5,  "sea_resist": 15, "emoji": "⛵"},
    "medium_ship": {"name": "کشتی متوسط",      "price": 20_000_000,  "hp": 1500, "speed": 20, "defense": 30,  "cargo": 80,  "crew_cap": 12, "sea_resist": 30, "emoji": "🚢"},
    "large_ship":  {"name": "کشتی بزرگ",       "price": 100_000_000, "hp": 4000, "speed": 28, "defense": 55,  "cargo": 200, "crew_cap": 30, "sea_resist": 55, "emoji": "🛳"},
    "legendary_ship": {"name": "کشتی افسانه‌ای", "price": 500_000_000, "hp": 10000, "speed": 40, "defense": 100, "cargo": 500, "crew_cap": 80, "sea_resist": 100, "emoji": "☠️"},
}

# ── Sea travel events ─────────────────────────────────────────────────────────

SEA_EVENTS = [
    {"id": "whale", "name": "🐋 نهنگ غول‌پیکر", "chance": 0.10, "beli": 50, "xp": 30},
    {"id": "storm", "name": "🌪 طوفان", "chance": 0.15, "beli": -20, "xp": 10},
    {"id": "pirate_attack", "name": "🏴‍☠️ حمله دزد دریایی", "chance": 0.20, "beli": 30, "xp": 40},
    {"id": "marine_attack", "name": "⚓ حمله Marine", "chance": 0.15, "beli": 25, "xp": 35},
    {"id": "hidden_island", "name": "🏝 جزیره مخفی", "chance": 0.05, "beli": 100, "xp": 80},
    {"id": "treasure", "name": "💰 گنج دریایی", "chance": 0.08, "beli": 200, "xp": 50},
    {"id": "ghost_ship", "name": "👻 کشتی ارواح", "chance": 0.07, "beli": 0, "xp": 60},
]

# ── Ranks ─────────────────────────────────────────────────────────────────────

PIRATE_RANKS = [
    (1, "Rookie", "تازه‌کار"),
    (10, "Super Rookie", "سوپر تازه‌کار"),
    (20, "Elite", "نخبه"),
    (35, "Captain", "کاپیتان"),
    (50, "Super Captain", "سوپر کاپیتان"),
    (65, "Legend", "افسانه"),
    (80, "Emperor Candidate", "نامزد امپراتور"),
    (95, "Yonko", "یونکو"),
    (100, "King of Pirates", "پادشاه دزدان دریایی"),
]

MARINE_RANKS = [
    (1, "Recruit", "سرباز تازه‌وارد"),
    (10, "Officer", "افسر"),
    (20, "Lieutenant", "ستوان"),
    (35, "Captain", "کاپیتان"),
    (50, "Vice Admiral", "معاون ادمیرال"),
    (70, "Admiral", "ادمیرال"),
    (95, "Fleet Admiral", "ادمیرال ناوگان"),
]

# ── World Bosses ──────────────────────────────────────────────────────────────

WORLD_BOSSES = {
    "kaido": {"name": "Kaido", "hp": 50000, "atk": 500, "beli_pool": 50000, "xp": 5000},
    "big_mom": {"name": "Big Mom", "hp": 45000, "atk": 480, "beli_pool": 45000, "xp": 4800},
    "blackbeard": {"name": "Blackbeard", "hp": 40000, "atk": 460, "beli_pool": 40000, "xp": 4500},
    "shanks": {"name": "Shanks", "hp": 42000, "atk": 490, "beli_pool": 42000, "xp": 4700},
    "akainu": {"name": "Akainu", "hp": 43000, "atk": 470, "beli_pool": 43000, "xp": 4600},
}

# ── Haki ──────────────────────────────────────────────────────────────────────

HAKI_TYPES = ("observation", "armament", "conqueror")

HAKI_UNLOCK_LEVELS = {
    "observation": 25,
    "armament": 40,
    "conqueror": 80,
}

# ── Core constants ────────────────────────────────────────────────────────────

MAX_ENERGY = 100
ENERGY_REGEN_MINS = 8
FIGHT_ENERGY_COST = 10
DEATH_COOLDOWN_MINS = 30
DAILY_REWARD_BASE = 150
DAILY_REWARD_STREAK_BONUS = 25
MAX_DAILY_STREAK = 7

LEVEL_XP = [0] + [int(100 * (i ** 1.5)) for i in range(1, 101)]

WHEEL_REWARDS = [
    {"type": "beli",   "amount": 500,  "weight": 3,  "label": "🎉 +500 Beli (جکپات!)"},
    {"type": "beli",   "amount": 200,  "weight": 8,  "label": "💰 +200 Beli"},
    {"type": "beli",   "amount": 100,  "weight": 15, "label": "💰 +100 Beli"},
    {"type": "beli",   "amount": 50,   "weight": 20, "label": "💰 +50 Beli"},
    {"type": "energy", "amount": 30,   "weight": 10, "label": "⚡ +30 انرژی"},
    {"type": "energy", "amount": 15,   "weight": 12, "label": "⚡ +15 انرژی"},
    {"type": "chest",  "chest": "silver", "weight": 5, "label": "🥈 صندوق نقره"},
    {"type": "chest",  "chest": "wooden", "weight": 10, "label": "📦 صندوق چوبی"},
    {"type": "beli",   "amount": -50,  "weight": 10, "label": "💸 -50 Beli (بدشانسی)"},
    {"type": "beli",   "amount": -150, "weight": 5,  "label": "💸 -150 Beli (خیلی بد!)"},
    {"type": "nothing","amount": 0,    "weight": 7,  "label": "😐 هیچی (دفعه بعد)"},
]

WHEEL_COOLDOWN_MINS = 10  # هر ۱۰ دقیقه یک بار

# ── Food System ───────────────────────────────────────────────────────────────

FOOD_ITEMS = {
    "simple_food":  {"name": "غذای ساده",   "price": 200,    "food": 20, "emoji": "🍞"},
    "meat":         {"name": "گوشت",        "price": 500,    "food": 40, "emoji": "🍖"},
    "seafood":      {"name": "غذای دریایی", "price": 800,    "food": 50, "emoji": "🐟"},
    "special_food": {"name": "غذای ویژه",  "price": 2000,   "food": 80, "emoji": "🍱"},
}

FISHING_RODS = {
    "simple_rod":      {"name": "قلاب ساده",       "price": 500,    "speed_bonus": 0,  "rare_bonus": 0,   "emoji": "🎣"},
    "pro_rod":         {"name": "قلاب حرفه‌ای",   "price": 3000,   "speed_bonus": 20, "rare_bonus": 10,  "emoji": "🎣"},
    "legendary_rod":   {"name": "قلاب افسانه‌ای", "price": 15000,  "speed_bonus": 50, "rare_bonus": 30,  "emoji": "🎣"},
}

FISH_TYPES = {
    # ضعیف
    "sardine":      {"name": "ساردین",           "food": 5,   "sell": 50,    "chance": 25, "emoji": "🐟", "rod_break": 0},
    "small_tuna":   {"name": "تون کوچک",         "food": 10,  "sell": 120,   "chance": 20, "emoji": "🐟", "rod_break": 0},
    "herring":      {"name": "شاه ماهی",         "food": 8,   "sell": 80,    "chance": 20, "emoji": "🐟", "rod_break": 0},
    # متوسط
    "sea_bream":    {"name": "شاه پیش",          "food": 20,  "sell": 300,   "chance": 12, "emoji": "🐠", "rod_break": 0},
    "mackerel":     {"name": "ماکارل",           "food": 25,  "sell": 400,   "chance": 10, "emoji": "🐠", "rod_break": 0},
    "snapper":      {"name": "سناپر",            "food": 30,  "sell": 600,   "chance": 5,  "emoji": "🐠", "rod_break": 0},
    # بزرگ
    "big_tuna":     {"name": "تون بزرگ",         "food": 50,  "sell": 1500,  "chance": 4,  "emoji": "🐡", "rod_break": 1},
    "swordfish":    {"name": "شمشیرماهی",        "food": 60,  "sell": 2500,  "chance": 2,  "emoji": "🐡", "rod_break": 1},
    "marlin":       {"name": "مارلین",           "food": 70,  "sell": 4000,  "chance": 1,  "emoji": "🐡", "rod_break": 2},
    # کمیاب و خطرناک
    "sea_king":     {"name": "Sea King کوچک",    "food": 100, "sell": 15000, "chance": 0.5,"emoji": "🦈", "rod_break": 3},
    "giant_octopus":{"name": "اختاپوس غول",     "food": 80,  "sell": 8000,  "chance": 0.8,"emoji": "🐙", "rod_break": 2},
    "devil_whale":  {"name": "نهنگ شیطانی",     "food": 150, "sell": 50000, "chance": 0.1,"emoji": "🐋", "rod_break": 5},
    "mermaid_fish": {"name": "ماهی پری دریایی", "food": 200, "sell": 100000,"chance": 0.05,"emoji":"✨", "rod_break": 0},
}

FISH_COOLDOWN_MINS = 5

COOK_MULTIPLIER = 3

CHEFS = {
    "novice_chef":  {"name": "آشپز مبتدی",   "price": 5000,   "speed": 1.0, "quality": 1.0, "emoji": "👨\u200d🍳"},
    "pro_chef":     {"name": "آشپز حرفه‌ای", "price": 30000,  "speed": 2.0, "quality": 1.5, "emoji": "🧑\u200d🍳"},
    "master_chef":  {"name": "آشپز استاد",   "price": 150000, "speed": 4.0, "quality": 2.0, "emoji": "👨\u200d🍳"},
}

# ثانیه تا پخته شدن (با آشپز مبتدی — سریع‌تر با آشپز حرفه‌ای)
FISH_COOK_SECS = {
    "sardine": 60, "small_tuna": 90, "herring": 90,
    "sea_bream": 180, "mackerel": 180, "snapper": 300,
    "big_tuna": 600, "swordfish": 900, "marlin": 1800,
    "sea_king": 3600, "giant_octopus": 2700, "devil_whale": 7200, "mermaid_fish": 10800,
}

# دقیقه تا خراب شدن ماهی خام
FISH_EXPIRE_MINS = {
    "sardine": 60, "small_tuna": 120, "herring": 90,
    "sea_bream": 180, "mackerel": 240, "snapper": 300,
    "big_tuna": 480, "swordfish": 600, "marlin": 900,
    "sea_king": 1440, "giant_octopus": 1080, "devil_whale": 2880, "mermaid_fish": 4320,
}

# ── Sea Battle Enemies ────────────────────────────────────────────────────────

SEA_ENEMIES = [
    {"name": "دزد دریایی ضعیف",  "lvl": 1,  "ship_hp": 200,  "atk": 15, "xp": 30,  "beli": 500,   "emoji": "🏴‍☠️"},
    {"name": "ناو Marine",       "lvl": 5,  "ship_hp": 500,  "atk": 30, "xp": 80,  "beli": 1500,  "emoji": "⚓"},
    {"name": "دزد دریایی قوی",   "lvl": 10, "ship_hp": 1000, "atk": 50, "xp": 150, "beli": 3000,  "emoji": "💀"},
    {"name": "ناو جنگی",         "lvl": 20, "ship_hp": 2000, "atk": 80, "xp": 300, "beli": 8000,  "emoji": "🚢"},
    {"name": "کشتی Yonko",       "lvl": 50, "ship_hp": 5000, "atk": 150, "xp": 800, "beli": 25000, "emoji": "👑"},
]

STORY_INTRO = """🏴‍☠️ *ONE PIECE RPG*

در دنیایی پر از اقیانوس‌های بی‌پایان، جزایر مرموز و گنجینه‌های افسانه‌ای...

تو یک فرد کاملاً ضعیف هستی. بدون قدرت، بدون شهرت، بدون هیچ چیز.

اما رویاهای بزرگی در سر داری:
• تبدیل شدن به *پادشاه دزدان دریایی* 🏴‍☠️
• یا رسیدن به مقام *ادمیرال ناوگان* ⚓

راه سخت است. ماه‌ها طول می‌کشد. اما هر سفر بزرگ با یک قدم شروع می‌شود.

*حالا انتخاب کن — این تصمیم برای همیشه است:*"""
