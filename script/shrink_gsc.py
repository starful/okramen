#!/usr/bin/env python3
"""Delete GSC delete-bucket topics (0 clicks, low impressions, not new)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "script"))
from gsc_cleanup_plan import GSC_ZIP, classify  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--zip", type=Path, default=GSC_ZIP)
    args = parser.parse_args()

    buckets = classify(args.zip)
    delete = buckets["delete"]
    paths = sorted({f["path"] for t in delete for f in t["files"]})
    print(f"Delete plan: {len(delete)} topics / {len(paths)} files")
    for t in sorted(delete, key=lambda x: (x["kind"], x["base"])):
        print(f"  DEL [{t['kind']}] {t['base']} imp={t['imp']}")
        for f in t["files"]:
            print(f"    {f['rel']}")

    if args.dry_run:
        print("[dry-run] no files removed")
        return 0

    for p in paths:
        if p.exists():
            p.unlink()
            print(f"🗑️  {p.relative_to(ROOT)}")
    print(f"Removed {len(paths)} files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
