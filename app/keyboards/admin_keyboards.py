from aiogram.types import KeyboardButton, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from app.common.texts import get_text

FEATURE_LABELS = {
    "uk": {
        "tv": "Телевізор",
        "fridge": "Холодильник",
        "microwave": "Мікрохвильова піч",
        "hot_water": "Гаряча вода",
        "air_conditioner": "Кондиціонер",
        "near_supermarket": "Поряд супермаркет",
        "good_transport": "Гарне транспортне сполучення",
        "smart_tv": "Smart TV",
        "balcony": "Балкон",
        "hob": "Варильна поверхня",
        "internet": "Інтернет",
        "cable_tv": "Кабельне ТБ",
        "secure_parking": "Парковка під охороною",
        "coded_entry": "Під'їзд на коді",
        "washing_machine": "Пральна машина",
        "satellite_tv": "Супутникове ТБ",
        "t2_tv": "T2 телебачення",
    },
    "en": {
        "tv": "TV",
        "fridge": "Refrigerator",
        "microwave": "Microwave",
        "hot_water": "Hot water",
        "air_conditioner": "Air conditioner",
        "near_supermarket": "Nearby supermarket",
        "good_transport": "Good transport links",
        "smart_tv": "Smart TV",
        "balcony": "Balcony",
        "hob": "Cooktop",
        "internet": "Internet",
        "cable_tv": "Cable TV",
        "secure_parking": "Secure parking",
        "coded_entry": "Code entry",
        "washing_machine": "Washing machine",
        "satellite_tv": "Satellite TV",
        "t2_tv": "T2 television",
    },
}


def admin_panel_kb(role, lang="uk"):
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text=get_text("btn_active_bookings", lang)))
    builder.add(KeyboardButton(text=get_text("btn_objects", lang)))
    if role == "boss":
        builder.add(KeyboardButton(text=get_text("btn_team", lang)))
    builder.add(KeyboardButton(text=get_text("btn_back_main", lang)))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


def apartment_mgmt_inline_kb(apartments, lang="uk", page=0):
    builder = InlineKeyboardBuilder()
    per_page = 12
    start, end = page * per_page, (page + 1) * per_page
    current_apartments = apartments[start:end]

    for apartment in current_apartments:
        title = apartment["title"].get(lang, apartment["title"].get("uk", "Apartment"))
        apartment_id = str(apartment.get("external_id", apartment["_id"]))
        status_icon = "✅" if apartment.get("is_available", True) else "🚫"
        builder.button(text=f"{status_icon} {title}", callback_data=f"m:{apartment_id}")

    builder.adjust(1)

    navigation = []
    if page > 0:
        navigation.append(InlineKeyboardButton(text="⬅️", callback_data=f"pg:adm:{page - 1}"))
    if end < len(apartments):
        navigation.append(InlineKeyboardButton(text="➡️", callback_data=f"pg:adm:{page + 1}"))
    if navigation:
        builder.row(*navigation)

    builder.row(InlineKeyboardButton(text=get_text("btn_add_object", lang), callback_data="add_ap"))
    builder.row(InlineKeyboardButton(text=get_text("btn_back_main", lang), callback_data="to_main"))
    return builder.as_markup()


def apartment_item_mgmt_kb(apartment_id, is_available, lang="uk", role="user"):
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text("btn_object_bookings", lang), callback_data=f"ab_{apartment_id}")

    if role == "boss":
        builder.button(text=get_text("btn_edit", lang), callback_data=f"ed_{apartment_id}")
        builder.button(
            text=get_text("btn_disable" if is_available else "btn_enable", lang),
            callback_data=f"tg_{apartment_id}",
        )
        builder.button(text=get_text("btn_delete", lang), callback_data=f"dl_{apartment_id}")

    builder.button(text=get_text("btn_back", lang), callback_data="adm_back")
    builder.adjust(1)
    return builder.as_markup()


def apartment_edit_fields_kb(apartment_id, lang="uk"):
    builder = InlineKeyboardBuilder()
    fields = [
        ("title", get_text("field_title", lang)),
        ("description", get_text("field_description", lang)),
        ("price", get_text("field_price", lang)),
        ("photo", get_text("field_photo", lang)),
        ("rooms", get_text("field_rooms", lang)),
        ("beds", get_text("field_beds", lang)),
        ("guests", get_text("field_guests", lang)),
        ("address", get_text("field_address", lang)),
        ("area", get_text("field_area", lang)),
        ("features", "Зручності" if lang == "uk" else "Features"),
    ]

    for field_key, label in fields:
        builder.button(text=label, callback_data=f"ef_{apartment_id}_{field_key}")

    builder.adjust(2)
    builder.row(InlineKeyboardButton(text=get_text("btn_back", lang), callback_data=f"m:{apartment_id}"))
    return builder.as_markup()


def staff_mgmt_inline_kb(lang="uk"):
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text("btn_staff_list", lang), callback_data="v_st")
    builder.button(text=get_text("btn_add_member", lang), callback_data="a_st")
    builder.button(text=get_text("btn_back_main", lang), callback_data="to_main")
    builder.adjust(1)
    return builder.as_markup()


def staff_delete_inline_kb(staff, lang="uk"):
    builder = InlineKeyboardBuilder()
    for member in staff:
        builder.button(text=f"🗑 {member.get('name', 'N/A')}", callback_data=f"rm_{member['user_id']}")
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text=get_text("btn_back", lang), callback_data="b_st"))
    return builder.as_markup()


def booking_action_inline_kb(booking_id, lang="uk", status="pending"):
    builder = InlineKeyboardBuilder()
    if status in {"pending_50", "paid_50"}:
        builder.button(text=get_text("btn_approve", lang), callback_data=f"ok_{booking_id}")
    builder.button(text=get_text("btn_reject", lang), callback_data=f"rj_{booking_id}")
    builder.button(text=get_text("btn_message_guest", lang), callback_data=f"ms_{booking_id}")
    builder.adjust(2)
    return builder.as_markup()


def admin_reply_inline_kb(user_id, lang="uk"):
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text("btn_reply", lang), callback_data=f"ms_u_{user_id}")
    return builder.as_markup()


def confirm_ap_add_kb(lang="uk"):
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text("btn_confirm", lang), callback_data="cf_ad")
    builder.button(text=get_text("btn_cancel", lang), callback_data="adm_back")
    return builder.as_markup()


def photo_done_kb(lang="uk"):
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text("btn_done", lang), callback_data="ph_done")
    return builder.as_markup()


def translation_confirm_kb(lang="uk"):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Все ок", callback_data="tr_ok")
    builder.button(text="📝 Змінити вручну", callback_data="tr_edit")
    builder.adjust(2)
    return builder.as_markup()


def features_selection_kb(selected_features=None, lang="uk"):
    selected_features = selected_features or []
    keys = [
        "tv",
        "fridge",
        "microwave",
        "hot_water",
        "air_conditioner",
        "near_supermarket",
        "good_transport",
        "smart_tv",
        "balcony",
        "hob",
        "internet",
        "cable_tv",
        "secure_parking",
        "coded_entry",
        "washing_machine",
        "satellite_tv",
        "t2_tv",
    ]

    builder = InlineKeyboardBuilder()
    for key in keys:
        label = FEATURE_LABELS.get(lang, FEATURE_LABELS["uk"]).get(key, key)
        prefix = "✅ " if key in selected_features else ""
        builder.button(text=f"{prefix}{label}", callback_data=f"fsel_{key}")

    builder.adjust(2)
    builder.row(InlineKeyboardButton(text=get_text("btn_done", lang), callback_data="fsel_done"))
    return builder.as_markup()
