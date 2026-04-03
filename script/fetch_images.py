import os
import csv
import time
import requests
from dotenv import load_dotenv

# ==========================================
# ⚙️ 설정
# ==========================================
load_dotenv()
API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
IMAGES_DIR = os.path.join(BASE_DIR, 'app', 'static', 'images')
CONTENT_DIR = os.path.join(BASE_DIR, 'app', 'content')
CSV_PATH = os.path.join(SCRIPT_DIR, 'csv', 'ramens.csv')

# 이미지 설정
MAX_WIDTH = 800   # 최대 가로 사이즈 (Places API 파라미터)
PHOTO_COUNT = 1   # 온천당 가져올 사진 수

# ==========================================
# 🔍 Places API (New) - Place Search
# ==========================================
def search_place(name, lat, lng):
    """온천 이름 + 위경도로 Place ID를 검색합니다."""
    url = "https://places.googleapis.com/v1/places:searchNearby"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": API_KEY,
        "X-Goog-FieldMask": "places.id,places.displayName,places.photos"
    }
    body = {
        "includedTypes": ["lodging", "spa", "tourist_attraction"],
        "locationRestriction": {
            "circle": {
                "center": {"latitude": float(lat), "longitude": float(lng)},
                "radius": 500.0  # 500m 반경 검색
            }
        },
        "maxResultCount": 5,
        "languageCode": "ja"
    }

    try:
        res = requests.post(url, headers=headers, json=body, timeout=10)
        data = res.json()
        places = data.get("places", [])

        if not places:
            return None

        # 이름이 가장 유사한 장소 선택
        name_lower = name.lower().replace(" ", "")
        for place in places:
            display = place.get("displayName", {}).get("text", "").lower().replace(" ", "")
            if name_lower in display or display in name_lower:
                return place

        # 없으면 첫 번째 결과 반환
        return places[0]

    except Exception as e:
        print(f"  ⚠️ Place 검색 오류 ({name}): {e}")
        return None


# ==========================================
# 📸 Places API - Photo Download
# ==========================================
def download_photo(photo_name, save_path):
    """Places API photo resource name으로 이미지를 다운로드합니다."""
    url = f"https://places.googleapis.com/v1/{photo_name}/media"
    params = {
        "maxWidthPx": MAX_WIDTH,
        "key": API_KEY,
        "skipHttpRedirect": "false"
    }

    try:
        res = requests.get(url, params=params, timeout=15, allow_redirects=True)
        if res.status_code == 200 and res.headers.get("Content-Type", "").startswith("image"):
            with open(save_path, "wb") as f:
                f.write(res.content)
            size_kb = len(res.content) / 1024
            print(f"  📥 다운로드 완료 ({size_kb:.0f}KB)")
            return True
        else:
            print(f"  ⚠️ 이미지 응답 오류: HTTP {res.status_code}")
            return False

    except Exception as e:
        print(f"  ⚠️ 다운로드 오류: {e}")
        return False


# ==========================================
# 🚀 메인 실행
# ==========================================
def fetch_all_images():
    if not API_KEY:
        print("❌ .env 파일에 GOOGLE_PLACES_API_KEY가 없습니다.")
        return

    os.makedirs(IMAGES_DIR, exist_ok=True)

    # 보호할 파일 목록
    protected = {'logo.png', 'logo.svg', 'favicons.ico', 'default.png', 'og_image.png', 'onsen_marker.png'}

    success = 0
    skipped = 0
    failed = 0

    # MD 파일이 존재하는 온천의 safe_name 목록 추출 (언어 suffix 제거)
    md_safe_names = set()
    if os.path.exists(CONTENT_DIR):
        for fname in os.listdir(CONTENT_DIR):
            if fname.endswith('.md'):
                # 예: hakone_ten-yu_ko.md → hakone_ten-yu
                base = fname.replace('.md', '')
                for lang in ['_ko', '_en', '_ja']:
                    if base.endswith(lang):
                        md_safe_names.add(base[:-len(lang)])
                        break

    # CSV에서 MD가 있는 온천만 필터링
    with open(CSV_PATH, mode='r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        all_rows = list(reader)

    rows = []
    for row in all_rows:
        name = (row.get('Name') or '').strip()
        if not name:
            continue
        safe_name = name.lower().replace(" ", "_").replace("'", "").replace(",", "")
        if safe_name in md_safe_names:
            rows.append(row)

    total = len(rows)
    print(f"\n♨️  MD 파일 기준 총 {total}개 온천 이미지 확인 시작...\n")
    print(f"   (전체 CSV {len(all_rows)}개 중 컨텐츠 생성된 {total}개만 처리)\n")

    for i, row in enumerate(rows, 1):
        name = (row.get('Name') or '').strip()
        lat  = (row.get('Lat') or '').strip()
        lng  = (row.get('Lng') or '').strip()

        if not name or not lat or not lng:
            continue

        safe_name = name.lower().replace(" ", "_").replace("'", "").replace(",", "")
        save_path = os.path.join(IMAGES_DIR, f"{safe_name}.jpg")

        print(f"[{i:03d}/{total}] {name}")

        # 이미 이미지가 있으면 스킵
        if os.path.exists(save_path) and f"{safe_name}.jpg" not in protected:
            print(f"  ⏭️  이미 존재 → 스킵")
            skipped += 1
            continue

        # Place 검색
        place = search_place(name, lat, lng)
        if not place:
            print(f"  ❌ 장소를 찾을 수 없음")
            failed += 1
            time.sleep(0.3)
            continue

        place_name = place.get("displayName", {}).get("text", "알 수 없음")
        photos = place.get("photos", [])

        if not photos:
            print(f"  ❌ 사진 없음 (장소: {place_name})")
            failed += 1
            time.sleep(0.3)
            continue

        # 첫 번째 사진 다운로드
        photo_name = photos[0].get("name", "")
        print(f"  🔍 장소: {place_name}")
        ok = download_photo(photo_name, save_path)

        if ok:
            success += 1
        else:
            failed += 1

        # API 과부하 방지
        time.sleep(0.3)

    print("\n" + "─" * 50)
    print(f"🎉 이미지 수집 완료!")
    print(f"   ✅ 성공: {success}개")
    print(f"   ⏭️  스킵: {skipped}개 (이미 존재)")
    print(f"   ❌ 실패: {failed}개")
    print("─" * 50)


if __name__ == "__main__":
    fetch_all_images()
