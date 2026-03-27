from aiogram.types import KeyboardButton, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

def main_menu_kb(role="user"):
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text="🏨 Бронювання"))
    builder.add(KeyboardButton(text="📋 Список апартаментів"))
    if role in ["admin", "boss"]:
        builder.add(KeyboardButton(text="📊 Адмін-панель"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def admin_panel_kb(role):
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="📅 Активні бронювання"))
    builder.row(KeyboardButton(text="🏢 Об'єкти"))
    if role == "boss":
        builder.row(KeyboardButton(text="👥 Команда"))
    builder.row(KeyboardButton(text="⬅️ На головну"))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)

def phone_kb():
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text="📱 Надати контактний номер", request_contact=True))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)

def apartments_inline_kb(apartments, for_booking=True):
    builder = InlineKeyboardBuilder()
    for ap in apartments:
        name = ap['title']['uk'] if isinstance(ap.get('title'), dict) else ap.get('name', 'Апартаменти')
        prefix = "📅" if for_booking else "📍"
        builder.button(text=f"{prefix} {name}", callback_data=f"ap_{ap['_id']}")
    builder.adjust(1)
    return builder.as_markup()

def info_only_apartment_kb(lat, lng):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🗺 Побудувати маршрут", url=f"https://www.google.com/maps/dir/?api=1&destination={lat},{lng}"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад до списку", callback_data="back_to_list"))
    return builder.as_markup()

def confirm_booking_inline_kb(lat, lng, ap_id):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🗺 Побудувати маршрут", url=f"https://www.google.com/maps/dir/?api=1&destination={lat},{lng}"))
    builder.row(InlineKeyboardButton(text="✅ Забронювати", callback_data=f"start_book_{ap_id}"))
    builder.row(InlineKeyboardButton(text="⬅️ Назад до вибору", callback_data="back_to_booking_list"))
    return builder.as_markup()

def ap_info_inline_kb(lat, lng, booking_id=None):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🗺 Побудувати маршрут", url=f"https://www.google.com/maps/dir/?api=1&destination={lat},{lng}"))
    if booking_id:
        builder.row(InlineKeyboardButton(text="💳 Сплатити передплату (50%)", callback_data=f"pay50_{booking_id}"))
    return builder.as_markup()

def admin_reply_inline_kb(user_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="💬 Відповісти гостю", callback_data=f"chat_user_{user_id}")
    return builder.as_markup()

def booking_action_inline_kb(booking_id):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="✅ Підтвердити", callback_data=f"approve_{booking_id}"))
    builder.row(InlineKeyboardButton(text="❌ Відхилити", callback_data=f"reject_{booking_id}"))
    builder.row(InlineKeyboardButton(text="✉️ Зв'язатися з гостем", callback_data=f"chat_{booking_id}"))
    return builder.as_markup()

def user_reply_inline_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="💬 Надіслати відповідь", callback_data="user_answer_admin")
    return builder.as_markup()

def staff_mgmt_inline_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="👥 Список команди", callback_data="view_staff")
    builder.button(text="➕ Додати учасника", callback_data="add_staff")
    builder.button(text="➖ Видалити учасника", callback_data="del_staff")
    builder.adjust(1)
    return builder.as_markup()

def apartment_mgmt_inline_kb(apartments):
    builder = InlineKeyboardBuilder()
    for ap in apartments:
        status = "🟢" if ap.get("is_available") else "🔴"
        name = ap['title']['uk'] if isinstance(ap.get('title'), dict) else ap.get('name', 'Апартаменти')
        builder.button(text=f"{status} {name}", callback_data=f"manage_ap_{ap['_id']}")
    builder.button(text="➕ Додати об'єкт", callback_data="add_ap")
    builder.adjust(1)
    return builder.as_markup()

def apartment_item_mgmt_kb(ap_id, is_available):
    builder = InlineKeyboardBuilder()
    toggle_text = "🔒 Вимкнути доступ" if is_available else "🔓 Увімкнути доступ"
    builder.button(text=toggle_text, callback_data=f"toggle_ap_{ap_id}")
    builder.button(text="🗑️ Видалити", callback_data=f"delete_ap_{ap_id}")
    builder.button(text="⬅️ До списку", callback_data="admin_apartments_back")
    builder.adjust(1)
    return builder.as_markup()
