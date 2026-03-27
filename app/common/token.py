import os
from dotenv import load_dotenv
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
PAYMENT_TOKEN = os.getenv("PAYMENT_TOKEN")
MONGODB_URI = os.getenv("MONGODB_URI")
MAIN_BOSS_ID = int(os.getenv("MAIN_BOSS_ID"))