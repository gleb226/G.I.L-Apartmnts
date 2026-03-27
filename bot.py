import asyncio
from aiogram import Bot, Dispatcher, F
from app.common.token import BOT_TOKEN, MAIN_BOSS_ID

from app.handlers import user_handlers, admin_handlers, error_handler
from app.databases.mongodb import upsert_user, db
from app.common.token import MAIN_BOSS_ID
import datetime
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
async def daily_reminder(bot: Bot):
    while True:
        try:
            now = datetime.datetime.now()
            if now.hour == 9 and now.minute == 0:
                today_str = now.strftime("%d.%m.%Y")
                bookings = await db.bookings.find({
                    "start_date": today_str,
                    "status": {"$in": ["paid_50", "confirmed"]}
                }).to_list(None)
                for b in bookings:
                    try:
                        builder = InlineKeyboardBuilder()
                        builder.button(text="💳 Оплатити залишок 50%", callback_data=f"pay50_final_{str(b['_id'])}")
                        msg = (
                            f"🏨 Сьогодні день вашого заселення!\n\n"
                            f"Будь ласка, оплатіть залишок 50% ({b['remaining']} грн) для завершення бронювання.\n"
                            f"🕒 Заїзд: з 12:00."
                        )
                        await bot.send_message(b['user_id'], msg, reply_markup=builder.as_markup())
                    except Exception as e:
                        pass
                await asyncio.sleep(86340) 
            else:
                await asyncio.sleep(60) 
        except Exception as e:
            await asyncio.sleep(60)
async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.include_router(error_handler.router)
    dp.include_router(admin_handlers.router)
    dp.include_router(user_handlers.router)
    await upsert_user(MAIN_BOSS_ID, role="boss", name="Main Boss")
    asyncio.create_task(daily_reminder(bot))
    try:
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot)
    finally:
        await bot.session.close()
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass