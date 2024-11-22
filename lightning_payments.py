import os
import logging
from datetime import datetime, timezone
import lightspark
from database import db
from flask import request
import requests
from offers import get_offer_by_id


_price_cache = {"timestamp": datetime.min.replace(tzinfo=timezone.utc), "price": 0}
def get_usd_amount_in_sats(cents):
    if (datetime.now(timezone.utc) - _price_cache["timestamp"]).total_seconds() > 600:
        try:
            response = requests.get("https://api.kraken.com/0/public/Ticker?pair=BTCUSD")
            btc_price = float(response.json()["result"]["XXBTZUSD"]["c"][0])
            sats_per_cent = 100_000_000 * 0.01 / btc_price  # sats per bitcoin (/100_000_000)  but then it's in cents (/00) but then it is in milisats (*000)
            _price_cache.update(timestamp=datetime.now(timezone.utc), price=sats_per_cent)
            logging.info(f"Updated BTC price cache. Current price: ${btc_price:,.2f}")
        except Exception as e:
            logging.error(f"Error fetching BTC price: {str(e)}")
            raise
    return int(cents * _price_cache["price"])


def init_lightning_webhook_routes(app):
    webhook_signing_key = os.environ.get("LIGHTSPARK_WEBHOOK_SIGNING_KEY")

    @app.route('/webhook/lightspark', methods=['POST'])
    def handle_lightspark_webhook():
        try:
            event = lightspark.WebhookEvent.verify_and_parse(
                data=request.data,
                hexdigest=request.headers.get(lightspark.SIGNATURE_HEADER),
                webhook_secret=webhook_signing_key
            )

            if event.event_type == lightspark.WebhookEventType.PAYMENT_FINISHED:
                logging.info(f"Payment finished event: {event}")
                client = lightspark.LightsparkSyncClient(
                    api_token_client_id=os.environ.get("LIGHTSPARK_API_TOKEN_CLIENT_ID"),
                    api_token_client_secret=os.environ.get("LIGHTSPARK_API_TOKEN_CLIENT_SECRET"),
                )

                entity_id = event.entity_id
                entity_class = lightspark.IncomingPayment
                
                # Get the payment entity
                payment = client.get_entity(entity_id, entity_class)

                logging.info(f"Payment details: {payment}")

                # Load payment request data
                payment_request = db.get_payment_request(payment.payment_request_id)
                if not payment_request:
                    logging.error(f"Invalid payment request: {payment.payment_request_id}")
                    return {}, 200
                
                payment_request_id = payment_request['id']
                user_id = payment_request['user_id']
                offer_id = payment_request['offer_id']
                
                # Load offer details to get credits amount
                offer = get_offer_by_id(offer_id)
                if not offer:
                    logging.error(f"Invalid offer: {offer_id}")
                    return {}, 200
                
                # Update user credits based on offer
                db.update_user_credits(user_id, offer['credits'])
                
                # Record the completed payment
                db.record_payment(
                    payment_request_id=payment_request_id,
                    credits=offer['credits'],
                    amount=offer['amount'],
                    currency=offer['currency'],
                )
            
            else:
                logging.info(f"Unhandled event type: {event.event_type}")

            return {}, 200
        except Exception as e:
            logging.error(f"Error handling Lightspark webhook({request.data}): {str(e)}")
            return {}, 200


def create_lightning_invoice(user_id, offer, expiry):    
    client = lightspark.LightsparkSyncClient(
        api_token_client_id=os.environ.get("LIGHTSPARK_API_TOKEN_CLIENT_ID"),
        api_token_client_secret=os.environ.get("LIGHTSPARK_API_TOKEN_CLIENT_SECRET"),
    )


    amount_msats = get_usd_amount_in_sats(offer["amount"])*1000
    expiry_secs = int((expiry - datetime.now(timezone.utc)).total_seconds())
    invoice = client.create_invoice(
        node_id=os.environ.get("LIGHTSPARK_NODE_ID"),
        amount_msats=amount_msats,
        memo=offer["title"],
        expiry_secs=expiry_secs
    )

    db.create_payment_request(invoice.id, user_id, offer["offer_id"])
    logging.info(f"Created Lightning invoice {invoice.id} for user {user_id}")

    return invoice.data.encoded_payment_request

