import aiohttp
import asyncio
import time
from app.common.token import USD_RATE

_cache = {
    "rate": float(USD_RATE),
    "last_update": 0
}

CACHE_DURATION = 3600

async def fetch_rate():
    try:
        url = "https://api.privatbank.ua/p24api/pubinfo?json&exchange&coursid=5"
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    for entry in data:
                        if entry.get("ccy") == "USD" and entry.get("base_ccy") == "UAH":
                            return float(entry["sale"])
    except:
        pass
    return None

async def get_usd_rate():
    now = time.time()
    
    if now - _cache["last_update"] > CACHE_DURATION or _cache["last_update"] == 0:
        new_rate = await fetch_rate()
        if new_rate:
            _cache["rate"] = new_rate
            _cache["last_update"] = now
    
    return _cache["rate"]

def format_price(price_uah, rate, preferred_currency="uah"):
    price_usd = round(price_uah / rate, 2)
    if preferred_currency == "usd":
        return f"{price_usd} $"
    elif preferred_currency == "uah":
        return f"{price_uah} грн" if preferred_currency == "uah" else f"{price_uah} UAH"
    return f"{price_uah} грн / {price_usd} $"
