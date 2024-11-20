from datetime import datetime, timedelta
import uuid

from stripe_payments import create_payment_link

# Service offers define the available payment options presented to users when payment is required.
# These can be used for different payment scenarios:
# - One-time payments for specific endpoint access
# - Subscription tier upgrades
# - Credit-based API access (current implementation)
# Each offer specifies the price, amount of credits, and supported payment methods.
service_offers = [
    {
        "title": "1 Credit Package",
        "description": "Purchase 1 credit for API access",
        "amount": 99,
        "currency": "USD",
        "credits": 1,
        "payment_methods": ["base"]
    },
    {
        "title": "10 Credits Package",
        "description": "Purchase 10 credits for API access",
        "amount": 299,
        "currency": "USD",
        "credits": 10,
        "payment_methods": ["base"]
    },
    {
        "title": "100 Credits Package",
        "description": "Purchase 100 credits for API access",
        "amount": 499,
        "currency": "USD",
        "credits": 100,
        "payment_methods": ["base", "stripe"]
    }
]


def create_new_response(user_id):
    """Creates a L402 Payment Required response following the protocol specification"""
    
    # We need to know the user's ID so can tie the offers to them
    if not user_id:
        raise ValueError("user_id is required")

    # Set the expiry time for the payments
    expire_in_minutes = 10
    expiry = (datetime.utcnow() + timedelta(minutes=expire_in_minutes)).isoformat() + "Z"

    offers = []

    for offer_template in service_offers:
        offer_id = f"offer_{uuid.uuid4().hex[:8]}"
        offer_title = offer_template["title"]
        offer_description = offer_template["description"]
        offer_amount = offer_template["amount"]
        offer_currency = offer_template["currency"]
        offer_credits = offer_template["credits"]
        payment_methods = []

        for payment_method in offer_template["payment_methods"]:
            if payment_method == "base":
                # TODO: Implement base payment method
                pass
            
            elif payment_method == "stripe":
                payment_methods.append({
                    "payment_type": "stripe",
                    "payment_details": {
                        "payment_link": create_payment_link(
                            offer_id=offer_id,
                            user_id=user_id,
                            credits=offer_credits,
                            amount=offer_amount,
                            currency=offer_currency
                        )
                    }
                })
            else:
                raise ValueError(f"Invalid payment method: {payment_method}")
        

        offer = {
            "id": offer_id,
            "title": offer_title,
            "description": offer_description,
            "amount": offer_amount,
            "currency": offer_currency,
            "payment_methods": payment_methods
        }

        offers.append(offer)

    
    return {
        "version": "0.1",
        "offers": offers,
        "expiry": expiry,
        "docs_url": "https://link-to-docs.com",
        "terms_url": "https://link-to-terms.com",
        "metadata": {
            "user_id": user_id,
            "client_note": "Not enough credits to access ticker data, payment required"
        }
    }
