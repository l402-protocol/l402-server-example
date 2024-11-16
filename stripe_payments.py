import os
import stripe
from flask import request
from db import db
from users import update_user_credits
from datetime import datetime

stripe.api_key = os.environ.get("STRIPE_SECRET_KEY")

def init_stripe_webhook_routes(app):
    @app.route('/webhook/stripe', methods=['POST'])
    def handle_stripe_webhook():
        try:
            event = stripe.Webhook.construct_event(
                request.data,
                request.headers['Stripe-Signature'],
                os.environ.get('STRIPE_WEBHOOK_SECRET')
            )
            
            if event['type'] == 'checkout.session.completed':
                session = event['data']['object']
                payment_id = session['payment_link']
                
                # Get stored payment details
                payment_data = db.get(f"stripe_payment_{payment_id}")
                if payment_data:
                    # Update user credits
                    update_user_credits(
                        payment_data['user_id'],
                        payment_data['credits'],
                        increment=True
                    )
                    
                    # Update payment status
                    payment_data['status'] = 'completed'
                    db[f"stripe_payment_{payment_id}"] = payment_data
            
            return {'status': 'success'}, 200
            
        except Exception as e:
            return {'error': str(e)}, 400

def create_payment_link(user_id, credits, amount, currency):
    if not all([user_id, credits, amount, currency]):
        raise ValueError("All parameters are required")
        
    try:
        payment_link = stripe.PaymentLink.create(
            line_items=[{"price": 'price_1QLJhrDh4HSWvy0Ttd2zz6PL', "quantity": 1}],
            api_key=os.environ.get("STRIPE_SECRET_KEY")
        )

        # Store payment link details
        db[f"stripe_payment_{payment_link.id}"] = {
            "user_id": user_id,
            "credits": credits,
            "amount": amount,
            "currency": currency,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat()
        }
        
        return payment_link.url
    except (stripe.error.StripeError, Exception) as e:
        # Log the error
        print(f"Error creating payment link: {str(e)}")
        raise
