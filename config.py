import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "8656415921:AAEHMziFqvWQVHPzmbkggbo5lIIxwvH772M")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///database.db")

# Google Maps API
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY", "")

# Google Calendar OAuth
GOOGLE_CALENDAR_CREDENTIALS = os.getenv("GOOGLE_CALENDAR_CREDENTIALS", "credentials/google_calendar.json")
GOOGLE_CALENDAR_TOKEN = os.getenv("GOOGLE_CALENDAR_TOKEN", "token.json")

# Outlook Calendar
OUTLOOK_CLIENT_ID = os.getenv("OUTLOOK_CLIENT_ID", "")
OUTLOOK_CLIENT_SECRET = os.getenv("OUTLOOK_CLIENT_SECRET", "")
OUTLOOK_TENANT_ID = os.getenv("OUTLOOK_TENANT_ID", "")

# YooKassa (ЮKassa)
YOOKASSA_SHOP_ID = os.getenv("YOOKASSA_SHOP_ID", "")
YOOKASSA_SECRET_KEY = os.getenv("YOOKASSA_SECRET_KEY", "")

# DonationAlerts
DONATION_ALERTS_TOKEN = os.getenv("DONATION_ALERTS_TOKEN", "")

# Telegram API для поиска групп (Telethon)
TELEGRAM_API_ID = os.getenv("TELEGRAM_API_ID", "")
TELEGRAM_API_HASH = os.getenv("TELEGRAM_API_HASH", "")

# Instagram (неофициальный API, осторожно)
INSTAGRAM_USERNAME = os.getenv("INSTAGRAM_USERNAME", "")
INSTAGRAM_PASSWORD = os.getenv("INSTAGRAM_PASSWORD", "")

ADMIN_IDS = [int(id) for id in os.getenv("ADMIN_IDS", "123456789").split(",")]

# amoCRM
AMOCRM_SUBDOMAIN = os.getenv("AMOCRM_SUBDOMAIN", "")
AMOCRM_ACCESS_TOKEN = os.getenv("AMOCRM_ACCESS_TOKEN", "")
AMOCRM_REFRESH_TOKEN = os.getenv("AMOCRM_REFRESH_TOKEN", "")
AMOCRM_CLIENT_ID = os.getenv("AMOCRM_CLIENT_ID", "")
AMOCRM_CLIENT_SECRET = os.getenv("AMOCRM_CLIENT_SECRET", "")
AMOCRM_REDIRECT_URI = os.getenv("AMOCRM_REDIRECT_URI", "")

# Bitrix24
BITRIX24_WEBHOOK_URL = os.getenv("BITRIX24_WEBHOOK_URL", "")