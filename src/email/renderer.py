from jinja2 import Environment, FileSystemLoader, select_autoescape
import os
from datetime import datetime

def render_email(market_data, watchlist_data):
    """
    Renders the HTML email with the given data.
    """
    env = Environment(
        loader=FileSystemLoader(os.path.join(os.path.dirname(__file__))),
        autoescape=select_autoescape(['html', 'xml'])
    )
    
    template = env.get_template('template.html')
    
    return template.render(
        date=datetime.now().strftime("%Y-%m-%d"),
        market=market_data,
        watchlist=watchlist_data
    )

if __name__ == "__main__":
    # Test rendering with dummy data
    html = render_email(
        market_data={'SPY': {'name': 'S&P 500', 'label': '+0.5%', 'change_pct': 0.5}},
        watchlist_data=[{
            'ticker': 'AAPL', 'price': 150.00, 'change_pct': 1.2, 'rsi': 55,
            'signals': {'Trend': 'Bullish', 'Volatility': 'Normal'},
            'narrative': {
                'summary': 'Stock is doing well.',
                'bull_case': ['New product'],
                'bear_case': ['Supply chain'],
                'watch': 'Earnings call'
            }
        }]
    )
    print(html[:500])
