import warnings
# Suppress pandas deprecation warnings from yfinance (upstream issue)
warnings.filterwarnings("ignore", message=".*Timestamp.utcnow.*", category=DeprecationWarning)

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
logger = logging.getLogger(__name__)

from src.db.client import db

def load_watchlist(path=None):
    if path is None:
        path = PROJECT_ROOT / "watchlist.yaml"
    try:
        with open(path, 'r') as f:
            config = yaml.safe_load(f)
        return config.get('watchlist', [])
    except Exception as e:
        logger.error(f"Failed to load watchlist: {e}")
        return []

def get_latest_trading_day():
    """
    Returns the latest trading day (Mon-Fri) relative to US/Eastern usage.
    """
    today = pd.Timestamp.now(tz='US/Eastern').date()
    # Weekend-aware "latest trading day" for daily bars
    if today.weekday() == 5:  # Sat
        return today - timedelta(days=1)
    elif today.weekday() == 6:  # Sun
        return today - timedelta(days=2)
    return today

def run_crawler():
    logger.info("--- Starting Stock Crawler ---")
    if not db:
        logger.error("❌ Database connection failed. Aborting.")
        return

    # 1. Load Watchlist
    target_tickers = set(load_watchlist())
    if not target_tickers:
        logger.error(f"❌ No tickers found in {PROJECT_ROOT / 'watchlist.yaml'}")
        return

    logger.info(f"Target Tickers: {', '.join(target_tickers)}")

    # 2. Get existing tickers from DB
    existing_tickers = set(db.get_all_tickers())
    
    # 3. Identify Removals
    tickers_to_remove = existing_tickers - target_tickers
    if tickers_to_remove:
        logger.info(f"Removing outdated tickers: {tickers_to_remove}")
        for t in tickers_to_remove:
            db.delete_ticker(t)
    
    # 4. Process Tickers (Additions/Updates)
    YEARS_OF_HISTORY = 5
    latest_trading_day = get_latest_trading_day()
    oldest_start = (datetime.now() - timedelta(days=365 * YEARS_OF_HISTORY)).date()

    # 5. Cleanup old data globally (or per ticker, but global is easier if schema allows)
    # We'll do it via the new method
    logger.info(f"Cleaning up data older than {oldest_start}...")
    db.delete_old_data(oldest_start)
    
    for ticker in target_tickers:
        logger.info(f"\nProcessing {ticker}...")
        
        # Check max date
        try:
            max_date = db.get_max_date(ticker)
            if max_date:
                logger.info(f"  Existing data up to: {max_date}")
        except Exception as e:
            logger.error(f"  Error checking max date: {e}")
            max_date = None
        
        # Determine fetch start
        if max_date and max_date >= latest_trading_day:
            logger.info(f"  ✅ Up to date (latest: {latest_trading_day}). Skipping download.")
            continue

        if max_date:
            fetch_start = max_date + timedelta(days=1)
        else:
            fetch_start = oldest_start

        # Avoid fetching if start is in future
        if fetch_start > latest_trading_day:
            continue

        # yfinance end is exclusive
        fetch_end = latest_trading_day + timedelta(days=1)
        
        logger.info(f"  Fetching history {fetch_start} -> {latest_trading_day}...")
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
                logger.info(f"  Downloaded {count} rows.")
                db.upsert_history(ticker, data)
                
                # Check results
                max_date_now = db.get_max_date(ticker)
                logger.info(f"  ✅ Upsert complete. Max date now: {max_date_now}")
            else:
                logger.warning("  ⚠️ No data returned.")
                
        except Exception as e:
            logger.error(f"  ❌ Error: {e}")

    logger.info("\n--- Crawler Complete ---")

if __name__ == "__main__":
    run_crawler()
