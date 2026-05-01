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

def main():
    print("🔨 Building OKRamen Production Data...")
    ramens = []

    if not os.path.exists(CONTENT_DIR):
        print("❌ Content directory not found.")
        return

    for filename in os.listdir(CONTENT_DIR):
        if not filename.endswith('.md'):
            continue

        try:
            with open(os.path.join(CONTENT_DIR, filename), 'r', encoding='utf-8') as f:
                raw_text = f.read()

            post = loads_ramen_post(raw_text)

            # 카테고리 정규화
            cats = post.get('categories') or []
            if isinstance(cats, str):
                cats = [c.strip() for c in cats.split(',')]

            # 요약문
            summary = post.get('summary', '')
            if not summary:
                content_only = re.sub(r'[#*`-]', '', post.content).strip()
                summary = content_only[:180].replace('\n', ' ') + '...'

            # ✅ lat/lng 강제 float 변환 (AI가 문자열로 생성하는 경우 대비)
            try:
                lat = float(post.get('lat', 0) or 0)
                lng = float(post.get('lng', 0) or 0)
            except (ValueError, TypeError):
                lat, lng = 0.0, 0.0

            # lat/lng 유효성 검사 — 0이면 마커가 NaN으로 표시되므로 스킵
            if lat == 0.0 or lng == 0.0:
                print(f"⚠️  Skip {filename}: invalid lat/lng ({lat}, {lng})")
                continue

            ramens.append({
                "id":        filename.replace('.md', ''),
                "lang":      post.get('lang', 'en'),
                "title":     post.get('title', 'Untitled'),
                "lat":       lat,
                "lng":       lng,
                "categories": cats,
                "thumbnail": post.get('thumbnail', '/static/images/default.jpg'),  # ✅ default.jpg
                "address":   post.get('address', 'Japan'),
                "published": str(post.get('date', datetime.now().strftime('%Y-%m-%d'))),
                "summary":   summary,
                "link":      f"/ramen/{filename.replace('.md', '')}"
            })

        except Exception as e:
            print(f"❌ Skip {filename}: {e}")

    ramens.sort(key=lambda x: x['published'], reverse=True)

    final_json = {
        "last_updated": datetime.now().strftime("%Y.%m.%d"),
        "total_count":  len(ramens),
        "ramens":       ramens
    }

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(final_json, f, ensure_ascii=False, indent=2)

    print(f"🎉 Success: {len(ramens)} entries compiled into ramen_data.json")

if __name__ == "__main__":
    main()