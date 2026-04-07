from aiogram.fsm.state import State, StatesGroup

class BookingStates(StatesGroup):
    choosing_apartment = State()
    entering_phone = State()
    waiting_checkin = State()
    waiting_checkout = State()
    entering_wishes = State()

class SetupStates(StatesGroup):
    choosing_language = State()
    choosing_currency = State()
    changing_name = State()
    changing_phone = State()
    completing_profile_name = State()
    completing_profile_phone = State()

class AdminStates(StatesGroup):
    adding_apartment_name = State()
    confirming_name_translation = State()
    adding_apartment_desc = State()
    confirming_desc_translation = State()
    adding_apartment_rooms = State()
    adding_apartment_beds = State()
    adding_apartment_area = State()
    adding_apartment_guests = State()
    adding_apartment_address = State()
    adding_apartment_price = State()
    adding_apartment_photo = State()
    adding_apartment_features = State()
    editing_apartment_field = State()
    searching_user = State()
    adding_staff_name = State()
    adding_staff_role = State()
    confirming_staff = State()
    replying_to_user = State()

class UserChatStates(StatesGroup):
    writing_to_admin = State()
    viewing_apartments = State()