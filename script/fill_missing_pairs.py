#!/usr/bin/env python3
"""Generate missing en/ko partner files for content that already exists on disk.

Default (orphans-only): one of _en.md / _ko.md exists for a slug → generate the other.
Full CSV backfill (--all-csv --yes): every row in ramens.csv / guides.csv with missing files.

The full backfill can create 100+ API calls; use it only when you intentionally want that.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import csv
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
WORK_ROOT = Path(SCRIPT_DIR).resolve().parents[1]
load_dotenv(WORK_ROOT / ".env")
load_dotenv(WORK_ROOT.parent / "okadmin" / ".env", override=True)

sys.path.insert(0, SCRIPT_DIR)

# Re-read API key after generators import (their load_dotenv must not win over okadmin)
load_dotenv(WORK_ROOT.parent / "okadmin" / ".env", override=True)

from guide_generator import GUIDE_CONTENT_DIR, generate_guide_article  # noqa: E402
from ramen_generator import CONTENT_DIR, generate_ramen_article  # noqa: E402
import guide_generator as _guide_mod  # noqa: E402
import ramen_generator as _ramen_mod  # noqa: E402

_hub_key = os.environ.get("GEMINI_API_KEY")
if _hub_key:
    _guide_mod.API_KEY = _hub_key
    _ramen_mod.API_KEY = _hub_key

RAMEN_WORKERS = int(os.environ.get("RAMEN_MAX_WORKERS", "2"))
GUIDE_WORKERS = int(os.environ.get("GUIDE_MAX_WORKERS", "2"))


def _safe_name(name: str) -> str:
    return name.lower().replace(" ", "_").replace("'", "").replace(",", "")


def _orphan_langs(content_dir: str) -> list[tuple[str, str]]:
    """Return (slug, missing_lang) where exactly one of en/ko exists on disk."""
    langs_by_slug: dict[str, set[str]] = {}
    for path in Path(content_dir).glob("*.md"):
        stem = path.stem
        if stem.endswith("_en"):
            langs_by_slug.setdefault(stem[:-3], set()).add("en")
        elif stem.endswith("_ko"):
            langs_by_slug.setdefault(stem[:-3], set()).add("ko")
    out: list[tuple[str, str]] = []
    for slug, langs in sorted(langs_by_slug.items()):
        if "en" in langs and "ko" in langs:
            continue
        if "en" not in langs:
            out.append((slug, "en"))
        else:
            out.append((slug, "ko"))
    return out


def _load_ramen_csv() -> dict[str, dict]:
    csv_path = os.path.join(SCRIPT_DIR, "csv", "ramens.csv")
    by_slug: dict[str, dict] = {}
    with open(csv_path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            name = (row.get("Name") or "").strip()
            if not name:
                continue
            by_slug[_safe_name(name)] = row
    return by_slug


def _load_guide_csv() -> dict[str, dict]:
    csv_path = os.path.join(SCRIPT_DIR, "csv", "guides.csv")
    by_id: dict[str, dict] = {}
    with open(csv_path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            gid = (row.get("id") or "").strip()
            if gid:
                by_id[gid] = row
    return by_id


def ramen_orphan_tasks() -> list[tuple]:
    rows = _load_ramen_csv()
    tasks: list[tuple] = []
    skipped: list[str] = []
    for slug, lang in _orphan_langs(CONTENT_DIR):
        row = rows.get(slug)
        if not row:
            skipped.append(slug)
            continue
        name = (row.get("Name") or slug).strip()
        tasks.append(
            (
                slug,
                name,
                row.get("Lat", "0"),
                row.get("Lng", "0"),
                row.get("Address", "Japan"),
                lang,
                row.get("Features", ""),
                row.get("Agoda", ""),
            )
        )
    if skipped:
        print(
            "⚠️  Ramen orphans skipped (no ramens.csv row):",
            ", ".join(skipped),
        )
    return tasks


def guide_orphan_tasks() -> list[tuple]:
    rows = _load_guide_csv()
    tasks: list[tuple] = []
    skipped: list[str] = []
    for gid, lang in _orphan_langs(GUIDE_CONTENT_DIR):
        row = rows.get(gid)
        if not row:
            skipped.append(gid)
            continue
        keywords = (row.get("keywords") or "").strip()
        topic = row.get("topic_en" if lang == "en" else "topic_ko") or gid
        tasks.append((gid, topic, lang, keywords))
    if skipped:
        print(
            "⚠️  Guide orphans skipped (no guides.csv row):",
            ", ".join(skipped),
        )
    return tasks


def ramen_csv_tasks() -> list[tuple]:
    """All missing ramen files listed in ramens.csv (expensive; opt-in)."""
    csv_path = os.path.join(SCRIPT_DIR, "csv", "ramens.csv")
    tasks: list[tuple] = []
    with open(csv_path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            name = (row.get("Name") or "").strip()
            if not name:
                continue
            sn = _safe_name(name)
            for lang in ("en", "ko"):
                if not os.path.exists(os.path.join(CONTENT_DIR, f"{sn}_{lang}.md")):
                    tasks.append(
                        (
                            sn,
                            name,
                            row.get("Lat", "0"),
                            row.get("Lng", "0"),
                            row.get("Address", "Japan"),
                            lang,
                            row.get("Features", ""),
                            row.get("Agoda", ""),
                        )
                    )
    return tasks


def guide_csv_tasks() -> list[tuple]:
    """All missing guide files listed in guides.csv (expensive; opt-in)."""
    csv_path = os.path.join(SCRIPT_DIR, "csv", "guides.csv")
    tasks: list[tuple] = []
    with open(csv_path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            gid = (row.get("id") or "").strip()
            if not gid:
                continue
            keywords = (row.get("keywords") or "").strip()
            en_path = os.path.join(GUIDE_CONTENT_DIR, f"{gid}_en.md")
            ko_path = os.path.join(GUIDE_CONTENT_DIR, f"{gid}_ko.md")
            if not os.path.exists(en_path):
                tasks.append((gid, row.get("topic_en") or gid, "en", keywords))
            if not os.path.exists(ko_path):
                tasks.append((gid, row.get("topic_ko") or gid, "ko", keywords))
    return tasks


def _run_tasks(ramen: list[tuple], guides: list[tuple], *, dry_run: bool) -> int:
    mode = "dry-run" if dry_run else "generate"
    print(f"🔔 [{mode}] Ramen: {len(ramen)} files · Guides: {len(guides)} files")
    if dry_run:
        for p in ramen:
            print(f"   ramen {p[0]}_{p[5]}.md")
        for p in guides:
            print(f"   guide {p[0]}_{p[2]}.md")
        if not ramen and not guides:
            print("✨ Nothing to do.")
        return 0
    if not ramen and not guides:
        print("✨ Nothing missing.")
        return 0

    if max(RAMEN_WORKERS, GUIDE_WORKERS) <= 1:
        for p in ramen:
            generate_ramen_article(*p)
        for p in guides:
            generate_guide_article(*p)
    else:
        if ramen:
            with concurrent.futures.ThreadPoolExecutor(max_workers=RAMEN_WORKERS) as ex:
                list(ex.map(lambda p: generate_ramen_article(*p), ramen))
        if guides:
            with concurrent.futures.ThreadPoolExecutor(max_workers=GUIDE_WORKERS) as ex:
                list(ex.map(lambda p: generate_guide_article(*p), guides))

    print("✅ fill_missing_pairs done")
    return 0


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate missing en/ko partner markdown. "
            "Default: orphans only (one language already on disk). "
            "Use --all-csv --yes for full CSV backfill."
        ),
    )
    parser.add_argument(
        "--all-csv",
        action="store_true",
        help="Backfill every missing file from ramens.csv and guides.csv (many API calls).",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Required with --all-csv to confirm intentional full backfill.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List files that would be generated without calling the API.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    if args.all_csv:
        if not args.yes:
            ramen_n = len(ramen_csv_tasks())
            guide_n = len(guide_csv_tasks())
            print(
                "⛔ Full CSV backfill blocked. Would generate "
                f"{ramen_n} ramen + {guide_n} guide files.\n"
                "   Re-run with: python script/fill_missing_pairs.py --all-csv --yes"
            )
            if args.dry_run:
                return _run_tasks(ramen_csv_tasks(), guide_csv_tasks(), dry_run=True)
            return 2
        ramen = ramen_csv_tasks()
        guides = guide_csv_tasks()
        print("⚠️  Mode: full CSV backfill (--all-csv --yes)")
    else:
        ramen = ramen_orphan_tasks()
        guides = guide_orphan_tasks()
        print("ℹ️  Mode: orphans only (existing slug missing en or ko). Use --all-csv --yes for full CSV.")

    return _run_tasks(ramen, guides, dry_run=args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
