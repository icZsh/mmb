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


def _write_markdown_index(vault_root, artifact_path, now):
    note_path = artifact_path.with_suffix(".md")
    html_path = Path(vault_root) / now.strftime("%Y") / now.strftime("%m") / f"Morning Market Briefing – {now.strftime('%Y-%m-%d')}.html"

    lines = [
        f"# Morning Briefing Artifact – {now.strftime('%Y-%m-%d')}",
        "",
        "这个索引页是给 Obsidian 用的，避免 `.json` 在侧边栏里不明显。",
        "",
    ]

    if html_path.exists():
        html_relative = os.path.relpath(html_path, start=note_path.parent)
        lines.append(f"- [查看 HTML 晨报]({html_relative})")
    else:
        lines.append("- HTML 晨报：未找到")

    lines.append(f"- [查看 JSON artifact]({artifact_path.name})")
    lines.append("")

    note_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Saved Obsidian index note: {note_path}")
    return note_path


def save_structured_brief(market_data, watchlist_data, vault_path=None):
    """Save a machine-readable daily briefing artifact under the Obsidian vault."""
    resolved_vault = vault_path or os.getenv("OBSIDIAN_VAULT_PATH")
    if not resolved_vault:
        return None

    now = datetime.now()
    vault_root = Path(resolved_vault)
    artifact_dir = vault_root.joinpath(*ARTIFACT_SUBDIR, now.strftime("%Y"), now.strftime("%m"))
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
    _write_markdown_index(vault_root, artifact_path, now)
    return artifact_path
