from dotenv import load_dotenv
from flask import Flask, request, render_template
import functools
import stock_data
import l402
import stripe_payments
import lightning_payments
import coinbase_payments
import offers
from database import db
import logging
import os
load_dotenv()

app = Flask(__name__)
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

stripe_payments.init_stripe_webhook_routes(app)  # For Stripe payments
lightning_payments.init_lightning_webhook_routes(app)  # For Lightning payments
coinbase_payments.init_coinbase_webhook_routes(app)  # For Coinbase payments


def require_auth(f):
    """
    Authentication middleware that checks if the request has a valid token.
    All protected endpoints must include a 'Bearer <token>' in Authorization header.
    """

    @functools.wraps(f)
    def decorated(*args, **kwargs):
        # Extract token from Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return {'error': 'Missing or invalid authorization header'}, 401

        # Validate user_id and get associated user data
        user_id = auth_header.split(' ')[1]
        user_data = db.get_user(user_id)
        if not user_data:
            return {'error': 'invalid token'}, 401

        return f(user_data, *args, **kwargs)

    return decorated


# Create a new user account
# Returns: User data including an authentication token for future requests
@app.route('/signup')
def signup():
    user_data = db.create_user()
    return user_data


# User information
# Requires: Authorization header with Bearer token
# Returns: User data if token is valid
@app.route('/info')
@require_auth
def info(user_data):
    # If the user is not logged in our middleware will have already return a 401 error
    return user_data

#  Request ticker data
# Requires:
#   - Authorization header with Bearer token
#   - User must have available credits
#   - Valid ticker symbol in URL
# Returns: Ticker data or error if no credits
@app.route('/ticker/<ticker_symbol>')
@require_auth
def ticker(user_data, ticker_symbol):
    logger.info(f"Received request for ticker {ticker_symbol} from user {user_data['id']}")
    
    if user_data['credits'] <= 0:
        logger.warning(f"User {user_data['id']} has insufficient credits")
        response = l402.create_new_response(user_data['id'])
        return response, 402

    try:
        ticker_data = stock_data.get_stock_data(ticker_symbol)
        if not ticker_data:
            logger.error(f"Failed to fetch data for ticker {ticker_symbol}")
            return {'error': f'unable to fetch stock data for ticker {ticker_symbol}'}, 400
        
        logger.info(f"Successfully fetched data for ticker {ticker_symbol}")
        db.update_user_credits(user_data['id'], -1)
        return ticker_data
    except ConnectionError:
        logger.error(f"Connection error while fetching {ticker_symbol}")
        return {'error': 'Unable to connect to stock data service. Please try again later.'}, 503
    except Exception as e:
        logger.exception(f"Unexpected error while fetching {ticker_symbol}")
        return {'error': 'Failed to fetch stock data'}, 500

@app.route('/l402/payment-request', methods=['POST'])
def payment_request():
    try:
        offer_id = request.json.get('offer_id')
        payment_method = request.json.get('payment_method')
        chain = request.json.get('chain', 'base-mainnet')
        asset = request.json.get('asset', 'usdc')
        
        # The payment context token allows the server to identify the user
        # this payment request is for. In this case we use the user_id
        # directly as the payment context token.
        user_id = request.json.get('payment_context_token')

        if not user_id:
            return {'error': 'Missing payment context token'}, 400
        
        user = db.get_user(user_id)
        if not user:
            return {'error': f'user {user_id} does not exist'}, 400
        
        if not offers.get_offer_by_id(offer_id):
            return {'error': f'offer {offer_id} does not exist'}, 400

        return l402.create_new_payment_request(
            user_id, 
            offer_id, 
            payment_method,
            chain=chain,
            asset=asset
        ), 200

    except ValueError as e:
        return {'error': str(e)}, 400
    except Exception as e:
        logger.exception(f"Unexpected error while creating payment request")
        return {'error': 'Failed to create payment request'}, 500


@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    debug = os.environ.get("DEBUG")=="true"
    app.run(host='0.0.0.0', port=5001, debug=debug)
