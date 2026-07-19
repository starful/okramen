"""Generate ramen shop markdown via Gemini — real map data only."""

from __future__ import annotations

import csv
import os
import sys
import concurrent.futures
from datetime import datetime

from dotenv import load_dotenv

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
CONTENT_DIR = os.path.join(BASE_DIR, "app", "content")

sys.path.insert(0, SCRIPT_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, "app"))

from content_quality import (  # noqa: E402
    QUALITY_PROMPT_RULES,
    RAMEN_MIN_CHARS,
    has_real_shop_data,
    is_non_ramen_slug,
    strip_code_fences,
    validate_generated_markdown,
)
from topic_queue_csv import resolve as resolve_queue_csv  # noqa: E402

load_dotenv()

MODEL = "gemini-2.5-flash"
MAX_ATTEMPTS = 3

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


def _emit_pipeline_result(**kwargs):
    try:
        from generation_result import emit_generation_result

        emit_generation_result(**kwargs)
    except ImportError:
        pass


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


def _sibling_exists(safe_name: str, lang: str) -> bool:
    other = "ko" if lang == "en" else "en"
    return os.path.isfile(os.path.join(CONTENT_DIR, f"{safe_name}_{other}.md"))


def build_ramen_prompt(
    *,
    safe_name: str,
    name: str,
    lat,
    lng,
    address: str,
    lang: str,
    features: str,
    agoda: str,
    feedback: str = "",
) -> str:
    cats = parse_categories(features, lang)
    lang_full = "Korean" if lang == "ko" else "English"
    filling = _sibling_exists(safe_name, lang)
    length_hint = (
        f"at least {RAMEN_MIN_CHARS + 1500} characters"
        if filling
        else f"at least {RAMEN_MIN_CHARS} characters"
    )
    today = datetime.now().strftime("%Y-%m-%d")
    feedback_block = f"\n[FIX PREVIOUS AT]\n{feedback}\n" if feedback else ""

    return f"""You are a practical Japan ramen travel editor for OKRamen.
Write in {lang_full} only. Trip-planning first — help a visitor decide whether to queue.

Shop: {name}
Address: {address}
Coordinates: {lat}, {lng}
Tags / features: {features}
Suggested categories: {cats[0]}, {cats[1]}
Optional lodging CTA slug hint: {agoda or "(none)"}

{QUALITY_PROMPT_RULES}
{feedback_block}
[HARD RULES]
- Body length: {length_hint}.
- This MUST be about ramen (or tsukemen). If the place is a cafe/bakery/coffee shop, refuse with only: SKIP_NOT_RAMEN
- Cover themes (unique ## titles, not copy-pasted labels): overview, what to order,
  queue/hours reality, access from nearest station, who it suits / who should skip.
- Prefer ranges and "verify on Maps" over invented exact hours or yen prices.
- At least 3 ## sections. Never use H1.

[OUTPUT]
Start with YAML frontmatter (no code fences):

---
lang: {lang}
title: "SEO title mentioning {name} and ramen"
summary: "One concrete sentence for travelers"
date: "{today}"
shop_name: "{name}"
address: "{address}"
lat: {lat}
lng: {lng}
categories:
- {cats[0]}
- {cats[1]}
thumbnail: "/static/images/{safe_name}.jpg"
agoda: "{agoda or ""}"
image_prompt: "{build_image_prompt(name, features, lang)}"
---
(Markdown body)
"""


def generate_ramen_article(safe_name, name, lat, lng, address, lang, features, agoda) -> str:
    """Gemini shop page. Returns status string."""
    filename = f"{safe_name}_{lang}.md"
    path = os.path.join(CONTENT_DIR, filename)

    if is_non_ramen_slug(safe_name, name, features=features, address=address):
        return f"⏭️ Skip non-ramen: {filename}"

    if not has_real_shop_data(lat=lat, lng=lng, address=address):
        return f"⏭️ Skip no real map data: {filename}"

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        return f"❌ API Key missing: {filename}"

    from google import genai

    client = genai.Client(api_key=api_key)
    filling_sibling = _sibling_exists(safe_name, lang)
    feedback = ""
    last_errors: list[str] = []

    print(f"🚀 [Gen] Gemini {lang} for: {name}...")
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            prompt = build_ramen_prompt(
                safe_name=safe_name,
                name=name,
                lat=lat,
                lng=lng,
                address=address,
                lang=lang,
                features=features,
                agoda=agoda,
                feedback=feedback,
            )
            response = client.models.generate_content(model=MODEL, contents=prompt)
            content = strip_code_fences(response.text or "")
            if "SKIP_NOT_RAMEN" in content[:80]:
                return f"⏭️ Model refused non-ramen: {filename}"

            ok, errors = validate_generated_markdown(
                content,
                kind="ramen",
                lang=lang,
                sibling_exists=filling_sibling,
            )
            if not ok:
                last_errors = errors
                feedback = "; ".join(errors)
                print(f"⚠️  quality fail {filename} attempt {attempt}: {feedback}")
                continue

            os.makedirs(CONTENT_DIR, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"✅ [Done] {filename} ({len(content)} chars)"
        except Exception as e:
            last_errors = [str(e)]
            feedback = str(e)
            print(f"❌ attempt {attempt} {filename}: {e}")

    return f"⛔ Quality failed · not saved: {filename} — {', '.join(last_errors)}"


def run_generator(limit=10):
    csv_path = resolve_queue_csv("items", os.path.join(SCRIPT_DIR, "csv", "ramens.csv"))
    if not os.path.exists(csv_path):
        print(f"❌ CSV not found: {csv_path}")
        return

    tasks = []
    skipped = 0
    pairs_queued = 0
    with open(csv_path, mode="r", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        for row in reader:
            if limit > 0 and pairs_queued >= limit:
                break
            name = (row.get("Name") or "").strip()
            if not name:
                continue
            safe_name = name.lower().replace(" ", "_").replace("'", "").replace(",", "")
            lat = row.get("Lat", "")
            lng = row.get("Lng", "")
            address = row.get("Address", "")
            features = row.get("Features", "")
            agoda = row.get("Agoda", "")

            if is_non_ramen_slug(safe_name, name, features=features, address=address):
                print(f"⏭️ Queue skip non-ramen: {name}")
                skipped += 1
                continue
            if not has_real_shop_data(lat=lat, lng=lng, address=address):
                print(f"⏭️ Queue skip no real data: {name}")
                skipped += 1
                continue

            en_path = os.path.join(CONTENT_DIR, f"{safe_name}_en.md")
            ko_path = os.path.join(CONTENT_DIR, f"{safe_name}_ko.md")
            if os.path.exists(en_path) and os.path.exists(ko_path):
                continue
            pair_tasks = []
            for lang in ["en", "ko"]:
                if not os.path.exists(os.path.join(CONTENT_DIR, f"{safe_name}_{lang}.md")):
                    pair_tasks.append(
                        (safe_name, name, lat, lng, address, lang, features, agoda)
                    )
            if not pair_tasks:
                continue
            pairs_queued += 1
            tasks.extend(pair_tasks)

    if not tasks:
        print("ℹ️  No new items to generate (all queued ramen already exist or filtered).")
        _emit_pipeline_result(step="items", topics=0, generated=0, skipped=skipped)
        return

    print(f"🔔 {pairs_queued} pair(s), {len(tasks)} file(s) — Gemini + quality gate...")
    ok = 0
    failed = 0
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [executor.submit(generate_ramen_article, *p) for p in tasks]
        for fut in concurrent.futures.as_completed(futures):
            result = fut.result()
            print(result)
            if result.startswith("✅"):
                ok += 1
            elif result.startswith("⛔") or result.startswith("❌"):
                failed += 1
            else:
                skipped += 1
    _emit_pipeline_result(
        step="items",
        topics=pairs_queued,
        generated=ok,
        failed=failed,
        skipped=skipped,
    )


if __name__ == "__main__":
    env_limit = os.environ.get("CONTENT_LIMIT")
    arg_limit = sys.argv[1] if len(sys.argv) > 1 else None
    try:
        run_limit = int(arg_limit or env_limit or 10)
    except ValueError:
        run_limit = 10
    run_generator(limit=run_limit)
