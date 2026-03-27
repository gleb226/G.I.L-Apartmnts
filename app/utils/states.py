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

class AdminStates(StatesGroup):
    adding_apartment_name = State()
    adding_apartment_desc = State()
    adding_apartment_rooms = State()
    adding_apartment_beds = State()
    adding_apartment_area = State()
    adding_apartment_guests = State()
    adding_apartment_address = State()
    adding_apartment_price = State()
    adding_apartment_photo = State()
    
    editing_apartment_field = State()

    searching_user = State()
    adding_staff_id = State()
    adding_staff_role = State()
    adding_staff_name = State()
    replying_to_user = State()

class UserChatStates(StatesGroup):
    writing_to_admin = State()
    viewing_apartments = State()
