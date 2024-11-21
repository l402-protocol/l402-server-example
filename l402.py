from datetime import datetime, timedelta, timezone

from offers import api_offers
from stripe_payments import create_stripe_session
from base_payments import create_new_address


def create_new_response(user_id):
    if not user_id:
        raise ValueError("user_id is required")

    expire_in_minutes = 10
    now = datetime.now(timezone.utc)
    expiry = now + timedelta(minutes=expire_in_minutes)

    offers = []
    for api_offer in api_offers:
        offer = {
            "id": api_offer["offer_id"],
            "title": api_offer["title"],
            "description": api_offer["description"],
            "amount": api_offer["amount"],
            "currency": api_offer["currency"],
            "payment_methods": []
        }

        for payment_method in api_offer["payment_methods"]:            
            if payment_method == "stripe":
                payment_link = create_stripe_session(user_id, api_offer, expiry)

                if payment_link:
                    method = {
                        "payment_type": "stripe",
                        "payment_details": {
                            "payment_link": payment_link
                        }
                    }
                    offer["payment_methods"].append(method)
                else:
                    print(f"Skipping payment method due to null payment link")

        if offer["payment_methods"]:
            offers.append(offer)
        else:
            print(f"Skipping offer {api_offer['offer_id']} as it has no valid payment methods")

    response = {
        "version": "0.1",
        "offers": offers,
        "expiry": expiry,
        "terms_url": "https://link-to-terms.com",
    }
    
    return response