from motor.motor_asyncio import AsyncIOMotorClient
from app.common.token import MONGODB_URI, BOSS_IDS
from bson import ObjectId
import datetime

client = AsyncIOMotorClient(MONGODB_URI)
db = client.get_database("gil_apartments")
users_col = db.users
apartments_col = db.apartments
bookings_col = db.bookings
errors_col = db.errors

async def get_user(user_id):
    return await users_col.find_one({"user_id": user_id})

async def get_user_by_query(query):
    return await users_col.find_one(query)

async def upsert_user(user_id, username=None, phone=None, role="user", name=None, language=None, currency=None):
    update_data = {"user_id": user_id}
    if username: update_data["username"] = username
    if phone: update_data["phone"] = phone
    if name: update_data["name"] = name
    if language: update_data["language"] = language
    if currency: update_data["currency"] = currency
    
    if user_id in BOSS_IDS:
        update_data["role"] = "boss"
    elif role != "user":
        update_data["role"] = role

    user = await get_user(user_id)
    if not user:
        if "role" not in update_data:
            update_data["role"] = role
        await users_col.insert_one(update_data)
    else:
        await users_col.update_one({"user_id": user_id}, {"$set": update_data})

async def update_user_pref(user_id, **kwargs):
    await users_col.update_one({"user_id": user_id}, {"$set": kwargs})

async def set_user_role(user_id, role):
    await users_col.update_one({"user_id": user_id}, {"$set": {"role": role}})

async def get_admins():
    return await users_col.find({"role": "admin"}).to_list(None)

async def get_all_admins_and_bosses():
    return await users_col.find({"role": {"$in": ["admin", "boss"]}}).to_list(None)

async def get_apartments(only_available=False):
    q = {}
    if only_available:
        q = {"is_available": True}
    return await apartments_col.find(q).to_list(None)

async def get_apartment(ap_id):
    try:
        return await apartments_col.find_one({"_id": ObjectId(ap_id)})
    except:
        return None

async def add_apartment(data: dict):
    if "is_available" not in data:
        data["is_available"] = True
    await apartments_col.insert_one(data)

async def delete_apartment(ap_id):
    await apartments_col.delete_one({"_id": ObjectId(ap_id)})

async def set_apartment_availability(ap_id, status: bool):
    await apartments_col.update_one({"_id": ObjectId(ap_id)}, {"$set": {"is_available": status}})

async def is_apartment_free(ap_id, start_date_str, end_date_str):
    start_dt = datetime.datetime.strptime(start_date_str, "%d.%m.%Y")
    end_dt = datetime.datetime.strptime(end_date_str, "%d.%m.%Y")
    
    bookings = await bookings_col.find({
        "ap_id": ObjectId(ap_id),
        "status": {"$in": ["paid_50", "confirmed", "completed"]}
    }).to_list(None)
    
    for b in bookings:
        b_start = datetime.datetime.strptime(b['start_date'], "%d.%m.%Y")
        b_end = datetime.datetime.strptime(b['end_date'], "%d.%m.%Y")
        
        if (start_dt < b_end) and (end_dt > b_start):
            return False, b['end_date']
            
    return True, None

async def create_booking(user_id, ap_id, start_date, end_date, phone, wishes, total_price):
    res = await bookings_col.insert_one({
        "user_id": user_id, 
        "ap_id": ObjectId(ap_id), 
        "start_date": start_date, 
        "end_date": end_date,
        "phone": phone, 
        "wishes": wishes, 
        "total_price": total_price,
        "prepayment": total_price * 0.5, 
        "remaining": total_price * 0.5, 
        "status": "pending_50", 
        "created_at": datetime.datetime.utcnow()
    })
    return res.inserted_id

async def get_booking(booking_id):
    try:
        return await bookings_col.find_one({"_id": ObjectId(booking_id)})
    except:
        return None

async def update_booking_status(booking_id, status):
    await bookings_col.update_one({"_id": ObjectId(booking_id)}, {"$set": {"status": status}})

async def delete_booking(booking_id):
    await bookings_col.delete_one({"_id": ObjectId(booking_id)})

async def get_active_bookings():
    return await bookings_col.find({"status": {"$in": ["paid_50", "confirmed"]}}).sort("created_at", -1).to_list(None)

async def log_error(error_msg, tb):
    await errors_col.insert_one({"error": error_msg, "traceback": tb, "timestamp": datetime.datetime.utcnow()})
