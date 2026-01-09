
import yaml
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import sys
import os
import time

# Add path
sys.path.append(os.getcwd())

from src.db.client import db

def load_watchlist(path="watchlist.yaml"):
    try:
        with open(path, 'r') as f:
            config = yaml.safe_load(f)
        return config.get('watchlist', [])
    except Exception as e:
        print(f"Failed to load watchlist: {e}")
        return []

def seed_database():
    print("--- Starting Database Seed ---")
    if not db:
        print("❌ Database connection failed. Aborting.")
        return

    # Check connection type by inspecting private attribute if possible or just inferring from logs
    # But let's verify connectivity
    try:
        res = db.con.execute("SELECT 1").fetchone()
        print("✅ DB Connectivity Check Passed")
    except Exception as e:
        print(f"❌ DB Check failed: {e}")
        return

    tickers = load_watchlist()
    if not tickers:
        print("❌ No tickers found in watchlist.yaml")
        return

    print(f"Target Tickers: {', '.join(tickers)}")
    
    # Configuration
    YEARS_OF_HISTORY = 5
    start_date = (datetime.now() - timedelta(days=365 * YEARS_OF_HISTORY)).strftime('%Y-%m-%d')
    
    for ticker in tickers:
        print(f"\nProcessing {ticker}...")
        
        # Check what we have
        try:
            max_date = db.get_max_date(ticker)
            if max_date:
                print(f"  Existing data up to: {max_date}")
        except Exception as e:
            print(f"  Error checking max date: {e}")
        
        print(f"  Fetching history from {start_date}...")
        try:
            time.sleep(1) 
            data = yf.download(ticker, start=start_date, progress=False, multi_level_index=False)
            
            if not data.empty:
                count = len(data)
                print(f"  Downloaded {count} rows.")
                db.upsert_history(ticker, data)
                print("  ✅ Upsert complete.")
            else:
                print("  ⚠️ No data returned.")
                
        except Exception as e:
            print(f"  ❌ Error: {e}")

    print("\n--- Seeding Complete ---")

if __name__ == "__main__":
    seed_database()
