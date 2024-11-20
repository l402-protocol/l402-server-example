import yfinance as yf
from datetime import datetime, timedelta

# Cache to store results with timestamps
_cache = {}

# Get the ticker's data from Yahoo Finance
def get_stock_data(ticker):
    # Check cache first
    if ticker in _cache:
        cached_time, cached_data = _cache[ticker]
        if datetime.now() - cached_time < timedelta(minutes=1):
            return cached_data

    try:
        stock = yf.Ticker(ticker)
        financials = stock.financials
        info = stock.info
        if financials.empty:
            return None
        financial_data = []
        for date, data in financials.items():
            financial_data.append({
                "fiscalDateEnding":
                date.strftime("%Y-%m-%d"),
                "totalRevenue":
                float(data.get("Total Revenue", 0)),
                "grossProfit":
                float(data.get("Gross Profit", 0)),
                "netIncome":
                float(data.get("Net Income", 0))
            })
        additional_data = {
            "eps": float(info.get("trailingEps", 0)),
            "pe_ratio": float(info.get("trailingPE", 0)),
            "current_price": float(info.get("currentPrice", 0))
        }
        result = {
            "financial_data":
            financial_data[:4],  # Return only the last 4 quarters
            "additional_data": additional_data
        }
        
        # Store in cache with current timestamp
        _cache[ticker] = (datetime.now(), result)
        return result
    except Exception as e:
        print(f"Error fetching data from yfinance: {e}")
        return None