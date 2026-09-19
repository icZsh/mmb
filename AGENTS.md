# AGENTS.md

Shared project instructions for coding agents (Codex, Cursor, Claude Code ≥2.1.277, etc.).

## Project overview

**Morning Market Briefing (MMB)** aggregates market data, technical analysis, news, and AI narratives into a daily email briefing.

## Commands

```bash
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

python -m unittest tests.test_stock_data
python -m unittest discover tests

python run.py                      # full briefing + email/HTML
python src/data/stock_crawler.py   # crawler only
```

Config: edit `watchlist.yaml`; copy `.env.example` → `.env` (`GEMINI_API_KEY` required for narratives; `MOTHERDUCK_TOKEN`, `NEWS_API_KEY`, SMTP optional).

## Architecture

Two-stage pipeline:

1. **Stock crawler** (weekdays ~14:30 UTC) — `.github/workflows/stock_crawler.yaml` → `src/data/stock_crawler.py`
2. **Daily briefing** (after crawler) — `.github/workflows/daily_briefing.yaml` → `run.py`

Hybrid data: DuckDB/MotherDuck first; `src/data/stock.py` gap-fills from yfinance without persisting (crawler owns persistence).

Key modules: `src/data/`, `src/analysis/`, `src/news/`, `src/llm/` (Gemini), `src/email/`, `src/db/`.

## Conventions

- Prefer DB-first reads; rate-limit yfinance (~2s between `Ticker()`).
- News dedupe by high title similarity.
- Do not store API keys in the database.
- README may still mention OpenAI; implementation uses `GEMINI_API_KEY` / Gemini — trust the code over stale README wording.
- Commits: Conventional Commits; only commit files you changed; do not push unless asked.
