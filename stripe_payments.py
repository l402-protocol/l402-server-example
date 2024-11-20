import os
import stripe
from flask import request
from database import db
from datetime import datetime

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")

def init_stripe_webhook_routes(app):
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
                
                payment_id = session.get('payment_link')
                if not payment_id:
                    return {'error': 'No payment_link in session'}, 400
                
                payment_data = db.get_payment(payment_id)
                if not payment_data:
                    return {'error': 'Payment data not found'}, 400
                    
                # Update user credits and payment status
                db.update_user_credits(
                    payment_data['user_id'],
                    payment_data['credits']
                )
                db.update_payment_status(payment_id, 'completed')
            
            return {'status': 'success'}, 200
            
        except Exception as e:
            print(f"\n=== ERROR DEBUG ===")
            print(f"Exception type: {type(e)}")
            print(f"Exception message: {str(e)}")
            return {'error': str(e)}, 400

def create_payment_link(offer_id, user_id, credits, amount, currency):
    if not all([offer_id, user_id, credits, amount, currency]):
        raise ValueError("All parameters are required")
        

    try:
        # Make sure the price is set up in stripe first
        price_id = os.environ.get("STRIPE_PRICE_ID")

        payment_link = stripe.PaymentLink.create(
            line_items=[{"price": price_id, "quantity": 1}],
            api_key=os.environ.get("STRIPE_SECRET_KEY")
        )

        db.create_payment(
            payment_id=payment_link.id,
            user_id=user_id,
            offer_id=offer_id,
            provider="stripe",
            amount=amount,
            currency=currency,
            credits=credits,
        )
        
        return payment_link.url
    except (stripe.error.StripeError, Exception) as e:
        print(f"Error creating payment link: {str(e)}")
        raise
