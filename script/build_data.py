import os
import sys
import json
import re
from datetime import datetime

BASE_DIR     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT_DIR  = os.path.join(BASE_DIR, 'app', 'content')
OUTPUT_PATH  = os.path.join(BASE_DIR, 'app', 'static', 'json', 'ramen_data.json')

APP_DIR = os.path.join(BASE_DIR, 'app')
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from ramen_md import loads_ramen_post  # noqa: E402
from md_dates import ensure_post_date, save_post  # noqa: E402

DEFAULT_THUMBNAIL = "/static/images/default.jpg"


def normalize_categories(categories) -> list[str]:
    cats = categories or []
    if isinstance(cats, str):
        return [c.strip() for c in cats.split(',')]
    return cats


def build_summary(post) -> str:
    summary = post.get('summary', '')
    if summary:
        return summary
    content_only = re.sub(r'[#*`-]', '', post.content).strip()
    return content_only[:180].replace('\n', ' ') + '...'


def parse_coordinates(post) -> tuple[float, float]:
    try:
        lat = float(post.get('lat', 0) or 0)
        lng = float(post.get('lng', 0) or 0)
    except (ValueError, TypeError):
        return 0.0, 0.0
    return lat, lng


def build_ramen_entry(filename: str, post, published_date: str):
    slug = filename.replace('.md', '')
    categories = normalize_categories(post.get('categories'))
    summary = build_summary(post)
    lat, lng = parse_coordinates(post)
    if lat == 0.0 or lng == 0.0:
        return None, lat, lng

    return {
        "id": slug,
        "lang": post.get('lang', 'en'),
        "title": post.get('title', 'Untitled'),
        "lat": lat,
        "lng": lng,
        "categories": categories,
        "thumbnail": post.get('thumbnail', DEFAULT_THUMBNAIL),
        "address": post.get('address', 'Japan'),
        "published": published_date,
        "summary": summary,
        "link": f"/ramen/{slug}",
    }, lat, lng


def main():
    print("🔨 Building OKRamen Production Data...")
    ramens = []
    backfilled = 0

    if not os.path.exists(CONTENT_DIR):
        print("❌ Content directory not found.")
        return

    for filename in os.listdir(CONTENT_DIR):
        if not filename.endswith('.md'):
            continue

        try:
            filepath = os.path.join(CONTENT_DIR, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                raw_text = f.read()

            post = loads_ramen_post(raw_text)
            published_date, changed = ensure_post_date(post, filepath)
            if changed:
                save_post(filepath, post)
                backfilled += 1

            ramen_entry, lat, lng = build_ramen_entry(filename, post, published_date)
            if ramen_entry is None:
                print(f"⚠️  Skip {filename}: invalid lat/lng ({lat}, {lng})")
                continue

            ramens.append(ramen_entry)

        except Exception as e:
            print(f"❌ Skip {filename}: {e}")

    ramens.sort(key=lambda x: (x['published'], x['id']), reverse=True)

    final_json = {
        "last_updated": datetime.now().strftime("%Y.%m.%d"),
        "total_count":  len(ramens),
        "ramens":       ramens
    }

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(final_json, f, ensure_ascii=False, indent=2)

    print(f"🎉 Success: {len(ramens)} entries compiled into ramen_data.json")
    if backfilled:
        print(f"📅 date 백필: {backfilled}개 MD")


    try:
        from build_sitemap import main as build_sitemap_main

        code = build_sitemap_main()
        if code:
            print(f"⚠️ sitemap refresh exit={code}")
    except Exception as e:
        print(f"⚠️ sitemap refresh failed: {e}")


if __name__ == "__main__":
    main()