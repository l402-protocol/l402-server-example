import os
import sqlite3
from uuid import uuid4
from contextlib import contextmanager
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone

class Database:
    def __init__(self):
        self.db_url = os.getenv('DATABASE_URL', 'app.db')
        self.init_db()
    
    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(
            self.db_url,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except sqlite3.Error:
            conn.rollback()
            raise
        finally:
            conn.close()

    def init_db(self):
        conn = sqlite3.connect(self.db_url)
        try:
            # Check if tables exist first
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='users'
            """)
            if cursor.fetchone() is None:
                # Only create tables if they don't exist
                with open('database/schema.sql', 'r') as f:
                    conn.executescript(f.read())
        finally:
            conn.close()

    # User methods
    def create_user(self, credits: int = 1) -> Dict:
        user_id = str(uuid4())
        timestamp = datetime.now(timezone.utc)

        with self.get_connection() as conn:
            conn.execute(
                'INSERT INTO users (id, credits, created_at, last_credit_update_at) VALUES (?, ?, ?, ?)',
                (user_id, credits, timestamp, timestamp)
            )
        return self.get_user(user_id)

    def get_user(self, user_id: str) -> Optional[Dict]:
        with self.get_connection() as conn:
            row = conn.execute(
                'SELECT * FROM users WHERE id = ?',
                (user_id,)
            ).fetchone()
            return dict(row) if row else None

    def update_user_credits(self, user_id: str, credits_delta: int) -> None:
        timestamp = datetime.now(timezone.utc)
        with self.get_connection() as conn:
            conn.execute('''
                UPDATE users 
                SET credits = credits + ?, last_credit_update_at = ?
                WHERE id = ?
            ''', (credits_delta, timestamp, user_id))
    
    # Payment methods
    def create_payment_request(self, request_id: str, user_id: str, offer_id: str) -> Dict:
        timestamp = datetime.now(timezone.utc)
        
        with self.get_connection() as conn:
            conn.execute(
                'INSERT INTO payment_requests (id, user_id, offer_id, created_at) VALUES (?, ?, ?, ?)',
                (request_id, user_id, offer_id, timestamp)
            )
            row = conn.execute(
                'SELECT * FROM payment_requests WHERE id = ?', 
                (request_id,)
            ).fetchone()
            return dict(row)

    def get_payment_request(self, request_id: str) -> Optional[Dict]:
        with self.get_connection() as conn:
            row = conn.execute(
                'SELECT * FROM payment_requests WHERE id = ?',
                (request_id,)
            ).fetchone()
            return dict(row) if row else None

    def record_payment(self, payment_request_id: str, credits: int, amount: int, currency: str) -> Dict:
        timestamp = datetime.now(timezone.utc)
        
        with self.get_connection() as conn:
            cursor = conn.execute(
                '''INSERT INTO payments 
                   (payment_request_id, credits, amount, currency, created_at) 
                   VALUES (?, ?, ?, ?, ?)
                   RETURNING *''',
                (payment_request_id, credits, amount, currency, timestamp)
            )
            row = cursor.fetchone()
            return dict(row)

db = Database()

