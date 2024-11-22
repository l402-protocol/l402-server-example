from datetime import datetime, timedelta, timezone
import os
import logging
from offers import api_offers
from stripe_payments import create_stripe_session
from lightning_payments import create_lightning_invoice


def create_new_response(user_id):
    if not user_id:
        raise ValueError("user_id is required")
    
    LIGHTNING_NETWORK_ENABLED = os.getenv("LIGHTNING_NETWORK_ENABLED", "false").lower() == "true"
    STRIPE_ENABLED = os.getenv("STRIPE_ENABLED", "false").lower() == "true"
    BASE_ENABLED = os.getenv("BASE_ENABLED", "false").lower() == "true"

    # NOTE: some methods like stripe ask for at least 30 minutes to complete payment
    # before they can expire.
    expire_in_minutes = 35
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
            if payment_method == "lightning" and LIGHTNING_NETWORK_ENABLED:
                logging.info(f"Creating Lightning payment request for offer {api_offer['offer_id']}")
                payment_request = create_lightning_invoice(user_id, api_offer, expiry)
                if payment_request:
                    method = {
                        "payment_type": "lightning",
                        "payment_details": {
                            "payment_request": payment_request
                        }
                    }
                    offer["payment_methods"].append(method)

            elif payment_method == "stripe" and STRIPE_ENABLED:
                logging.info(f"Creating Stripe payment link for offer {api_offer['offer_id']}")
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
                    logging.warning(f"Skipping payment method due to null payment link")

        
        offers.append(offer)
        
    response = {
        "version": "0.1",
        "offers": offers,
        "expiry": expiry.replace(microsecond=0).isoformat(),
        "terms_url": "https://link-to-terms.com",
    }
    
    return response