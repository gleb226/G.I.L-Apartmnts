import os
from dotenv import load_dotenv
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
PAYMENT_TOKEN = os.getenv("PAYMENT_TOKEN")
MONGODB_URI = os.getenv("MONGODB_URI")

raw_boss_ids = os.getenv("BOSS_IDS", "")
BOSS_IDS = [int(i.strip()) for i in raw_boss_ids.split(",") if i.strip().isdigit()]

USD_RATE = float(os.getenv("USD_RATE", 42.0))
