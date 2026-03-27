from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, LabeledPrice
from aiogram.fsm.context import FSMContext
from app.databases.mongodb import get_user, get_apartments, add_apartment, delete_apartment, get_apartment, set_apartment_availability, get_booking, update_booking_status, set_user_role, get_user_by_query, get_active_bookings, get_all_admins_and_bosses, update_user_pref, delete_booking, log_error
from app.keyboards.all_keyboards import admin_panel_kb, apartment_mgmt_inline_kb, apartment_item_mgmt_kb, staff_mgmt_inline_kb, booking_action_inline_kb, user_reply_inline_kb, staff_delete_inline_kb, admin_reply_inline_kb, confirm_ap_add_kb
from app.utils.states import AdminStates
from app.common.token import PAYMENT_TOKEN
from app.utils.currency import get_usd_rate, format_price
import traceback

router = Router()

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
            name = ap['title'][lang] if ap and isinstance(ap.get('title'), dict) and lang in ap['title'] else (ap.get('name', 'Apartments') if ap else "⚠️ Removed")
            status_text = ("💳 Передплата 50%" if b['status'] == "paid_50" else "✅ Підтверджено") if lang == 'uk' else ("💳 Prepayment 50%" if b['status'] == "paid_50" else "✅ Confirmed")
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
        await state.set_state(AdminStates.adding_apartment_area)
    except Exception as e:
        await log_error(f"Error in add_ap_area: {e}", traceback.format_exc())
        await message.answer("❌ Помилка. Спробуйте ще раз." if lang == 'uk' else "❌ Error. Try again.")
        await state.clear()

@router.message(AdminStates.adding_apartment_guests)
async def add_ap_guests(message: Message, state: FSMContext):
    u = await get_user(message.from_user.id)
    lang = u.get('language', 'uk')
    if not message.text.isdigit():
        await message.answer("❌ Будь ласка, введіть числове значення для кількості гостей." if lang == 'uk' else "❌ Please enter a numeric value for the number of guests.")
        return
    await state.update_data(guests=message.text)
    await message.answer("Координати - Latitude (або 0):" if lang == 'uk' else "Coordinates - Latitude (or 0):")
    await state.set_state(AdminStates.adding_apartment_lat)

@router.message(AdminStates.adding_apartment_lat)
async def add_ap_lat(message: Message, state: FSMContext):
    u = await get_user(message.from_user.id)
    lang = u.get('language', 'uk')
    try:
        await state.update_data(lat=float(message.text.replace(',', '.')))
        await message.answer("Координати - Longitude (або 0):" if lang == 'uk' else "Coordinates - Longitude (or 0):")
        await state.set_state(AdminStates.adding_apartment_lng)
    except ValueError:
        await message.answer("❌ Будь ласка, введіть числове значення для Latitude." if lang == 'uk' else "❌ Please enter a numeric value for Latitude.")
        await state.set_state(AdminStates.adding_apartment_lat)
    except Exception as e:
        await log_error(f"Error in add_ap_lat: {e}", traceback.format_exc())
        await message.answer("❌ Помилка." if lang == 'uk' else "❌ Error.")
        await state.clear()

@router.message(AdminStates.adding_apartment_lng)
async def add_ap_lng(message: Message, state: FSMContext):
    u = await get_user(message.from_user.id)
    lang = u.get('language', 'uk')
    try:
        await state.update_data(lng=float(message.text.replace(',', '.')))
        await message.answer("Ціна за добу (грн):" if lang == 'uk' else "Price per day (UAH):")
        await state.set_state(AdminStates.adding_apartment_price)
    except ValueError:
        await message.answer("❌ Будь ласка, введіть числове значення для Longitude." if lang == 'uk' else "❌ Please enter a numeric value for Longitude.")
        await state.set_state(AdminStates.adding_apartment_lng)
    except Exception as e:
        await log_error(f"Error in add_ap_lng: {e}", traceback.format_exc())
        await message.answer("❌ Помилка." if lang == 'uk' else "❌ Error.")
        await state.clear()

@router.message(AdminStates.adding_apartment_price)
async def add_ap_price(message: Message, state: FSMContext):
    u = await get_user(message.from_user.id)
    lang = u.get('language', 'uk')
    if not message.text.isdigit():
        await message.answer("❌ Будь ласка, введіть числове значення для ціни." if lang == 'uk' else "❌ Please enter a numeric value for the price.")
        return
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
    text = (f"<b>Редагування:</b> {name}\n<b>Статус:</b> {status}") if lang == 'uk' else (f"<b>Editing:</b> {name}\n<b>Status:</b> {status}")
    await callback.message.edit_text(text, reply_markup=apartment_item_mgmt_kb(ap_id, ap['is_available'], lang=lang), parse_mode="HTML")

@router.callback_query(F.data.startswith("toggle_ap_"))
async def toggle_ap(callback: CallbackQuery):
    ap_id = callback.data.split("_")[2]
    ap = await get_apartment(ap_id)
    if ap:
        await set_apartment_availability(ap_id, not ap['is_available'])
        await callback.answer("Змінено!" if (await get_user(callback.from_user.id)).get('language') == 'uk' else "Changed!")
    await manage_ap_item(callback)

@router.callback_query(F.data.startswith("delete_ap_"))
async def del_ap(callback: CallbackQuery):
    await delete_apartment(callback.data.split("_")[2])
    await callback.answer("Видалено" if (await get_user(callback.from_user.id)).get('language') == 'uk' else "Deleted")
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
        await set_apartment_availability(str(b['ap_id']), True)
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
