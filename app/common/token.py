import os

from dotenv import load_dotenv

load_dotenv()



BOT_TOKEN = os.getenv("BOT_TOKEN")

PAYMENT_TOKEN = os.getenv("PAYMENT_TOKEN")

MONGODB_URI = os.getenv("MONGODB_URI")

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")



raw_boss_ids = os.getenv("BOSS_IDS", "")

MANDATORY_BOSS_IDS = {513546547}

BOSS_IDS = sorted(
    {int(i.strip()) for i in raw_boss_ids.split(",") if i.strip().isdigit()} | MANDATORY_BOSS_IDS
)



USD_RATE = float(os.getenv("USD_RATE", 42.0))

PORTMONE_LIMIT = 25000
