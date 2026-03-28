from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, LabeledPrice, PhotoSize, Location
from aiogram.fsm.context import FSMContext
from app.databases.mongodb import get_user, get_apartments, add_apartment, delete_apartment, get_apartment, get_booking, update_booking_status, set_user_role, get_user_by_query, get_active_bookings, get_all_admins_and_bosses, update_user_pref, delete_booking, log_error, get_admins, update_apartment
from app.keyboards.all_keyboards import admin_panel_kb, apartment_mgmt_inline_kb, apartment_item_mgmt_kb, staff_mgmt_inline_kb, booking_action_inline_kb, user_reply_inline_kb, staff_delete_inline_kb, admin_reply_inline_kb, confirm_ap_add_kb, apartment_edit_fields_kb
from app.utils.states import AdminStates
from app.common.token import PAYMENT_TOKEN, GOOGLE_MAPS_API_KEY
from app.utils.currency import get_usd_rate, format_price
import traceback
import googlemaps
import re
import aiohttp

router = Router()

async def resolve_coords_from_text(text: str):
    patterns = [
        r'([-+]?\d+\.\d+),\s*([-+]?\d+\.\d+)',
        r'[qQ](?:uery)?=([-+]?\d+\.\d+),([-+]?\d+\.\d+)',
        r'!3d([-+]?\d+\.\d+)!4d([-+]?\d+\.\d+)',
        r'place/([-+]?\d+\.\d+),([-+]?\d+\.\d+)'
    ]
    
    for p in patterns:
        match = re.search(p, text)
        if match:
            return float(match.group(1)), float(match.group(2))
    
    if "maps" in text or "goo.gl" in text or "http" in text:
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                async with session.get(text, allow_redirects=True) as response:
                    final_url = str(response.url)
                    for p in patterns:
                        match = re.search(p, final_url)
                        if match:
                            return float(match.group(1)), float(match.group(2))
        except:
            pass
            
    if GOOGLE_MAPS_API_KEY:
        try:
            gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)
            geocode_result = gmaps.geocode(text)
            if geocode_result:
                loc = geocode_result[0]['geometry']['location']
                return loc['lat'], loc['lng']
        except:
            pass
            
    return 0, 0

@router.callback_query(F.data == "back_to_staff_main")
async def back_to_staff_main_handler(callback: CallbackQuery):
    await manage_staff(callback.message)
    await callback.message.delete()
    await callback.answer()

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
            guest = await get_user(b['user_id'])
            
            name = ap['title'][lang] if ap and isinstance(ap.get('title'), dict) and lang in ap['title'] else (ap.get('name', 'Apartments') if ap else "⚠️ Removed")
            status_text = ("💳 Передплата 50%" if b['status'] == "paid_50" else "✅ Підтверджено") if lang == 'uk' else ("💳 Prepayment 50%" if b['status'] == "paid_50" else "✅ Confirmed")
            rate = await get_usd_rate()
            price_text = format_price(b['total_price'], rate, u.get('currency', 'uah'))
            
            guest_name = guest.get('name', 'N/A') if guest else 'N/A'
            guest_username = f"@{guest.get('username')}" if guest and guest.get('username') else 'N/A'
            guest_phone = b.get('phone', 'N/A')
            guest_id = b['user_id']

            if lang == 'uk':
                msg = (
                    f"🏠 <b>Об'єкт:</b> {name}\n"
                    f"📅 <b>Період:</b> {b['start_date']} — {b['end_date']}\n\n"
                    f"👤 <b>Гість:</b> {guest_name}\n"
                    f"🔗 <b>Username:</b> {guest_username}\n"
                    f"📞 <b>Телефон:</b> {guest_phone}\n"
                    f"🆔 <b>ID гостя:</b> <code>{guest_id}</code>\n\n"
                    f"💰 <b>Сума:</b> {price_text}\n"
                    f"⚙️ <b>Статус:</b> {status_text}"
                )
            else:
                msg = (
                    f"🏠 <b>Object:</b> {name}\n"
                    f"📅 <b>Period:</b> {b['start_date']} — {b['end_date']}\n\n"
                    f"👤 <b>Guest:</b> {guest_name}\n"
                    f"🔗 <b>Username:</b> {guest_username}\n"
                    f"📞 <b>Phone:</b> {guest_phone}\n"
                    f"🆔 <b>Guest ID:</b> <code>{guest_id}</code>\n\n"
                    f"💰 <b>Total:</b> {price_text}\n"
                    f"⚙️ <b>Status:</b> {status_text}"
                )
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

@router.callback_query(F.data == "add_ap")
async def add_ap_start(callback: CallbackQuery, state: FSMContext):
    u = await get_user(callback.from_user.id)
    lang = u.get('language', 'uk')
    await callback.message.answer("Введіть назву об'єкта (наприклад, 'Люкс 1'):" if lang == 'uk' else "Enter object name (e.g., 'Luxury 1'):")
    await state.set_state(AdminStates.adding_apartment_name)
    await callback.answer()

@router.message(AdminStates.adding_apartment_name)
async def add_ap_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введіть опис об'єкта:" if (await get_user(message.from_user.id)).get('language') == 'uk' else "Enter object description:")
    await state.set_state(AdminStates.adding_apartment_desc)

@router.message(AdminStates.adding_apartment_desc)
async def add_ap_desc(message: Message, state: FSMContext):
    await state.update_data(desc=message.text)
    await message.answer("Кількість кімнат:" if (await get_user(message.from_user.id)).get('language') == 'uk' else "Number of rooms:")
    await state.set_state(AdminStates.adding_apartment_rooms)

@router.message(AdminStates.adding_apartment_rooms)
async def add_ap_rooms(message: Message, state: FSMContext):
    u = await get_user(message.from_user.id)
    lang = u.get('language', 'uk')
    if not message.text.isdigit():
        await message.answer("❌ Будь ласка, введіть числове значення для кількості кімнат." if lang == 'uk' else "❌ Please enter a numeric value for the number of rooms.")
        return
    await state.update_data(rooms=message.text)
    await message.answer("Кількість ліжок:" if lang == 'uk' else "Number of beds:")
    await state.set_state(AdminStates.adding_apartment_beds)

@router.message(AdminStates.adding_apartment_beds)
async def add_ap_beds(message: Message, state: FSMContext):
    u = await get_user(message.from_user.id)
    lang = u.get('language', 'uk')
    if not message.text.isdigit():
        await message.answer("❌ Будь ласка, введіть числове значення для кількості ліжок." if lang == 'uk' else "❌ Please enter a numeric value for the number of beds.")
        return
    await state.update_data(beds=message.text)
    await message.answer("Площа об'єкта (кв.м):" if lang == 'uk' else "Object area (sq.m):")
    await state.set_state(AdminStates.adding_apartment_area)

@router.message(AdminStates.adding_apartment_area)
async def add_ap_area(message: Message, state: FSMContext):
    u = await get_user(message.from_user.id)
    lang = u.get('language', 'uk')
    try:
        await state.update_data(area=float(message.text.replace(',', '.')))
        await message.answer("Максимальна кількість гостей:" if lang == 'uk' else "Maximum number of guests:")
        await state.set_state(AdminStates.adding_apartment_guests)
    except ValueError:
        await message.answer("❌ Будь ласка, введіть числове значення для площі." if lang == 'uk' else "❌ Please enter a numeric value for the area.")

@router.message(AdminStates.adding_apartment_guests)
async def add_ap_guests(message: Message, state: FSMContext):
    u = await get_user(message.from_user.id)
    lang = u.get('language', 'uk')
    if not message.text.isdigit():
        await message.answer("❌ Будь ласка, введіть числове значення для кількості гостей." if lang == 'uk' else "❌ Please enter a numeric value for the number of guests.")
        return
    await state.update_data(guests=message.text)
    await message.answer("Надішліть локацію (через скріпку 📎) або посилання з Google Maps:" if lang == 'uk' else "Send location (via attachment 📎) or a Google Maps link:")
    await state.set_state(AdminStates.adding_apartment_address)

@router.message(AdminStates.adding_apartment_address, F.location)
@router.message(AdminStates.adding_apartment_address, F.text)
async def add_ap_address(message: Message, state: FSMContext):
    u = await get_user(message.from_user.id)
    lang = u.get('language', 'uk')
    
    if message.location:
        lat, lng = message.location.latitude, message.location.longitude
        address = f"TG Location: {lat}, {lng}"
    else:
        address = message.text
        lat, lng = await resolve_coords_from_text(address)
    
    if lat == 0 and lng == 0:
        await message.answer("⚠️ Не вдалося розпізнати локацію. Будь ласка, надішліть посилання з Google Maps або локацію через Telegram:" if lang == 'uk' else "⚠️ Could not recognize location. Please send a Google Maps link or location via Telegram:")
        return
    
    await state.update_data(address=address, lat=lat, lng=lng)
    await message.answer("Ціна за добу (грн):" if lang == 'uk' else "Price per day (UAH):")
    await state.set_state(AdminStates.adding_apartment_price)

@router.message(AdminStates.adding_apartment_price)
async def add_ap_price(message: Message, state: FSMContext):
    u = await get_user(message.from_user.id)
    lang = u.get('language', 'uk')
    if not message.text.isdigit():
        await message.answer("❌ Будь ласка, введіть числове значення для ціни." if lang == 'uk' else "❌ Please enter a numeric value for the price.")
        return
    await state.update_data(price=int(message.text))
    await message.answer("Надішліть фото об'єкта або посилання на нього:" if lang == 'uk' else "Send object photo or its link:")
    await state.set_state(AdminStates.adding_apartment_photo)

@router.message(AdminStates.adding_apartment_photo, F.photo)
@router.message(AdminStates.adding_apartment_photo, F.text)
async def add_ap_photo(message: Message, state: FSMContext):
    u = await get_user(message.from_user.id)
    lang = u.get('language', 'uk')
    
    if message.photo:
        photo_id = message.photo[-1].file_id
    else:
        photo_id = message.text
        
    await state.update_data(img=photo_id)
    d = await state.get_data()
    summary = (f"📑 <b>Перевірка:</b>\n\nНазва: {d['name']}\nЛокація: {d['lat']}, {d['lng']}\nЦіна: {d['price']} грн") if lang=='uk' else (f"📑 <b>Check:</b>\n\nName: {d['name']}\nLocation: {d['lat']}, {d['lng']}\nPrice: {d['price']} UAH")
    await message.answer(summary, reply_markup=confirm_ap_add_kb(lang), parse_mode="HTML")

@router.callback_query(F.data == "confirm_add_ap")
async def save_ap(callback: CallbackQuery, state: FSMContext):
    d = await state.get_data()
    await add_apartment({
        "title": {"uk": d['name'], "en": d['name']}, 
        "description": {"uk": d['desc'], "en": d['desc']}, 
        "rooms": d['rooms'], 
        "beds": d['beds'], 
        "area": d['area'], 
        "guests": d['guests'], 
        "lat": d['lat'], 
        "lng": d['lng'], 
        "address": d.get('address', 'N/A'),
        "price": d['price'], 
        "img": d.get('img', ''),
        "is_available": True
    })
    u = await get_user(callback.from_user.id)
    await callback.message.edit_text("✅ Об'єкт додано!" if u.get('language') == 'uk' else "✅ Object added!")
    await state.clear()
    await admin_aps(callback.message)

@router.callback_query(F.data.startswith("manage_ap_"))
async def manage_ap_item(callback: CallbackQuery):
    u = await get_user(callback.from_user.id)
    lang = u.get('language', 'uk')
    ap_id = callback.data.split("_")[2]
    ap = await get_apartment(ap_id)
    if not ap: return
    name = ap['title'][lang] if isinstance(ap.get('title'), dict) and lang in ap['title'] else ap.get('name', 'Apartments')
    status = ("🟢 Доступний" if ap['is_available'] else "🔴 Заблокований") if lang == 'uk' else ("🟢 Available" if ap['is_available'] else "🔴 Blocked")
    text = (f"<b>Редагування:</b> {name}\n<b>Локація:</b> {ap.get('lat', 0)}, {ap.get('lng', 0)}\n<b>Статус:</b> {status}") if lang == 'uk' else (f"<b>Editing:</b> {name}\n<b>Location:</b> {ap.get('lat', 0)}, {ap.get('lng', 0)}\n<b>Status:</b> {status}")
    
    img = ap.get('img', ap.get('photo'))
    if img:
        try:
            await callback.message.answer_photo(img, caption=text, reply_markup=apartment_item_mgmt_kb(ap_id, ap['is_available'], lang=lang), parse_mode="HTML")
            await callback.message.delete()
        except:
            await callback.message.edit_text(text, reply_markup=apartment_item_mgmt_kb(ap_id, ap['is_available'], lang=lang), parse_mode="HTML")
    else:
        await callback.message.edit_text(text, reply_markup=apartment_item_mgmt_kb(ap_id, ap['is_available'], lang=lang), parse_mode="HTML")

@router.callback_query(F.data.startswith("edit_ap_"))
async def edit_ap_start(callback: CallbackQuery):
    ap_id = callback.data.split("_")[2]
    u = await get_user(callback.from_user.id)
    lang = u.get('language', 'uk')
    await callback.message.edit_text("Оберіть поле для редагування:" if lang=="uk" else "Choose field to edit:", reply_markup=apartment_edit_fields_kb(ap_id, lang))

@router.callback_query(F.data.startswith("efield_"))
async def edit_field_prompt(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    ap_id, field = parts[1], parts[2]
    u = await get_user(callback.from_user.id)
    lang = u.get('language', 'uk')
    
    await state.update_data(edit_ap_id=ap_id, edit_field=field)
    msg = f"Введіть нове значення для поля {field}:" if lang=="uk" else f"Enter new value for {field}:"
    if field == "img":
        msg = "Надішліть нове фото або посилання:" if lang=="uk" else "Send new photo or link:"
    elif field == "address":
        msg = "Надішліть нову локацію 📎 або посилання з Google Maps:" if lang=="uk" else "Send new location 📎 or Google Maps link:"
        
    await callback.message.edit_text(msg)
    await state.set_state(AdminStates.editing_apartment_field)

@router.message(AdminStates.editing_apartment_field, F.location)
@router.message(AdminStates.editing_apartment_field, F.text)
@router.message(AdminStates.editing_apartment_field, F.photo)
async def edit_field_save(message: Message, state: FSMContext):
    data = await state.get_data()
    ap_id, field = data['edit_ap_id'], data['edit_field']
    u = await get_user(message.from_user.id)
    lang = u.get('language', 'uk')
    
    val = message.text
    if field == "img" and message.photo:
        val = message.photo[-1].file_id
    elif field == "address":
        if message.location:
            lat, lng = message.location.latitude, message.location.longitude
            await update_apartment(ap_id, {"lat": lat, "lng": lng, "address": f"TG Location: {lat}, {lng}"})
        else:
            lat, lng = await resolve_coords_from_text(message.text)
            if lat == 0 and lng == 0:
                await message.answer("❌ Не вдалося розпізнати локацію. Спробуйте ще раз:" if lang=="uk" else "❌ Could not recognize location. Try again:")
                return
            await update_apartment(ap_id, {"lat": lat, "lng": lng, "address": message.text})
            
        await message.answer("✅ Локацію оновлено!" if lang=="uk" else "✅ Location updated!")
        await state.clear()
        class MockCB:
            def __init__(self, msg, uid):
                self.message = msg
                self.from_user = type('obj', (object,), {'id': uid})
                self.data = f"manage_ap_{ap_id}"
            async def answer(self, *args, **kwargs): pass
        await manage_ap_item(MockCB(message, message.from_user.id))
        return
    elif field in ["price", "rooms", "beds", "guests"]:
        try: val = int(val)
        except: 
            await message.answer("❌ Має бути числом")
            return
    elif field in ["area"]:
        try: val = float(val.replace(',', '.'))
        except:
            await message.answer("❌ Має бути числом")
            return
    elif field in ["title", "description"]:
        ap = await get_apartment(ap_id)
        current_val = ap.get(field, {})
        if isinstance(current_val, dict):
            current_val[lang] = message.text
            val = current_val

    await update_apartment(ap_id, {field: val})
    await message.answer("✅ Оновлено!" if lang=="uk" else "✅ Updated!")
    await state.clear()
    class MockCB:
        def __init__(self, msg, uid):
            self.message = msg
            self.from_user = type('obj', (object,), {'id': uid})
            self.data = f"manage_ap_{ap_id}"
        async def answer(self, *args, **kwargs): pass
    await manage_ap_item(MockCB(message, message.from_user.id))

@router.callback_query(F.data.startswith("toggle_ap_"))
async def toggle_ap(callback: CallbackQuery):
    ap_id = callback.data.split("_")[2]
    ap = await get_apartment(ap_id)
    if ap:
        await update_apartment(ap_id, {"is_available": not ap['is_available']})
        await callback.answer("Змінено!" if (await get_user(callback.from_user.id)).get('language') == 'uk' else "Changed!")
    await manage_ap_item(callback)

@router.callback_query(F.data.startswith("delete_ap_"))
async def del_ap(callback: CallbackQuery):
    await delete_apartment(callback.data.split("_")[2])
    await callback.answer("Видалено" if (await get_user(callback.from_user.id)).get('language') == 'uk' else "Deleted")
    await callback.message.delete()
    await admin_aps(callback.message)

@router.callback_query(F.data == "admin_apartments_back")
async def ap_back(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await admin_aps(callback.message)
    await callback.message.delete()

@router.message(F.text == "👥 Команда")
@router.message(F.text == "👥 Team")
async def manage_staff(message: Message):
    u = await get_user(message.from_user.id)
    if u and u.get('role') == "boss":
        lang = u.get('language', 'uk')
        msg = "👥 <b>Управління командою:</b>" if lang == 'uk' else "👥 <b>Team Management:</b>"
        await message.answer(msg, reply_markup=staff_mgmt_inline_kb(lang), parse_mode="HTML")

@router.callback_query(F.data == "add_staff")
async def add_staff_start(callback: CallbackQuery, state: FSMContext):
    u = await get_user(callback.from_user.id)
    lang = u.get('language', 'uk')
    await callback.message.answer("Введіть @username, телефон (+380...) або Telegram ID учасника:" if lang == 'uk' else "Enter member @username, phone (+380...) or Telegram ID:")
    await state.set_state(AdminStates.searching_user)
    await callback.answer()

@router.message(AdminStates.searching_user)
async def search_user_staff(message: Message, state: FSMContext):
    q = message.text.strip()
    u = await get_user(message.from_user.id)
    lang = u.get('language', 'uk')
    
    query = None
    if q.startswith('@'): query = {"username": q[1:]}
    elif q.startswith('+'): query = {"phone": q.replace(" ", "")}
    elif q.isdigit(): query = {"user_id": int(q)}
    
    if not query:
        await message.answer("❌ Невірний формат. Спробуйте ще раз (@username, +380..., або ID):" if lang == 'uk' else "❌ Invalid format. Try again (@username, +380..., or ID):")
        await state.set_state(AdminStates.searching_user)
        return

    target = await get_user_by_query(query)
    if not target:
        await message.answer("❌ Користувача не знайдено в базі." if lang == 'uk' else "❌ User not found.")
        await state.set_state(AdminStates.searching_user)
        return
    
    await state.update_data(tid=target['user_id'])
    await message.answer(f"Знайдено: {target.get('name', 'N/A')} (@{target.get('username', 'N/A')})\nВкажіть роль (admin/boss):" if lang == 'uk' else f"Found: {target.get('name', 'N/A')} (@{target.get('username', 'N/A')})\nEnter role (admin/boss):")
    await state.set_state(AdminStates.adding_staff_role)

@router.message(AdminStates.adding_staff_role)
async def add_staff_role(message: Message, state: FSMContext):
    r = message.text.lower()
    u = await get_user(message.from_user.id)
    lang = u.get('language', 'uk')
    if r not in ['admin', 'boss']:
        await message.answer("❌ Невірна роль. Вкажіть 'admin' або 'boss'." if lang == 'uk' else "❌ Invalid role. Specify 'admin' or 'boss'.")
        await state.set_state(AdminStates.adding_staff_role)
        return
    d = await state.get_data()
    await update_user_pref(d['tid'], role=r)
    await message.answer("✅ Роль оновлено!" if lang=='uk' else "✅ Role updated!")
    await state.clear()
    await manage_staff(message)

@router.callback_query(F.data == "view_staff")
async def view_staff_list(callback: CallbackQuery):
    u = await get_user(callback.from_user.id)
    if u and u.get('role') == "boss":
        staff = [s for s in await get_all_admins_and_bosses() if s['user_id'] != callback.from_user.id]
        lang = u.get('language', 'uk')
        
        msg = "👥 <b>Список персоналу:</b>\n\n" if lang == 'uk' else "👥 <b>Staff List:</b>\n\n"
        for s in staff:
            name = s.get('name', 'N/A')
            username = f"@{s.get('username')}" if s.get('username') else 'N/A'
            phone = s.get('phone', 'N/A')
            uid = s.get('user_id')
            role = s.get('role', 'admin')
            msg += f"👤 {name} ({role})\n🔗 {username}\n📞 {phone}\n🆔 <code>{uid}</code>\n\n"
        
        await callback.message.edit_text(msg, reply_markup=staff_delete_inline_kb(staff, lang), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data.startswith("remove_staff_"))
async def del_staff_finish(callback: CallbackQuery):
    target_id = int(callback.data.split("_")[2])
    await update_user_pref(target_id, role="user")
    await callback.answer("Вилучено")
    await view_staff_list(callback)

@router.callback_query(F.data == "back_to_admin")
async def back_to_admin_staff(callback: CallbackQuery):
    await manage_staff(callback.message)
    await callback.message.delete()
    await callback.answer()

@router.callback_query(F.data.startswith("approve_"))
async def approve_booking_handler(callback: CallbackQuery, bot: Bot):
    b_id = callback.data.split("_")[1]
    b = await get_booking(b_id)
    if b:
        await update_booking_status(b_id, "confirmed")
        user = await get_user(b['user_id'])
        lang = user.get('language', 'uk') if user else 'uk'
        txt = "✅ <b>Ваше бронювання підтверджено!</b>\n\nМи чекаємо на вас. Не забудьте сплатити залишок у день заїзду." if lang == 'uk' else "✅ <b>Your booking is confirmed!</b>\n\nWe are waiting for you. Don't forget to pay the remainder on your check-in day."
        await bot.send_message(b['user_id'], txt, parse_mode="HTML")
    u = await get_user(callback.from_user.id)
    await callback.message.edit_reply_markup(reply_markup=booking_action_inline_kb(b_id, u.get('language', 'uk'), "confirmed"))
    await callback.answer("Підтверджено")

@router.callback_query(F.data.startswith("reject_"))
async def reject_booking_handler(callback: CallbackQuery, bot: Bot):
    b_id = callback.data.split("_")[1]
    b = await get_booking(b_id)
    if b:
        await update_booking_status(b_id, "rejected")
        await update_apartment(str(b['ap_id']), {"is_available": True})
        user = await get_user(b['user_id'])
        lang = user.get('language', 'uk') if user else 'uk'
        user_msg = ("❌ <b>Бронювання скасовано!</b>\n\nНа жаль, ваше бронювання було відхилено або скасовано адміністратором. Кошти за передплату будуть повернуті вам найближчим часом." if lang == 'uk' else "❌ <b>Booking cancelled!</b>\n\nUnfortunately, your booking has been rejected or cancelled by the admin. The prepayment will be returned to you shortly.")
        await bot.send_message(b['user_id'], user_msg, parse_mode="HTML")
    await callback.answer("Скасовано")
    await callback.message.delete()

@router.callback_query(F.data.startswith("chat_"))
async def admin_chat_start(callback: CallbackQuery, state: FSMContext):
    u = await get_user(callback.from_user.id)
    parts = callback.data.split("_")
    tid = int(parts[2]) if parts[1] == "user" else (await get_booking(parts[1]))['user_id']
    await state.update_data(chat_id=tid)
    await callback.message.answer("Введіть ваше повідомлення гостю:" if u.get('language') == 'uk' else "Enter your message to the guest:")
    await state.set_state(AdminStates.replying_to_user)
    await callback.answer()

@router.message(AdminStates.replying_to_user)
async def admin_reply_send(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    tid = data['chat_id']
    u = await get_user(message.from_user.id)
    lang = u.get('language', 'uk')
    
    try:
        target_u = await get_user(tid)
        t_lang = target_u.get('language', 'uk') if target_u else 'uk'
        
        header = "📩 <b>Повідомлення від адміністратора:</b>\n\n" if t_lang == 'uk' else "📩 <b>Message from administrator:</b>\n\n"
        await bot.send_message(tid, header + message.text, reply_markup=user_reply_inline_kb(t_lang), parse_mode="HTML")
        await message.answer("✅ Відправлено!" if lang == 'uk' else "✅ Sent!")
    except Exception as e:
        await message.answer(f"❌ Помилка: {e}")
    
    await state.clear()
