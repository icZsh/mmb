# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Morning Market Briefing (MMB)** is an automated financial data aggregation and analysis system that delivers daily stock market insights via email. It combines market data collection, technical analysis, news aggregation, and AI-powered narrative generation into a production-ready pipeline.

## Key Commands

### Development
```bash
# Setup (requires Python 3.12+)
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run tests
python -m unittest tests.test_stock_data
python -m unittest discover tests

# Run main briefing (generates and sends email)
python run.py

# Run stock crawler only (updates database)
python src/data/stock_crawler.py
```

### Configuration
- **Watchlist**: Edit `watchlist.yaml` to add/remove stock tickers
- **Environment**: Copy `.env.example` to `.env` and configure:
  - `GEMINI_API_KEY`: Google Gemini API key (required for AI narratives)
  - `MOTHERDUCK_TOKEN`: MotherDuck cloud database token (optional, falls back to local DuckDB)
  - `NEWS_API_KEY`: NewsAPI key (optional, supplements Yahoo Finance news)
  - SMTP settings for email delivery (falls back to local HTML file if not configured)

## Architecture

### Two-Stage Pipeline

**Stage 1: Stock Crawler** (Scheduled weekdays 14:30 UTC / 9:30 AM ET)
- Updates DuckDB/MotherDuck with latest OHLCV data for all tickers in watchlist
- Triggered by: `.github/workflows/stock_crawler.yaml`
- Entry point: `src/data/stock_crawler.py`

**Stage 2: Daily Briefing** (Triggered after crawler completion)
- Fetches data from database, performs analysis, generates AI narratives, sends email
- Triggered by: `.github/workflows/daily_briefing.yaml`
- Entry point: `run.py`

### Data Flow

```
watchlist.yaml → Stock Crawler → DuckDB/MotherDuck
                                      ↓
                              Daily Briefing (run.py)
                                      ↓
                    ┌─────────────────┴──────────────────┐
                    ↓                                    ↓
            Technical Analysis                    News Aggregation
            (RSI, MACD, Bollinger)               (Yahoo + NewsAPI)
                    ↓                                    ↓
                    └─────────────────┬──────────────────┘
                                      ↓
                            Google Gemini (AI Narrative)
                                      ↓
                            Jinja2 HTML Template
                                      ↓
                            SMTP Email Delivery
```

### Hybrid Data Strategy

**Database-First Approach**: Stock data is primarily fetched from DuckDB/MotherDuck to reduce yfinance API rate limits and improve performance.

**Gap-Filling**: If database data is stale or missing, `src/data/stock.py` automatically fetches recent data from yfinance and uses it for current day calculations (without persisting it - that's the crawler's job).

**Key files**:
- `src/data/stock.py`: Implements hybrid DB + yfinance strategy with 7-day fundamental info cache
- `src/data/stock_crawler.py`: Maintains database freshness (MERGE/INSERT OR IGNORE logic)
- `src/db/client.py`: DuckDB client with MotherDuck cloud support

### Module Responsibilities

**`src/data/`**: Market data acquisition
- `market.py`: Fetches market snapshot (SPY, QQQ, VIX, IXIC)
- `stock.py`: Fetches individual stock data with DB-first + yfinance gap-fill strategy
- `stock_crawler.py`: Scheduled pipeline to keep database fresh

**`src/analysis/`**: Technical analysis engine
- `indicators.py`: Calculates RSI, MACD, Bollinger Bands, ATR, SMAs
- `signals.py`: Generates Trend/Momentum/Volatility signals from indicators

**`src/news/`**: News aggregation
- `aggregator.py`: Multi-source news fetcher (Yahoo Finance + NewsAPI) with >80% title similarity deduplication

**`src/llm/`**: AI narrative generation
- `generator.py`: Uses Google Gemini 3 Flash to generate structured analysis (SUMMARY/BULL/BEAR/WATCH sections) from stock data, indicators, signals, and news

**`src/email/`**: Email rendering and delivery
- `template.html`: Jinja2 HTML email template with responsive mobile/desktop design
- `renderer.py`: Renders template with market data and watchlist analysis
- `sender.py`: SMTP email delivery with local HTML fallback

**`src/db/`**: Database layer
- `client.py`: DuckDB singleton with MotherDuck cloud backend support
  - Tables: `market_history` (OHLCV data), `news_items` (cached headlines)
  - Uses MERGE for upserts, cleans data >5 years old

## Important Patterns

### Database Schema
```sql
-- market_history: OHLCV data with ticker + date as composite primary key
CREATE TABLE IF NOT EXISTS market_history (
    ticker TEXT, date DATE, open DOUBLE, high DOUBLE, low DOUBLE,
    close DOUBLE, volume BIGINT, PRIMARY KEY (ticker, date)
)

-- news_items: Cached news with ticker + title uniqueness
CREATE TABLE IF NOT EXISTS news_items (
    ticker TEXT, title TEXT, url TEXT, published_at TIMESTAMP,
    UNIQUE (ticker, title)
)
```

### MotherDuck Configuration
- Set `MOTHERDUCK_TOKEN` to use cloud backend
- Set `MOTHERDUCK_STRICT=1` to fail workflows if MotherDuck is unavailable
- Database name controlled via `MOTHERDUCK_DB` env var (defaults to `mmb_db`)
- Omit `MOTHERDUCK_TOKEN` to use local `mmb.duckdb` file

### LLM Integration
The system uses **Google Gemini 3 Flash (Preview)** for narrative generation:
- Model ID: `gemini-3.0-flash-exp-preview-01-16`
- Structured prompt requests SUMMARY/BULL/BEAR/WATCH sections
- Response parsing in `src/llm/generator.py` extracts these sections via regex
- Falls back gracefully if parsing fails (returns raw response or empty dict)

### Rate Limiting
- 2-second delays between yfinance `Ticker()` instantiations to avoid rate limits
- Fundamental info cached locally in `fundamental_cache.json` for 7 days
- News articles deduplicated by >80% title similarity to reduce redundant API calls

### Testing Approach
Tests use `unittest.mock` to mock external dependencies:
- `yfinance.Ticker()` mocked to return test fixtures
- `DuckDBClient` mocked to simulate cache hits/misses
- Temporary test databases created to avoid polluting production data
- Tests verify gap-filling logic and data freshness calculations

## Recent Evolution

Based on git history:
1. **v2 Migration**: Moved from pickle caching to DuckDB for better scalability
2. **Cloud Support**: Added MotherDuck integration for distributed/shared data
3. **LLM Upgrade**: Switched from OpenAI GPT-4o-mini to Google Gemini 3 Flash
4. **Two-Stage Pipeline**: Split data collection (crawler) from report generation (briefing) for better workflow orchestration

## Commit Rules

**IMPORTANT:** Before completing any task, you MUST run `/commit` to commit your changes.

- Only commit files YOU modified in this session — never commit unrelated changes
- Use atomic commits with descriptive messages following Conventional Commits format:
  - `feat:` for new features
  - `fix:` for bug fixes
  - `refactor:` for code refactoring
  - `test:` for adding/updating tests
  - `docs:` for documentation changes
  - `chore:` for maintenance tasks
- If there are no changes to commit, skip this step
- Do not push unless explicitly asked

## Notes for Future Development

- The README.md still references "OpenAI (GPT-4o-mini)" but the actual implementation uses Google Gemini (see `src/llm/generator.py`)
- The `.env.example` includes `OPENAI_API_KEY` for legacy compatibility but current code uses `GEMINI_API_KEY`
- Watchlist changes require manual edit of `watchlist.yaml` - no CLI tool for this yet
- Email template styling is inline CSS for maximum email client compatibility
- No tests yet for `test_crawler_pipeline.py` - this is a gap in coverage
