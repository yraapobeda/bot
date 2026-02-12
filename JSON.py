import json
from pathlib import Path
from aiogram import types
from datetime import datetime
import pytz
from aiogram import types
from datetime import datetime


DB_DIR = Path("bd")
DB_FILE = DB_DIR / "users.json"

DB_DIR.mkdir(parents=True, exist_ok=True)

if not DB_FILE.exists():
    DB_FILE.write_text("{}", encoding="utf-8")


def load_db():
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)






def register_user(user: types.User):
    db = load_db()
    uid = str(user.id)

    reg_date = datetime.now().strftime("%d.%m.%Y %H:%M")

    if uid not in db:
        db[uid] = {
            "id": user.id,
            "full_name": user.full_name,
            "username": user.username,
            "is_premium": user.is_premium,
            "registered_at": reg_date,  
            "rcy": 0,
            "keys": 0,
            "referrals": 0,
            "referrer": None
        }

    else:
        db[uid].setdefault("id", user.id)
        db[uid].setdefault("full_name", user.full_name)
        db[uid].setdefault("username", user.username)
        db[uid].setdefault("is_premium", user.is_premium)
        db[uid].setdefault("registered_at", reg_date)  
        db[uid].setdefault("rcy", 0)
        db[uid].setdefault("keys", 0)

        db[uid].setdefault("referrals", 0)
        db[uid].setdefault("referrer", None)

        db[uid]["username"] = user.username
        db[uid]['is_premium'] = user.is_premium

    save_db(db)




def get_name(user_id: int) -> str:
    db = load_db()
    user = db.get(str(user_id))
    if user and "full_name" in user:
        return user["full_name"]
    return "Нн ¯\_(ツ)_/¯"

def add_balance(user_id: int, currency: str, amount: int) -> bool:
    db = load_db()
    uid = str(user_id)

    if uid not in db:
        return False

    currency = currency.lower()
    if currency not in ("rcy", "keys"):
        return False

    db[uid][currency] = int(db[uid].get(currency, 0)) + int(amount)
    save_db(db)
    return True