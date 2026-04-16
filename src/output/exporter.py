import json
import os
from datetime import datetime
from pathlib import Path


ARTIFACT_SUBDIR = ("Hermes", "Morning Briefing")
ARTIFACT_TYPE = "mmb-daily-brief"


def _sanitize(value):
    if isinstance(value, dict):
        return {str(k): _sanitize(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_sanitize(v) for v in value]
    if isinstance(value, tuple):
        return [_sanitize(v) for v in value]
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, "isoformat") and not isinstance(value, (str, bytes)):
        try:
            return value.isoformat()
        except TypeError:
            pass
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return value


def save_structured_brief(market_data, watchlist_data, vault_path=None):
    """Save a machine-readable daily briefing artifact under the Obsidian vault."""
    resolved_vault = vault_path or os.getenv("OBSIDIAN_VAULT_PATH")
    if not resolved_vault:
        return None

    now = datetime.now()
    artifact_dir = Path(resolved_vault).joinpath(*ARTIFACT_SUBDIR, now.strftime("%Y"), now.strftime("%m"))
    artifact_dir.mkdir(parents=True, exist_ok=True)

    artifact_path = artifact_dir / f"{now.strftime('%Y-%m-%d')}-mmb.json"
    payload = {
        "artifact_type": ARTIFACT_TYPE,
        "generated_at": now.isoformat(),
        "market": _sanitize(market_data),
        "watchlist": _sanitize(watchlist_data),
    }
    artifact_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved structured briefing artifact: {artifact_path}")
    return artifact_path
