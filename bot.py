import asyncio
import datetime
import logging
import os
import traceback
from aiogram import Bot, Dispatcher, F
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.common.token import BOT_TOKEN, BOSS_IDS, PORTMONE_LIMIT
from app.handlers import user_handlers, admin_handlers, error_handler
from app.databases.mongodb import upsert_user, db, cleanup_old_bookings, cleanup_logs, refresh_apartments_cache, export_site_json, add_log, log_error, cleanup_runtime_diagnostics, get_apartments
from app.keyboards.user_keyboards import ap_info_inline_kb
from app.common.texts import get_text
from app.common.middleware import LanguageMiddleware
from aiohttp import web
last_reminder_date = None


class MongoLogHandler(logging.Handler):
    def __init__(self, loop: asyncio.AbstractEventLoop):
        super().__init__()
        self.loop = loop

    def emit(self, record: logging.LogRecord):
        try:
            details = self.format(record)
            extra = {}
            if record.exc_info:
                extra["traceback"] = "".join(traceback.format_exception(*record.exc_info))
            coro = add_log(
                source=record.name,
                action=record.levelname.lower(),
                details=details,
                level=record.levelname,
                extra=extra,
            )
            self.loop.call_soon_threadsafe(asyncio.create_task, coro)
        except Exception:
            pass


def configure_logging(loop: asyncio.AbstractEventLoop):
    formatter = logging.Formatter("%(asctime)s | %(name)s | %(levelname)s | %(message)s")
    mongo_handler = MongoLogHandler(loop)
    mongo_handler.setLevel(logging.INFO)
    mongo_handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(mongo_handler)

    logging.getLogger("aiohttp.access").setLevel(logging.INFO)
    logging.getLogger("aiogram").setLevel(logging.INFO)
    return logging.getLogger("gil")

async def daily_reminder(bot: Bot):
    global last_reminder_date
    while True:
        try:
            now = datetime.datetime.now()
            today_str = now.strftime("%d.%m.%Y")
            if now.hour >= 10 and last_reminder_date != today_str:
                bookings = await db.bookings.find({"start_date": today_str, "status": {"$in": ["paid_50", "confirmed"]}}).to_list(None)
                for b in bookings:
                    try:
                        user = await db.users.find_one({"user_id": b['user_id']})
                        lang = user.get('language', 'uk') if user else 'uk'
                        rem = b['remaining'] - b.get('paid_remaining', 0)
                        if rem <= 0: continue
                        msg = get_text('msg_checkin_reminder', lang, remaining=rem)
                        ap = await db.apartments.find_one({"_id": b['ap_id']})
                        kb = ap_info_inline_kb(ap['lat'], ap['lng'], str(b['_id']), lang, amount=rem, is_final=True)
                        await bot.send_message(b['user_id'], msg, reply_markup=kb, parse_mode="HTML")
                        await add_log("scheduler", "daily_reminder_sent", f"Reminder sent for booking {b['_id']}", user_id=b["user_id"])
                    except: pass
                await cleanup_old_bookings()
                await cleanup_logs()
                await add_log("scheduler", "daily_maintenance", "Daily cleanup completed")
                last_reminder_date = today_str
            await asyncio.sleep(60) 
        except Exception as e:
            await log_error(str(e), "")
            await asyncio.sleep(60)

async def apartments_sync_loop():
    while True:
        try:
            await refresh_apartments_cache()
            await export_site_json()
            await add_log("sync", "apartments_sync", "Apartments cache and site JSON synchronized from MongoDB")
        except Exception as e:
            await log_error(f"Apartments sync failed: {e}", "")
        await asyncio.sleep(30)

async def get_apartments_api(request):
    apartments = await get_apartments()
    await add_log("api", "get_apartments", details=f"Returned {len(apartments)} apartments")
    return web.json_response(apartments, headers={"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "GET, OPTIONS", "Access-Control-Allow-Headers": "*"})

async def get_profile_api(request):
    user_id_raw = request.query.get("user_id", "").strip()
    if not user_id_raw.isdigit():
        await add_log("api", "get_profile_invalid_user_id", details=f"Invalid user_id: {user_id_raw}", level="WARNING")
        return web.json_response({"error": "invalid_user_id"}, status=400)

    user = await db.users.find_one({"user_id": int(user_id_raw)})
    if not user:
        await add_log("api", "get_profile_not_found", details=f"User not found: {user_id_raw}", level="WARNING")
        return web.json_response({"error": "user_not_found"}, status=404)

    await add_log("api", "get_profile", details=f"Profile returned for {user_id_raw}", user_id=int(user_id_raw))
    return web.json_response({
        "user_id": user["user_id"],
        "name": user.get("name", ""),
        "phone": user.get("phone", ""),
        "language": user.get("language", "uk"),
        "currency": user.get("currency", "")
    }, headers={"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "GET, OPTIONS", "Access-Control-Allow-Headers": "*"})

async def start_web_server():
    app = web.Application()
    app.router.add_get('/api/apartments', get_apartments_api)
    app.router.add_get('/api/profile', get_profile_api)
    site_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'Site'))
    app.router.add_static('/', path=site_path, name='site', show_index=True)
    async def cors_middleware(app, handler):
        async def middleware(request):
            if request.method == 'OPTIONS':
                return web.Response(headers={"Access-Control-Allow-Origin": "*", "Access-Control-Allow-Methods": "GET, POST, OPTIONS", "Access-Control-Allow-Headers": "*"})
            resp = await handler(request)
            resp.headers["Access-Control-Allow-Origin"] = "*"
            return resp
        return middleware
    app.middlewares.append(cors_middleware)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", "8000"))
    await web.TCPSite(runner, '0.0.0.0', port).start()
    await add_log("server", "web_server_started", f"Web server started on 0.0.0.0:{port}", extra={"port": port})

async def main():
    loop = asyncio.get_running_loop()
    logger = configure_logging(loop)
    try:
        await cleanup_runtime_diagnostics()
    except Exception:
        pass
    bot = None
    try:
        logger.info("Application startup initiated")
        await add_log("app", "startup", "Application startup initiated")
        await add_log("database", "connect", "MongoDB client initialized", extra={"database": "gil_apartments"})
        await refresh_apartments_cache()
        await export_site_json()
        await add_log("app", "bootstrap_ready", "Apartment cache refreshed and site JSON exported")
        bot = Bot(token=BOT_TOKEN)
        dp = Dispatcher()
        dp.update.middleware(LanguageMiddleware())
        dp.include_router(error_handler.router)
        dp.include_router(admin_handlers.router)
        dp.include_router(user_handlers.router)
        for b_id in BOSS_IDS:
            await upsert_user(b_id, role="boss")
        await add_log("auth", "boss_ids_synced", details="Boss users upserted", extra={"boss_ids": BOSS_IDS})
        asyncio.create_task(daily_reminder(bot))
        asyncio.create_task(apartments_sync_loop())
        await start_web_server()
        await add_log("telegram", "delete_webhook", "Deleting webhook before polling")
        await bot.delete_webhook(drop_pending_updates=True)
        await add_log("telegram", "start_polling", "Starting aiogram polling")
        await dp.start_polling(bot)
    finally:
        if bot is not None:
            try:
                await bot.session.close()
            except Exception:
                pass

if __name__ == "__main__":
    import sys
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Startup error: {e}")
        sys.exit(1)
