import yfinance as yf

# Get the ticker's data from Yahoo Finance
def get_stock_data(ticker):
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
        return {
            "financial_data":
            financial_data[:4],  # Return only the last 4 quarters
            "additional_data": additional_data
        }
    except Exception as e:
        print(f"Error fetching data from yfinance: {e}")
        return None