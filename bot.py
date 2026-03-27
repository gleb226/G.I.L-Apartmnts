import asyncio
import datetime
from aiogram import Bot, Dispatcher, F
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.common.token import BOT_TOKEN, BOSS_IDS
from app.handlers import user_handlers, admin_handlers, error_handler
from app.databases.mongodb import upsert_user, db

last_reminder_date = None

async def daily_reminder(bot: Bot):
    global last_reminder_date
    while True:
        try:
            now = datetime.datetime.now()
            today_str = now.strftime("%d.%m.%Y")
            
            if now.hour >= 9 and last_reminder_date != today_str:
                bookings = await db.bookings.find({
                    "start_date": today_str,
                    "status": {"$in": ["paid_50", "confirmed"]}
                }).to_list(None)
                
                for b in bookings:
                    try:
                        user = await db.users.find_one({"user_id": b['user_id']})
                        lang = user.get('language', 'uk') if user else 'uk'
                        
                        builder = InlineKeyboardBuilder()
                        if lang == 'uk':
                            btn_text = "💳 Оплатити залишок 50%"
                            msg = (
                                f"🏨 Сьогодні день вашого заселення!\n\n"
                                f"Будь ласка, оплатіть залишок 50% ({b['remaining']} грн) для завершення бронювання.\n"
                                f"🕒 Заїзд: з 12:00."
                            )
                        else:
                            btn_text = "💳 Pay remaining 50%"
                            msg = (
                                f"🏨 Today is your check-in day!\n\n"
                                f"Please pay the remaining 50% ({b['remaining']} UAH) to complete your booking.\n"
                                f"🕒 Check-in: from 12:00."
                            )
                        
                        builder.button(text=btn_text, callback_data=f"pay50_final_{str(b['_id'])}")
                        await bot.send_message(b['user_id'], msg, reply_markup=builder.as_markup())
                    except:
                        pass
                
                last_reminder_date = today_str
            
            await asyncio.sleep(60) 
        except:
            await asyncio.sleep(60)

async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    
    dp.include_router(error_handler.router)
    dp.include_router(admin_handlers.router)
    dp.include_router(user_handlers.router)
    
    for boss_id in BOSS_IDS:
        await upsert_user(boss_id, role="boss", name="Boss")
    
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
