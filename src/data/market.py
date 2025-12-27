import yfinance as yf
import pandas as pd

def get_market_snapshot():
    """
    Fetches market snapshot for SPY, QQQ, VIX and IXIC.
    Returns a dictionary with formatted strings for the briefing.
    """
    tickers = ['SPY', 'QQQ', '^VIX', '^IXIC']
    data = yf.Tickers(' '.join(tickers))
    
    snapshot = {}
    
    for ticker_symbol in tickers:
        try:
            ticker = data.tickers[ticker_symbol]
            hist = ticker.history(period="5d")
            
            if hist.empty:
                snapshot[ticker_symbol] = {"price": 0.0, "change_pct": 0.0, "label": "N/A"}
                continue
                
            current_price = hist['Close'].iloc[-1]
            prev_close = hist['Close'].iloc[-2] if len(hist) > 1 else current_price
            
            # Try to get real-time price if available (during market hours or pre-market)
            # yfinance often provides 'regularMarketPrice' or 'preMarketPrice' in info
            # fast_info is reliable for latest price
            # but for simplicity and reliability with history, we stick to Close for now, 
            # or use fast_info.last_price
            
            latest_price = ticker.fast_info.last_price
            if latest_price:
                 current_price = latest_price
            
            change = current_price - prev_close
            change_pct = (change / prev_close) * 100
            
            label = ""
            if ticker_symbol == '^VIX':
                label = f"{current_price:.2f} ({change_pct:+.1f}%)"
            else:
                label = f"{change_pct:+.1f}%"
                
            # Determine readable name
            name = ticker_symbol
            if ticker_symbol == 'SPY':
                name = "S&P 500"
            elif ticker_symbol == 'QQQ':
                name = "Nasdaq-100"
            elif ticker_symbol == '^VIX':
                name = "VIX"
            elif ticker_symbol == '^IXIC':
                name = "Nasdaq Composite"
                
            snapshot[ticker_symbol] = {
                "price": current_price,
                "change_pct": change_pct,
                "label": label,
                "name": name
            }
            
        except Exception as e:
            print(f"Error serving {ticker_symbol}: {e}")
            snapshot[ticker_symbol] = {"price": 0.0, "change_pct": 0.0, "label": "Error"}
            
    return snapshot

if __name__ == "__main__":
    print(get_market_snapshot())
