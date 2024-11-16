from db import db
from uuid import uuid4
from typing import Optional, Dict
from datetime import datetime, timezone


def user_db_key(user_id: str) -> str:
    return 'users_' + user_id

def new_user() -> Dict:
    try:
        user_id = str(uuid4())
        user_id = "d6050855-906e-4123-a254-10816163879d"
        data = {
            "id": user_id,
            "credits": 0,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        db[user_db_key(user_id)] = data
    
        return data
    except Exception as e:
        raise Exception(f"Failed to create new user: {str(e)}")

def get_user(user_id: str) -> Optional[Dict]:
    try:
        return db.get(user_db_key(user_id))
    except Exception as e:
        raise Exception(f"Failed to get user {user_id}: {str(e)}")

def get_user_by_token(token: str) -> Optional[Dict]:
    return get_user(token)

def update_user_credits(user_id: str, credits: int) -> None:
    try:
        user_key = user_db_key(user_id)
        data = db.get(user_key)
        if data is None:
            raise Exception(f"User {user_id} not found")
        data['credits'] = credits
        db[user_key] = data
    except Exception as e:
        raise Exception(f"Failed to update credits for user {user_id}: {str(e)}")
