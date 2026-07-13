#!/usr/bin/env python3
"""Compute okramen GSC cleanup buckets from Performance export + local MD dates."""

from __future__ import annotations

import csv
import io
import re
import zipfile
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

import frontmatter

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "app" / "content"
GUIDES = CONTENT / "guides"
GSC_ZIP = Path("/Users/starful/Downloads/okramen.net-Performance-on-Search-2026-07-13.zip")
TODAY = date(2026, 7, 13)
ONE_MONTH = date(2026, 6, 13)
IMP_THRESHOLD = 30


def base_slug(stem: str) -> str:
    if stem.endswith("_en") or stem.endswith("_ko"):
        return stem.rsplit("_", 1)[0]
    return stem


def lang_from_stem(stem: str) -> str:
    return "ko" if stem.endswith("_ko") else "en"


def parse_date(meta: dict) -> date | None:
    d = meta.get("date")
    if not d:
        return None
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, date):
        return d
    try:
        return datetime.strptime(str(d)[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def load_gsc_pages(zip_path: Path = GSC_ZIP) -> dict[str, dict[str, int]]:
    stats: dict[str, dict[str, int]] = {}
    if not zip_path.exists():
        return stats
    with zipfile.ZipFile(zip_path) as z:
        raw = None
        for name in z.namelist():
            data = z.read(name).decode("utf-8-sig")
            if data.startswith("인기 페이지") or data.startswith("Top pages"):
                raw = data
                break
        if raw is None:
            return stats
    for row in csv.DictReader(io.StringIO(raw)):
        url = (row.get("인기 페이지") or row.get("Top pages") or "").strip().rstrip("/")
        if not url.startswith("http"):
            continue
        clicks = int(float(row.get("클릭수") or row.get("Clicks") or 0))
        imp = int(float(row.get("노출") or row.get("Impressions") or 0))
        stats[url] = {"clicks": clicks, "imp": imp}
    return stats


def url_for(kind: str, base: str, lang: str) -> str:
    seg = "guide" if kind == "guide" else "ramen"
    return f"https://okramen.net/{seg}/{base}_{lang}"


def local_topics() -> dict[tuple[str, str], list[dict]]:
    topics: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for p in list(CONTENT.glob("*.md")) + list(GUIDES.glob("*.md")):
        post = frontmatter.loads(p.read_text(encoding="utf-8"))
        kind = "guide" if "guides" in p.parts else "ramen"
        base = base_slug(p.stem)
        lang = lang_from_stem(p.stem)
        topics[(kind, base)].append(
            {
                "path": p,
                "rel": str(p.relative_to(ROOT)),
                "kind": kind,
                "base": base,
                "lang": lang,
                "url": url_for(kind, base, lang),
                "date": parse_date(dict(post.metadata)),
            }
        )
    return topics


def classify(zip_path: Path = GSC_ZIP) -> dict[str, list[dict]]:
    page_stats = load_gsc_pages(zip_path)
    topics = local_topics()
    buckets: dict[str, list[dict]] = {
        "protect_click": [],
        "protect_new": [],
        "rewrite": [],
        "delete": [],
    }

    for (kind, base), files in sorted(topics.items()):
        total_clicks = 0
        total_imp = 0
        newest = None
        enriched = []
        for f in files:
            st = page_stats.get(f["url"], {"clicks": 0, "imp": 0})
            total_clicks += st["clicks"]
            total_imp += st["imp"]
            if f["date"] and (newest is None or f["date"] > newest):
                newest = f["date"]
            enriched.append({**f, **st})
        entry = {
            "kind": kind,
            "base": base,
            "clicks": total_clicks,
            "imp": total_imp,
            "newest": newest,
            "files": enriched,
        }
        if total_clicks > 0:
            buckets["protect_click"].append(entry)
        elif newest and newest >= ONE_MONTH:
            buckets["protect_new"].append(entry)
        elif total_imp >= IMP_THRESHOLD:
            buckets["rewrite"].append(entry)
        else:
            buckets["delete"].append(entry)
    return buckets


def main() -> int:
    buckets = classify()
    for name, items in buckets.items():
        nfiles = sum(len(t["files"]) for t in items)
        print(f"{name}: {len(items)} topics / {nfiles} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
