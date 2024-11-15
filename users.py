import replit
from uuid import uuid4
from typing import Optional, Dict

db = replit.db

def user_db_key(user_id: str) -> str:
    return 'users_' + user_id

def new_user() -> str:
    user_id = str(uuid4())

    data = {
        "id": user_id,
        "credits": 1,
        "created_at": replit.utils.timestamp(),
    }

    db[user_db_key(user_id)] = data
    
    return data

def get_user(user_id: str) -> Optional[Dict]:
    return db.get(user_db_key(user_id))

def update_user_credits(user_id: str, credits: int) -> None:
    user_key = user_db_key(user_id)
    
    data = db[user_key]
    data['credits'] = credits
    db[user_key] = data
