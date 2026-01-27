# Morning Market Briefing (MMB) 📈

**Morning Market Briefing (MMB)** is an automated tool designed to deliver a concise, data-driven daily investment briefing directly to your inbox every morning at 8:00 AM PST.

It aggregates market data, performs technical analysis, fetches relevant news, and uses AI to generate actionable narratives for your personal watchlist.

## 🚀 Features

- **Market Snapshot**: Daily pulse on S&P 500 (SPY), Nasdaq-100 (QQQ), Nasdaq Composite (^IXIC), and VIX.
- **Smart Watchlist**: customizable tracking via `watchlist.yaml`.
- **Technical Analysis**:
    - Indicators: RSI, MACD, Bollinger Bands, Moving Averages.
    - Signals: Trend (Bullish/Bearish), Momentum (Overbought/Oversold), and Volatility flags.
- **AI Narratives**: Uses OpenAI (GPT-4o-mini) to generate:
    - "Why it matters" summaries.
    - Bull & Bear cases.
    - "What to watch today" highlights.
- **News Aggregation**: Smart deduplication of headlines from Yahoo Finance & NewsAPI.
- **Email Delivery**: Beautiful, mobile-friendly HTML email reports.
- **Automated**: Runs completely autonomously via GitHub Actions.

## 🛠️ Setup & Installation

### Prerequisites
- Python 3.12+
- OpenAI API Key

### 1. Clone & Install
```bash
git clone https://github.com/yourusername/mmb.git
cd mmb
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configuration (`.env`)
Create a `.env` file in the root directory (copy from `.env.example`):
```bash
cp .env.example .env
```
Fill in your credentials:
```ini
OPENAI_API_KEY=sk-...
NEWS_API_KEY=... (Optional)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASSWORD=your_app_password
EMAIL_RECIPIENT=target_email@domain.com
```

> **Note**: For Gmail, you must use an [App Password](https://support.google.com/accounts/answer/185833), not your login password.

### 3. Edit Watchlist
Modify `watchlist.yaml` to track your favorite stocks:
```yaml
watchlist:
  - AAPL
  - NVDA
  - TSLA
  - BTC-USD
```

## 🏃 Usage

### Run Locally
```bash
python run.py
```
If SMTP credentials are not set, the report will be saved locally as `latest_briefing.html` for preview.

### Run via GitHub Actions
This project is configured to run automatically every weekday at **8:00 AM PST**.

To enable this:
1. Push this code to a minimal GitHub repository.
2. Go to **Settings > Secrets and variables > Actions**.
3. Add the environment variables from your `.env` file as **Repository Secrets**.

You can also manually trigger the workflow from the "Actions" tab.

## 📂 Project Structure
```
mmb/
├── .github/workflows/   # Daily schedule automation
├── src/
│   ├── data/           # Market & Stock data fetchers
│   ├── analysis/       # Technical indicators & signals
│   ├── news/           # News aggregator
│   ├── llm/            # OpenAI narrative generator
│   └── email/          # HTML renderer & Sender
├── watchlist.yaml      # Configuration
├── run.py              # Main entry point
└── requirements.txt    # Dependencies
```

## 📜 License
MIT
