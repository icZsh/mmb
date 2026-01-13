import yaml
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import sys
import os
import time
import logging
from pathlib import Path
from dotenv import load_dotenv

# Ensure env vars are loaded (MOTHERDUCK_TOKEN, etc.)
load_dotenv()

# Make imports + relative paths stable no matter where this script is run from.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

from src.db.client import db

def load_watchlist(path=None):
    if path is None:
        path = PROJECT_ROOT / "watchlist.yaml"
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

    # Be explicit about where we're writing (MotherDuck vs local path).
    try:
        backend = getattr(db, "backend", "unknown")
        local_path = getattr(db, "local_path", None)
        if backend == "motherduck":
            print("✅ Connected to MotherDuck (md:mmb_db)")
        elif backend == "local":
            print(f"⚠️ Using local DuckDB: {local_path}")
        else:
            print(f"ℹ️ DB backend: {backend}")
    except Exception:
        pass

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
        print(f"❌ No tickers found in {PROJECT_ROOT / 'watchlist.yaml'}")
        return

    print(f"Target Tickers: {', '.join(tickers)}")
    
    # Configuration
    YEARS_OF_HISTORY = 5
    today = pd.Timestamp.now(tz='US/Eastern').date()
    # Weekend-aware "latest trading day" for daily bars
    latest_trading_day = today
    if latest_trading_day.weekday() == 5:  # Sat
        latest_trading_day = latest_trading_day - timedelta(days=1)
    elif latest_trading_day.weekday() == 6:  # Sun
        latest_trading_day = latest_trading_day - timedelta(days=2)
    oldest_start = (datetime.now() - timedelta(days=365 * YEARS_OF_HISTORY)).date()
    
    for ticker in tickers:
        print(f"\nProcessing {ticker}...")
        
        # Check what we have
        try:
            max_date = db.get_max_date(ticker)
            if max_date:
                print(f"  Existing data up to: {max_date}")
        except Exception as e:
            print(f"  Error checking max date: {e}")
            max_date = None
        
        # Only download what's missing:
        # - First run: download YEARS_OF_HISTORY
        # - Subsequent runs: download from max_date+1 to latest_trading_day
        if max_date and max_date >= latest_trading_day:
            print(f"  ✅ Up to date (latest: {latest_trading_day}). Skipping download.")
            continue

        if max_date:
            fetch_start = max_date + timedelta(days=1)
        else:
            fetch_start = oldest_start

        # yfinance end is exclusive
        fetch_end = latest_trading_day + timedelta(days=1)
        print(f"  Fetching history {fetch_start} -> {latest_trading_day}...")
        try:
            data = yf.download(
                ticker,
                start=fetch_start.strftime("%Y-%m-%d"),
                end=fetch_end.strftime("%Y-%m-%d"),
                progress=False,
                auto_adjust=False,
                multi_level_index=False,
            )
            
            if not data.empty:
                # Filter out weekends (0=Mon, 5=Sat, 6=Sun)
                data = data[data.index.dayofweek < 5]

            if not data.empty:
                count = len(data)
                print(f"  Downloaded {count} rows.")
                db.upsert_history(ticker, data)
                # Verify inserts so we don't "succeed" silently.
                rows_now = db.con.execute(
                    "SELECT COUNT(*) FROM market_history WHERE ticker = ?",
                    [ticker],
                ).fetchone()[0]
                max_date_now = db.get_max_date(ticker)
                print(f"  ✅ Upsert complete. Rows now: {rows_now}, max date: {max_date_now}")
            else:
                print("  ⚠️ No data returned.")
                
        except Exception as e:
            print(f"  ❌ Error: {e}")

    print("\n--- Seeding Complete ---")

if __name__ == "__main__":
    seed_database()
