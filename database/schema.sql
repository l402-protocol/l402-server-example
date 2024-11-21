-- Users table - core user data
CREATE TABLE users (
    id TEXT PRIMARY KEY,

    credits INTEGER NOT NULL DEFAULT 0,
    last_credit_update_at TIMESTAMP,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- payment_requests table - all payment requests
CREATE TABLE payment_requests (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    offer_id TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Payments table - all completed payments
CREATE TABLE payments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    payment_request_id TEXT NOT NULL,
    credits INTEGER NOT NULL,
    amount INTEGER NOT NULL,
    currency TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (payment_request_id) REFERENCES payment_requests(id)
);
