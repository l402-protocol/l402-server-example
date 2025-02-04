import os
import requests
import logging
from typing import Dict
from database import db
import hmac
import hashlib
from flask import request
from offers import get_offer_by_id

def init_coinbase_webhook_routes(app):
    webhook_secret = os.environ.get("COINBASE_WEBHOOK_SECRET")

    def verify_coinbase_signature(payload: str, signature: str, webhook_secret: str) -> bool:
        try:
            expected_sig = hmac.new(
                webhook_secret.encode('utf-8'),
                payload.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected_sig)
        except Exception as e:
            logging.error(f"Error verifying Coinbase signature: {e}")
            return False

    @app.route('/webhook/coinbase', methods=['POST'])
    def handle_coinbase_webhook():
        try:
            # Get the signature from headers
            signature = request.headers.get('X-CC-Webhook-Signature')
            if not signature:
                logging.error(f"Missing Coinbase webhook signature: {request.headers}")
                return {}, 200

            # Get raw request payload
            payload = request.get_data().decode('utf-8')

            # Verify signature
            if not verify_coinbase_signature(payload, signature, webhook_secret):
                logging.error(f"Invalid Coinbase webhook signature({signature}): {payload}")
                return {}, 200

            webhook_data = request.json
            event = webhook_data.get('event', {})
            
            # Check if this is a charge event and get charge data
            if event.get('type') != 'charge:pending':
                logging.info(f"Coinbase webhook event type({event.get('type')}): {event}")
                return {}, 200
            
            charge_data = event.get('data', {})

            # Check metadata app_id
            metadata = charge_data.get('metadata', {})
            if metadata.get('app_id') != os.environ.get("APP_ID"):
                logger.error(f"Invalid app_id in webhook metadata: {metadata.get('app_id')}")
                return True

            charge_code = charge_data.get('code')
            if not charge_code:
                logging.error("Missing charge code in webhook data")
                return {}, 200
            
            # Load payment request data
            payment_request = db.get_payment_request(charge_code)
            if not payment_request:
                logging.error(f"Invalid payment request: {charge_code}")
                return {}, 200
                
            user_id = payment_request['user_id']
            offer_id = payment_request['offer_id']
            
            # Load offer details
            offer = get_offer_by_id(offer_id)
            if not offer:
                logging.error(f"Invalid offer: {offer_id}")
                return {}, 200
            
            # Update user credits based on offer
            db.update_user_credits(user_id, offer['balance'])
            
            # Record the completed payment
            pricing = charge_data.get('pricing', {}).get('local', {})
            db.record_payment(
                payment_request_id=payment_request['id'],
                credits=offer['balance'],
                amount=int(float(pricing.get('amount', 0)) * 100),  # Convert to cents
                currency=pricing.get('currency', '').upper(),
            )
            
            return {'status': 'success'}, 200
            
        except Exception as e:
            logging.error(f"Error handling Coinbase webhook: {e}")
            return {}, 200

def create_coinbase_charge(user_id, offer, expiry):
    COINBASE_API_KEY = os.getenv("COINBASE_COMMERCE_API_KEY")
    COINBASE_API_URL = "https://api.commerce.coinbase.com"

    try:
        url = "https://api.commerce.coinbase.com/charges/"
        headers = {
            "Content-Type": "application/json",
            "X-CC-Api-Key": os.environ.get("COINBASE_COMMERCE_API_KEY"),
            "X-CC-Version": "2018-03-22"
        }
        
        # There is no way to set expiry for a charge in Coinbase Commerce.
        payload = {
            "name": offer["title"],
            "description": offer["description"],
            "pricing_type": "fixed_price",
            "local_price": {
                # Coinbase expects the amount in dollars not cents
                "amount": str(float(offer["amount"]) / 100), 
                "currency": offer["currency"],
            },
            "redirect_url": os.environ.get("HOST"),
            "metadata": {
                "app_id": os.environ.get("APP_ID"),
            },
        }
       
        response = requests.post(url, json=payload, headers=headers)
        if not response.ok:
            logging.error(f"Coinbase charge creation failed: {response.text}")
            return None
    
        charge_data = response.json()["data"]
        
        # Store payment request in database
        db.create_payment_request(
            request_id=charge_data["code"],
            user_id=user_id,
            offer_id=offer["offer_id"]
        )
        
        return {
            "contract_addresses": charge_data["web3_data"]["contract_addresses"],
            "checkout_url": charge_data["hosted_url"]
        }
        

    except Exception as e:
        logging.error(f"Error creating Coinbase charge: {e}")
        return None
