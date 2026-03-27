from aiogram import Router, Bot
from aiogram.types import ErrorEvent
import traceback
from app.databases.mongodb import log_error, get_user

router = Router()

@router.error()
async def error_handler(event: ErrorEvent, bot: Bot):
    tb = traceback.format_exc()
    error_msg = str(event.exception)
    await log_error(error_msg, tb)
    
    dev_id = 513546547
    dev_msg = (
        f"‼️ <b>ERROR</b> ‼️\n\n"
        f"<b>Msg:</b> {error_msg}\n\n"
        f"<code>{tb[:3800]}</code>"
    )
    
    try:
        await bot.send_message(dev_id, dev_msg, parse_mode="HTML")
    except:
        pass
    
    chat_id = None
    if event.update.message:
        chat_id = event.update.message.chat.id
    elif event.update.callback_query:
        chat_id = event.update.callback_query.message.chat.id
        
    if chat_id and chat_id != dev_id:
        user = await get_user(chat_id)
        lang = user.get('language', 'uk') if user else 'uk'
        
        if lang == 'uk':
            user_msg = (
                "💎 <b>Вибачте за незручності!</b>\n\n"
                "Виникла помилка. Ми вже працюємо над її усуненням. "
                "Будь ласка, спробуйте ще раз пізніше."
            )
        else:
            user_msg = (
                "💎 <b>Sorry for inconvenience!</b>\n\n"
                "An error occurred. We are already working on a fix. "
                "Please try again later."
            )
        try:
            await bot.send_message(chat_id, user_msg, parse_mode="HTML")
        except:
            pass
