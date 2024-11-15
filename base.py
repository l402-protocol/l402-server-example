import os

from cdp import *
from flask import request
from replit import db                

from users import update_user_credits

api_key_name = os.environ.get("COINBASE_API_KEY_NAME")
api_key_private_key = os.environ.get("COINBASE_API_KEY_PRIVATE_KEY")

Cdp.configure(api_key_name, api_key_private_key)

def init_webhook_routes(app):
    @app.route('/webhook', methods=['POST'])
    def handle_webhook():
        event = request.json

        print(event)
        
        if event['type'] == 'address.payment':
            address_id = event['data']['id']
            payment_data = {
                'amount': event['data']['payment']['value']['local']['amount'],
                'currency': event['data']['payment']['value']['local']['currency'],
                'status': event['data']['payment']['status'],
                'received_at': event['data']['payment']['created_at']
            }
            
            stored_address = db[f"address_{address_id}"]
            stored_address['payments'] = stored_address.get('payments', [])
            stored_address['payments'].append(payment_data)
            
            # If payment is completed, update user credits
            if payment_data['status'] == 'COMPLETED':
                user_id = stored_address['user_id']
                credits_to_add = stored_address['credits_to_add']
                update_user_credits(user_id, credits_to_add, increment=True)
            
            db[f"address_{address_id}"] = stored_address
            return {'status': 'success'}, 200
        
        return {'status': 'ignored'}, 200

# Create a new address
def create_new_address(user_id, credits, amount, currency):
    new_address = Cdp.create_address()
    
    db[f"address_{new_address.id}"] = {
        "id": new_address.id,
        "address": new_address.address,
        "created_at": new_address.created_at,
        "user_id": user_id,
        "credits": credits,
        "amount": amount,
        "currency": currency,
        "payments": []
    }
    
    return new_address
