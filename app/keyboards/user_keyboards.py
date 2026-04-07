from aiogram.types import KeyboardButton, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from app.common.texts import get_text
from app.common.token import PORTMONE_LIMIT


def main_menu_kb(role="user", lang="uk"):
    builder = ReplyKeyboardBuilder()
    builder.add(KeyboardButton(text=get_text("btn_booking", lang)))
    builder.add(KeyboardButton(text=get_text("btn_apartments", lang)))
    builder.add(KeyboardButton(text=get_text("btn_profile", lang)))
    builder.add(KeyboardButton(text=get_text("btn_contacts", lang)))
    if role in ["admin", "boss"]:
        builder.add(KeyboardButton(text=get_text("btn_admin", lang)))
    builder.adjust(2)
    return builder.as_markup(resize_keyboard=True)


def phone_kb(lang="uk"):
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text=get_text("btn_provide_phone", lang), request_contact=True))
    builder.row(KeyboardButton(text=get_text("btn_back", lang)))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def apartments_inline_kb(apartments, for_booking=True, lang="uk", page=0):
    builder = InlineKeyboardBuilder()
    per_page = 12
    start, end = page * per_page, (page + 1) * per_page
    current_apartments = apartments[start:end]
    prefix = "b:" if for_booking else "v:"
    icon = "🗓" if for_booking else "📍"

    for apartment in current_apartments:
        title = apartment["title"].get(lang, apartment["title"].get("uk", "Apartment"))
        apartment_id = str(apartment.get("external_id", apartment["_id"]))
        builder.button(text=f"{icon} {title}", callback_data=f"{prefix}{apartment_id}")

    builder.adjust(1)

    navigation = []
    mode = "book" if for_booking else "list"
    if page > 0:
        navigation.append(InlineKeyboardButton(text="⬅️", callback_data=f"pg:{mode}:{page - 1}"))
    if end < len(apartments):
        navigation.append(InlineKeyboardButton(text="➡️", callback_data=f"pg:{mode}:{page + 1}"))
    if navigation:
        builder.row(*navigation)

    builder.row(InlineKeyboardButton(text=get_text("btn_back", lang), callback_data="to_main"))
    return builder.as_markup()


def info_only_apartment_kb(apartment_id, lat, lng, lang="uk", route_url=None):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=get_text("btn_book_action", lang), callback_data=f"b:{apartment_id}"))
    builder.row(InlineKeyboardButton(text=get_text("btn_route", lang), url=route_url or f"https://www.google.com/maps/dir/?api=1&destination={lat},{lng}"))
    builder.row(InlineKeyboardButton(text=get_text("btn_back", lang), callback_data="to_list"))
    return builder.as_markup()


def suggest_dates_kb(dates, lang="uk"):
    builder = InlineKeyboardBuilder()
    for date_value in dates:
        formatted = date_value.strftime("%d.%m.%Y")
        builder.button(text=f"🗓 {formatted}", callback_data=f"suggest_{formatted}")
    builder.button(text=get_text("btn_back", lang), callback_data="to_main")
    builder.adjust(1)
    return builder.as_markup()


def ap_info_inline_kb(lat, lng, booking_id=None, lang="uk", amount=0, is_final=False, route_url=None):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=get_text("btn_route", lang), url=route_url or f"https://www.google.com/maps/dir/?api=1&destination={lat},{lng}"))

    if booking_id and int(amount or 0) > 0:
        suffix = "_final" if is_final else ""
        if amount > PORTMONE_LIMIT:
            parts = (int(amount) + PORTMONE_LIMIT - 1) // PORTMONE_LIMIT
            for index in range(parts):
                value = PORTMONE_LIMIT if index < parts - 1 else int(amount) - (parts - 1) * PORTMONE_LIMIT
                builder.row(
                    InlineKeyboardButton(
                        text=get_text("btn_pay_part", lang, part=index + 1, amount=value),
                        callback_data=f"p50{suffix}_{booking_id}_{value}",
                    )
                )
        else:
            builder.row(
                InlineKeyboardButton(
                    text=get_text("btn_pay_balance" if is_final else "btn_pay_50", lang),
                    callback_data=f"p50{suffix}_{booking_id}",
                )
            )

    builder.row(InlineKeyboardButton(text=get_text("btn_back", lang), callback_data="to_main"))
    return builder.as_markup()


def user_reply_inline_kb(lang="uk"):
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text("btn_reply", lang), callback_data="u_ans")
    return builder.as_markup()


def language_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="🇺🇦 Українська", callback_data="sl_uk")
    builder.button(text="🇬🇧 English", callback_data="sl_en")
    builder.adjust(2)
    return builder.as_markup()


def currency_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="₴ UAH", callback_data="sc_uah")
    builder.button(text="$ USD", callback_data="sc_usd")
    builder.adjust(2)
    return builder.as_markup()


def settings_kb(lang="uk"):
    builder = InlineKeyboardBuilder()
    builder.button(text=get_text("btn_change_name", lang), callback_data="ch_name")
    builder.button(text=get_text("btn_change_phone", lang), callback_data="ch_phone")
    builder.button(text=get_text("btn_change_lang", lang), callback_data="ch_lang")
    builder.button(text=get_text("btn_change_curr", lang), callback_data="ch_curr")
    builder.button(text=get_text("btn_back", lang), callback_data="to_main")
    builder.adjust(1)
    return builder.as_markup()


def profile_phone_kb(lang="uk"):
    builder = ReplyKeyboardBuilder()
    builder.row(KeyboardButton(text=get_text("btn_provide_phone", lang), request_contact=True))
    builder.row(KeyboardButton(text=get_text("btn_back", lang)))
    return builder.as_markup(resize_keyboard=True, one_time_keyboard=True)


def contacts_inline_kb(lang="uk"):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📸 Instagram", url="https://instagram.com/gil_apartments"))
    builder.row(InlineKeyboardButton(text="📱 Telegram", url="https://t.me/gil_apartments_admin"))
    builder.row(InlineKeyboardButton(text=get_text("btn_back", lang), callback_data="to_main"))
    return builder.as_markup()
