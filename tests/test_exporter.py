import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.output.exporter import save_structured_brief


class SaveStructuredBriefTests(unittest.TestCase):
    def test_writes_json_artifact_to_obsidian_briefing_directory(self):
        market = {
            "SPY": {"price": 523.1, "change_pct": 0.42, "name": "S&P 500"},
            "QQQ": {"price": 440.2, "change_pct": -0.17, "name": "Nasdaq-100"},
        }
        watchlist = [
            {
                "ticker": "AAPL",
                "price": 199.5,
                "change_pct": 1.2,
                "gap_pct": 0.3,
                "intraday_move": 0.9,
                "day_range_pct": 1.7,
                "rsi": 58.4,
                "signals": {"Trend": "Bullish", "Momentum": "Strong", "Volatility": "Normal"},
                "narrative": {
                    "summary": "AAPL tracked stronger than the tape.",
                    "bull_case": ["Services mix stayed firm."],
                    "bear_case": ["Valuation is full."],
                    "watch": "Watch supply-chain commentary."
                },
                "news": [{"title": "Apple supplier update", "publisher": "Reuters", "link": "https://example.com"}],
            }
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Isaac's Vault"
            expected_dir = vault / "Hermes" / "Morning Briefing" / "2026" / "04"

            class FixedDateTime:
                @classmethod
                def now(cls):
                    import datetime
                    return datetime.datetime(2026, 4, 16, 7, 0, 0)

            with patch("src.output.exporter.datetime", FixedDateTime):
                artifact_path = save_structured_brief(market, watchlist, vault_path=str(vault))

            self.assertEqual(
                artifact_path,
                expected_dir / "2026-04-16-mmb.json",
            )
            self.assertTrue(artifact_path.exists())

            payload = json.loads(artifact_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["watchlist"][0]["ticker"], "AAPL")
            self.assertEqual(payload["market"]["SPY"]["name"], "S&P 500")
            self.assertEqual(payload["artifact_type"], "mmb-daily-brief")


if __name__ == "__main__":
    unittest.main()
