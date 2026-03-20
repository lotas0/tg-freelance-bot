import os
from dotenv import load_dotenv


load_dotenv()


BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_CHAT_ID = os.getenv("OWNER_CHAT_ID")


if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не задан в .env")

if not OWNER_CHAT_ID:
    raise RuntimeError("OWNER_CHAT_ID не задан в .env")

try:
    OWNER_CHAT_ID = int(OWNER_CHAT_ID)
except ValueError as exc:
    raise RuntimeError("OWNER_CHAT_ID должен быть числом (chat_id)") from exc


SCAN_INTERVAL_SECONDS = int(os.getenv("SCAN_INTERVAL_SECONDS", "300"))

# Базовые ключевые слова для заказов
DEFAULT_KEYWORDS = [
    # сайты, лендинги, интернет‑магазины
    "создать сайт",
    "сделать сайт",
    "разработка сайта",
    "landing",
    "лендинг",
    "интернет магазин",
    "интернет-магазин",
    "верстка",
    "верстка сайта",
    "frontend",
    "frontend разработка",
    "backend",
    "fullstack",
    "фуллстек",
    "django",
    "flask",
    "fastapi",
    "react",
    "vue",
    "next.js",
    "nuxt",
    "node.js",
    "node js",
    "api разработка",
    "разработка api",
    "rest api",
    "web приложение",
    "веб приложение",
    "web-разработка",
    "веб-разработка",
    "web разработка",
    "веб разработка",
    # python
    "python",
    "python разработчик",
    "скрипт на python",
    "бот на python",
    "парсер на python",
    # боты (telegram, discord, vk и др.)
    "telegram бот",
    "телеграм бот",
    "бот telegram",
    "бот телеграм",
    "создать бота",
    "разработка бота",
    "написать бота",
    "чат-бот",
    "чат бот",
    "создать чат-бота",
    "discord бот",
    "бот discord",
    "vk бот",
    "бот вк",
    "бот для telegram",
    "бот для телеграм",
    "telegram-бот",
    "телеграм-бот",
]
