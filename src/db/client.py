
import duckdb
import os
import logging
from dotenv import load_dotenv

# Ensure env vars are loaded if this module is imported directly or by a script that forgot to load them
load_dotenv()

logger = logging.getLogger(__name__)

class MMBDb:
    def __init__(self):
        self.con = None
        self.connect()
        self.init_schema()

    def connect(self):
        """
        Connects to MotherDuck using the token from env, or falls back to local file.
        """
        token = os.getenv("MOTHERDUCK_TOKEN")
        if token:
            try:
                # 'md:' prefix connects to MotherDuck
                # 'mmb_db' is the database name in MotherDuck
                self.con = duckdb.connect(f"md:mmb_db?motherduck_token={token}")
                logger.info("Connected to MotherDuck (md:mmb_db)")
            except Exception as e:
                logger.error(f"Failed to connect to MotherDuck: {e}. Falling back to local.")
                self.con = duckdb.connect("mmb.duckdb")
        else:
            logger.info("No MOTHERDUCK_TOKEN found. Using local DuckDB (mmb.duckdb).")
            self.con = duckdb.connect("mmb.duckdb")

    def init_schema(self):
        """
        Creates necessary tables if they don't exist.
        """
        try:
            # 1. Market History (OHLCV)
            # We use IF NOT EXISTS so it's safe to run every time
            self.con.execute("""
                CREATE TABLE IF NOT EXISTS market_history (
                    ticker VARCHAR,
                    date DATE,
                    open DOUBLE,
                    high DOUBLE,
                    low DOUBLE,
                    close DOUBLE,
                    volume BIGINT,
                    PRIMARY KEY (ticker, date)
                )
            """)
            
            # 2. News Items
            self.con.execute("""
                CREATE TABLE IF NOT EXISTS news_items (
                    ticker VARCHAR,
                    title VARCHAR,
                    publisher VARCHAR,
                    link VARCHAR,
                    provider_publish_time BIGINT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(ticker, title)
                )
            """)
            
            logger.info("Database schema initialized.")
        except Exception as e:
            logger.error(f"Error initializing schema: {e}")
            raise

    def get_max_date(self, ticker):
        """
        Returns the latest date we have data for the given ticker.
        """
        result = self.con.execute("SELECT MAX(date) FROM market_history WHERE ticker = ?", [ticker]).fetchone()
        return result[0] if result else None

    def upsert_history(self, ticker, df):
        """
        Inserts new historical data for a ticker.
        df should have index as Date and columns: Open, High, Low, Close, Volume
        """
        if df.empty:
            return

        # Prepare list of tuples
        data = []
        for index, row in df.iterrows():
            # index is Timestamp
            date_val = index.date()
            data.append((
                ticker,
                date_val,
                row.get('Open', 0),
                row.get('High', 0),
                row.get('Low', 0),
                row.get('Close', 0),
                int(row.get('Volume', 0))
            ))
            
        # Bulk insert/ignore to handle duplicates overlap
        try:
            self.con.executemany("""
                INSERT OR IGNORE INTO market_history (ticker, date, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, data)
        except Exception as e:
            logger.error(f"Error inserting history for {ticker}: {e}")

    def get_history(self, ticker, limit_days=365):
        """
        Retrieves history from DB as a DataFrame-like structure (list of dicts).
        """
        query = f"""
            SELECT date, open, high, low, close, volume 
            FROM market_history 
            WHERE ticker = ? 
            ORDER BY date ASC
        """
        # We can implement limit logic in WHERE date > now - limit... if needed
        # For now, get all
        
        result = self.con.execute(query, [ticker]).df()
        if not result.empty:
             # Set date as index to match yfinance generic output format expectations if needed,
             # but we'll handle conversion in stock.py
             pass
        return result

    def get_recent_news(self, ticker, hours=24):
        """
        Get news from DB that is newer than X hours ago.
        """
        # Provider publish time is epoch seconds
        # We also check created_at for freshness if needed, but publisher time is better source of truth
        cutoff = (datetime.now() - timedelta(hours=hours)).timestamp()
        
        query = """
            SELECT title, link, publisher, provider_publish_time 
            FROM news_items 
            WHERE ticker = ? AND provider_publish_time > ?
            ORDER BY provider_publish_time DESC
        """
        result = self.con.execute(query, [ticker, cutoff]).fetchall()
        
        news_list = []
        for r in result:
            news_list.append({
                'title': r[0],
                'link': r[1],
                'publisher': r[2],
                'providerPublishTime': r[3]
            })
        return news_list

    def insert_news(self, ticker, news_list):
        """
        Inserts news items, ignoring duplicates.
        """
        if not news_list:
            return
            
        data = []
        for n in news_list:
            data.append((
                ticker,
                n.get('title'),
                n.get('publisher'),
                n.get('link'),
                n.get('providerPublishTime', 0)
            ))
            
        try:
            self.con.executemany("""
                INSERT OR IGNORE INTO news_items (ticker, title, publisher, link, provider_publish_time)
                VALUES (?, ?, ?, ?, ?)
            """, data)
        except Exception as e:
            logger.error(f"Error inserting news for {ticker}: {e}")

# Singleton instance
from datetime import datetime, timedelta
# (re-importing here because class method used it)

try:
    db = MMBDb()
except Exception as e:
    # If imports fail or something (e.g. during script load without env), handle gently
    print(f"DB Init Warning: {e}")
    db = None
