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
    def create_user(self, credits: int = 1, created_at: datetime = datetime.now(timezone.utc)) -> Dict:
        user_id = str(uuid4())

        with self.get_connection() as conn:
            conn.execute(
                'INSERT INTO users (id, credits, created_at) VALUES (?, ?, ?)',
                (user_id, credits, created_at)
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
        with self.get_connection() as conn:
            conn.execute('''
                UPDATE users 
                SET credits = credits + ? 
                WHERE id = ?
            ''', (credits_delta, user_id))

    # Payment methods
    def create_payment(self, 
                      payment_id: str,
                      user_id: str,
                      offer_id: str,
                      provider: str,
                      amount: float,
                      currency: str,
                      credits: int) -> str:
        with self.get_connection() as conn:
            conn.execute('''
                INSERT INTO payment_requests (
                    id, user_id, offer_id, provider, amount, currency, credits,
                    status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                payment_id, user_id, offer_id, provider, amount, currency, credits,
                'pending'
            ))
        return payment_id

    def update_payment_status(self, payment_id: str, status: str) -> None:
        completed_at = datetime.now() if status == 'completed' else None
        with self.get_connection() as conn:
            conn.execute('''
                UPDATE payment_requests 
                SET status = ?, completed_at = ?
                WHERE id = ?
            ''', (status, completed_at, payment_id))

    def get_payment(self, payment_id: str) -> Optional[Dict]:
        with self.get_connection() as conn:
            row = conn.execute(
                'SELECT * FROM payment_requests WHERE id = ?',
                (payment_id,)
            ).fetchone()
            return dict(row) if row else None

    def get_user_payments(self, user_id: str) -> List[Dict]:
        with self.get_connection() as conn:
            rows = conn.execute(
                'SELECT * FROM payment_requests WHERE user_id = ? ORDER BY created_at DESC',
                (user_id,)
            ).fetchall()
            return [dict(row) for row in rows]

    # Stock cache methods
    def set_stock_cache(self, ticker: str, data: Dict[str, Any]) -> None:
        with self.get_connection() as conn:
            conn.execute('''
                INSERT OR REPLACE INTO stock_cache (ticker, data)
                VALUES (?, json(?))
            ''', (ticker, str(data)))

    def get_stock_cache(self, ticker: str) -> Optional[Dict]:
        with self.get_connection() as conn:
            row = conn.execute(
                'SELECT * FROM stock_cache WHERE ticker = ?',
                (ticker,)
            ).fetchone()
            return dict(row) if row else None

db = Database()

