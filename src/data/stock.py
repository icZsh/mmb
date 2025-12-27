import yfinance as yf
import pandas as pd

def get_stock_data(tickers):
    """
    Fetches historical data and fundamental info for a list of tickers.
    Returns a dict where keys are tickers and values are dicts with 'history' and 'info'.
    """
    if not tickers:
        return {}
        
    print(f"Fetching data for: {', '.join(tickers)}")
    
    # Batch fetch history for efficiency
    # Using period="2y" to ensure we have enough data for 200 SMA and other indicators
    # grouped_by='ticker' ensures we get a MultiIndex if multiple tickers, but let's handle single vs multiple carefully
    try:
        data = yf.download(tickers, period="2y", group_by='ticker', auto_adjust=True, progress=False)
    except Exception as e:
        print(f"Error downloading batch data: {e}")
        return {}

    results = {}
    
    for ticker_symbol in tickers:
        try:
            # Handle DataFrame structure
            if isinstance(data.columns, pd.MultiIndex):
                # If MultiIndex, the top level is likely Tickers because group_by='ticker'
                try:
                     hist = data[ticker_symbol]
                except KeyError:
                     # This might happen if yfinance returned something unexpected
                     print(f"Warning: Could not find {ticker_symbol} in columns.")
                     continue
            else:
                 # Single ticker download often returns simple index
                 hist = data

            # Clean and validate history
            if hist.empty:
                print(f"Warning: No history found for {ticker_symbol}")
                continue
            
            # Fetch fundamentals (requires separate Ticker object calls usually, but Tickers object might cache)
            # yfinance batch download only gets price data. Need to iterate for info.
            # This is slower but necessary for P/E, Market Cap, etc.
            t = yf.Ticker(ticker_symbol)
            info = t.info
            
            # Extract key fundamental metrics we care about
            fundamental_snapshot = {
                "marketCap": info.get("marketCap"),
                "trailingPE": info.get("trailingPE"),
                "forwardPE": info.get("forwardPE"),
                "dividendYield": info.get("dividendYield"),
                "profitMargins": info.get("profitMargins"),
                "revenueGrowth": info.get("revenueGrowth"),
                "shortName": info.get("shortName", ticker_symbol),
                "sector": info.get("sector", "Unknown"),
                "industry": info.get("industry", "Unknown")
            }

            results[ticker_symbol] = {
                "history": hist,
                "info": fundamental_snapshot
            }
            
        except Exception as e:
            print(f"Error processing {ticker_symbol}: {e}")
            
    return results

if __name__ == "__main__":
    res = get_stock_data(['AAPL', 'MSFT'])
    for t, d in res.items():
        print(f"--- {t} ---")
        print(d['info'])
        print(d['history'].tail(2))
