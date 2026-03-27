from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, LabeledPrice
from aiogram.fsm.context import FSMContext
from app.databases.mongodb import get_user, get_apartments, add_apartment, delete_apartment, get_apartment, set_apartment_availability, get_booking, update_booking_status, set_user_role, get_user_by_query, get_active_bookings, get_all_admins_and_bosses, update_user_pref
from app.keyboards.all_keyboards import admin_panel_kb, apartment_mgmt_inline_kb, apartment_item_mgmt_kb, staff_mgmt_inline_kb, booking_action_inline_kb, user_reply_inline_kb, staff_delete_inline_kb, admin_reply_inline_kb, confirm_ap_add_kb
from app.utils.states import AdminStates
from app.common.token import PAYMENT_TOKEN, MAIN_BOSS_ID
from app.utils.currency import get_usd_rate, format_price

router = Router()

@router.message(F.text == "📅 Активні бронювання")
@router.message(F.text == "📅 Active Bookings")
async def view_active_bookings(message: Message):
    u = await get_user(message.from_user.id)
    if u and u.get('role') in ['admin', 'boss']:
        lang = u.get('language', 'uk')
        bookings = await get_active_bookings()
        if not bookings:
            msg = "Наразі активних бронювань немає." if lang == 'uk' else "There are no active bookings."
            await message.answer(msg)
            return
        for b in bookings:
            ap = await get_apartment(b['ap_id'])
            name = ap['title'][lang] if ap and isinstance(ap.get('title'), dict) and lang in ap['title'] else (ap.get('name', 'Apartments') if ap else "⚠️ Removed")
            status_text = ("💳 Очікує 50%" if b['status'] == "paid_50" else "✅ Підтверджено") if lang == 'uk' else ("💳 Awaiting 50%" if b['status'] == "paid_50" else "✅ Confirmed")
            rate = await get_usd_rate()
            price_text = format_price(b['total_price'], rate, u.get('currency', 'uah'))
            msg = (f"🔖 <b>ID:</b> <code>{str(b['_id'])}</code>\n🏠 <b>Об'єкт:</b> {name}\n📅 <b>Період:</b> {b['start_date']} — {b['end_date']}\n👤 <b>ID гостя:</b> <code>{b['user_id']}</code>\n📞 <b>Контакт:</b> {b['phone']}\n💰 <b>Сума:</b> {price_text}\n⚙️ <b>Статус:</b> {status_text}") if lang == 'uk' else (f"🔖 <b>ID:</b> <code>{str(b['_id'])}</code>\n🏠 <b>Object:</b> {name}\n📅 <b>Period:</b> {b['start_date']} — {b['end_date']}\n👤 <b>Guest ID:</b> <code>{b['user_id']}</code>\n📞 <b>Contact:</b> {b['phone']}\n💰 <b>Total:</b> {price_text}\n⚙️ <b>Status:</b> {status_text}")
            await message.answer(msg, reply_markup=booking_action_inline_kb(str(b['_id']), lang=lang, status=b['status']), parse_mode="HTML")

@router.message(F.text == "🏢 Об'єкти")
@router.message(F.text == "🏢 Objects")
async def admin_aps(message: Message):
    u = await get_user(message.from_user.id)
    if u and u.get('role') in ['admin', 'boss']:
        aps = await get_apartments()
        lang = u.get('language', 'uk')
        msg = "🏢 <b>Управління об'єктами:</b>" if lang == 'uk' else "🏢 <b>Object management:</b>"
        await message.answer(msg, reply_markup=apartment_mgmt_inline_kb(aps, lang=lang), parse_mode="HTML")

@router.callback_query(F.data.startswith("manage_ap_"))
async def manage_ap_item(callback: CallbackQuery):
    u = await get_user(callback.from_user.id)
    lang = u.get('language', 'uk')
    ap_id = callback.data.split("_")[2]
    ap = await get_apartment(ap_id)
    if not ap:
        await callback.answer()
        return
    name = ap['title'][lang] if isinstance(ap.get('title'), dict) and lang in ap['title'] else ap.get('name', 'Apartments')
    status = ("🟢 Доступний" if ap['is_available'] else "🔴 Заблокований") if lang == 'uk' else ("🟢 Available" if ap['is_available'] else "🔴 Blocked")
    text = (f"<b>Редагування:</b> {name}\n<b>Статус:</b> {status}") if lang == 'uk' else (f"<b>Editing:</b> {name}\n<b>Status:</b> {status}")
    await callback.message.edit_text(text, reply_markup=apartment_item_mgmt_kb(ap_id, ap['is_available'], lang=lang), parse_mode="HTML")

@router.callback_query(F.data.startswith("toggle_ap_"))
async def toggle_ap(callback: CallbackQuery):
    ap_id = callback.data.split("_")[2]
    ap = await get_apartment(ap_id)
    if ap:
        await set_apartment_availability(ap_id, not ap['is_available'])
        await callback.answer()
    await manage_ap_item(callback)

@router.callback_query(F.data.startswith("delete_ap_"))
async def del_ap(callback: CallbackQuery):
    await delete_apartment(callback.data.split("_")[2])
    await callback.answer()
    await admin_aps(callback.message)

@router.callback_query(F.data == "admin_apartments_back")
async def ap_back(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await admin_aps(callback.message)

@router.callback_query(F.data == "add_ap")
async def add_ap_start(callback: CallbackQuery, state: FSMContext):
    u = await get_user(callback.from_user.id)
    await callback.message.answer("Адреса (назва):" if u.get('language') == 'uk' else "Address (name):")
    await state.set_state(AdminStates.adding_apartment_name)
    await callback.answer()

@router.message(AdminStates.adding_apartment_name)
async def add_ap_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Опис:")
    await state.set_state(AdminStates.adding_apartment_desc)

@router.message(AdminStates.adding_apartment_desc)
async def add_ap_desc(message: Message, state: FSMContext):
    await state.update_data(desc=message.text)
    await message.answer("Кількість кімнат:")
    await state.set_state(AdminStates.adding_apartment_rooms)

@router.message(AdminStates.adding_apartment_rooms)
async def add_ap_rooms(message: Message, state: FSMContext):
    if not message.text.isdigit(): return
    await state.update_data(rooms=message.text)
    await message.answer("Ліжок:")
    await state.set_state(AdminStates.adding_apartment_beds)

@router.message(AdminStates.adding_apartment_beds)
async def add_ap_beds(message: Message, state: FSMContext):
    if not message.text.isdigit(): return
    await state.update_data(beds=message.text)
    await message.answer("Площа:")
    await state.set_state(AdminStates.adding_apartment_area)

@router.message(AdminStates.adding_apartment_area)
async def add_ap_area(message: Message, state: FSMContext):
    try:
        await state.update_data(area=float(message.text.replace(',', '.')))
        await message.answer("Максимальна кількість осіб:")
        await state.set_state(AdminStates.adding_apartment_guests)
    except: pass

@router.message(AdminStates.adding_apartment_guests)
async def add_ap_guests(message: Message, state: FSMContext):
    if not message.text.isdigit(): return
    await state.update_data(guests=message.text)
    await message.answer("Latitude (або 0):")
    await state.set_state(AdminStates.adding_apartment_lat)

@router.message(AdminStates.adding_apartment_lat)
async def add_ap_lat(message: Message, state: FSMContext):
    try:
        await state.update_data(lat=float(message.text.replace(',', '.')))
        await message.answer("Longitude (або 0):")
        await state.set_state(AdminStates.adding_apartment_lng)
    except: pass

@router.message(AdminStates.adding_apartment_lng)
async def add_ap_lng(message: Message, state: FSMContext):
    try:
        await state.update_data(lng=float(message.text.replace(',', '.')))
        await message.answer("Ціна за добу (грн):")
        await state.set_state(AdminStates.adding_apartment_price)
    except: pass

@router.message(AdminStates.adding_apartment_price)
async def add_ap_price(message: Message, state: FSMContext):
    if not message.text.isdigit(): return
    u = await get_user(message.from_user.id)
    lang = u.get('language', 'uk')
    price = int(message.text)
    d = await state.get_data()
    await state.update_data(price=price)
    summary = (f"📑 <b>Перевірка:</b>\n\nНазва: {d['name']}\nКімнат: {d['rooms']}\nЦіна: {price} грн") if lang=='uk' else (f"📑 <b>Check:</b>\n\nName: {d['name']}\nRooms: {d['rooms']}\nPrice: {price} UAH")
    await message.answer(summary, reply_markup=confirm_ap_add_kb(lang), parse_mode="HTML")

@router.callback_query(F.data == "confirm_add_ap")
async def save_ap(callback: CallbackQuery, state: FSMContext):
    d = await state.get_data()
    await add_apartment({"title": {"uk": d['name'], "en": d['name']}, "description": {"uk": d['desc'], "en": d['desc']}, "rooms": d['rooms'], "beds": d['beds'], "area": d['area'], "guests": d['guests'], "lat": d['lat'], "lng": d['lng'], "price": d['price'], "is_available": True})
    u = await get_user(callback.from_user.id)
    await callback.message.edit_text("✅ Готово" if u.get('language') == 'uk' else "✅ Done")
    await state.clear()

@router.callback_query(F.data.startswith("approve_"))
async def approve(callback: CallbackQuery, bot: Bot):
    b_id = callback.data.split("_")[1]
    b = await get_booking(b_id)
    if b:
        await update_booking_status(b_id, "confirmed")
        user = await get_user(b['user_id'])
        lang = user.get('language', 'uk') if user else 'uk'
        txt = "✅ Підтверджено! Чекаємо на вас." if lang == 'uk' else "✅ Confirmed! We are waiting for you."
        await bot.send_message(b['user_id'], txt, reply_markup=user_reply_inline_kb(lang))
    u = await get_user(callback.from_user.id)
    await callback.message.edit_reply_markup(reply_markup=booking_action_inline_kb(b_id, u.get('language', 'uk'), "confirmed"))
    await callback.answer()

@router.callback_query(F.data.startswith("reject_"))
async def reject(callback: CallbackQuery, bot: Bot):
    b_id = callback.data.split("_")[1]
    b = await get_booking(b_id)
    if b:
        await update_booking_status(b_id, "rejected")
        await set_apartment_availability(str(b['ap_id']), True)
        user = await get_user(b['user_id'])
        lang = user.get('language', 'uk') if user else 'uk'
        await bot.send_message(b['user_id'], "❌ Відхилено" if lang == 'uk' else "❌ Rejected", reply_markup=user_reply_inline_kb(lang))
    u = await get_user(callback.from_user.id)
    await callback.message.edit_reply_markup(reply_markup=booking_action_inline_kb(b_id, u.get('language', 'uk'), "rejected"))
    await callback.answer()

@router.message(F.text == "👥 Команда")
@router.message(F.text == "👥 Team")
async def manage_staff(message: Message):
    u = await get_user(message.from_user.id)
    if u and u.get('role') == "boss":
        lang = u.get('language', 'uk')
        msg = "👥 <b>Управління командою:</b>" if lang == 'uk' else "👥 <b>Team Management:</b>"
        await message.answer(msg, reply_markup=staff_mgmt_inline_kb(lang), parse_mode="HTML")

@router.callback_query(F.data == "view_staff")
async def view_staff_list(callback: CallbackQuery):
    u = await get_user(callback.from_user.id)
    if u and u.get('role') == "boss":
        staff = await get_all_admins_and_bosses()
        lang = u.get('language', 'uk')
        msg = "👥 <b>Команда:</b>\n\n" if lang == 'uk' else "👥 <b>Team:</b>\n\n"
        for s in staff:
            msg += f"• {s.get('name', 'User')} (@{s.get('username', '-')})\n  ID: <code>{s['user_id']}</code> | Role: {s['role']}\n\n"
        await callback.message.answer(msg, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "add_staff")
async def add_staff_start(callback: CallbackQuery, state: FSMContext):
    u = await get_user(callback.from_user.id)
    lang = u.get('language', 'uk')
    await callback.message.answer("Введіть @username, +телефон або ID:" if lang == 'uk' else "Enter @username, +phone or ID:")
    await state.set_state(AdminStates.searching_user)
    await callback.answer()

@router.message(AdminStates.searching_user)
async def search_user_staff(message: Message, state: FSMContext):
    q = message.text.strip()
    u = await get_user(message.from_user.id)
    lang = u.get('language', 'uk')
    query = {"username": q[1:]} if q.startswith('@') else ({"phone": q} if q.startswith('+') else ({"user_id": int(q)} if q.isdigit() else None))
    if not query: return
    target = await get_user_by_query(query)
    if not target:
        await message.answer("❌ Не знайдено." if lang == 'uk' else "❌ Not found.")
        return
    await state.update_data(tid=target['user_id'])
    await message.answer("Роль (admin/boss):" if lang == 'uk' else "Role (admin/boss):")
    await state.set_state(AdminStates.adding_staff_role)

@router.message(AdminStates.adding_staff_role)
async def add_staff_role(message: Message, state: FSMContext):
    r = message.text.lower()
    if r not in ['admin', 'boss']: return
    d = await state.get_data()
    await update_user_pref(d['tid'], role=r)
    u = await get_user(message.from_user.id)
    await message.answer("✅ Додано" if u.get('language')=='uk' else "✅ Added")
    await state.clear()

@router.callback_query(F.data == "del_staff")
async def del_staff_list(callback: CallbackQuery):
    u = await get_user(callback.from_user.id)
    if u and u.get('role') == "boss":
        staff = [s for s in await get_all_admins_and_bosses() if s['user_id'] != callback.from_user.id]
        lang = u.get('language', 'uk')
        await callback.message.answer("Виберіть для видалення:" if lang == 'uk' else "Select to remove:", reply_markup=staff_delete_inline_kb(staff, lang))
    await callback.answer()

@router.callback_query(F.data.startswith("remove_staff_"))
async def del_staff_finish(callback: CallbackQuery):
    await update_user_pref(int(callback.data.split("_")[2]), role="user")
    u = await get_user(callback.from_user.id)
    await callback.answer()
    await callback.message.delete()

@router.callback_query(F.data.startswith("chat_"))
async def chat_start(callback: CallbackQuery, state: FSMContext):
    u = await get_user(callback.from_user.id)
    parts = callback.data.split("_")
    tid = int(parts[2]) if parts[1] == "user" else (await get_booking(parts[1]))['user_id']
    await state.update_data(chat_id=tid)
    await callback.message.answer("Повідомлення:" if u.get('language') == 'uk' else "Message:")
    await state.set_state(AdminStates.replying_to_user)
    await callback.answer()

@router.message(AdminStates.replying_to_user)
async def chat_send(message: Message, state: FSMContext, bot: Bot):
    d = await state.get_data()
    t = await get_user(d['chat_id'])
    tl = t.get('language', 'uk') if t else 'uk'
    try:
        hdr = "🏨 <b>Адміністрація:</b>" if tl == 'uk' else "🏨 <b>Administration:</b>"
        await bot.send_message(d['chat_id'], f"{hdr}\n\n{message.text}", reply_markup=user_reply_inline_kb(tl), parse_mode="HTML")
        u = await get_user(message.from_user.id)
        await message.answer("✅ Надіслано" if u.get('language') == 'uk' else "✅ Sent")
    except: await message.answer("❌")
    await state.clear()
