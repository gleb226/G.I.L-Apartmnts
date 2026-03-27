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
    builder.button(text="⬅️ Назад" if lang == "uk" else "⬅️ Back", callback_data="back_to_main")
    builder.adjust(1)
    return builder.as_markup()

def info_only_apartment_kb(lat, lng, lang="uk"):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🗺 Маршрут" if lang == "uk" else "🗺 Route", url=f"https://www.google.com/maps/dir/?api=1&destination={lat},{lng}"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад до списку" if lang == "uk" else "⬅️ Back to list", callback_data="back_to_list"))
    return builder.as_markup()

def confirm_booking_inline_kb(lat, lng, ap_id, lang="uk"):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🗺 Маршрут" if lang == "uk" else "🗺 Route", url=f"https://www.google.com/maps/dir/?api=1&destination={lat},{lng}"))
    builder.row(InlineKeyboardButton(text="✅ Забронювати" if lang == "uk" else "✅ Book", callback_data=f"start_book_{ap_id}"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад" if lang == "uk" else "⬅️ Back", callback_data="back_to_main"))
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

def user_reply_inline_kb(lang="uk"):
    builder = InlineKeyboardBuilder()
    text = "💬 Відповісти" if lang == "uk" else "💬 Reply"
    builder.button(text=text, callback_data="user_answer_admin")
    return builder.as_markup()

def booking_action_inline_kb(booking_id, lang="uk", status="pending"):
    builder = InlineKeyboardBuilder()
    if status in ["confirmed", "completed"]:
        builder.row(InlineKeyboardButton(text="✉️ Написати гостю" if lang == "uk" else "✉️ Message guest", callback_data=f"chat_{booking_id}"))
        builder.row(InlineKeyboardButton(text="❌ Скасувати бронь" if lang == "uk" else "❌ Cancel booking", callback_data=f"reject_{booking_id}"))
    else:
        builder.row(InlineKeyboardButton(text="✅ Підтвердити" if lang == "uk" else "✅ Approve", callback_data=f"approve_{booking_id}"))
        builder.row(InlineKeyboardButton(text="❌ Відхилити" if lang == "uk" else "❌ Reject", callback_data=f"reject_{booking_id}"))
        builder.row(InlineKeyboardButton(text="✉️ Написати гостю" if lang == "uk" else "✉️ Message guest", callback_data=f"chat_{booking_id}"))
    return builder.as_markup()

def staff_mgmt_inline_kb(lang="uk"):
    builder = InlineKeyboardBuilder()
    if lang == "uk":
        builder.button(text="👥 Список команди", callback_data="view_staff")
        builder.button(text="➕ Додати учасника", callback_data="add_staff")
        builder.button(text="⬅️ Назад", callback_data="back_to_main")
    else:
        builder.button(text="👥 Team list", callback_data="view_staff")
        builder.button(text="➕ Add member", callback_data="add_staff")
        builder.button(text="⬅️ Back", callback_data="back_to_main")
    builder.adjust(1)
    return builder.as_markup()

def staff_delete_inline_kb(staff_list, lang="uk"):
    builder = InlineKeyboardBuilder()
    for s in staff_list:
        builder.button(text=f"🗑 {s.get('name', 'User')}", callback_data=f"remove_staff_{s['user_id']}")
    builder.button(text="⬅️ Назад" if lang == "uk" else "⬅️ Back", callback_data="back_to_staff_main")
    builder.adjust(1)
    return builder.as_markup()

def apartment_mgmt_inline_kb(apartments, lang="uk"):
    builder = InlineKeyboardBuilder()
    for ap in apartments:
        status = "🟢" if ap.get("is_available") else "🔴"
        name = ap['title'][lang] if isinstance(ap.get('title'), dict) and lang in ap['title'] else ap.get('name', 'Apartments')
        builder.button(text=f"{status} {name}", callback_data=f"manage_ap_{ap['_id']}")
    builder.button(text="➕ Додати об'єкт" if lang == "uk" else "➕ Add object", callback_data="add_ap")
    builder.button(text="⬅️ Назад" if lang == "uk" else "⬅️ Back", callback_data="back_to_main")
    builder.adjust(1)
    return builder.as_markup()

def apartment_item_mgmt_kb(ap_id, is_available, lang="uk"):
    builder = InlineKeyboardBuilder()
    if lang == "uk":
        edit_text = "📝 Редагувати"
        toggle_text = "🔒 Вимкнути" if is_available else "🔓 Увімкнути"
        delete_text = "🗑️ Видалити"
        back_text = "⬅️ Назад"
    else:
        edit_text = "📝 Edit"
        toggle_text = "🔒 Disable" if is_available else "🔓 Enable"
        delete_text = "🗑️ Delete"
        back_text = "⬅️ Back"
    builder.button(text=edit_text, callback_data=f"edit_ap_{ap_id}")
    builder.button(text=toggle_text, callback_data=f"toggle_ap_{ap_id}")
    builder.button(text=delete_text, callback_data=f"delete_ap_{ap_id}")
    builder.button(text=back_text, callback_data="admin_apartments_back")
    builder.adjust(1)
    return builder.as_markup()

def apartment_edit_fields_kb(ap_id, lang="uk"):
    builder = InlineKeyboardBuilder()
    fields = [
        ("title", "Назва" if lang=="uk" else "Title"),
        ("description", "Опис" if lang=="uk" else "Description"),
        ("price", "Ціна" if lang=="uk" else "Price"),
        ("photo", "Фото" if lang=="uk" else "Photo"),
        ("rooms", "Кімнати" if lang=="uk" else "Rooms"),
        ("beds", "Ліжка" if lang=="uk" else "Beds"),
        ("guests", "Гості" if lang=="uk" else "Guests"),
        ("address", "Адреса" if lang=="uk" else "Address"),
        ("area", "Площа" if lang=="uk" else "Area")
    ]
    for field_id, field_name in fields:
        builder.button(text=field_name, callback_data=f"efield_{ap_id}_{field_id}")
    builder.button(text="⬅️ Назад" if lang == "uk" else "⬅️ Back", callback_data=f"manage_ap_{ap_id}")
    builder.adjust(2)
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
    builder.button(text="🌐 Мова / Language", callback_data="change_lang")
    builder.button(text="💰 Валюта / Currency", callback_data="change_curr")
    builder.button(text="⬅️ На головну" if lang == "uk" else "⬅️ To Main", callback_data="back_to_main")
    builder.adjust(1)
    return builder.as_markup()
