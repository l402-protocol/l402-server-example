from flask import Flask, request
import functools
import users
import stock_data

app = Flask(__name__)


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

        # Validate token and get associated user data
        token = auth_header.split(' ')[1]
        user_data = users.get_user_by_token(token)
        if not user_data:
            return {'error': 'invalid token'}, 401

        return f(user_data, *args, **kwargs)

    return decorated


# Create a new user account
# Returns: User data including an authentication token for future requests
@app.route('/signup')
def signup():
    user_data = users.new_user()
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
    # If the user is not logged in our middleware will have already return a 401 error

    # If our user has no credits then we will return a 402 with information so
    # they can automatically buy more credits
    if user_data['credits'] <= 0:
        return {'error': 'no credits'}, 402

    # Get the ticker data from Yahoo Finance
    ticker_data = stock_data.get_ticker_data(ticker_symbol)
    if not ticker_data:
        return {'error': 'invalid ticker'}, 400

    # Update the user's credits
    user_id = user_data['id']
    new_credits = user_data['credits'] - 1
    users.update_user_credits(user_id, new_credits)

    # Return the ticker data
    return ticker_data


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
