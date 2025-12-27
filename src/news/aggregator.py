import os
import yfinance as yf
import requests
from datetime import datetime, timedelta
import difflib

def get_news_yfinance(ticker):
    """
    Fetches news from Yahoo Finance via yfinance library.
    """
    try:
        t = yf.Ticker(ticker)
        news = t.news
        return news
    except Exception as e:
        print(f"Error fetching yfinance news for {ticker}: {e}")
        return []

def get_news_newsapi(ticker, api_key):
    """
    Fetches news from NewsAPI.
    """
    try:
        url = "https://newsapi.org/v2/everything"
        # Calculate date for last 24 hours
        from_date = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        
        params = {
            'q': ticker,
            'from': from_date,
            'sortBy': 'relevancy',
            'apiKey': api_key,
            'language': 'en',
            'pageSize': 5
        }
        response = requests.get(url, params=params)
        data = response.json()
        
        if data.get('status') == 'ok':
            articles = []
            for art in data.get('articles', []):
                articles.append({
                    'title': art['title'],
                    'link': art['url'],
                    'publisher': art['source']['name'],
                    'providerPublishTime': int(datetime.strptime(art['publishedAt'], "%Y-%m-%dT%H:%M:%SZ").timestamp())
                })
            return articles
        else:
            print(f"NewsAPI error for {ticker}: {data.get('message')}")
            return []
            
    except Exception as e:
        print(f"Error fetching NewsAPI for {ticker}: {e}")
        return []

def is_similar(title1, title2, threshold=0.8):
    """Checks if two titles are similar."""
    ratio = difflib.SequenceMatcher(None, title1, title2).ratio()
    return ratio > threshold

def deduplicate_news(news_list):
    """
    Removes duplicate news articles based on title similarity.
    """
    if not news_list:
        return []
        
    unique_news = []
    seen_titles = []
    
    for article in news_list:
        title = article.get('title', '')
        if not title:
            continue
            
        is_dup = False
        for seen in seen_titles:
            if is_similar(title, seen):
                is_dup = True
                break
        
        if not is_dup:
            seen_titles.append(title)
            unique_news.append(article)
            
    return unique_news

def get_agg_news(ticker):
    """
    Aggregates news from available sources.
    Prioritizes yfinance as it is free and specific.
    """
    news_items = []
    
    # Try yfinance first (it's robust and specific for stocks)
    yf_news = get_news_yfinance(ticker)
    if yf_news:
        news_items.extend(yf_news)
        
    # If using NewsAPI
    api_key = os.getenv('NEWS_API_KEY')
    if api_key and api_key != 'your_news_api_key_here':
        na_news = get_news_newsapi(ticker, api_key)
        if na_news:
            news_items.extend(na_news)
    
    # Sort by time (newest first)
    # yfinance uses 'providerPublishTime' (epoch)
    # Ensure all have this field
    clean_news = []
    for item in news_items:
        # Normalize fields
        if 'providerPublishTime' not in item:
            item['providerPublishTime'] = 0 # Push to bottom if invalid
        clean_news.append(item)
        
    clean_news.sort(key=lambda x: x['providerPublishTime'], reverse=True)
    
    # Deduplicate
    final_news = deduplicate_news(clean_news)
    
    # Limit to top 3 relevant pieces
    return final_news[:3]

if __name__ == "__main__":
    n = get_agg_news("AAPL")
    for i in n:
        print(f"- {i['title']} ({datetime.fromtimestamp(i['providerPublishTime'])})")
