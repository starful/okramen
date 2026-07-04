from pathlib import Path
import sys

import frontmatter

ROOT_DIR = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT_DIR / "script"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from build_data import build_ramen_entry, build_summary, normalize_categories, parse_coordinates


def test_normalize_categories_handles_csv_string():
    assert normalize_categories("shoyu, tonkotsu, vegan") == ["shoyu", "tonkotsu", "vegan"]


def test_build_summary_falls_back_to_markdown_content():
    post = frontmatter.loads("---\ntitle: Demo\n---\nFresh broth\nand noodles")
    assert build_summary(post) == "Fresh broth and noodles..."


def test_parse_coordinates_returns_zeroes_for_invalid_values():
    post = frontmatter.loads("---\nlat: nope\nlng: 139.70\n---\nBody")
    assert parse_coordinates(post) == (0.0, 0.0)


def test_build_ramen_entry_uses_normalized_fields():
    post = frontmatter.loads(
        "---\n"
        "lang: en\n"
        "title: Sample Shop\n"
        "lat: '35.12'\n"
        "lng: '139.45'\n"
        "categories: shio, vegan\n"
        "address: Tokyo, Japan\n"
        "---\n"
        "Simple summary body"
    )
    entry, lat, lng = build_ramen_entry("sample_shop_en.md", post, "2026-07-04")

    assert (lat, lng) == (35.12, 139.45)
    assert entry == {
        "id": "sample_shop_en",
        "lang": "en",
        "title": "Sample Shop",
        "lat": 35.12,
        "lng": 139.45,
        "categories": ["shio", "vegan"],
        "thumbnail": "/static/images/default.jpg",
        "address": "Tokyo, Japan",
        "published": "2026-07-04",
        "summary": "Simple summary body...",
        "link": "/ramen/sample_shop_en",
    }
