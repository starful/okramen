#!/usr/bin/env python3
"""Write app/static/sitemap.xml from the same logic as the live /sitemap.xml route."""

from __future__ import annotations

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
APP_DIR = BASE_DIR / "app"
OUTPUT = APP_DIR / "static" / "sitemap.xml"

if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

os.chdir(BASE_DIR)


def main() -> int:
    from __init__ import app  # noqa: WPS433

    with app.test_client() as client:
        response = client.get("/sitemap.xml")
    if response.status_code != 200:
        print(f"❌ sitemap generation failed: HTTP {response.status_code}")
        return 1
    OUTPUT.write_bytes(response.data)
    count = response.get_data(as_text=True).count("<loc>")
    print(f"🎉 Wrote {OUTPUT} ({count} URLs)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
