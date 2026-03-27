from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, PreCheckoutQuery, LabeledPrice
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from app.databases.mongodb import upsert_user, get_user, get_apartments, get_apartment, create_booking, update_booking_status, get_booking, get_admins, get_all_admins_and_bosses, set_apartment_availability
from app.keyboards.all_keyboards import main_menu_kb, apartments_inline_kb, phone_kb, confirm_booking_inline_kb, booking_action_inline_kb, admin_panel_kb, user_reply_inline_kb, admin_reply_inline_kb, ap_info_inline_kb, info_only_apartment_kb
from app.utils.states import BookingStates, UserChatStates
from app.common.token import PAYMENT_TOKEN, MAIN_BOSS_ID
import datetime
import re

router = Router()

def parse_date(text):
    text = text.strip()
    try: return datetime.datetime.strptime(text, "%d.%m.%Y")
    except: pass
    try:
        dt = datetime.datetime.strptime(text, "%d.%m.%y")
        if dt.year < 2000: dt = dt.replace(year=dt.year + 2000)
        return dt
    except: return None

@router.message(CommandStart())
async def start_cmd(message: Message, state: FSMContext):
    await state.clear()
    role = "boss" if message.from_user.id == MAIN_BOSS_ID else "user"
    await upsert_user(message.from_user.id, message.from_user.username, role=role, name=message.from_user.full_name)
    user = await get_user(message.from_user.id)
    welcome_text = (
        f"✨ <b>Вітаємо у G.I.L Apartments!</b>\n\n"
        f"Ми дбаємо про ваш комфорт та пропонуємо найкращі умови для проживання в Ужгороді.\n\n"
        f"<b>Стандарти нашого сервісу:</b>\n"
        f"🕒 Заїзд: <b>з 12:00</b>\n"
        f"🕙 Виїзд: <b>до 10:00</b>\n\n"
        f"Оберіть бажаний розділ меню нижче."
    )
    await message.answer(welcome_text, reply_markup=main_menu_kb(user['role']), parse_mode="HTML")

@router.message(F.text == "🏨 Бронювання")
async def start_booking(message: Message, state: FSMContext):
    aps = await get_apartments()
    if not aps:
        await message.answer("⚠️ На даний момент апартаменти недоступні для бронювання.")
        return
    await message.answer("Оберіть апартаменти для бронювання:", reply_markup=apartments_inline_kb(aps, for_booking=True))
    await state.set_state(BookingStates.choosing_apartment)

@router.callback_query(F.data == "back_to_booking_list")
async def back_to_booking_list(callback: CallbackQuery, state: FSMContext):
    await start_booking(callback.message, state)
    await callback.answer()

@router.message(F.text == "📋 Список апартаментів")
async def list_apartments_direct(message: Message, state: FSMContext):
    aps = await get_apartments()
    if not aps:
        await message.answer("⚠️ Список апартаментів наразі порожній.")
        return
    await message.answer("🏢 <b>Наші об'єкти:</b>\nОберіть апартаменти для перегляду деталей:", reply_markup=apartments_inline_kb(aps, for_booking=False), parse_mode="HTML")
    await state.set_state(UserChatStates.viewing_apartments)

@router.callback_query(F.data == "back_to_list")
async def back_to_list(callback: CallbackQuery, state: FSMContext):
    await list_apartments_direct(callback.message, state)
    await callback.answer()

@router.callback_query(UserChatStates.viewing_apartments, F.data.startswith("ap_"))
async def show_ap_info(callback: CallbackQuery):
    ap_id = callback.data.split("_")[1]
    ap = await get_apartment(ap_id)
    if not ap:
        await callback.answer("⚠️ Об'єкт не знайдено.")
        return
    
    name = ap['title']['uk'] if isinstance(ap.get('title'), dict) else ap.get('name', 'Апартаменти')
    desc = ap['description']['uk'] if isinstance(ap.get('description'), dict) else ap.get('description', '-')
    
    info_msg = (
        f"🏨 <b>{name}</b>\n\n"
        f"📝 {desc}\n\n"
        f"🛏 <b>Кімнат:</b> {ap.get('rooms', '-')}\n"
        f"💤 <b>Спальних місць:</b> {ap.get('beds', '-')}\n"
        f"📐 <b>Площа:</b> {ap.get('area', '-')} м²\n"
        f"👥 <b>Місткість:</b> до {ap.get('guests', '-')} осіб\n\n"
        f"💰 <b>Вартість:</b> {ap['price']} грн/доба"
    )
    await callback.message.edit_text(info_msg, reply_markup=info_only_apartment_kb(ap.get('lat', 0), ap.get('lng', 0)), parse_mode="HTML")
    await callback.answer()

@router.callback_query(BookingStates.choosing_apartment, F.data.startswith("ap_"))
async def choose_ap(callback: CallbackQuery, state: FSMContext):
    ap_id = callback.data.split("_")[1]
    ap = await get_apartment(ap_id)
    if not ap:
        await callback.answer("⚠️ Об'єкт не знайдено.")
        return
    
    name = ap['title']['uk'] if isinstance(ap.get('title'), dict) else ap.get('name', 'Апартаменти')
    desc = ap['description']['uk'] if isinstance(ap.get('description'), dict) else ap.get('description', '-')

    info_msg = (
        f"🏨 <b>{name}</b>\n\n"
        f"📝 {desc}\n\n"
        f"🛏 <b>Кімнат:</b> {ap.get('rooms', '-')}\n"
        f"💤 <b>Спальних місць:</b> {ap.get('beds', '-')}\n"
        f"📐 <b>Площа:</b> {ap.get('area', '-')} м²\n"
        f"👥 <b>Місткість:</b> до {ap.get('guests', '-')} осіб\n\n"
        f"💰 <b>Вартість:</b> {ap['price']} грн/доба\n\n"
        f"Бажаєте забронювати цей об'єкт?"
    )
    
    await state.update_data(ap_id=ap_id, ap_name=name, price=ap['price'])
    await callback.message.edit_text(info_msg, reply_markup=confirm_booking_inline_kb(ap.get('lat', 0), ap.get('lng', 0), ap_id), parse_mode="HTML")
    await callback.answer()

@router.message(F.text == "📊 Адмін-панель")
async def admin_panel_direct(message: Message):
    user = await get_user(message.from_user.id)
    if user and user.get('role') in ['admin', 'boss']:
        await message.answer("📊 <b>Панель управління:</b>", reply_markup=admin_panel_kb(user['role']), parse_mode="HTML")
    else:
        await message.answer("❌ У вас немає прав доступу до цього розділу.")

@router.callback_query(F.data.startswith("start_book_"))
async def start_book_process(callback: CallbackQuery, state: FSMContext):
    user = await get_user(callback.from_user.id)
    tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).strftime("%d.%m.%Y")
    
    if user.get('phone'):
        await state.update_data(phone=user['phone'])
        await callback.message.answer(f"Вкажіть дату <b>ЗАЇЗДУ</b> (у форматі ДД.ММ.РРРР, мінімум з {tomorrow}):", parse_mode="HTML")
        await state.set_state(BookingStates.waiting_checkin)
    else:
        await callback.message.answer("Для оформлення бронювання, будь ласка, надайте ваш номер телефону:", reply_markup=phone_kb())
        await state.set_state(BookingStates.entering_phone)
    await callback.answer()

@router.message(BookingStates.entering_phone, F.contact)
@router.message(BookingStates.entering_phone, F.text)
async def phone_input(message: Message, state: FSMContext):
    phone = message.contact.phone_number if message.contact else message.text
    if not re.match(r"^\+?380\d{9}$", phone):
        await message.answer("❌ Будь ласка, введіть коректний номер телефону (+380XXXXXXXXX)")
        return
    await state.update_data(phone=phone)
    await upsert_user(message.from_user.id, phone=phone)
    tomorrow = (datetime.date.today() + datetime.timedelta(days=1)).strftime("%d.%m.%Y")
    await message.answer(f"✅ Номер збережено. Тепер вкажіть дату <b>ЗАЇЗДУ</b> (мінімум з {tomorrow}):", reply_markup=main_menu_kb(), parse_mode="HTML")
    await state.set_state(BookingStates.waiting_checkin)

@router.message(BookingStates.waiting_checkin)
async def checkin_input(message: Message, state: FSMContext):
    dt = parse_date(message.text)
    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days=1)
    max_date = today + datetime.timedelta(days=120)
    
    if not dt:
        await message.answer("⚠️ Будь ласка, введіть дату у форматі ДД.ММ.РРРР (наприклад, 27.03.2026)")
        return
    
    if dt.date() < tomorrow:
        await message.answer(f"❌ Бронювання можливе лише з завтрашнього дня ({tomorrow.strftime('%d.%m.%Y')})")
        return
        
    if dt.date() > max_date:
        await message.answer(f"❌ Ви можете забронювати апартаменти максимум на 4 місяці вперед ({max_date.strftime('%d.%m.%Y')})")
        return
        
    await state.update_data(checkin=dt, checkin_str=dt.strftime("%d.%m.%Y"))
    next_day = (dt + datetime.timedelta(days=1)).strftime("%d.%m.%Y")
    await message.answer(f"Чудово. Тепер вкажіть дату <b>ВИЇЗДУ</b> (мінімум {next_day}):", parse_mode="HTML")
    await state.set_state(BookingStates.waiting_checkout)

@router.message(BookingStates.waiting_checkout)
async def checkout_input(message: Message, state: FSMContext):
    dt = parse_date(message.text)
    data = await state.get_data()
    
    if not dt:
        await message.answer("⚠️ Будь ласка, введіть дату виїзду у форматі ДД.ММ.РРРР")
        return

    if dt <= data['checkin']:
        await message.answer("❌ Дата виїзду має бути пізніше за дату заїзду. Спробуйте ще раз:")
        return
        
    days = (dt - data['checkin']).days
    if days > 31:
        await message.answer("❌ Максимальний термін перебування за одне бронювання — 31 день.")
        return
        
    await state.update_data(checkout_str=dt.strftime("%d.%m.%Y"), days=days)
    await message.answer(f"Термін перебування: <b>{days} діб</b>. Бажаєте додати особливі побажання? (Напишіть їх одним повідомленням або вкажіть 'ні')", parse_mode="HTML")
    await state.set_state(BookingStates.entering_wishes)

@router.message(BookingStates.entering_wishes)
async def wishes_input(message: Message, state: FSMContext):
    data = await state.get_data()
    total = data['price'] * data['days']
    prepayment = total * 0.5
    remaining = total * 0.5
    
    wishes = message.text if message.text.lower() != 'ні' else "Немає"
    b_id = await create_booking(message.from_user.id, data['ap_id'], data['checkin_str'], data['checkout_str'], data['phone'], wishes, total)
    
    confirm_msg = (
        f"🧾 <b>Ваше бронювання сформовано:</b>\n\n"
        f"🏠 <b>{data['ap_name']}</b>\n"
        f"📅 <b>Період:</b> {data['checkin_str']} — {data['checkout_str']} ({data['days']} діб)\n"
        f"🕒 <b>Заїзд:</b> 12:00 | 🕙 <b>Виїзд:</b> 10:00\n"
        f"💎 <b>Загальна вартість:</b> {total} грн\n\n"
        f"💳 <b>До оплати зараз (50%):</b> <b>{prepayment} грн</b>\n"
        f"💳 <b>Залишок (в день заїзду):</b> <b>{remaining} грн</b>\n\n"
        f"<i>Для завершення бронювання внесіть передплату через платіжну систему:</i>"
    )
    
    ap = await get_apartment(data['ap_id'])
    await message.answer(confirm_msg, reply_markup=ap_info_inline_kb(ap['lat'], ap['lng'], b_id), parse_mode="HTML")
    await state.clear()

@router.callback_query(F.data.startswith("pay50_"))
async def pay_50(callback: CallbackQuery, bot: Bot):
    b = await get_booking(callback.data.split("_")[-1])
    if not b:
        await callback.answer("⚠️ Помилка: бронювання не знайдено.")
        return
        
    amount = int(b['prepayment'] * 100) if not callback.data.startswith("pay50_final_") else int(b['remaining'] * 100)
    title = "Передплата 50%" if not callback.data.startswith("pay50_final_") else "Залишок 50%"
    
    await bot.send_invoice(
        chat_id=callback.from_user.id, title=f"G.I.L Apartments: {title}", description=f"Бронювання {b['start_date']}-{b['end_date']}",
        payload=callback.data, provider_token=PAYMENT_TOKEN, currency="UAH",
        prices=[LabeledPrice(label=title, amount=amount)]
    )
    await callback.answer()

@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await query.answer(ok=True)

@router.message(F.successful_payment)
async def success_pay(message: Message, bot: Bot):
    payload = message.successful_payment.invoice_payload
    b_id = payload.split("_")[-1]
    b = await get_booking(b_id)
    if not b: return

    if "pay50_" in payload and "final" not in payload:
        await update_booking_status(b_id, "paid_50")
        await set_apartment_availability(b['ap_id'], False)
        await message.answer("✅ <b>Оплату отримано успішно!</b>\n\nВаші апартаменти заброньовано. Ми зв'яжемося з вами ближче до дати заїзду.", parse_mode="HTML")
        admins = await get_admins()
        for a in admins:
            try: await bot.send_message(a['user_id'], f"🆕 <b>Оплачено 50%!</b>\nОб'єкт: {b.get('ap_name', 'Апартаменти')}\nПеріод: {b['start_date']} - {b['end_date']}", parse_mode="HTML", reply_markup=booking_action_inline_kb(b_id))
            except: pass
    elif "pay50_final" in payload:
        await update_booking_status(b_id, "completed")
        await message.answer("✅ <b>Оплату залишку отримано!</b>\n\nЛаскаво просимо до G.I.L Apartments! Приємного відпочинку.", parse_mode="HTML")

@router.callback_query(F.data == "user_answer_admin")
async def user_answer_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Будь ласка, введіть ваше повідомлення для адміністрації:")
    await state.set_state(UserChatStates.writing_to_admin)
    await callback.answer()

@router.message(UserChatStates.writing_to_admin)
async def global_chat_handler(message: Message, state: FSMContext, bot: Bot):
    admins = await get_admins()
    for a in admins:
        try:
            await bot.send_message(
                a['user_id'], 
                f"✉️ <b>Повідомлення від гостя (ID: {message.from_user.id}):</b>\n\n{message.text}",
                parse_mode="HTML",
                reply_markup=admin_reply_inline_kb(message.from_user.id)
            )
        except: pass
    await message.answer("✅ Ваше повідомлення надіслано адміністратору.")
    await state.clear()

@router.message(F.text == "⬅️ На головну")
async def back_menu(message: Message):
    u = await get_user(message.from_user.id)
    await message.answer("Повертаємось у головне меню:", reply_markup=main_menu_kb(u['role']))
