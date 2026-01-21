import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

def generate_narrative(ticker, stock_data, signals, news):
    """
    Generates a narrative for the stock using Google's Gemini.
    """
    try:
        # The client automatically uses GEMINI_API_KEY or GOOGLE_API_KEY from environment
        client = genai.Client()
        
        # Prepare context
        news_summary = ""
        for n in news:
            news_summary += f"- {n.get('title')} (Source: {n.get('publisher')})\n"
        if not news_summary:
            news_summary = "No recent major news."
            
        # Prepare technical context
        hist = stock_data.get('history')
        if hist is None or hist.empty:
             # Handle case where history is empty or missing
             latest_close = "N/A"
             change_pct_str = "N/A"
             rsi_val = "N/A"
        else:
            latest = hist.iloc[-1]
            prev = hist.iloc[-2] if len(hist) > 1 else latest
            
            change_pct = ((latest['Close'] - prev['Close']) / prev['Close']) * 100
            latest_close = f"{latest['Close']:.2f}"
            change_pct_str = f"{change_pct:+.2f}%"
            rsi_val = latest.get('RSI', 'N/A')
    
        context = f"""
        Ticker: {ticker}
        Sector: {stock_data.get('info', {}).get('sector', 'N/A')}
        Industry: {stock_data.get('info', {}).get('industry', 'N/A')}
        
        Price: {latest_close} ({change_pct_str})
        RSI: {rsi_val}
        Trend: {signals.get('Trend')}
        Momentum: {signals.get('Momentum')}
        Volatility: {signals.get('Volatility')}
        
        News Highlights:
        {news_summary}
        """
        
        prompt = f"""
        You are a financial analyst writing a morning brief for an investor.
        Analyze the following data for {ticker} and provide a concise update.
        
        Data:
        {context}
        
        Format output EXACTLY as follows (json format not needed, just the sections):
        SUMMARY: [One sentence summary of what changed and why]
        BULL: [1-2 concise bullet points for bull case]
        BEAR: [1-2 concise bullet points for bear case]
        WATCH: [What to watch today in 1 sentence]
        
        Rules:
        - Be brief. Total reading time should be < 30 seconds.
        - Focus on the "Why" and "So What".
        - Do not give financial advice.
        - Use Markdown formatting for bullets.
        """
        
        # Use gemini-2.0-flash as the standard model for the new SDK
        # User previously asked for 3, but 2.0 Flash is the documented "Flash" model usually coupled with this SDK update.
        # I'll stick to 'gemini-2.0-flash' or 'gemini-1.5-flash' unless I'm sure 3 is available.
        # But the user specifically asked for "gemini 3" earlier.
        # And he used "gemini-3-flash-preview" in his manual edit.
        # I will respect that model name choice but wrap it safely.
        
        response = client.models.generate_content(
            model='gemini-3-flash-preview', 
            contents=prompt
        )
        
        # New SDK response structure handling
        if response.text:
            return parse_llm_response(response.text)
        else:
             return {
                "summary": "Error: No content generated.",
                "bull_case": [],
                "bear_case": [],
                "watch": "Check manual news sources."
            }
        
    except Exception as e:
        print(f"Error generating narrative for {ticker}: {e}")
        return {
            "summary": "Error generating narrative.",
            "bull_case": [],
            "bear_case": [],
            "watch": "Check manual news sources."
        }

def parse_llm_response(text):
    """
    Parses the text output into a structured dict.
    """
    sections = {
        "summary": "",
        "bull_case": [],
        "bear_case": [],
        "watch": ""
    }
    
    current_section = None
    lines = text.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if line.startswith("SUMMARY:"):
            current_section = "summary"
            sections["summary"] = line.replace("SUMMARY:", "").strip()
        elif line.startswith("BULL:"):
            current_section = "bull_case"
            # If content is on the same line
            content = line.replace("BULL:", "").strip()
            if content:
                sections["bull_case"].append(content)
        elif line.startswith("BEAR:"):
            current_section = "bear_case"
            content = line.replace("BEAR:", "").strip()
            if content:
                sections["bear_case"].append(content)
        elif line.startswith("WATCH:"):
             current_section = "watch"
             sections["watch"] = line.replace("WATCH:", "").strip()
        else:
            # Continuation of previous section
            if current_section == "bull_case" or current_section == "bear_case":
                # Clean up bullets like "- " or "* "
                clean_line = line.lstrip("-*• ")
                sections[current_section].append(clean_line)
            elif current_section == "summary":
                sections["summary"] += " " + line
            elif current_section == "watch":
                sections["watch"] += " " + line
                
    return sections

if __name__ == "__main__":
    # Mock data for testing
    import pandas as pd
    mock_df = pd.DataFrame({'Close': [100, 102], 'RSI': [55, 60]})
    mock_signals = {"Trend": "Bullish", "Momentum": "Strong", "Volatility": "Normal"}
    mock_info = {"sector": "Tech", "industry": "Consumer Electronics"}
    mock_stock = {"history": mock_df, "info": mock_info}
    mock_news = [{"title": "Company releases new AI product", "publisher": "TechCrunch"}]
    
    # Simple test execution
    print("Testing Gemini Generator...")
    # Enable debug logging for the library if possible, but let's just catch the error details
    try:
        # Check if API key is present
        if not os.getenv("GEMINI_API_KEY"):
            print("WARNING: GEMINI_API_KEY not set for test.")

        result = generate_narrative("TEST", mock_stock, mock_signals, mock_news)
        print("\nGenerated Result:")
        print(result)
        
        # Check if result indicates error
        if result.get('summary') == "Error generating narrative.":
            print("\n!!! VALIDATION FAILED !!!")
            # We can't see the internal error here because it's caught inside the function.
            # I will assume the function printed it to stdout/stderr.
            
    except Exception as e:
        print(f"\nTest Failed: {e}")
