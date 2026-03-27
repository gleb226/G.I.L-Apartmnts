from aiogram import Router, Bot
from aiogram.types import ErrorEvent
import traceback
from app.databases.mongodb import log_error

router = Router()

@router.error()
async def error_handler(event: ErrorEvent, bot: Bot):
    tb = traceback.format_exc()
    error_msg = str(event.exception)
    await log_error(error_msg, tb)
    
    dev_id = 513546547
    dev_msg = (
        f"‼️ <b>СИСТЕМНА ПОМИЛКА</b> ‼️\n\n"
        f"<b>Подія:</b> {error_msg}\n\n"
        f"<code>{tb[:3800]}</code>"
    )
    
    try:
        await bot.send_message(dev_id, dev_msg, parse_mode="HTML")
    except:
        pass
    
    user_msg = (
        "💎 <b>Вибачте за тимчасові незручності!</b>\n\n"
        "Виникла технічна помилка. Наші фахівці вже отримали звіт і працюють над її усуненням. "
        "Будь ласка, спробуйте ще раз через кілька хвилин."
    )
    
    chat_id = None
    if event.update.message:
        chat_id = event.update.message.chat.id
    elif event.update.callback_query:
        chat_id = event.update.callback_query.message.chat.id
        
    if chat_id and chat_id != dev_id:
        try:
            await bot.send_message(chat_id, user_msg, parse_mode="HTML")
        except:
            pass
