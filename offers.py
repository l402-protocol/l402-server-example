from typing import Optional, Dict

# Service offers define the available payment options presented to users when payment is required.
# These can be used for different payment scenarios:
# - One-time payments for specific endpoint access
# - Subscription tier upgrades
# - Credit-based API access (current implementation)
# Each offer specifies the price, amount of credits, and supported payment methods.
api_offers = [
    {
        "offer_id": "offer_c668e0c0",
        "title": "1 Credit Package",
        "description": "Purchase 1 credit for API access",
        "amount": 1,
        "currency": "USD",
        "credits": 1,
        "payment_methods": ["base", "lightning"]
    }, 
    {
        "offer_id": "offer_97bf23f7",
        "title": "10 Credits Package",
        "description": "Purchase 10 credits for API access",
        "amount": 99,
        "currency": "USD",
        "credits": 100,
        "payment_methods": ["base", "lightning"]
    },
    {
        "offer_id": "offer_a896b13c",
        "title": "100 Credits Package",
        "description": "Purchase 100 credits for API access",
        "amount": 499,
        "currency": "USD",
        "credits": 500,
        "payment_methods": ["base", "lightning", "stripe"]
    }
]


# Get an offer by its ID
def get_offer_by_id(offer_id: str) -> Optional[Dict]:
    for offer in api_offers:
        if offer["offer_id"] == offer_id:
            return offer
    return None