from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, PreCheckoutQuery, LabeledPrice, FSInputFile, InlineKeyboardButton
from aiogram.filters import CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from app.databases.mongodb import upsert_user, get_user, get_apartments, get_apartment, create_booking, update_booking_status, get_booking, get_admins, get_all_admins_and_bosses, update_user_pref, is_apartment_free, find_next_free_dates, update_booking_payment, add_log
from app.keyboards.user_keyboards import main_menu_kb, apartments_inline_kb, phone_kb, ap_info_inline_kb, info_only_apartment_kb, language_kb, currency_kb, contacts_inline_kb, suggest_dates_kb, profile_phone_kb
from app.keyboards.admin_keyboards import booking_action_inline_kb
from app.utils.states import BookingStates, UserChatStates, SetupStates
from app.common.token import PAYMENT_TOKEN, BOSS_IDS, PORTMONE_LIMIT
from app.utils.currency import get_usd_rate, format_price
from app.common.texts import get_text, get_all_translations
import datetime, html, os, re, asyncio

router = Router()

BTNS_BOOKING = get_all_translations('btn_booking')
BTNS_APS = get_all_translations('btn_apartments')
BTNS_PROFILE = get_all_translations('btn_profile')
BTNS_CONTACTS = get_all_translations('btn_contacts')
BTNS_ADMIN = get_all_translations('btn_admin')
BTNS_BACK_MAIN = get_all_translations('btn_back_main')
ALL_MAIN_BTNS = BTNS_BOOKING + BTNS_APS + BTNS_PROFILE + BTNS_CONTACTS + BTNS_ADMIN + BTNS_BACK_MAIN

FEATURE_LABELS = {
    "uk": {
        "tv": "Телевізор",
        "fridge": "Холодильник",
        "microwave": "Мікрохвильова піч",
        "hot_water": "Гаряча вода",
        "air_conditioner": "Кондиціонер",
        "near_supermarket": "Поруч супермаркет",
        "good_transport": "Зручна транспортна розв'язка",
        "smart_tv": "Smart TV",
        "balcony": "Балкон",
        "hob": "Варильна поверхня",
        "internet": "Інтернет",
        "cable_tv": "Кабельне ТБ",
        "secure_parking": "Паркінг",
        "coded_entry": "Кодовий вхід",
        "washing_machine": "Пральна машина",
        "satellite_tv": "Супутникове ТБ",
        "t2_tv": "Т2 ТБ",
    },
    "en": {
        "tv": "TV",
        "fridge": "Fridge",
        "microwave": "Microwave",
        "hot_water": "Hot water",
        "air_conditioner": "Air conditioner",
        "near_supermarket": "Near supermarket",
        "good_transport": "Good transport",
        "smart_tv": "Smart TV",
        "balcony": "Balcony",
        "hob": "Cooktop",
        "internet": "Internet",
        "cable_tv": "Cable TV",
        "secure_parking": "Secure parking",
        "coded_entry": "Coded entry",
        "washing_machine": "Washing machine",
        "satellite_tv": "Satellite TV",
        "t2_tv": "T2 TV",
    },
}

def normalize_menu_text(value: str) -> str:
    text = (value or "").strip().lower()
    text = re.sub(r"[\W_]+", " ", text, flags=re.UNICODE)
    return " ".join(text.split())

def matches_any_button(text: str, variants: list[str]) -> bool:
    normalized = normalize_menu_text(text)
    return any(normalized == normalize_menu_text(variant) for variant in variants)

def detect_menu_intent(text: str) -> str | None:
    normalized = normalize_menu_text(text)

    if matches_any_button(text, BTNS_PROFILE) or "проф" in normalized or "РїСЂРѕС„" in normalized or "profile" in normalized:
        return "profile"
    if matches_any_button(text, BTNS_BOOKING) or "брон" in normalized or "Р±СЂРѕРЅ" in normalized or "booking" in normalized:
        return "booking"
    if matches_any_button(text, BTNS_APS) or "апарт" in normalized or "Р°РїР°СЂС‚" in normalized or "object" in normalized or "apartment" in normalized:
        return "apartments"
    if matches_any_button(text, BTNS_CONTACTS) or "контакт" in normalized or "РєРѕРЅС‚Р°РєС‚" in normalized or "contact" in normalized:
        return "contacts"
    if matches_any_button(text, BTNS_ADMIN) or "адмін" in normalized or "админ" in normalized or "Р°РґРјС–РЅ" in normalized or "admin" in normalized:
        return "admin"
    if matches_any_button(text, BTNS_BACK_MAIN) or "головн" in normalized or "РіРѕР»РѕРІРЅ" in normalized or "main menu" in normalized:
        return "main"
    return None

def extract_start_payload(message: Message) -> str:
    text = (message.text or "").strip()
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        return ""
    return parts[1].strip()

def resolve_apartment_image(apartment: dict):
    img_src = apartment.get('img')
    if not img_src:
        gallery = apartment.get('gallery') or []
        img_src = gallery[0] if gallery else None
    if not img_src:
        return None
    if isinstance(img_src, str) and img_src.startswith("images/"):
        local_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "Site", img_src))
        if os.path.exists(local_path):
            return FSInputFile(local_path)
    return img_src

def format_area_value(area, lang: str) -> str:
    value = str(area or "").strip()
    if not value or value in {"-", "None", "null"}:
        return "Не вказано" if lang == "uk" else "Not specified"
    lower = value.lower()
    if "м²" in lower or "m²" in lower or "sqm" in lower or "sq.m" in lower:
        return value
    if value.isdigit():
        return f"{value} м²" if lang == "uk" else f"{value} m²"
    return value

def format_feature_list(features: list[str] | None, lang: str) -> str:
    if not features:
        return "Не вказано" if lang == "uk" else "Not specified"
    labels = FEATURE_LABELS.get(lang, FEATURE_LABELS["uk"])
    return ", ".join(labels.get(feature, feature.replace("_", " ")) for feature in features)

def normalize_phone_input(raw_phone: str | None) -> str:
    digits = "".join(filter(str.isdigit, raw_phone or ""))
    return f"+{digits}" if digits else ""

def has_valid_phone(user: dict | None) -> bool:
    if not user:
        return False
    return len(normalize_phone_input(user.get("phone"))) >= 11

async def send_apartment_message(target, image, text: str, reply_markup):
    if image:
        if len(text) <= 1024:
            await safe_send(
                target.answer_photo,
                image,
                caption=text,
                reply_markup=reply_markup,
                parse_mode="HTML",
            )
            return
        await safe_send(target.answer_photo, image)
    await safe_send(target.answer, text, reply_markup=reply_markup, parse_mode="HTML")

async def safe_send(sender, *args, **kwargs):
    try:
        return await sender(*args, **kwargs)
    except Exception:
        await asyncio.sleep(1)
        return await sender(*args, **kwargs)

def build_booking_apartment_text(apartment: dict, lang: str, price_text: str) -> str:
    apartment_name = html.escape(apartment['title'].get(lang, apartment['title'].get('uk', 'Apartment')))
    if lang == "uk":
        return (
            f"🏢 <b>{apartment_name}</b>\n\n"
            f"🕒 <b>Заїзд:</b> з 12:00\n"
            f"🕙 <b>Виїзд:</b> до 10:00\n"
            f"📄 <b>Документи:</b> паспорт або ID-картка\n"
            f"💰 <b>Ціна:</b> {price_text}"
        )
    return (
        f"🏢 <b>{apartment_name}</b>\n\n"
        f"🕒 <b>Check-in:</b> from 12:00\n"
        f"🕙 <b>Check-out:</b> until 10:00\n"
        f"📄 <b>Documents:</b> passport or ID card\n"
        f"💰 <b>Price:</b> {price_text}"
    )

async def notify_admins(bot: Bot, text: str, booking_id: str | None = None, booking_status: str = "pending"):
    admins = await get_admins()
    for admin in admins:
        admin_id = admin.get("user_id")
        if not admin_id:
            continue
        try:
            reply_markup = None
            if booking_id:
                reply_markup = booking_action_inline_kb(booking_id, admin.get("language", "uk"), booking_status)
            await bot.send_message(admin_id, text, parse_mode="HTML", reply_markup=reply_markup)
        except Exception:
            pass

async def start_booking_for_apartment(event: Message | CallbackQuery, state: FSMContext, ap_id: str, lang: str):
    apartment = await get_apartment(ap_id)
    if not apartment:
        if isinstance(event, CallbackQuery):
            await event.message.answer(get_text('msg_no_apartments', lang))
            await event.answer()
        else:
            await event.answer(get_text('msg_no_apartments', lang))
        return

    checkin_example = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%d.%m.%Y")
    apartment_name = apartment.get('title', {}).get(lang, apartment.get('title', {}).get('uk', 'Apartment'))
    apartment_price = format_price(apartment.get('price', 0), await get_usd_rate(), "uah")

    await state.clear()
    await state.update_data(
        ap_id=str(apartment.get('_id')),
        ap_external_id=str(apartment.get('external_id', apartment.get('_id'))),
        ap_name=apartment_name
    )
    await state.set_state(BookingStates.waiting_checkin)
    image = resolve_apartment_image(apartment)

    prompt = (
        f"Обрано апартамент: <b>{html.escape(apartment_name)}</b>\n"
        f"Ціна за добу: <b>{apartment_price}</b>\n\n"
        f"{get_text('msg_enter_checkin', lang, date=checkin_example)}"
        if lang == "uk" else
        f"Selected apartment: <b>{html.escape(apartment_name)}</b>\n"
        f"Price per day: <b>{apartment_price}</b>\n\n"
        f"{get_text('msg_enter_checkin', lang, date=checkin_example)}"
    )

    if isinstance(event, CallbackQuery):
        if image:
            await event.message.answer_photo(image, caption=f"🏢 <b>{html.escape(apartment_name)}</b>", parse_mode="HTML")
        await event.message.answer(prompt, parse_mode="HTML")
        await event.answer()
    else:
        if image:
            await event.answer_photo(image, caption=f"🏢 <b>{html.escape(apartment_name)}</b>", parse_mode="HTML")
        await event.answer(prompt, parse_mode="HTML")

async def menu_redirect(message: Message, state: FSMContext, bot: Bot):
    t = message.text
    await state.clear()
    intent = detect_menu_intent(t)
    if intent == "profile": return await profile_h(message, state)
    if intent == "booking": return await book_h(message, state)
    if intent == "apartments": return await list_h(message, state)
    if intent == "contacts": return await contacts_h(message, state)
    if intent == "admin":
        from app.handlers.admin_handlers import admin_h
        return await admin_h(message, state)
    if intent == "main": return await start_cmd(message, state)
    return await start_cmd(message, state)

async def ensure_profile_user(event: Message | CallbackQuery):
    uid = event.from_user.id
    user = await get_user(uid)
    if not user:
        default_lang = "uk" if event.from_user.language_code in ["uk", "ru"] else "en"
        await upsert_user(
            uid,
            event.from_user.username,
            role="boss" if uid in BOSS_IDS else "user",
            name=event.from_user.full_name,
            language=default_lang,
        )
        return await get_user(uid)

    sync_data = {}
    current_username = (event.from_user.username or "").replace("@", "")
    if current_username and user.get("username") != current_username:
        sync_data["username"] = current_username
    if event.from_user.full_name and user.get("name") != event.from_user.full_name:
        sync_data["name"] = event.from_user.full_name
    if sync_data:
        await update_user_pref(uid, **sync_data)
        user = await get_user(uid)
    return user

def build_profile_keyboard(lang: str):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=get_text("btn_change_lang", lang), callback_data="profile_lang"),
        InlineKeyboardButton(text=get_text("btn_change_curr", lang), callback_data="profile_curr"),
    )
    builder.row(InlineKeyboardButton(text=get_text("btn_back", lang), callback_data="to_main"))
    builder.adjust(2, 1)
    return builder.as_markup()

def build_profile_language_keyboard(lang: str):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🇺🇦 Українська", callback_data="profile_lang_uk"),
        InlineKeyboardButton(text="🇬🇧 English", callback_data="profile_lang_en"),
    )
    builder.row(InlineKeyboardButton(text=get_text("btn_back", lang), callback_data="to_profile"))
    return builder.as_markup()

def build_profile_currency_keyboard(lang: str):
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="₴ UAH", callback_data="profile_curr_uah"),
        InlineKeyboardButton(text="$ USD", callback_data="profile_curr_usd"),
    )
    builder.row(InlineKeyboardButton(text=get_text("btn_back", lang), callback_data="to_profile"))
    return builder.as_markup()

@router.message(F.text.in_(BTNS_BACK_MAIN), StateFilter("*"))
async def back_main_handler(message: Message, state: FSMContext):
    await state.clear()
    await start_cmd(message, state)

@router.message(F.text.regexp(r"(?i)(проф|profile|РїСЂРѕС„)"), StateFilter("*"))
@router.message(F.text.in_(BTNS_PROFILE), StateFilter("*"))
@router.callback_query(F.data == "to_profile", StateFilter("*"))
async def profile_h(event: Message | CallbackQuery, state: FSMContext):
    await state.clear()
    u = await ensure_profile_user(event)
    await add_log("user", "open_profile", "User opened profile", user_id=event.from_user.id)

    l = u.get("language", "uk")
    name_raw = event.from_user.full_name or u.get("name")
    username_raw = u.get("username")
    phone_raw = u.get("phone")
    name = html.escape(name_raw) if name_raw else get_text("msg_not_set", l)
    username = f"@{html.escape(username_raw)}" if username_raw else get_text("msg_not_set", l)
    phone = html.escape(phone_raw) if phone_raw else get_text("msg_not_set", l)
    currency = u.get("currency", "uah").upper()

    txt = get_text(
        "msg_profile",
        l,
        name=name,
        username=username,
        phone=phone,
        role=get_text(f"role_{u.get('role', 'user')}", l),
        language_label=get_text(f"lang_{l}", l),
        curr=currency,
    )
    kb = build_profile_keyboard(l)

    if isinstance(event, CallbackQuery):
        try:
            await event.message.delete()
        except:
            pass
        await event.message.answer(txt, reply_markup=kb, parse_mode="HTML")
        await event.answer()
    else:
        await event.answer(txt, reply_markup=kb, parse_mode="HTML")

@router.message(CommandStart(), StateFilter("*"))
async def start_cmd(message: Message, state: FSMContext):
    payload = extract_start_payload(message)
    await state.clear()
    uid = message.from_user.id
    u = await get_user(uid)
    if not u:
        r = "boss" if uid in BOSS_IDS else "user"
        l = "uk" if message.from_user.language_code in ["uk", "ru"] else "en"
        await upsert_user(uid, message.from_user.username, role=r, name=message.from_user.full_name, language=l)
        u = await get_user(uid)
        await add_log("user", "first_start", "New user started bot", user_id=uid, extra={"payload": payload})
    await add_log("user", "start", "User triggered /start", user_id=uid, extra={"payload": payload})
    
    l = u.get('language', 'uk')
    if not u.get('currency'):
        if payload:
            await state.update_data(pending_start_payload=payload)
        await message.answer(get_text('msg_choose_currency', l), reply_markup=currency_kb())
        await state.set_state(SetupStates.choosing_currency)
        return
    if payload.startswith("book_"):
        await start_booking_for_apartment(message, state, payload[5:], l)
        return
    await message.answer(get_text('msg_welcome', l), reply_markup=main_menu_kb(u.get('role', 'user'), l), parse_mode="HTML")

@router.message(F.text.in_(BTNS_BOOKING), StateFilter("*"))
async def book_h(message: Message, state: FSMContext):
    await state.clear()
    u = await get_user(message.from_user.id)
    l = u.get('language', 'uk') if u else 'uk'
    aps = await get_apartments(only_available=True)
    await add_log("user", "open_booking", f"Opened booking list with {len(aps)} apartments", user_id=message.from_user.id)
    await message.answer(get_text('msg_choose_apartment', l), reply_markup=apartments_inline_kb(aps, True, l))
    await state.set_state(BookingStates.choosing_apartment)

@router.message(F.text.in_(BTNS_APS), StateFilter("*"))
async def list_h(message: Message, state: FSMContext):
    await state.clear()
    u = await get_user(message.from_user.id)
    l = u.get('language', 'uk') if u else 'uk'
    aps = await get_apartments(only_available=True)
    await add_log("user", "open_apartments", f"Opened apartments list with {len(aps)} apartments", user_id=message.from_user.id)
    await message.answer(get_text('msg_our_apartments', l), reply_markup=apartments_inline_kb(aps, False, l), parse_mode="HTML")

@router.message(F.text.in_(BTNS_CONTACTS), StateFilter("*"))
async def contacts_h(message: Message, state: FSMContext):
    await state.clear()
    u = await get_user(message.from_user.id)
    l = u.get('language', 'uk') if u else 'uk'
    await add_log("user", "open_contacts", "Opened contacts", user_id=message.from_user.id)
    await message.answer(get_text('msg_contacts', l), reply_markup=contacts_inline_kb(l), parse_mode="HTML")

@router.callback_query(F.data.startswith("v:"), StateFilter("*"))
async def view_apartment_h(callback: CallbackQuery, state: FSMContext):
    u = await get_user(callback.from_user.id)
    l = u.get('language', 'uk')
    ap_id = callback.data[2:]
    ap = await get_apartment(ap_id)

    if not ap:
        await callback.answer(get_text('msg_no_apartments', l), show_alert=True)
        return
    await add_log("user", "view_apartment", f"Viewed apartment {ap_id}", user_id=callback.from_user.id)

    rate = await get_usd_rate()
    ap_name = html.escape(ap['title'].get(l, ap['title'].get('uk', 'Apartment')))
    ap_desc = html.escape(ap.get('description', {}).get(l, ap.get('description', {}).get('uk', '')))
    ap_area = html.escape(format_area_value(ap.get('area'), l))
    ap_price = format_price(ap.get('price', 0), rate, u.get('currency', 'uah'))
    ap_features = html.escape(format_feature_list(ap.get('features', []), l))
    ap_lat = ap.get('lat', 0)
    ap_lng = ap.get('lng', 0)

    txt = get_text(
        'msg_ap_info',
        l,
        name=ap_name,
        desc=ap_desc,
        guests=ap.get('guests', '-'),
        rooms=ap.get('rooms', '-'),
        beds=ap.get('beds', '-'),
        area=ap_area,
        features=ap_features,
        price=ap_price
    )

    await state.update_data(last_list_mode="list")
    image = resolve_apartment_image(ap)
    await send_apartment_message(
        callback.message,
        image,
        txt,
        info_only_apartment_kb(str(ap.get('external_id', ap['_id'])), ap_lat, ap_lng, l, ap.get("route_url")),
    )
    await callback.answer()

@router.callback_query(F.data == "to_list", StateFilter("*"))
async def to_list_h(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    u = await get_user(callback.from_user.id)
    l = u.get('language', 'uk')
    mode = data.get("last_list_mode", "list")
    aps = await get_apartments(only_available=True)

    if mode == "book":
        await callback.message.answer(get_text('msg_choose_apartment', l), reply_markup=apartments_inline_kb(aps, True, l))
        await state.set_state(BookingStates.choosing_apartment)
    else:
        await callback.message.answer(get_text('msg_our_apartments', l), reply_markup=apartments_inline_kb(aps, False, l), parse_mode="HTML")

    await callback.answer()

@router.callback_query(F.data.startswith("b:"), StateFilter("*"))
async def book_apartment_h(callback: CallbackQuery, state: FSMContext):
    u = await get_user(callback.from_user.id)
    l = u.get('language', 'uk')
    ap_id = callback.data[2:]
    ap = await get_apartment(ap_id)

    if not ap:
        await callback.answer(get_text('msg_no_apartments', l), show_alert=True)
        return
    await add_log("user", "select_apartment_for_booking", f"Selected apartment {ap_id} for booking", user_id=callback.from_user.id)

    await state.update_data(
        ap_id=str(ap.get('_id')),
        ap_external_id=str(ap.get('external_id', ap.get('_id'))),
        ap_name=ap['title'].get(l, ap['title'].get('uk', 'Apartment')),
        last_list_mode="book"
    )

    ap_price = format_price(ap.get('price', 0), await get_usd_rate(), u.get('currency', 'uah'))
    info_text = build_booking_apartment_text(ap, l, ap_price)
    image = resolve_apartment_image(ap)

    if not has_valid_phone(u):
        await send_apartment_message(callback.message, image, info_text, None)
        await safe_send(callback.message.answer, get_text('msg_enter_phone', l), reply_markup=phone_kb(l))
        await state.set_state(BookingStates.entering_phone)
        await callback.answer()
        return

    checkin_example = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%d.%m.%Y")
    await send_apartment_message(callback.message, image, info_text, None)
    checkin_prompt = (
        f"Обрано апартамент: <b>{html.escape(ap['title'].get(l, ap['title'].get('uk', 'Apartment')))}</b>\n"
        f"Ціна за добу: <b>{ap_price}</b>\n\n"
        f"{get_text('msg_enter_checkin', l, date=checkin_example)}"
        if l == "uk" else
        f"Selected apartment: <b>{html.escape(ap['title'].get(l, ap['title'].get('uk', 'Apartment')))}</b>\n"
        f"Price per day: <b>{ap_price}</b>\n\n"
        f"{get_text('msg_enter_checkin', l, date=checkin_example)}"
    )
    await safe_send(callback.message.answer, checkin_prompt, parse_mode="HTML")
    await state.set_state(BookingStates.waiting_checkin)
    await callback.answer()

@router.message(BookingStates.entering_phone)
async def booking_phone_in(message: Message, state: FSMContext, bot: Bot):
    if detect_menu_intent(message.text):
        return await menu_redirect(message, state, bot)

    u = await get_user(message.from_user.id)
    l = u.get('language', 'uk') if u else 'uk'
    p = normalize_phone_input(message.contact.phone_number if message.contact else message.text)
    if len(p) < 11:
        return await message.answer(get_text('msg_enter_phone', l), reply_markup=phone_kb(l))

    await update_user_pref(message.from_user.id, phone=p)
    u = await get_user(message.from_user.id)
    l = u.get('language', 'uk')
    checkin_example = (datetime.datetime.now() + datetime.timedelta(days=1)).strftime("%d.%m.%Y")
    await message.answer(get_text('msg_phone_saved', l, date=checkin_example), parse_mode="HTML")
    await state.set_state(BookingStates.waiting_checkin)

@router.message(BookingStates.waiting_checkin)
async def checkin_in(message: Message, state: FSMContext, bot: Bot):
    if detect_menu_intent(message.text): return await menu_redirect(message, state, bot)
    t = message.text.strip().replace('/', '.').replace('-', '.').replace(' ', '.')
    try:
        parts = t.split('.')
        d, m, y = int(parts[0]), int(parts[1]), int(parts[2])
        if y < 100: y += 2000
        dt = datetime.datetime(y, m, d)
    except: return await message.answer(get_text('msg_invalid_date', 'uk'))
    
    u = await get_user(message.from_user.id)
    l = u.get('language', 'uk') if u else 'uk'
    now = datetime.datetime.now()
    checkin_at = dt.replace(hour=12, minute=0, second=0, microsecond=0)
    if checkin_at <= now:
        return await message.answer(get_text('msg_invalid_date', l))
    if checkin_at < now + datetime.timedelta(hours=24):
        return await message.answer(get_text('msg_date_too_early', l))
    if checkin_at > now + datetime.timedelta(days=120):
        text = (
            "❌ Бронювання доступне лише на 4 місяці вперед. Оберіть ближчу дату заїзду."
            if l == "uk" else
            "❌ Booking is available only up to 4 months ahead. Please choose an earlier check-in date."
        )
        return await message.answer(text)

    await state.update_data(checkin=dt, checkin_str=dt.strftime("%d.%m.%Y"))
    await message.answer(get_text('msg_enter_checkout', l), parse_mode="HTML")
    await state.set_state(BookingStates.waiting_checkout)

@router.message(BookingStates.waiting_checkout)
async def checkout_in(message: Message, state: FSMContext, bot: Bot):
    if detect_menu_intent(message.text): return await menu_redirect(message, state, bot)
    t = message.text.strip().replace('/', '.').replace('-', '.').replace(' ', '.')
    try:
        parts = t.split('.')
        d, m, y = int(parts[0]), int(parts[1]), int(parts[2])
        if y < 100: y += 2000
        dt = datetime.datetime(y, m, d)
    except: return await message.answer(get_text('msg_invalid_date', 'uk'))
    
    data = await state.get_data()
    u = await get_user(message.from_user.id)
    l = u.get('language', 'uk') if u else 'uk'
    if dt <= data['checkin']:
        return await message.answer(get_text('msg_checkout_after_checkin', l))
    if (dt - data['checkin']).days > 31:
        text = (
            "❌ Максимальна тривалість бронювання 1 місяць. Оберіть ближчу дату виїзду."
            if l == "uk" else
            "❌ Maximum booking length is 1 month. Please choose an earlier check-out date."
        )
        return await message.answer(text)

    await state.update_data(checkout_str=dt.strftime("%d.%m.%Y"), days=(dt - data['checkin']).days)
    await message.answer(get_text('msg_wishes', l))
    await state.set_state(BookingStates.entering_wishes)

@router.message(BookingStates.entering_wishes)
async def wishes_in(message: Message, state: FSMContext, bot: Bot):
    if detect_menu_intent(message.text):
        return await menu_redirect(message, state, bot)

    data = await state.get_data()
    user = await get_user(message.from_user.id)
    lang = user.get("language", "uk")
    apartment = await get_apartment(data.get("ap_id"))
    if not apartment:
        await state.clear()
        await message.answer(get_text("msg_no_apartments", lang))
        return

    wishes = (message.text or "").strip()
    if wishes.lower() in {"ні", "нет", "no", "-", "нема", "none"}:
        wishes = ""

    is_free, next_date = await is_apartment_free(data["ap_id"], data["checkin_str"], data["checkout_str"])
    if not is_free:
        if next_date:
            await message.answer(get_text("msg_already_booked", lang, next_date=next_date, duration=data["days"]))
        else:
            await message.answer(get_text("msg_no_apartments", lang))
        suggestions = await find_next_free_dates(data["ap_id"], data["checkin_str"], data["days"])
        if suggestions:
            await message.answer(get_text("msg_enter_checkin", lang, date=suggestions[0].strftime("%d.%m.%Y")), reply_markup=suggest_dates_kb(suggestions, lang))
        await state.set_state(BookingStates.waiting_checkin)
        return

    total_price = int(apartment.get("price", 0)) * int(data.get("days", 1))
    booking_id = await create_booking(
        message.from_user.id,
        data["ap_id"],
        data["checkin_str"],
        data["checkout_str"],
        user.get("phone", ""),
        wishes,
        total_price,
    )

    rate = await get_usd_rate()
    preferred_currency = user.get("currency", "uah")
    prepayment_amount = int(total_price * 0.5)
    ap_name = apartment["title"].get(lang, apartment["title"].get("uk", "Apartment"))
    price_text = format_price(prepayment_amount, rate, preferred_currency)
    split_note = ""
    if prepayment_amount > PORTMONE_LIMIT:
        split_note = (
            f"\n\n⚠️ Передплата перевищує ліміт Portmone {PORTMONE_LIMIT} грн, тому кнопки нижче розіб’ють оплату на кілька частин."
            if lang == "uk" else
            f"\n\n⚠️ The prepayment exceeds the Portmone limit of {PORTMONE_LIMIT} UAH, so the buttons below will split it into several payments."
        )
    flow_note = (
        "\n\n<b>Як проходить оплата:</b>\n1. Зараз сплачується 50% для підтвердження броні.\n2. Ще 50% сплачується в день заїзду.\n3. Це потрібно, щоб закріпити дати за вами і зменшити ризик скасувань."
        if lang == "uk" else
        "\n\n<b>How payment works:</b>\n1. You pay 50% now to confirm the booking.\n2. The remaining 50% is paid on the check-in day.\n3. This secures your dates and reduces cancellation risk."
    )

    await state.clear()
    await message.answer(
        get_text(
            "msg_order_created",
            lang,
            ap_name=html.escape(ap_name),
            checkin=data["checkin_str"],
            checkout=data["checkout_str"],
            price=price_text,
        ) + flow_note + split_note,
        reply_markup=ap_info_inline_kb(apartment.get("lat", 0), apartment.get("lng", 0), str(booking_id), lang, amount=prepayment_amount, route_url=apartment.get("route_url")),
        parse_mode="HTML",
    )
@router.callback_query(F.data.startswith("suggest_"), StateFilter("*"))
async def suggest_date_h(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(callback.data.split("_", 1)[1])
    await callback.answer()

@router.callback_query(F.data.startswith("p50"), StateFilter("*"))
async def pay_booking_h(callback: CallbackQuery):
    user = await get_user(callback.from_user.id)
    lang = user.get("language", "uk") if user else "uk"
    if not PAYMENT_TOKEN:
        await callback.answer("Payment token is not configured", show_alert=True)
        return

    payload = callback.data
    is_final = payload.startswith("p50_final_")
    parts = payload.split("_")
    booking_id = parts[2] if is_final else parts[1]
    custom_amount = int(parts[3]) if len(parts) > 3 else None
    booking = await get_booking(booking_id)
    if not booking:
        await callback.answer(get_text("msg_list_empty", lang), show_alert=True)
        return
    if is_final:
        remaining_to_pay = int(booking.get("remaining", 0) - booking.get("paid_remaining", 0))
        if booking.get("status") == "confirmed" or remaining_to_pay <= 0:
            await callback.answer(get_text("msg_already_paid", lang), show_alert=True)
            return
    else:
        prepayment_to_pay = int(booking.get("prepayment", 0) - booking.get("paid_prepayment", 0))
        if booking.get("status") in {"paid_50", "confirmed"} or prepayment_to_pay <= 0:
            await callback.answer(get_text("msg_already_paid", lang), show_alert=True)
            return

    amount = custom_amount
    if amount is None:
        amount = int(
            booking["remaining"] - booking.get("paid_remaining", 0)
            if is_final else
            booking["prepayment"] - booking.get("paid_prepayment", 0)
        )

    description_key = "msg_invoice_desc_balance" if is_final else "msg_invoice_desc_prepayment"
    await callback.message.answer_invoice(
        title="G.I.L Apartments",
        description=get_text(description_key, lang),
        payload=f"booking:{booking_id}:{amount}:{1 if is_final else 0}",
        provider_token=PAYMENT_TOKEN,
        currency="UAH",
        prices=[LabeledPrice(label="G.I.L Apartments", amount=amount * 100)],
    )
    await callback.answer()

@router.pre_checkout_query()
async def pre_checkout_h(pre_checkout_query: PreCheckoutQuery):
    await pre_checkout_query.answer(ok=True)

@router.message(F.successful_payment)
async def successful_payment_h(message: Message, bot: Bot):
    payment = message.successful_payment
    payload = payment.invoice_payload or ""
    if not payload.startswith("booking:"):
        return

    _, booking_id, amount_raw, is_final_raw = payload.split(":")
    amount = int(amount_raw)
    is_final = is_final_raw == "1"
    user = await get_user(message.from_user.id)
    lang = user.get("language", "uk") if user else "uk"
    current_booking = await get_booking(booking_id)
    if not current_booking:
        return
    if is_final:
        remaining_to_pay = int(current_booking.get("remaining", 0) - current_booking.get("paid_remaining", 0))
        if current_booking.get("status") == "confirmed" or remaining_to_pay <= 0:
            await message.answer(get_text("msg_already_paid", lang))
            return
        amount = min(amount, remaining_to_pay)
    else:
        prepayment_to_pay = int(current_booking.get("prepayment", 0) - current_booking.get("paid_prepayment", 0))
        if current_booking.get("status") in {"paid_50", "confirmed"} or prepayment_to_pay <= 0:
            await message.answer(get_text("msg_already_paid", lang))
            return
        amount = min(amount, prepayment_to_pay)

    booking = await update_booking_payment(booking_id, amount, is_final)
    if not booking:
        return

    if is_final:
        await update_booking_status(booking_id, "confirmed")
    else:
        await update_booking_status(booking_id, "paid_50")

    apartment = await get_apartment(booking["ap_id"])
    lat = apartment.get("lat", 0) if apartment else 0
    lng = apartment.get("lng", 0) if apartment else 0
    text_key = "msg_payment_completed" if is_final else "msg_prepayment_received"
    extra_note = (
        "\n\n💡 У день заїзду бот нагадає вам про оплату залишку 50%."
        if (lang == "uk" and not is_final) else
        "\n\n💡 The bot will remind you on the check-in day about the remaining 50% payment."
        if not is_final else
        ""
    )
    await message.answer(
        get_text(text_key, lang) + extra_note,
        reply_markup=ap_info_inline_kb(
            lat,
            lng,
            None if is_final else str(booking_id),
            lang,
            amount=max(0, int(booking.get("remaining", 0) - booking.get("paid_remaining", 0))),
            is_final=True,
            route_url=apartment.get("route_url") if apartment else None,
        ),
        parse_mode="HTML",
    )
    apartment_name = apartment["title"].get(lang, apartment["title"].get("uk", "Apartment")) if apartment else "Apartment"
    await notify_admins(
        bot,
        (
            f"💳 <b>{'Оплачено повністю' if is_final else 'Отримано 50% передплати'}</b>\n\n"
            f"🏢 <b>Об'єкт:</b> {html.escape(apartment_name)}\n"
            f"🗓 <b>Дати:</b> {booking['start_date']} - {booking['end_date']}\n"
            f"💰 <b>Сума:</b> {amount} грн\n"
            f"👤 <b>Гість:</b> {html.escape(user.get('name') or message.from_user.full_name or 'Guest')}\n"
            f"📞 <b>Телефон:</b> <code>{html.escape(user.get('phone') or '-')}</code>"
        ),
        booking_id=str(booking_id),
        booking_status="confirmed" if is_final else "paid_50",
    )

@router.callback_query(F.data == "profile_complete", StateFilter("*"))
async def complete_profile_h(callback: CallbackQuery, state: FSMContext):
    u = await ensure_profile_user(callback)
    l = u.get('language', 'uk')
    await callback.message.answer(get_text('msg_enter_phone', l), reply_markup=profile_phone_kb(l))
    await state.set_state(SetupStates.completing_profile_phone)
    await callback.answer()

@router.callback_query(F.data == "profile_phone", StateFilter("*"))
async def ch_phone_h(callback: CallbackQuery, state: FSMContext):
    u = await ensure_profile_user(callback)
    l = u.get('language', 'uk')
    await callback.message.answer(get_text('msg_enter_phone', l), reply_markup=profile_phone_kb(l))
    await state.set_state(SetupStates.changing_phone)
    await callback.answer()

@router.message(SetupStates.changing_phone)
async def changing_phone_in(message: Message, state: FSMContext, bot: Bot):
    if detect_menu_intent(message.text): 
        return await menu_redirect(message, state, bot)
    p = message.contact.phone_number if message.contact else message.text
    if not p: return
    p = "".join(filter(str.isdigit, p))
    if not p.startswith('+'): p = '+' + p
    await update_user_pref(message.from_user.id, phone=p)
    await add_log("user", "change_phone", "User changed phone", user_id=message.from_user.id, extra={"phone": p})
    u = await get_user(message.from_user.id)
    await message.answer(get_text('msg_phone_changed', u.get('language', 'uk') if u else 'uk'))
    await profile_h(message, state)

@router.message(SetupStates.completing_profile_phone)
async def complete_phone_in(message: Message, state: FSMContext, bot: Bot):
    if detect_menu_intent(message.text): return await menu_redirect(message, state, bot)
    p = message.contact.phone_number if message.contact else message.text
    if not p: return
    p = "".join(filter(str.isdigit, p))
    if not p.startswith('+'): p = '+' + p
    await upsert_user(message.from_user.id, phone=p)
    await add_log("user", "complete_profile_phone", "User completed phone in profile", user_id=message.from_user.id, extra={"phone": p})
    await state.clear()
    await profile_h(message, state)

@router.callback_query(F.data == "u_ans", StateFilter("*"))
async def user_reply_start_h(callback: CallbackQuery, state: FSMContext):
    user = await get_user(callback.from_user.id)
    lang = user.get("language", "uk") if user else "uk"
    await state.set_state(UserChatStates.writing_to_admin)
    await callback.message.answer(get_text("msg_write_to_admin", lang))
    await callback.answer()

@router.message(UserChatStates.writing_to_admin)
async def user_reply_to_staff_h(message: Message, state: FSMContext, bot: Bot):
    if detect_menu_intent(message.text):
        return await menu_redirect(message, state, bot)

    user = await get_user(message.from_user.id)
    lang = user.get("language", "uk") if user else "uk"
    staff = await get_all_admins_and_bosses()
    if not staff:
        await state.clear()
        await message.answer(get_text("msg_list_empty", lang))
        return

    sender_name = html.escape(user.get("name") or message.from_user.full_name or "Guest") if user else html.escape(message.from_user.full_name or "Guest")
    sender_username = html.escape((user.get("username") if user else message.from_user.username) or "-")
    sender_text = html.escape(message.text or "")

    sent = False
    for staff_member in staff:
        staff_id = staff_member.get("user_id")
        if not staff_id:
            continue
        try:
            staff_lang = staff_member.get("language", "uk")
            notice = (
                f"✉️ <b>Нове повідомлення від гостя</b>\n\n"
                f"👤 <b>Гість:</b> {sender_name} (@{sender_username})\n"
                f"🆔 <code>{message.from_user.id}</code>\n\n"
                f"💬 <b>Повідомлення:</b>\n{sender_text}"
                if staff_lang == "uk" else
                f"✉️ <b>New message from guest</b>\n\n"
                f"👤 <b>Guest:</b> {sender_name} (@{sender_username})\n"
                f"🆔 <code>{message.from_user.id}</code>\n\n"
                f"💬 <b>Message:</b>\n{sender_text}"
            )
            try:
                await bot.send_message(staff_id, notice, parse_mode="HTML", reply_markup=admin_reply_inline_kb(message.from_user.id, staff_lang))
                sent = True
            except Exception:
                await asyncio.sleep(1)
                await bot.send_message(staff_id, notice, parse_mode="HTML", reply_markup=admin_reply_inline_kb(message.from_user.id, staff_lang))
                sent = True
        except Exception:
            pass

    await state.clear()
    await message.answer(get_text("msg_sent_to_admin", lang if sent else "uk"))

@router.callback_query(F.data == "to_main", StateFilter("*"))
async def to_main_h(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    uid = callback.from_user.id
    u = await get_user(uid)
    if not u:
        r = "boss" if uid in BOSS_IDS else "user"
        l = "uk" if callback.from_user.language_code in ["uk", "ru"] else "en"
        await upsert_user(uid, callback.from_user.username, role=r, name=callback.from_user.full_name, language=l)
        u = await get_user(uid)
    
    l = u.get('language', 'uk')
    if not u.get('currency'):
        await callback.message.answer(get_text('msg_choose_currency', l), reply_markup=currency_kb())
        await state.set_state(SetupStates.choosing_currency)
    else:
        await callback.message.answer(get_text('msg_welcome', l), reply_markup=main_menu_kb(u.get('role','user'), l), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "profile_lang", StateFilter("*"))
async def profile_lang_h(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SetupStates.choosing_language)
    user = await ensure_profile_user(callback)
    lang = user.get("language", "uk")
    await add_log("user", "open_language_picker", "Opened language picker", user_id=callback.from_user.id)
    await callback.message.answer(get_text("msg_choose_lang", lang), reply_markup=build_profile_language_keyboard(lang))
    await callback.answer()

@router.callback_query(F.data.startswith("profile_lang_"), StateFilter("*"))
async def profile_lang_set_h(callback: CallbackQuery, state: FSMContext):
    language = callback.data.removeprefix("profile_lang_")
    await update_user_pref(callback.from_user.id, language=language)
    await add_log("user", "change_language", f"Changed language to {language}", user_id=callback.from_user.id)
    await state.clear()
    await profile_h(callback, state)

@router.callback_query(F.data == "profile_curr", StateFilter("*"))
async def profile_curr_h(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SetupStates.choosing_currency)
    user = await ensure_profile_user(callback)
    lang = user.get("language", "uk") if user else "uk"
    await add_log("user", "open_currency_picker", "Opened currency picker", user_id=callback.from_user.id)
    await callback.message.answer(get_text("msg_choose_currency", lang), reply_markup=build_profile_currency_keyboard(lang))
    await callback.answer()

@router.callback_query(F.data.startswith("profile_curr_"), StateFilter("*"))
async def profile_curr_set_h(callback: CallbackQuery, state: FSMContext):
    currency = callback.data.removeprefix("profile_curr_").lower()
    await update_user_pref(callback.from_user.id, currency=currency)
    await add_log("user", "change_currency", f"Changed currency to {currency}", user_id=callback.from_user.id)
    await state.clear()
    await profile_h(callback, state)

@router.callback_query(F.data.startswith("sc_"), StateFilter("*"))
async def sc_h(callback: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    currency = callback.data[3:].upper()
    user = await get_user(callback.from_user.id)
    await update_user_pref(callback.from_user.id, currency=currency.lower())
    payload = data.get("pending_start_payload", "")
    await state.clear()
    if payload.startswith("book_"):
        u = await get_user(callback.from_user.id)
        await start_booking_for_apartment(callback, state, payload[5:], u.get('language', 'uk'))
        return
    await profile_h(callback, state)

@router.message(F.text, StateFilter("*"))
async def main_menu_fallback_h(message: Message, state: FSMContext, bot: Bot):
    if detect_menu_intent(message.text):
        return await menu_redirect(message, state, bot)
