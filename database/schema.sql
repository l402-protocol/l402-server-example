-- Users table - core user data
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    credits INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Payment requests table - initial payment intent
CREATE TABLE payment_requests (
    id TEXT PRIMARY KEY, -- external id for the webhook: coinbase address, stripe link id....
    user_id TEXT NOT NULL,
    offer_id TEXT NOT NULL,
    amount DECIMAL NOT NULL,
    currency TEXT NOT NULL,
    credits INTEGER NOT NULL,
    provider TEXT NOT NULL,  -- 'stripe' or 'coinbase'
    status TEXT NOT NULL,    -- 'pending', 'completed', 'failed'
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
