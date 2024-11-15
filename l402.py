from datetime import datetime, timedelta
import uuid

from stripe_payments import create_payment_link


def create_new_response(user_id):
    """Creates a L402 Payment Required response following the protocol specification"""
    
    if not user_id:
        raise ValueError("user_id is required")
        
    expiry = (datetime.utcnow() + timedelta(minutes=10)).isoformat() + "Z"
    
    offers = [
        {
            "id": f"offer_{uuid.uuid4().hex[:8]}",
            "title": "1 Credit Package",
            "description": "Purchase 1 credit for API access",
            "amount": 0.99,
            "currency": "USD",
            "payment_methods": [
                {
                    "payment_type": "stripe",
                    "payment_details": {
                        "payment_link": create_payment_link(
                            user_id=user_id,
                            credits=1,
                            amount=99,
                            currency="usd"
                        )
                    }
                }
            ]
        },
        {
            "id": f"offer_{uuid.uuid4().hex[:8]}",
            "title": "10 Credits Package",
            "description": "Purchase 10 credits for API access",
            "amount": 2.99,
            "currency": "USD",
            "payment_methods": []
        },
        {
            "id": f"offer_{uuid.uuid4().hex[:8]}",
            "title": "100 Credits Package",
            "description": "Purchase 100 credits for API access",
            "amount": 4.99,
            "currency": "USD",
            "payment_methods": [
                {
                    "payment_type": "stripe",
                    "payment_details": {
                        "payment_link": create_payment_link(
                            user_id=user_id,
                            credits=100,
                            amount=499,
                            currency="usd"
                        )
                    }
                }
            ]
        }
    ]
    
    return {
        "version": "1.0",
        "offers": offers,
        "expiry": expiry,
        "terms_url": "https://example.com/terms",
        "metadata": {
            "user_id": user_id,
            "client_note": "Payment required to access ticker data"
        }
    }
