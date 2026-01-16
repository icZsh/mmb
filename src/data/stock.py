import yfinance as yf
import pandas as pd
import json
import os
import time
from datetime import datetime, timedelta

try:
    # MotherDuck/local DuckDB cache (preferred over local pickle cache)
    from src.db.client import db
except Exception:
    db = None


def _latest_trading_day_date() -> datetime.date:
    """
    Best-effort "latest trading day" (Mon-Fri) based on US/Eastern time.
    This avoids treating weekends as "missing" data when syncing daily bars.
    """
    # Use US/Eastern time as the source of truth for "today"
    # This prevents Monday morning in Asia from being treated as "future" relative to Sunday in NY,
    # or Sunday evening in NY being treated as Monday.
    d = pd.Timestamp.now(tz='US/Eastern').normalize()
    
    # Monday=0, Sunday=6
    if d.weekday() == 5: # Saturday
        d = d - pd.Timedelta(days=1)
    elif d.weekday() == 6: # Sunday
        d = d - pd.Timedelta(days=2)
    return d.date()


def _history_from_db(ticker: str, start_date: datetime.date) -> pd.DataFrame:
    """
    Returns OHLCV history from DB in yfinance-like shape:
    - index: DatetimeIndex named 'Date'
    - columns: Open, High, Low, Close, Volume
    """
    if not db:
        return pd.DataFrame()

    try:
        if hasattr(db, "get_history_since"):
            df = db.get_history_since(ticker, start_date)
        else:
            # Older client: returns all rows for ticker; filter here.
            df = db.get_history(ticker)
    except Exception:
        return pd.DataFrame()

    if df is None or df.empty:
        return pd.DataFrame()

    # Normalize schema from DB -> yfinance-like dataframe
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df[df["date"].dt.date >= start_date].sort_values("date")
    if df.empty:
        return pd.DataFrame()

    df = df.rename(
        columns={
            "date": "Date",
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume",
        }
    )
    df = df.set_index("Date")
    df.index.name = "Date"
    return df[["Open", "High", "Low", "Close", "Volume"]]


def get_stock_data(tickers):
    """
    Fetches historical data and fundamental info for a list of tickers.
    Returns a dict where keys are tickers and values are dicts with 'history' and 'info'.
    """
    if not tickers:
        return {}
        
    print(f"Fetching data for: {', '.join(tickers)}")

    # We need enough data for SMA_200 etc. Keep ~2y locally in-memory, but persist in DB.
    latest_trading_day = _latest_trading_day_date()
    start_date = (pd.Timestamp(latest_trading_day) - pd.Timedelta(days=365 * 2)).date()

    results = {}
    
    for ticker_symbol in tickers:
        try:
            # 1) Try DB first
            hist = _history_from_db(ticker_symbol, start_date)

            # 2) Gaps Calculation
            # If DB data is stale (e.g. crawler hasn't run today, or we are mid-day),
            # we might want to fetch the "latest" daily bar from Yahoo to complete the dataset.
            # However, the requirement says "stock.py will only need to fetch today's data without worrying about upserting"
            
            # Find the last date we have
            if not hist.empty:
                last_db_date = hist.index[-1].date()
            else:
                last_db_date = start_date - timedelta(days=1)
            
            # If we are missing data up to latest_trading_day (inclusive)
            if last_db_date < latest_trading_day:
                fetch_start = last_db_date + timedelta(days=1)
                fetch_end = latest_trading_day + timedelta(days=1)
                
                # Fetch ephemeral data
                try:
                    dl = yf.download(
                        ticker_symbol,
                        start=fetch_start.strftime("%Y-%m-%d"),
                        end=fetch_end.strftime("%Y-%m-%d"),
                        progress=False,
                        auto_adjust=False,
                        multi_level_index=False,
                    )
                    
                    if dl is not None and not dl.empty:
                        if "Adj Close" in dl.columns:
                            dl = dl.drop(columns=["Adj Close"])
                        
                        # Filter out weekends
                        dl = dl[dl.index.dayofweek < 5]
                        dl.index.name = "Date"
                        
                        # Concat with history (in-memory only)
                        # Ensure columns match
                        ephemeral_hist = dl[["Open", "High", "Low", "Close", "Volume"]]
                        hist = pd.concat([hist, ephemeral_hist])
                        
                        # Deduplicate in case of overlap logic errors (keep last)
                        hist = hist[~hist.index.duplicated(keep='last')]
                        
                except Exception as e:
                    print(f"Warning: Failed to fetch ephemeral data for {ticker_symbol}: {e}")

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
