from datetime import datetime, timedelta, timezone
import os
import logging
from offers import api_offers, get_offer_by_id
from stripe_payments import create_stripe_session
from lightning_payments import create_lightning_invoice
from coinbase_payments import create_coinbase_charge


L402_VERSION = "0.2.1"

def is_payment_method_enabled(payment_method):
    LIGHTNING_NETWORK_ENABLED = os.getenv("LIGHTNING_NETWORK_ENABLED", "false").lower() == "true"
    STRIPE_ENABLED = os.getenv("STRIPE_ENABLED", "false").lower() == "true"
    COINBASE_ENABLED = os.getenv("COINBASE_ENABLED", "false").lower() == "true"

    if payment_method == "lightning" and LIGHTNING_NETWORK_ENABLED:
        return True
    elif payment_method == "onchain" and COINBASE_ENABLED:
        return True
    elif payment_method == "credit_card" and STRIPE_ENABLED:
        return True

    return False


def create_new_response(payment_context_token):
    return {
        "version": L402_VERSION,
        "offers": api_offers,
        "payment_request_url": os.getenv("HOST") + "/l402/payment-request",
        "payment_context_token": payment_context_token,
        "terms_url": "https://link-to-terms.com",
    }


def validate_onchain_params(payment_method, chain, asset):
    if payment_method != "onchain":
        return True
        
    if chain != "base-mainnet" or asset != "usdc":
        raise ValueError(
            "Invalid chain or asset. Only base-mainnet/usdc is supported"
        )
    return True


def create_new_payment_request(user_id, offer_id, payment_method, chain=None, asset=None):
    if not user_id:
        raise ValueError("user_id is required")
    
    if not is_payment_method_enabled(payment_method):
        raise ValueError(f"Payment method {payment_method} is not enabled")
    
    validate_onchain_params(payment_method, chain, asset)
    
    offer = get_offer_by_id(offer_id)
    if not offer:
        raise ValueError(f"Offer {offer_id} does not exist")
    
    # NOTE: some methods like stripe ask for at least 30 minutes to complete payment
    # before they can expire.
    expire_in_minutes = 35
    now = datetime.now(timezone.utc)
    expiry = now + timedelta(minutes=expire_in_minutes)

    response = {
        "version": L402_VERSION,
        "offer_id": offer_id,
        "payment_request": {},
        "expires_at": expiry.isoformat(),
    }
    
    try:
        if payment_method == "lightning":
            logging.info(f"Creating Lightning payment request for offer {offer_id}")
            response["payment_request"]["lightning_invoice"] = create_lightning_invoice(user_id, offer, expiry)

        elif payment_method == "onchain":
            network_id = "8453"  # base-mainnet
            logging.info(f"Creating onchain payment request for offer {offer_id}")
            payment_details = create_coinbase_charge(user_id, offer, expiry)
            response["payment_request"]["checkout_url"] = payment_details["checkout_url"]
            response["payment_request"]["address"] = payment_details["contract_addresses"][network_id]
            response["payment_request"]["asset"] = asset
            response["payment_request"]["chain"] = chain

        elif payment_method == "credit_card":
            logging.info(f"Creating Stripe payment link for offer {offer_id}")
            response["payment_request"]["checkout_url"] = create_stripe_session(user_id, offer, expiry)
    
        return response

    except Exception as e:
        logging.error(f"Failed to create payment request for offer {offer_id} with payment method {payment_method}: {e}")
        raise ValueError(f"Failed to create payment request")
