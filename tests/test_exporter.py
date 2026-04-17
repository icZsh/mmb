import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.email.sender import send_email
from src.output.exporter import save_structured_brief


class SaveStructuredBriefTests(unittest.TestCase):
    def test_send_email_can_be_disabled_for_local_artifact_runs(self):
        html = "<html><body>brief</body></html>"

        with patch.dict(
            os.environ,
            {
                "MMB_DISABLE_EMAIL": "1",
                "SMTP_USER": "user@example.com",
                "SMTP_PASSWORD": "secret",
                "EMAIL_RECIPIENT": "isaac@example.com",
            },
            clear=False,
        ), patch("builtins.open", wraps=open) as mocked_open:
            with patch("src.email.sender.smtplib.SMTP") as mock_smtp:
                result = send_email(html)

        self.assertTrue(result)
        mock_smtp.assert_not_called()
        self.assertTrue(any(call.args[0] == "latest_briefing.html" for call in mocked_open.mock_calls if call.args))

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

    def test_writes_markdown_index_note_linking_html_and_json_outputs(self):
        market = {"SPY": {"price": 523.1, "change_pct": 0.42, "name": "S&P 500"}}
        watchlist = []

        with tempfile.TemporaryDirectory() as tmpdir:
            vault = Path(tmpdir) / "Isaac's Vault"
            html_dir = vault / "2026" / "04"
            html_dir.mkdir(parents=True, exist_ok=True)
            html_path = html_dir / "Morning Market Briefing – 2026-04-16.html"
            html_path.write_text("<html></html>", encoding="utf-8")

            class FixedDateTime:
                @classmethod
                def now(cls):
                    import datetime
                    return datetime.datetime(2026, 4, 16, 7, 0, 0)

            with patch("src.output.exporter.datetime", FixedDateTime):
                artifact_path = save_structured_brief(market, watchlist, vault_path=str(vault))

            note_path = vault / "Hermes" / "Morning Briefing" / "2026" / "04" / "2026-04-16-mmb.md"
            self.assertTrue(note_path.exists())
            note_content = note_path.read_text(encoding="utf-8")
            self.assertIn("[查看 HTML 晨报](../../../../2026/04/Morning Market Briefing – 2026-04-16.html)", note_content)
            self.assertIn(f"[查看 JSON artifact]({artifact_path.name})", note_content)


if __name__ == "__main__":
    unittest.main()
