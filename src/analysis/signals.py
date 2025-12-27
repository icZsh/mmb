import pandas as pd

def generate_signals(df):
    """
    Generates signals based on the latest indicators.
    Returns a dictionary of signals.
    """
    if df.empty or 'RSI' not in df:
        return {"Trend": "Unknown", "Momentum": "Unknown", "Volatility": "Unknown"}
        
    latest = df.iloc[-1]
    
    # Trend Signal
    close = latest['Close']
    sma50 = latest['SMA_50']
    sma200 = latest['SMA_200']
    
    trend = "Neutral"
    if pd.notna(sma50) and pd.notna(sma200):
        if close > sma50 and sma50 > sma200:
            trend = "Bullish"
        elif close < sma50 and sma50 < sma200:
            trend = "Bearish"
        elif close > sma200:
            trend = "Leaning Bullish" # Above 200 but maybe below 50
        elif close < sma200:
            trend = "Leaning Bearish"
            
    # Momentum Signal (RSI)
    rsi = latest['RSI']
    momentum = "Neutral"
    if pd.notna(rsi):
        if rsi > 70:
            momentum = "Overbought"
        elif rsi < 30:
            momentum = "Oversold"
        elif rsi > 60:
            momentum = "Strong"
        elif rsi < 40:
            momentum = "Weak"
            
    # Volatility Signal (BB Bandwidth vs recent average)
    # If current width is much larger than average width of last 20 days
    current_width = latest['BB_Bandwidth']
    avg_width = df['BB_Bandwidth'].rolling(window=20).mean().iloc[-1]
    
    volatility = "Normal"
    if pd.notna(current_width) and pd.notna(avg_width):
        if current_width > avg_width * 1.5:
            volatility = "Elevated"
        elif current_width < avg_width * 0.7:
            volatility = "Compressed" # Squeeze
            
    return {
        "Trend": trend,
        "Momentum": momentum,
        "Volatility": volatility
    }
