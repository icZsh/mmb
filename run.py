import yaml
import logging
from datetime import datetime
import time

# Modules
from src.data.market import get_market_snapshot
from src.data.stock import get_stock_data
from src.analysis.indicators import add_indicators
from src.analysis.signals import generate_signals
from src.news.aggregator import get_agg_news
from src.llm.generator import generate_narrative
from src.email.renderer import render_email
from src.email.sender import send_email

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_watchlist(path="watchlist.yaml"):
    try:
        with open(path, 'r') as f:
            config = yaml.safe_load(f)
        return config.get('watchlist', [])
    except Exception as e:
        logger.error(f"Failed to load watchlist: {e}")
        return []

def main():
    logger.info("Starting Morning Market Briefing execution...")
    
    # 1. Load Watchlist
    tickers = load_watchlist()
    if not tickers:
        logger.error("No tickers found in watchlist.")
        return

    # 2. Market Snapshot
    logger.info("Fetching market snapshot...")
    market_snapshot = get_market_snapshot()
    
    # 3. Process Stocks
    logger.info("Processing watchlist...")
    watchlist_data = []
    
    # Batch fetch raw data
    raw_data = get_stock_data(tickers)
    
    for ticker in tickers:
        try:
            logger.info(f"Analyzing {ticker}...")
            
            if ticker not in raw_data:
                logger.warning(f"No data for {ticker}. Skipping.")
                continue
                
            stock_info = raw_data[ticker]
            history = stock_info['history']
            info = stock_info['info']
            
            # Technical Analysis
            analyzed_df = add_indicators(history)
            signals = generate_signals(analyzed_df)
            
            # News
            news = get_agg_news(ticker)
            
            # LLM Narrative
            narrative = generate_narrative(ticker, {'history': analyzed_df, 'info': info}, signals, news)
            
            # Prepare data for template
            latest = analyzed_df.iloc[-1]
            try:
                latest_close = latest['Close']
            except:
                latest_close = 0 # Fallback
                
            prev = analyzed_df.iloc[-2] if len(analyzed_df) > 1 else latest
            change_pct = ((latest_close - prev['Close']) / prev['Close']) * 100
            
            watchlist_data.append({
                'ticker': ticker,
                'price': float(latest_close),
                'change_pct': change_pct,
                'rsi': float(latest.get('RSI', 0)),
                'signals': signals,
                'narrative': narrative,
                'news': news
            })
            
        except Exception as e:
            logger.error(f"Error processing {ticker}: {e}")
            
    # 4. Generate Email
    logger.info("Rendering email...")
    html_content = render_email(market_snapshot, watchlist_data)
    
    # 5. Send Email
    logger.info("Sending email...")
    success = send_email(html_content)
    
    if success:
        logger.info("Briefing completed successfully.")
    else:
        logger.warning("Briefing completed but email failed (check local HTML).")

if __name__ == "__main__":
    main()
