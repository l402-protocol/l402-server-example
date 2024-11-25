import os
import stripe
import logging
from flask import request
from database import db
from uuid import uuid4
from offers import get_offer_by_id


def init_stripe_webhook_routes(app):
    stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")

    @app.route('/webhook/stripe', methods=['POST'])
    def handle_stripe_webhook():
        try:
            event = stripe.Webhook.construct_event(
                payload=request.data,
                sig_header=request.headers['Stripe-Signature'],
                secret=os.environ.get('STRIPE_WEBHOOK_SECRET'),
                api_key=os.environ.get('STRIPE_SECRET_KEY')
            )
            
            if event['type'] == 'checkout.session.completed':
                session = event['data']['object']
                
                # Extract payment request from metadata
                metadata = session.get('metadata', {})
                payment_request_id = metadata.get('payment_request')
                
                if not payment_request_id:
                    logging.error(f"Missing payment request ID: {event}")
                    return {}, 200
                
                # Load payment request data
                payment_request = db.get_payment_request(payment_request_id)
                if not payment_request:
                    logging.error(f"Invalid payment request: {payment_request_id}")
                    return {}, 200
                    
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
            
            return {'status': 'success'}, 200
            
        except Exception as e:
            return {'error': str(e)}, 400

stripe_payment_links = {
    "offer_a896b13c": "https://buy.stripe.com/test_fZe7vZad0cZhdAk7sL"
}

def create_stripe_session(user_id, offer, expiry):
    payment_request = str(uuid4())

    try:
        # Verify Stripe configuration
        if not stripe.api_key:
            logging.error("Stripe API key not set")
            return None

        db.create_payment_request(payment_request, user_id, offer["offer_id"])
        
        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=[{
                "price_data": {
                    "currency": offer["currency"].lower(),
                    "unit_amount": offer["amount"],
                    "product_data": {
                        "name": offer["title"],
                        "description": offer["description"]
                    }
                },
                "quantity": 1,
            }],
            metadata={
                "payment_request": payment_request,
                "user_id": user_id,
                "offer_id": offer["offer_id"]
            },
            success_url="https://stock.l402.org/payment/success",
            cancel_url="https://stock.l402.org/payment/cancel",
            expires_at=int(expiry.timestamp())
        )

        return session.url

    except stripe.error.StripeError as e:
        logging.error(f"Stripe error: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error creating Stripe session: {e}")
        return None
