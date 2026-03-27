from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, PreCheckoutQuery, LabeledPrice
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from app.databases.mongodb import upsert_user, get_user, get_apartments, get_apartment, create_booking, update_booking_status, get_booking, get_admins, get_all_admins_and_bosses, set_apartment_availability, update_user_pref
from app.keyboards.all_keyboards import main_menu_kb, apartments_inline_kb, phone_kb, confirm_booking_inline_kb, booking_action_inline_kb, admin_panel_kb, user_reply_inline_kb, admin_reply_inline_kb, ap_info_inline_kb, info_only_apartment_kb, language_kb, currency_kb, settings_kb
from app.utils.states import BookingStates, UserChatStates, SetupStates
from app.common.token import PAYMENT_TOKEN, BOSS_IDS
from app.utils.currency import get_usd_rate, format_price
import datetime
import re

router = Router()

def parse_date(text):
    text = text.strip().replace('/', '.').replace('-', '.').replace(' ', '.')
    parts = text.split('.')
    if len(parts) != 3: return None
    try:
        d, m, y = int(parts[0]), int(parts[1]), int(parts[2])
        if y < 100: y += 2000
        return datetime.datetime(y, m, d)
    except: return None

@router.message(CommandStart())
async def start_cmd(message: Message, state: FSMContext):
    await state.clear()
    user = await get_user(message.from_user.id)
    role = "boss" if message.from_user.id in BOSS_IDS else (user.get("role", "user") if user else "user")
    if not user:
        await upsert_user(message.from_user.id, message.from_user.username, role=role, name=message.from_user.full_name)
        user = await get_user(message.from_user.id)
    elif user.get("role") != role:
        await update_user_pref(message.from_user.id, role=role)
        user["role"] = role
    if not user.get("language"):
        l = message.from_user.language_code
        lang = "uk" if l in ["uk", "ru"] else "en"
        await update_user_pref(message.from_user.id, language=lang)
        user = await get_user(message.from_user.id)
    if not user.get("currency"):
        msg = "Оберіть валюту:" if user['language'] == 'uk' else "Choose currency:"
        await message.answer(msg, reply_markup=currency_kb())
        await state.set_state(SetupStates.choosing_currency)
        return
        
    if user['language'] == 'uk':
        msg = (
            "✨ <b>Вітаємо у G.I.L Apartments!</b>\n\n"
            "Ми надаємо найкращі апартаменти для вашого комфортного відпочинку. "
            "За допомогою цього бота ви можете швидко забронювати житло, "
            "керувати своїми замовленнями та зв'язатися з нашою підтримкою.\n\n"
            "Оберіть потрібний розділ меню нижче: 👇"
        )
    else:
        msg = (
            "✨ <b>Welcome to G.I.L Apartments!</b>\n\n"
            "We provide the best apartments for your comfortable stay. "
            "With this bot, you can quickly book accommodation, "
            "manage your orders, and contact our support.\n\n"
            "Choose the required menu section below: 👇"
        )
    await message.answer(msg, reply_markup=main_menu_kb(user['role'], lang=user['language']), parse_mode="HTML")

@router.callback_query(SetupStates.choosing_language, F.data.startswith("set_lang_"))
async def set_language(callback: CallbackQuery, state: FSMContext):
    lang = callback.data.split("_")[-1]
    await update_user_pref(callback.from_user.id, language=lang)
    user = await get_user(callback.from_user.id)
    if not user.get("currency"):
        msg = "Мову встановлено! Тепер оберіть зручну валюту для відображення цін:" if lang == 'uk' else "Language set! Now choose your preferred currency for prices:"
        await callback.message.edit_text(msg, reply_markup=currency_kb())
        await state.set_state(SetupStates.choosing_currency)
    else:
        await callback.answer()
        await show_profile_internal(callback.message, callback.from_user.id)
        await state.clear()
    await callback.answer()

@router.callback_query(SetupStates.choosing_currency, F.data.startswith("set_curr_"))
async def set_currency(callback: CallbackQuery, state: FSMContext):
    curr = callback.data.split("_")[-1]
    await update_user_pref(callback.from_user.id, currency=curr)
    user = await get_user(callback.from_user.id)
    msg = "Налаштування збережено!" if user['language'] == 'uk' else "Settings saved!"
    await callback.message.edit_text(msg)
    await callback.message.answer(msg, reply_markup=main_menu_kb(user['role'], lang=user['language']))
    await state.clear()
    await callback.answer()

async def show_profile_internal(message: Message, user_id: int):
    u = await get_user(user_id)
    lang = u.get('language', 'uk')
    text = (f"👤 <b>Ваш профіль:</b>\n\nID: <code>{u['user_id']}</code>\nІм'я: {u.get('name', '-')}\nМова: Українська\nВалюта: {u.get('currency', 'uah').upper()}" if lang == 'uk' else f"👤 <b>Your Profile:</b>\n\nID: <code>{u['user_id']}</code>\nName: {u.get('name', '-')}\nLanguage: English\nCurrency: {u.get('currency', 'uah').upper()}")
    await message.answer(text, reply_markup=settings_kb(lang=lang), parse_mode="HTML")

@router.message(F.text == "👤 Профіль")
@router.message(F.text == "👤 Profile")
async def show_profile(message: Message):
    await show_profile_internal(message, message.from_user.id)

@router.callback_query(F.data == "change_lang")
async def change_lang_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Оберіть мову / Choose language:", reply_markup=language_kb())
    await state.set_state(SetupStates.choosing_language)
    await callback.answer()

@router.callback_query(F.data == "change_curr")
async def change_curr_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text("Оберіть валюту / Choose currency:", reply_markup=currency_kb())
    await state.set_state(SetupStates.choosing_currency)
    await callback.answer()

@router.message(F.text == "🏨 Бронювання")
@router.message(F.text == "🏨 Booking")
async def start_booking(message: Message, state: FSMContext):
    u = await get_user(message.from_user.id)
    aps = await get_apartments(only_available=True)
    if not aps:
        await message.answer("⚠️ На жаль, зараз немає вільних апартаментів для бронювання." if u['language'] == 'uk' else "⚠️ Sorry, there are currently no available apartments for booking.")
        return
    await message.answer("Будь ласка, оберіть об'єкт, який вас зацікавив:" if u['language'] == 'uk' else "Please choose the object you are interested in:", reply_markup=apartments_inline_kb(aps, True, u['language']))
    await state.set_state(BookingStates.choosing_apartment)

@router.message(F.text == "📋 Список апартаментів")
@router.message(F.text == "📋 Apartment List")
async def list_apartments_direct(message: Message, state: FSMContext):
    u = await get_user(message.from_user.id)
    aps = await get_apartments(only_available=True)
    if not aps:
        await message.answer("⚠️ Список об'єктів наразі порожній." if u['language'] == 'uk' else "⚠️ The list of objects is currently empty.")
        return
    await message.answer("🏢 <b>Наші апартаменти:</b>\n\nОберіть об'єкт для перегляду детальної інформації:" if u['language'] == 'uk' else "🏢 <b>Our apartments:</b>\n\nChoose an object to view detailed information:", reply_markup=apartments_inline_kb(aps, False, u['language']), parse_mode="HTML")
    await state.set_state(UserChatStates.viewing_apartments)

@router.callback_query(UserChatStates.viewing_apartments, F.data.startswith("ap_"))
async def show_ap_info(callback: CallbackQuery):
    ap = await get_apartment(callback.data.split("_")[1])
    u = await get_user(callback.from_user.id)
    if not ap: return
    p = format_price(ap['price'], await get_usd_rate(), u.get('currency', 'uah'))
    msg = (f"🏨 <b>{ap['title'].get(u['language'], ap.get('name'))}</b>\n\n{ap['description'].get(u['language'], '-')}\n\n💰 <b>Ціна:</b> {p}" if u['language'] == 'uk' else f"🏨 <b>{ap['title'].get(u['language'], ap.get('name'))}</b>\n\n{ap['description'].get(u['language'], '-')}\n\n💰 <b>Price:</b> {p}")
    await callback.message.edit_text(msg, reply_markup=info_only_apartment_kb(ap['lat'], ap['lng'], u['language']), parse_mode="HTML")
    await callback.answer()

@router.callback_query(BookingStates.choosing_apartment, F.data.startswith("ap_"))
async def choose_ap(callback: CallbackQuery, state: FSMContext):
    ap = await get_apartment(callback.data.split("_")[1])
    u = await get_user(callback.from_user.id)
    if not ap: return
    await state.update_data(ap_id=str(ap['_id']), ap_name=ap['title'].get(u['language'], ap.get('name')), price=ap['price'])
    st = "📝 <b>Правила проживання:</b>\n🕒 Заїзд: з 12:00\n🕙 Виїзд: до 10:00\n\n" if u['language'] == 'uk' else "📝 <b>House rules:</b>\n🕒 Check-in: from 12:00\n🕙 Check-out: until 10:00\n\n"
    tom = (datetime.date.today() + datetime.timedelta(days=1)).strftime("%d.%m.%Y")
    if u.get('phone'):
        await state.update_data(phone=u['phone'])
        await callback.message.answer(st + (f"Вкажіть дату <b>ЗАЇЗДУ</b> (наприклад, {tom}):" if u['language'] == 'uk' else f"Specify the <b>CHECK-IN</b> date (e.g., {tom}):"), parse_mode="HTML")
        await state.set_state(BookingStates.waiting_checkin)
    else:
        await callback.message.answer(st + ("Для продовження нам потрібен ваш номер телефону:" if u['language'] == 'uk' else "To continue, we need your phone number:"), reply_markup=phone_kb(u['language']), parse_mode="HTML")
        await state.set_state(BookingStates.entering_phone)
    await callback.answer()

@router.message(BookingStates.entering_phone, F.contact)
@router.message(BookingStates.entering_phone, F.text)
async def phone_input(message: Message, state: FSMContext):
    p = message.contact.phone_number if message.contact else message.text
    p = "".join(filter(str.isdigit, p))
    if not p.startswith('+'): p = '+' + p
    if len(p) < 8: return
    await upsert_user(message.from_user.id, phone=p)
    await state.update_data(phone=p)
    u = await get_user(message.from_user.id)
    tom = (datetime.date.today() + datetime.timedelta(days=1)).strftime("%d.%m.%Y")
    await message.answer(f"Номер збережено. Тепер вкажіть дату <b>ЗАЇЗДУ</b> (наприклад, {tom}):" if u.get('language') == 'uk' else f"Number saved. Now specify the <b>CHECK-IN</b> date (e.g., {tom}):", reply_markup=main_menu_kb(u['role'], u['language']), parse_mode="HTML")
    await state.set_state(BookingStates.waiting_checkin)

@router.message(BookingStates.waiting_checkin)
async def checkin_input(message: Message, state: FSMContext):
    dt = parse_date(message.text)
    if not dt or dt.date() < datetime.date.today(): return
    await state.update_data(checkin=dt, checkin_str=dt.strftime("%d.%m.%Y"))
    u = await get_user(message.from_user.id)
    await message.answer("Чудово. Тепер вкажіть дату <b>ВИЇЗДУ</b>:" if u['language'] == 'uk' else "Great. Now specify the <b>CHECK-OUT</b> date:", parse_mode="HTML")
    await state.set_state(BookingStates.waiting_checkout)

@router.message(BookingStates.waiting_checkout)
async def checkout_input(message: Message, state: FSMContext):
    dt = parse_date(message.text)
    data = await state.get_data()
    if not dt or dt <= data['checkin']: return
    await state.update_data(checkout_str=dt.strftime("%d.%m.%Y"), days=(dt - data['checkin']).days)
    u = await get_user(message.from_user.id)
    await message.answer("Чи маєте ви особливі побажання? (якщо ні, просто напишіть 'ні')" if u['language'] == 'uk' else "Do you have any special wishes? (if not, just write 'no')")
    await state.set_state(BookingStates.entering_wishes)

@router.message(BookingStates.entering_wishes)
async def wishes_input(message: Message, state: FSMContext):
    data = await state.get_data()
    u = await get_user(message.from_user.id)
    w = message.text if message.text.lower() not in ['ні', 'no'] else "-"
    b_id = await create_booking(u['user_id'], data['ap_id'], data['checkin_str'], data['checkout_str'], data['phone'], w, data['price']*data['days'])
    p = format_price(data['price']*data['days']*0.5, await get_usd_rate(), u.get('currency', 'uah'))
    
    if u['language'] == 'uk':
        msg = (
            f"🧾 <b>Ваше замовлення сформовано!</b>\n\n"
            f"🏠 <b>Об'єкт:</b> {data['ap_name']}\n"
            f"📅 <b>Дати:</b> {data['checkin_str']} — {data['checkout_str']}\n"
            f"💰 <b>Передплата (50%):</b> {p}\n\n"
            f"ℹ️ <b>Як це працює?</b>\n"
            f"1. Ви оплачуєте 50% зараз, щоб ми миттєво зняли об'єкт з продажу та закріпили його за вами (гарантія броні).\n"
            f"2. Решту 50% ви оплачуєте в день заїзду безпосередньо через цей бот.\n\n"
            f"Натисніть кнопку нижче, щоб перейти до оплати: 👇"
        )
    else:
        msg = (
            f"🧾 <b>Your order has been created!</b>\n\n"
            f"🏠 <b>Object:</b> {data['ap_name']}\n"
            f"📅 <b>Dates:</b> {data['checkin_str']} — {data['checkout_str']}\n"
            f"💰 <b>Prepayment (50%):</b> {p}\n\n"
            f"ℹ️ <b>How it works?</b>\n"
            f"1. You pay 50% now so we can instantly take the object off sale and secure it for you (booking guarantee).\n"
            f"2. You pay the remaining 50% on your check-in day directly via this bot.\n\n"
            f"Click the button below to proceed to payment: 👇"
        )
        
    ap = await get_apartment(data['ap_id'])
    await message.answer(msg, reply_markup=ap_info_inline_kb(ap['lat'], ap['lng'], b_id, u['language']), parse_mode="HTML")
    await state.clear()

@router.callback_query(F.data.startswith("pay50_"))
async def pay_50(callback: CallbackQuery, bot: Bot):
    b = await get_booking(callback.data.split("_")[-1])
    if not b: return
    
    u = await get_user(callback.from_user.id)
    lang = u.get('language', 'uk') if u else 'uk'
    
    if not PAYMENT_TOKEN:
        await callback.answer("⚠️ Помилка конфігурації платежів.", show_alert=True)
        return

    amount = int(b['prepayment'] * 100)
    if "final" in callback.data:
        amount = int(b.get('remaining', b['total_price'] * 0.5) * 100)
    
    title = "G.I.L Apartments"
    description = "Передплата 50% для гарантії броні" if lang == 'uk' else "50% Prepayment for booking guarantee"
    if "final" in callback.data:
        description = "Фінальна оплата 50% (день заїзду)" if lang == 'uk' else "Final 50% payment (check-in day)"

    try:
        await bot.send_invoice(
            chat_id=callback.from_user.id,
            title=title,
            description=description,
            payload=callback.data,
            provider_token=PAYMENT_TOKEN,
            currency="UAH",
            prices=[LabeledPrice(label="До сплати" if lang == 'uk' else "To pay", amount=amount)],
            need_phone_number=True,
            send_phone_number_to_provider=True,
            is_flexible=False
        )
        await callback.answer()
    except Exception as e:
        await callback.answer(f"Error: {str(e)[:50]}", show_alert=True)

@router.pre_checkout_query()
async def pre_checkout(q: PreCheckoutQuery):
    await q.answer(ok=True)

@router.message(F.successful_payment)
async def success_pay(message: Message, bot: Bot):
    b_id = message.successful_payment.invoice_payload.split("_")[-1]
    b = await get_booking(b_id)
    if not b: return
    
    u = await get_user(message.from_user.id)
    lang = u.get('language', 'uk') if u else 'uk'

    if "pay50_" in message.successful_payment.invoice_payload and "final" not in message.successful_payment.invoice_payload:
        await update_booking_status(b_id, "paid_50")
        await set_apartment_availability(str(b['ap_id']), False)
        
        success_msg = (
            "🎉 <b>Вітаємо! Передплату отримано.</b>\n\n"
            "Ми забронювали цей об'єкт спеціально для вас. Нагадування про фінальну оплату та деталі заїзду прийдуть вранці у день вашого візиту.\n\n"
            "Дякуємо, що обрали G.I.L Apartments!"
            if lang == 'uk' else
            "🎉 <b>Success! Prepayment received.</b>\n\n"
            "We have secured this object specifically for you. A reminder for the final payment and check-in details will arrive on the morning of your visit.\n\n"
            "Thank you for choosing G.I.L Apartments!"
        )
        await message.answer(success_msg, parse_mode="HTML")
        
        for a in await get_all_admins_and_bosses():
            try:
                al = a.get('language', 'uk')
                await bot.send_message(a['user_id'], f"🆕 Guest paid 50%!" if al == 'en' else f"🆕 Гість оплатив 50%!", reply_markup=booking_action_inline_kb(b_id, al, "paid_50"))
            except: pass
    elif "pay50_final" in message.successful_payment.invoice_payload:
        await update_booking_status(b_id, "completed")
        
        final_msg = (
            "✅ <b>Оплату завершено!</b>\n\n"
            "Ми раді вітати вас у нашому апартаменті. Бажаємо приємного відпочинку та комфортного проживання!\n\n"
            "Якщо у вас виникнуть запитання, ми завжди на зв'язку."
            if lang == 'uk' else
            "✅ <b>Payment completed!</b>\n\n"
            "We are happy to welcome you to our apartment. We wish you a pleasant stay and a comfortable experience!\n\n"
            "If you have any questions, we are always here to help."
        )
        await message.answer(final_msg, parse_mode="HTML")
        
        for a in await get_all_admins_and_bosses():
            try:
                al = a.get('language', 'uk')
                await bot.send_message(a['user_id'], f"✅ Full Payment received!" if al == 'en' else f"✅ Отримано повну оплату!", reply_markup=booking_action_inline_kb(b_id, al, "completed"))
            except: pass

@router.callback_query(F.data == "user_answer_admin")
async def user_answer_start(callback: CallbackQuery, state: FSMContext):
    u = await get_user(callback.from_user.id)
    await callback.message.answer("Будь ласка, введіть ваше повідомлення адміністратору:" if u['language'] == 'uk' else "Please enter your message to the admin:")
    await state.set_state(UserChatStates.writing_to_admin)
    await callback.answer()

@router.message(UserChatStates.writing_to_admin)
async def global_chat_handler(message: Message, state: FSMContext, bot: Bot):
    u = await get_user(message.from_user.id)
    for a in await get_all_admins_and_bosses():
        try:
            al = a.get('language', 'uk')
            await bot.send_message(a['user_id'], f"✉️ Guest {u['user_id']}:\n{message.text}", reply_markup=admin_reply_inline_kb(u['user_id'], al))
        except: pass
    await message.answer("Ваше повідомлення надіслано. Ми відповімо вам найближчим часом." if u['language'] == 'uk' else "Your message has been sent. We will reply to you as soon as possible.")
    await state.clear()

@router.message(F.text == "📊 Адмін-панель")
@router.message(F.text == "📊 Admin Panel")
async def admin_panel_direct(message: Message):
    u = await get_user(message.from_user.id)
    if u and u.get('role') in ['admin', 'boss']:
        lang = u.get('language', 'uk')
        msg = "📊 <b>Панель управління:</b>" if lang == 'uk' else "📊 <b>Admin Panel:</b>"
        await message.answer(msg, reply_markup=admin_panel_kb(u['role'], lang), parse_mode="HTML")

@router.message(F.text == "⬅️ На головну")
@router.message(F.text == "⬅️ To Main Menu")
async def back_menu(message: Message):
    u = await get_user(message.from_user.id)
    await message.answer("Повертаємось до головного меню:" if u['language'] == 'uk' else "Returning to main menu:", reply_markup=main_menu_kb(u['role'], u['language']))
