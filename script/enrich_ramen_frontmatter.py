#!/usr/bin/env python3
"""Insert shop_name into ramen markdown frontmatter without reformatting the file."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "app"))

from ramen_practical import slug_to_shop_name  # noqa: E402

CONTENT_DIR = ROOT / "app" / "content"


def main() -> None:
    updated = 0
    for path in sorted(CONTENT_DIR.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        if "shop_name:" in text.split("---", 2)[1] if text.startswith("---") else "":
            continue
        if not text.startswith("---\n"):
            continue
        name = slug_to_shop_name(path.stem)
        path.write_text(text.replace("---\n", f'---\nshop_name: "{name}"\n', 1), encoding="utf-8")
        updated += 1
    print(f"Inserted shop_name into {updated} files")


if __name__ == "__main__":
    main()
