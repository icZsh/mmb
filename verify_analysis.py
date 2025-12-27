from src.data.stock import get_stock_data
from src.analysis.indicators import add_indicators
from src.analysis.signals import generate_signals

def verify():
    # Fetch data
    print("Fetching data...")
    stock_data = get_stock_data(['AAPL'])
    if not stock_data:
        print("Failed to fetch data.")
        return

    df = stock_data['AAPL']['history']
    
    # Calculate indicators
    print("Calculating indicators...")
    df_analyzed = add_indicators(df)
    
    print("\n--- Recent Data ---")
    print(df_analyzed[['Close', 'RSI', 'SMA_50', 'SMA_200', 'BB_Bandwidth']].tail())
    
    # Generate signals
    print("\n--- Signals ---")
    signals = generate_signals(df_analyzed)
    print(signals)

if __name__ == "__main__":
    verify()
