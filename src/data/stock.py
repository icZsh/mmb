import yfinance as yf
import pandas as pd
import json
import os
import time
from datetime import datetime, timedelta

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
    
    HISTORY_CACHE = "market_history.pkl"
    history_data = None
    
    # Check cache
    if os.path.exists(HISTORY_CACHE):
        try:
            mod_time = datetime.fromtimestamp(os.path.getmtime(HISTORY_CACHE))
            if datetime.now() - mod_time < timedelta(hours=4): # Cache for 4 hours
                history_data = pd.read_pickle(HISTORY_CACHE)
                print("Using cached market history.")
        except Exception as e:
            print(f"Failed to load history cache: {e}")

    if history_data is None:
        try:
            history_data = yf.download(tickers, period="2y", group_by='ticker', auto_adjust=True, progress=False)
            # Validate data was actually returned
            if not history_data.empty:
                history_data.to_pickle(HISTORY_CACHE)
        except Exception as e:
            print(f"Error downloading batch data: {e}")
            return {}
            
    data = history_data

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
            
            # Check cache for fundamentals
            CACHE_FILE = "fundamental_cache.json"
            cache = {}
            if os.path.exists(CACHE_FILE):
                try:
                    with open(CACHE_FILE, 'r') as f:
                        cache = json.load(f)
                except:
                    pass
            
            # Check if we have valid cached data (e.g., less than 7 days old)
            cached_info = cache.get(ticker_symbol)
            use_cache = False
            if cached_info:
                last_fetch = cached_info.get('_last_fetched')
                if last_fetch:
                    dt = datetime.fromtimestamp(last_fetch)
                    if datetime.now() - dt < timedelta(days=7):
                        use_cache = True
            
            if use_cache:
                info = cached_info
            else:
                # Fetch fundamentals
                # Add delay to avoid rate limits
                time.sleep(2) 
                t = yf.Ticker(ticker_symbol)
                try:
                    info = t.info
                    # Update cache
                    info['_last_fetched'] = datetime.now().timestamp()
                    cache[ticker_symbol] = info
                    with open(CACHE_FILE, 'w') as f:
                        json.dump(cache, f)
                except Exception as e:
                    print(f"Warning: Could not fetch info for {ticker_symbol}: {e}")
                    info = {}
            
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
