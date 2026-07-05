#!/usr/bin/env python3
"""Generate new ramen shop markdown as practical trip-planning guides (EN+KO)."""

from __future__ import annotations

import csv
import os
import sys
import concurrent.futures
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
CONTENT_DIR = os.path.join(BASE_DIR, "app", "content")

sys.path.insert(0, SCRIPT_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "app"))

from rewrite_ramen_practical import build_region_index, rewrite_file  # noqa: E402
from topic_queue_csv import resolve as resolve_queue_csv  # noqa: E402


def _emit_pipeline_result(**kwargs):
    try:
        from generation_result import emit_generation_result

        emit_generation_result(**kwargs)
    except ImportError:
        pass


# Map CSV Features (often Korean) -> [flavor, vibe] per language
FLAVOR_KEYS = {
    "돈코츠": ("Tonkotsu", "돈코츠"),
    "tonkotsu": ("Tonkotsu", "돈코츠"),
    "쇼유": ("Shoyu", "쇼유"),
    "shoyu": ("Shoyu", "쇼유"),
    "미소": ("Miso", "미소"),
    "miso": ("Miso", "미소"),
    "시오": ("Shio", "시오"),
    "shio": ("Shio", "시오"),
    "츠케멘": ("Tsukemen", "츠케멘"),
    "tsukemen": ("Tsukemen", "츠케멘"),
    "치킨": ("Chicken", "치킨 라멘"),
    "chicken": ("Chicken", "치킨 라멘"),
    "유즈": ("Shoyu", "쇼유"),
    "유즈시오": ("Shio", "시오"),
}

VIBE_KEYS = {
    "현지인맛집": ("Local Gem", "현지인맛집"),
    "local gem": ("Local Gem", "현지인맛집"),
    "심야": ("Late Night", "심야영업"),
    "late night": ("Late Night", "심야영업"),
    "야식": ("Late Night", "야식"),
    "혼밥": ("Solo Friendly", "혼밥성지"),
    "solo": ("Solo Friendly", "혼밥성지"),
    "프리미엄": ("Premium", "프리미엄"),
    "premium": ("Premium", "프리미엄"),
}

DEFAULT_FLAVOR = ("Tonkotsu", "돈코츠")
DEFAULT_VIBE = ("Local Gem", "현지인맛집")


def parse_categories(features: str, lang: str) -> list[str]:
    text = (features or "").lower()
    flavor = DEFAULT_FLAVOR[0 if lang == "en" else 1]
    vibe = DEFAULT_VIBE[0 if lang == "en" else 1]
    for key, pair in FLAVOR_KEYS.items():
        if key.lower() in text:
            flavor = pair[0 if lang == "en" else 1]
            break
    for key, pair in VIBE_KEYS.items():
        if key.lower() in text:
            vibe = pair[0 if lang == "en" else 1]
            break
    return [flavor, vibe]


def build_image_prompt(name: str, features: str, lang: str) -> str:
    style = parse_categories(features, lang)[0]
    moods = [
        "warm wooden counter seat",
        "neon-lit late night alley",
        "bright minimalist shop interior",
    ]
    shots = ["45-degree steaming macro shot", "side profile close-up", "overhead flat-lay"]
    idx = sum(ord(c) for c in name) % len(moods)
    return (
        f"A {shots[idx % len(shots)]} of {name} {style} ramen, "
        f"swirling steam, {moods[idx]}, cinematic food photography, no text, 8k detail."
    )


def write_stub_frontmatter(
    safe_name: str,
    name: str,
    lat: float,
    lng: float,
    address: str,
    lang: str,
    features: str,
    agoda: str,
) -> str:
    shop_name = name.strip()
    categories = parse_categories(features, lang)
    return f"""---
lang: {lang}
address: "{address}"
lat: {lat}
lng: {lng}
shop_name: "{shop_name}"
categories:
- {categories[0]}
- {categories[1]}
date: '{datetime.now().strftime("%Y-%m-%d")}'
thumbnail: "/static/images/{safe_name}.jpg"
agoda: "{agoda or ""}"
image_prompt: "{build_image_prompt(name, features, lang)}"
---

"""


def generate_ramen_article(safe_name, name, lat, lng, address, lang, features, agoda):
    """Create practical guide markdown via rewrite_ramen_practical (same as site-wide rollout)."""
    filename = f"{safe_name}_{lang}.md"
    path = os.path.join(CONTENT_DIR, filename)
    print(f"🚀 [Gen] Practical {lang} guide for: {name}...")

    os.makedirs(CONTENT_DIR, exist_ok=True)
    stub = write_stub_frontmatter(safe_name, name, lat, lng, address, lang, features, agoda)
    with open(path, "w", encoding="utf-8") as f:
        f.write(stub)

    from pathlib import Path

    region_index = build_region_index()
    rewrite_file(Path(path), region_index)
    final_len = Path(path).stat().st_size
    print(f"✅ [Done] {filename} ({final_len} bytes, practical layout)")


def run_generator(limit=10):
    csv_path = resolve_queue_csv("items", os.path.join(SCRIPT_DIR, "csv", "ramens.csv"))
    if not os.path.exists(csv_path):
        print(f"❌ CSV not found: {csv_path}")
        return

    tasks = []
    pairs_queued = 0
    with open(csv_path, mode="r", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        for row in reader:
            if limit > 0 and pairs_queued >= limit:
                break
            name = row["Name"].strip()
            safe_name = name.lower().replace(" ", "_").replace("'", "").replace(",", "")
            en_path = os.path.join(CONTENT_DIR, f"{safe_name}_en.md")
            ko_path = os.path.join(CONTENT_DIR, f"{safe_name}_ko.md")
            if os.path.exists(en_path) and os.path.exists(ko_path):
                continue
            pair_tasks = []
            for lang in ["en", "ko"]:
                if not os.path.exists(os.path.join(CONTENT_DIR, f"{safe_name}_{lang}.md")):
                    pair_tasks.append(
                        (
                            safe_name,
                            name,
                            row["Lat"],
                            row["Lng"],
                            row["Address"],
                            lang,
                            row["Features"],
                            row.get("Agoda", ""),
                        )
                    )
            if not pair_tasks:
                continue
            pairs_queued += 1
            tasks.extend(pair_tasks)

    if not tasks:
        print("ℹ️  No new items to generate (all queued ramen already exist).")
        _emit_pipeline_result(step="items", topics=0, generated=0)
        return

    print(f"🔔 {pairs_queued} pair(s), {len(tasks)} file(s) — practical guide format...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        executor.map(lambda p: generate_ramen_article(*p), tasks)
    _emit_pipeline_result(step="items", topics=pairs_queued, generated=len(tasks))


if __name__ == "__main__":
    env_limit = os.environ.get("CONTENT_LIMIT")
    arg_limit = sys.argv[1] if len(sys.argv) > 1 else None
    try:
        run_limit = int(arg_limit or env_limit or 10)
    except ValueError:
        run_limit = 10
    run_generator(limit=run_limit)
