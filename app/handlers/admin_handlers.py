from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, LabeledPrice
from aiogram.fsm.context import FSMContext
from app.databases.mongodb import get_user, get_apartments, add_apartment, delete_apartment, get_apartment, set_apartment_availability, get_booking, update_booking_status, set_user_role, get_user_by_query, get_active_bookings, get_all_admins_and_bosses
from app.keyboards.all_keyboards import admin_panel_kb, apartment_mgmt_inline_kb, apartment_item_mgmt_kb, staff_mgmt_inline_kb, booking_action_inline_kb, user_reply_inline_kb
from app.utils.states import AdminStates
from app.common.token import PAYMENT_TOKEN

router = Router()

@router.message(F.text == "📅 Активні бронювання")
async def view_active_bookings(message: Message):
    u = await get_user(message.from_user.id)
    if u['role'] in ['admin', 'boss']:
        bookings = await get_active_bookings()
        if not bookings:
            await message.answer("Наразі активних бронювань немає.")
            return
        for b in bookings:
            ap = await get_apartment(b['ap_id'])
            name = ap['title']['uk'] if ap and isinstance(ap.get('title'), dict) else (ap.get('name', 'Апартаменти') if ap else "⚠️ Об'єкт видалено")
            
            status_text = "💳 Очікує 50%" if b['status'] == "paid_50" else "✅ Підтверджено"
            msg = (
                f"🔖 <b>ID:</b> <code>{str(b['_id'])}</code>\n"
                f"🏠 <b>Об'єкт:</b> {name}\n"
                f"📅 <b>Період:</b> {b['start_date']} — {b['end_date']}\n"
                f"👤 <b>ID гостя:</b> <code>{b['user_id']}</code>\n"
                f"📞 <b>Контакт:</b> {b['phone']}\n"
                f"💰 <b>Сума:</b> {b['total_price']} грн\n"
                f"⚙️ <b>Статус:</b> {status_text}"
            )
            await message.answer(msg, reply_markup=booking_action_inline_kb(str(b['_id'])), parse_mode="HTML")

@router.message(F.text == "🏢 Об'єкти")
async def admin_aps(message: Message):
    u = await get_user(message.from_user.id)
    if u['role'] in ['admin', 'boss']:
        aps = await get_apartments()
        await message.answer("🏢 <b>Управління об'єктами:</b>", reply_markup=apartment_mgmt_inline_kb(aps), parse_mode="HTML")

@router.callback_query(F.data.startswith("manage_ap_"))
async def manage_ap_item(callback: CallbackQuery):
    ap_id = callback.data.split("_")[2]
    ap = await get_apartment(ap_id)
    if not ap:
        await callback.answer("Об'єкт не знайдено.")
        return
    name = ap['title']['uk'] if isinstance(ap.get('title'), dict) else ap.get('name', 'Апартаменти')
    status = "🟢 Доступний" if ap['is_available'] else "🔴 Заблокований"
    await callback.message.edit_text(
        f"<b>Редагування:</b> {name}\n"
        f"<b>Статус:</b> {status}",
        reply_markup=apartment_item_mgmt_kb(ap_id, ap['is_available']),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("toggle_ap_"))
async def toggle_ap(callback: CallbackQuery):
    ap_id = callback.data.split("_")[2]
    ap = await get_apartment(ap_id)
    if ap:
        new_status = not ap['is_available']
        await set_apartment_availability(ap_id, new_status)
        await callback.answer("Статус оновлено")
    await manage_ap_item(callback)

@router.callback_query(F.data.startswith("delete_ap_"))
async def del_ap(callback: CallbackQuery):
    ap_id = callback.data.split("_")[2]
    await delete_apartment(ap_id)
    await callback.answer("Об'єкт видалено")
    await admin_aps(callback.message)

@router.callback_query(F.data == "admin_apartments_back")
async def ap_back(callback: CallbackQuery):
    await admin_aps(callback.message)

@router.callback_query(F.data == "add_ap")
async def add_ap_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введіть назву апартаментів (адресу):")
    await state.set_state(AdminStates.adding_apartment_name)
    await callback.answer()

@router.message(AdminStates.adding_apartment_name)
async def add_ap_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введіть опис об'єкта:")
    await state.set_state(AdminStates.adding_apartment_desc)

@router.message(AdminStates.adding_apartment_desc)
async def add_ap_desc(message: Message, state: FSMContext):
    await state.update_data(desc=message.text)
    await message.answer("Вкажіть кількість кімнат (число):")
    await state.set_state(AdminStates.adding_apartment_rooms)

@router.message(AdminStates.adding_apartment_rooms)
async def add_ap_rooms(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Будь ласка, введіть число.")
        return
    await state.update_data(rooms=message.text)
    await message.answer("Вкажіть кількість спальних місць (число):")
    await state.set_state(AdminStates.adding_apartment_beds)

@router.message(AdminStates.adding_apartment_beds)
async def add_ap_beds(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ Будь ласка, введіть число.")
        return
    await state.update_data(beds=message.text)
    await message.answer("Вкажіть площу в м² (число):")
    await state.set_state(AdminStates.adding_apartment_area)

@router.message(AdminStates.adding_apartment_beds) # This was a duplicate state in logic, fixing to area
@router.message(AdminStates.adding_apartment_area)
async def add_ap_area(message: Message, state: FSMContext):
    try:
        area = float(message.text.replace(',', '.'))
        if area <= 0: raise ValueError
        await state.update_data(area=area)
        await message.answer("Вкажіть максимальну місткість осіб (число):")
        await state.set_state(AdminStates.adding_apartment_guests)
    except: await message.answer("❌ Введіть коректне число більше 0.")

@router.message(AdminStates.adding_apartment_guests)
async def add_ap_guests(message: Message, state: FSMContext):
    if not message.text.isdigit() or int(message.text) <= 0:
        await message.answer("❌ Введіть число більше 0.")
        return
    await state.update_data(guests=message.text)
    await message.answer("Вкажіть Широту (Latitude) для карти (напр. 48.62, або 0):")
    await state.set_state(AdminStates.adding_apartment_lat)

@router.message(AdminStates.adding_apartment_lat)
async def add_ap_lat(message: Message, state: FSMContext):
    try:
        lat = float(message.text.replace(',', '.'))
        await state.update_data(lat=lat)
        await message.answer("Вкажіть Довготу (Longitude) для карти (напр. 22.29, або 0):")
        await state.set_state(AdminStates.adding_apartment_lng)
    except: await message.answer("❌ Введіть числове значення.")

@router.message(AdminStates.adding_apartment_lng)
async def add_ap_lng(message: Message, state: FSMContext):
    try:
        lng = float(message.text.replace(',', '.'))
        await state.update_data(lng=lng)
        await message.answer("Вкажіть вартість за добу в грн (ціле число):")
        await state.set_state(AdminStates.adding_apartment_price)
    except: await message.answer("❌ Введіть числове значення.")

@router.message(AdminStates.adding_apartment_price)
async def add_ap_price(message: Message, state: FSMContext):
    if not message.text.isdigit() or int(message.text) <= 0:
        await message.answer("❌ Вкажіть коректну ціну більше 0.")
        return
    
    price = int(message.text)
    data = await state.get_data()
    await add_apartment({
        "title": {"uk": data['name']}, 
        "description": {"uk": data['desc']}, 
        "rooms": data['rooms'],
        "beds": data['beds'],
        "area": data['area'],
        "guests": data['guests'],
        "lat": data['lat'],
        "lng": data['lng'],
        "price": price, 
        "availableFromMonth": 1, 
        "availableToMonth": 12, 
        "is_available": True
    })
    await message.answer(f"✅ Об'єкт «{data['name']}» успішно додано!")
    await state.clear()

@router.callback_query(F.data.startswith("approve_"))
async def approve(callback: CallbackQuery, bot: Bot):
    b = await get_booking(callback.data.split("_")[1])
    if b:
        await update_booking_status(b['_id'], "confirmed")
        confirm_text = (
            "✅ <b>Ваше бронювання підтверджено!</b>\n\n"
            "Ми чекаємо на вас. Решту оплати (50%) можна буде внести безпосередньо при заїзді або через бот."
        )
        await bot.send_message(b['user_id'], confirm_text, reply_markup=user_reply_inline_kb(), parse_mode="HTML")
    await callback.message.edit_text("✅ Бронювання підтверджено")

@router.callback_query(F.data.startswith("reject_"))
async def reject(callback: CallbackQuery, bot: Bot):
    b = await get_booking(callback.data.split("_")[1])
    if b:
        await update_booking_status(b['_id'], "rejected")
        await set_apartment_availability(b['ap_id'], True)
        reject_text = (
            "❌ <b>На жаль, ваше бронювання відхилено.</b>\n\n"
            "Для уточнення деталей ви можете зв'язатися з адміністратором."
        )
        await bot.send_message(b['user_id'], reject_text, reply_markup=user_reply_inline_kb(), parse_mode="HTML")
    await callback.message.edit_text("❌ Бронювання відхилено")

@router.message(F.text == "👥 Команда")
async def manage_staff(message: Message):
    u = await get_user(message.from_user.id)
    if u['role'] == "boss":
        await message.answer("👥 <b>Управління командою:</b>", reply_markup=staff_mgmt_inline_kb(), parse_mode="HTML")

@router.callback_query(F.data == "view_staff")
async def view_staff_list(callback: CallbackQuery):
    u = await get_user(callback.from_user.id)
    if u['role'] == "boss":
        staff = await get_all_admins_and_bosses()
        msg = "👥 <b>Діюча команда:</b>\n\n"
        for s in staff:
            phone = s.get('phone', '-')
            msg += f"• {s.get('name', 'Користувач')} (@{s.get('username', '-')})\n  ID: <code>{s['user_id']}</code> | Тел: {phone}\n  Роль: {s['role']}\n\n"
        await callback.message.answer(msg, parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "add_staff")
async def add_staff(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Введіть Telegram ID нового учасника:")
    await state.set_state(AdminStates.adding_staff_id)
    await callback.answer()

@router.message(AdminStates.adding_staff_id)
async def add_staff_id(message: Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("❌ ID має складатися лише з цифр.")
        return
    await state.update_data(tid=int(message.text))
    await message.answer("Вкажіть роль (admin/boss):")
    await state.set_state(AdminStates.adding_staff_role)

@router.message(AdminStates.adding_staff_role)
async def add_staff_role(message: Message, state: FSMContext):
    role = message.text.lower()
    if role not in ['admin', 'boss']:
        await message.answer("❌ Доступні ролі: admin, boss")
        return
    await state.update_data(role=role)
    await message.answer("Вкажіть ім'я учасника:")
    await state.set_state(AdminStates.adding_staff_name)

@router.message(AdminStates.adding_staff_name)
async def add_staff_finish(message: Message, state: FSMContext):
    d = await state.get_data()
    await set_user_role(d['tid'], d['role'])
    await message.answer("✅ Учасника додано до команди.")
    await state.clear()

@router.callback_query(F.data.startswith("chat_"))
async def chat_start(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    target_id = int(parts[2]) if parts[1] == "user" else (await get_booking(parts[1]))['user_id']
    
    await state.update_data(chat_id=target_id)
    await callback.message.answer("Введіть ваше повідомлення для гостя:")
    await state.set_state(AdminStates.replying_to_user)
    await callback.answer()

@router.message(AdminStates.replying_to_user)
async def chat_send(message: Message, state: FSMContext, bot: Bot):
    d = await state.get_data()
    try:
        await bot.send_message(d['chat_id'], f"🏨 <b>Адміністрація G.I.L Apartments:</b>\n\n{message.text}", reply_markup=user_reply_inline_kb(), parse_mode="HTML")
        await message.answer("✅ Повідомлення надіслано.")
    except: await message.answer("❌ Не вдалося надіслати повідомлення.")
    await state.clear()
