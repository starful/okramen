"""Frontmatter date helpers — stable published dates for NEW badges."""
from __future__ import annotations

import os
from datetime import date, datetime


def file_mtime_date(filepath: str) -> str:
    return datetime.fromtimestamp(os.path.getmtime(filepath)).strftime("%Y-%m-%d")


def parse_date_string(raw) -> str | None:
    if not raw:
        return None
    s = str(raw).strip()[:10]
    if len(s) < 10:
        return None
    try:
        return date.fromisoformat(s).isoformat()
    except ValueError:
        return None


def published_from_post(post, filepath: str) -> str:
    return parse_date_string(post.get("date")) or file_mtime_date(filepath)


def ensure_post_date(post, filepath: str) -> tuple[str, bool]:
    """Set post['date'] from mtime when missing. Returns (date, changed)."""
    existing = parse_date_string(post.get("date"))
    if existing:
        return existing, False
    pub = file_mtime_date(filepath)
    post["date"] = pub
    return pub, True


def save_post(filepath: str, post) -> None:
    import frontmatter

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(frontmatter.dumps(post))
