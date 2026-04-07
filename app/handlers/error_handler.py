from aiogram import Bot, Router
from aiogram.types import ErrorEvent
import html
import traceback

from app.common.token import BOSS_IDS
from app.databases.mongodb import get_user, log_error


router = Router()


@router.error()
async def error_handler(event: ErrorEvent, bot: Bot):
    tb_text = "".join(
        traceback.format_exception(None, event.exception, event.exception.__traceback__)
    )
    error_msg = str(event.exception)
    await log_error(error_msg, tb_text)

    dev_msg = (
        "🚨 <b>CRITICAL ERROR REPORT</b> 🚨\n\n"
        f"❌ <b>Error:</b> <code>{html.escape(error_msg)}</code>\n\n"
        f"📋 <b>Traceback:</b>\n<code>{html.escape(tb_text[:3500])}</code>"
    )

    for boss_id in BOSS_IDS:
        try:
            await bot.send_message(boss_id, dev_msg, parse_mode="HTML")
        except Exception:
            pass

    chat_id = None
    if event.update.message:
        chat_id = event.update.message.chat.id
    elif event.update.callback_query and event.update.callback_query.message:
        chat_id = event.update.callback_query.message.chat.id

    if not chat_id or chat_id in BOSS_IDS:
        return

    user = await get_user(chat_id)
    lang = user.get("language", "uk") if user else "uk"
    user_msg = (
        "🙏 <b>Вибачте за незручності!</b>\n\n"
        "Виникла технічна помилка. Власник вже отримав детальний звіт та працює над виправленням."
        if lang == "uk"
        else "🙏 <b>Sorry for inconvenience!</b>\n\n"
        "An error occurred. The owner has received a detailed report and is working on a fix."
    )

    try:
        await bot.send_message(chat_id, user_msg, parse_mode="HTML")
    except Exception:
        pass
