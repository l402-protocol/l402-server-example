# Stock Data L402 Demo

A demonstration of how to build AI-agent friendly paid APIs using the [L402 protocol](https://github.com/l402-protocol/l402 
). 

This service provides stock market data with automated payment processing, specifically designed for AI agents to consume programmatically.

Live demo: https://stock.l402.org

## Why L402 for AI Agents?

Traditional payment flows are designed for human interaction, requiring manual setup and browser-based interfaces. This project demonstrates how L402 protocol enables:

- **Automated Discovery & Payments**: AI agents can understand payment requirements, and process transactions autonomously
- **Programmatic Access**: Clean API interface designed for machine consumption
- **Multiple Payment Methods**: Support for Lightning Network, Stripe, and Coinbase, allowing AI agents to use their preferred payment network
- **Flexible Pricing**: From credit systems to subscriptions the L402  allows fine-grained control over API access

## Payment Providers

The L402 protocol is payment-provider-agnostic and can integrate with any payment system. This demo implements three payment methods to showcase different approaches:

### Stripe (Credit Cards)
- Uses Stripe Payment Links for seamless credit card processing
- Compatible with AI agents using the latest Stripe libraries
- Direct integration via [Stripe's AI-agent workflows](https://stripe.dev/blog/adding-payments-to-your-agentic-workflows)
- Enables traditional payment methods (credit/debit cards) for AI agents

### Lightning Network (via Lightspark)
- Leverages Lightning Network for instant, low-cost payments
- Real-time settlement with minimal fees
- Highly interoperable and secure transaction processing
- Ideal for micropayments and programmatic access

### Coinbase Commerce (Crypto)
- Supports multiple blockchain networks:
  - Ethereum
  - Polygon
  - Base
- Provides hosted checkout information
- Returns contract addresses for direct blockchain interaction
- Direct integration with [Coinbase AgentKit](https://www.coinbase.com/en-ca/developer-platform/discover/launches/introducing-agentkit) for AI-native crypto payments
- Enables crypto-native payment flows

## API Documentation

### Stock Data Endpoints

- `GET /signup`
  - Creates a new user account
  - Returns: User data including authentication token
  - Authentication: Not required
  ```bash
  # Request
  curl https://stock.l402.org/signup
  
  # Response
  {
    "id": "57d102ff-9060-4eb6-8d50-10f35eba23cd",
    "credits": 1,
    "created_at": "2024-11-26T02:39:44Z",
    "last_credit_update_at": "2024-11-26T02:39:44Z"
  }
  ```

- `GET /info`
  - Retrieves current user information
  - Returns: User data including credit balance
  - Authentication: Required via Bearer token
  ```bash
  # Request
  curl -H "Authorization: Bearer 57d102ff-9060-4eb6-8d50-10f35eba23cd" https://stock.l402.org/info
  
  # Response
  {
    "id": "57d102ff-9060-4eb6-8d50-10f35eba23cd",
    "credits": 1,
    "created_at": "2024-11-26T02:39:44Z",
    "last_credit_update_at": "2024-11-26T02:39:44Z"
  }
  ```

- `GET /ticker/<symbol>`
  - Get financial data for a specific stock symbol
  - Returns: Current price, P/E ratio, revenue, and net income
  - Authentication: Required via Bearer token
  - Credits: Deducts 1 credit per successful call
  ```bash
  # Request
  curl -H "Authorization: Bearer 57d102ff-9060-4eb6-8d50-10f35eba23cd" https://stock.l402.org/ticker/AAPL
  
  # Success Response (200)
  {
    "additional_data": {
      "current_price": 232.87,
      "eps": 6.07,
      "pe_ratio": 38.36
    },
    "financial_data": [
      {
        "fiscalDateEnding": "2024-09-30",
        "totalRevenue": 391035000000.0,
        "netIncome": 93736000000.0
      }
      // ... additional years
    ]
  }

  # Insufficient Credits Response (402)
  {
    "expiry": "2024-11-26T03:16:32Z",
    "offers": [
      {
        "amount": 1,
        "currency": "USD",
        "description": "Purchase 1 credit for API access",
        "title": "1 Credit Package",
        // ... payment details omitted for brevity
      }
      // ... additional offers
    ]
  }
  ```

### L402 Payment Flow

The API uses a credit-based system where each API call consumes credits. Here's how it works:

1. **Normal API Usage**
   - AI agent authenticates with Bearer token
   - If sufficient credits exist, API returns requested data
   - 1 credit is deducted per successful call

2. **When Credits are Depleted**
   - API responds with 402 Payment Required
   - Response includes available payment options (Lightning, Stripe, Coinbase)
   - Example:
   ```json
   {
     "expiry": "2024-11-26T03:16:32Z",
     "offers": [
       {
         "amount": 1,
         "currency": "USD",
         "description": "Purchase 1 credit for API access",
         "title": "1 Credit Package"
         // ... payment details
       }
     ]
   }
   ```

3. **Payment Process**
   - AI agent selects payment method and processes payment
   - Payment provider sends webhook to server confirming payment
   - Server automatically adds credits to agent's account

4. **Normal API Usage**
   - Agent can immediately resume API calls with existing Bearer token

### Authentication

The L402 protocol is payment-focused and authentication-agnostic - it can work with any authentication system. In this implementation, we use a simplified Bearer token approach:

- Get a user ID via the `/signup` endpoint
- Use this ID as a Bearer token for all API calls
```
Authorization: Bearer <user_id>
```

Example:
```bash
# 1. Get user ID
curl https://stock.l402.org/signup
# Response: {"id": "57d102ff-9060-4eb6-8d50-10f35eba23cd", ...}

# 2. Use ID as Bearer token
curl -H "Authorization: Bearer 57d102ff-9060-4eb6-8d50-10f35eba23cd" https://stock.l402.org/ticker/AAPL
```

## Technical Stack

- **Backend**: Python/Flask
- **Payment Processing**: 
  - Lightning Network (L402 native)
  - Stripe API
  - Coinbase Commerce API
- **Market Data**: Yahoo Finance API

## Local Development

### Prerequisites

- Docker and Docker Compose
- API keys for enabled payment methods

### Environment Variables

```plaintext
STRIPE_SECRET_KEY=your_stripe_key
COINBASE_COMMERCE_API_KEY=your_coinbase_key
COINBASE_WEBHOOK_SECRET=your_webhook_secret
LIGHTNING_NETWORK_ENABLED=true/false
STRIPE_ENABLED=true/false
COINBASE_ENABLED=true/false
HOST=your_host_url
DEBUG=true/false
LOG_LEVEL=INFO
```

### Running with Docker

1. Clone the repository
2. Create `.env` file with required environment variables
3. Build and start the service:

```bash
docker compose up --build
```

The service will be available at `http://localhost:5000`

## License

This project is licensed under the MIT License - see the LICENSE.md file for details