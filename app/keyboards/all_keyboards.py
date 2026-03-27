from aiogram.types import KeyboardButton, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

def main_menu_kb(role="user", lang="uk"):
    builder = ReplyKeyboardBuilder()
    if lang == "uk":
        builder.add(KeyboardButton(text="🏨 Бронювання"))
        builder.add(KeyboardButton(text="📋 Список апартаментів"))
        builder.add(KeyboardButton(text="👤 Профіль"))
    else:
        builder.add(KeyboardButton(text="🏨 Booking"))
        builder.add(KeyboardButton(text="📋 Apartment List"))
        builder.add(KeyboardButton(text="👤 Profile"))
        
    if role in ["admin", "boss"]:
        builder.add(KeyboardButton(text="📊 Адмін-панель" if lang == "uk" else "📊 Admin Panel"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def admin_panel_kb(role, lang="uk"):
    builder = ReplyKeyboardBuilder()
    if lang == "uk":
        builder.row(KeyboardButton(text="📅 Активні бронювання"))
        builder.row(KeyboardButton(text="🏢 Об'єкти"))
        if role == "boss":
            builder.row(KeyboardButton(text="👥 Команда"))
        builder.row(KeyboardButton(text="⬅️ На головну"))
    else:
        builder.row(KeyboardButton(text="📅 Active Bookings"))
        builder.row(KeyboardButton(text="🏢 Objects"))
        if role == "boss":
            builder.row(KeyboardButton(text="👥 Team"))
        builder.row(KeyboardButton(text="⬅️ To Main Menu"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def phone_kb(lang="uk"):
    builder = ReplyKeyboardBuilder()
    text = "📱 Надати номер" if lang == "uk" else "📱 Provide number"
    builder.row(KeyboardButton(text=text, request_contact=True))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)

def apartments_inline_kb(apartments, for_booking=True, lang="uk"):
    builder = InlineKeyboardBuilder()
    for ap in apartments:
        name = ap['title'][lang] if isinstance(ap.get('title'), dict) and lang in ap['title'] else ap.get('name', 'Apartments')
        prefix = "📅" if for_booking else "📍"
        builder.button(text=f"{prefix} {name}", callback_data=f"ap_{ap['_id']}")
    builder.adjust(1)
    return builder.as_markup()

def info_only_apartment_kb(lat, lng, lang="uk"):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🗺 Маршрут" if lang == "uk" else "🗺 Route", url=f"https://www.google.com/maps/dir/?api=1&destination={lat},{lng}"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад" if lang == "uk" else "⬅️ Back", callback_data="back_to_list"))
    return builder.as_markup()

def confirm_booking_inline_kb(lat, lng, ap_id, lang="uk"):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🗺 Маршрут" if lang == "uk" else "🗺 Route", url=f"https://www.google.com/maps/dir/?api=1&destination={lat},{lng}"))
    builder.row(InlineKeyboardButton(text="✅ Забронювати" if lang == "uk" else "✅ Book", callback_data=f"start_book_{ap_id}"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад" if lang == "uk" else "⬅️ Back", callback_data="back_to_booking_list"))
    return builder.as_markup()

def ap_info_inline_kb(lat, lng, booking_id=None, lang="uk"):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🗺 Маршрут" if lang == "uk" else "🗺 Route", url=f"https://www.google.com/maps/dir/?api=1&destination={lat},{lng}"))
    if booking_id:
        text = "💳 Оплатити 50%" if lang == "uk" else "💳 Pay 50%"
        builder.row(InlineKeyboardButton(text=text, callback_data=f"pay50_{booking_id}"))
    return builder.as_markup()

def admin_reply_inline_kb(user_id, lang="uk"):
    builder = InlineKeyboardBuilder()
    text = "💬 Відповісти" if lang == "uk" else "💬 Reply"
    builder.button(text=text, callback_data=f"chat_user_{user_id}")
    return builder.as_markup()

def booking_action_inline_kb(booking_id, lang="uk", status="pending"):
    builder = InlineKeyboardBuilder()
    if status in ["confirmed", "paid_50"]:
        text = "✉️ Зв'язатися" if lang == "uk" else "✉️ Contact"
        builder.row(InlineKeyboardButton(text=text, callback_data=f"chat_{booking_id}"))
    else:
        if lang == "uk":
            builder.row(InlineKeyboardButton(text="✅ Підтвердити", callback_data=f"approve_{booking_id}"))
            builder.row(InlineKeyboardButton(text="❌ Відхилити", callback_data=f"reject_{booking_id}"))
            builder.row(InlineKeyboardButton(text="✉️ Зв'язатися", callback_data=f"chat_{booking_id}"))
        else:
            builder.row(InlineKeyboardButton(text="✅ Approve", callback_data=f"approve_{booking_id}"))
            builder.row(InlineKeyboardButton(text="❌ Reject", callback_data=f"reject_{booking_id}"))
            builder.row(InlineKeyboardButton(text="✉️ Contact", callback_data=f"chat_{booking_id}"))
    return builder.as_markup()

def user_reply_inline_kb(lang="uk"):
    builder = InlineKeyboardBuilder()
    text = "💬 Відповісти" if lang == "uk" else "💬 Reply"
    builder.button(text=text, callback_data="user_answer_admin")
    return builder.as_markup()

def staff_mgmt_inline_kb(lang="uk"):
    builder = InlineKeyboardBuilder()
    if lang == "uk":
        builder.button(text="👥 Список команди", callback_data="view_staff")
        builder.button(text="➕ Додати учасника", callback_data="add_staff")
        builder.button(text="➖ Видалити учасника", callback_data="del_staff")
    else:
        builder.button(text="👥 Team list", callback_data="view_staff")
        builder.button(text="➕ Add member", callback_data="add_staff")
        builder.button(text="➖ Remove member", callback_data="del_staff")
    builder.adjust(1)
    return builder.as_markup()

def staff_delete_inline_kb(staff_list, lang="uk"):
    builder = InlineKeyboardBuilder()
    for s in staff_list:
        builder.button(text=f"🗑 {s.get('name', 'User')}", callback_data=f"remove_staff_{s['user_id']}")
    builder.adjust(1)
    return builder.as_markup()

def apartment_mgmt_inline_kb(apartments, lang="uk"):
    builder = InlineKeyboardBuilder()
    for ap in apartments:
        status = "🟢" if ap.get("is_available") else "🔴"
        name = ap['title'][lang] if isinstance(ap.get('title'), dict) and lang in ap['title'] else ap.get('name', 'Apartments')
        builder.button(text=f"{status} {name}", callback_data=f"manage_ap_{ap['_id']}")
    builder.button(text="➕ Додати" if lang == "uk" else "➕ Add", callback_data="add_ap")
    builder.adjust(1)
    return builder.as_markup()

def apartment_item_mgmt_kb(ap_id, is_available, lang="uk"):
    builder = InlineKeyboardBuilder()
    if lang == "uk":
        toggle_text = "🔒 Вимкнути" if is_available else "🔓 Увімкнути"
        delete_text = "🗑️ Видалити"
        back_text = "⬅️ Назад"
    else:
        toggle_text = "🔒 Disable" if is_available else "🔓 Enable"
        delete_text = "🗑️ Delete"
        back_text = "⬅️ Back"
    builder.button(text=toggle_text, callback_data=f"toggle_ap_{ap_id}")
    builder.button(text=delete_text, callback_data=f"delete_ap_{ap_id}")
    builder.button(text=back_text, callback_data="admin_apartments_back")
    builder.adjust(1)
    return builder.as_markup()

def confirm_ap_add_kb(lang="uk"):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Підтвердити" if lang=="uk" else "✅ Confirm", callback_data="confirm_add_ap")
    builder.button(text="❌ Скасувати" if lang=="uk" else "❌ Cancel", callback_data="admin_apartments_back")
    return builder.as_markup()

def language_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="🇺🇦 Українська", callback_data="set_lang_uk")
    builder.button(text="🇬🇧 English", callback_data="set_lang_en")
    builder.adjust(2)
    return builder.as_markup()

def currency_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="₴ UAH", callback_data="set_curr_uah")
    builder.button(text="$ USD", callback_data="set_curr_usd")
    builder.adjust(2)
    return builder.as_markup()

def settings_kb(lang="uk"):
    builder = InlineKeyboardBuilder()
    if lang == "uk":
        builder.button(text="🌐 Мова", callback_data="change_lang")
        builder.button(text="💰 Валюта", callback_data="change_curr")
    else:
        builder.button(text="🌐 Language", callback_data="change_lang")
        builder.button(text="💰 Currency", callback_data="change_curr")
    builder.adjust(1)
    return builder.as_markup()
