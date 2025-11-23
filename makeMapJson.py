# makeMapJson.py
import os
import json
import googlemaps
from google.cloud import storage
from hatena_client import get_all_posts

# 환경 변수
GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY') 
BUCKET_NAME = "jinjamap-data"
FILE_NAME = "shrines_data.json"

def load_existing_data(bucket):
    """GCS에서 기존 JSON 파일을 읽어와서 주소별 좌표 사전을 만듭니다."""
    try:
        blob = bucket.blob(FILE_NAME)
        if not blob.exists():
            print("⚠️ 기존 데이터 파일이 없습니다. (첫 실행으로 간주)")
            return {}
        
        data_str = blob.download_as_text()
        existing_list = json.loads(data_str)
        
        # 주소를 키(Key)로 사용하여 좌표를 빠르게 찾을 수 있는 딕셔너리 생성
        coord_cache = {}
        for item in existing_list:
            if 'address' in item and 'lat' in item and 'lng' in item:
                coord_cache[item['address']] = {'lat': item['lat'], 'lng': item['lng']}
        
        print(f"📦 기존 데이터 {len(coord_cache)}개를 캐시로 로드했습니다.")
        return coord_cache

    except Exception as e:
        print(f"⚠️ 기존 데이터 로드 중 오류 발생 (무시하고 진행): {e}")
        return {}

def main():
    print("🔥 데이터 갱신 스크립트 시작...")

    # GCS 클라이언트 초기화
    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)

    # 1. 기존 데이터 로드 (캐시)
    coord_cache = load_existing_data(bucket)

    # 2. 하테나 블로그 최신 글 가져오기
    posts = get_all_posts()
    if not posts:
        print("❌ 글을 가져오지 못했습니다. 빈 데이터로 덮어쓰지 않고 종료합니다.")
        return

    print(f"📝 총 {len(posts)}개의 글을 처리합니다. (Geocoding 최적화 시작)")

    # 3. 좌표 변환 (캐시 확인 -> 없으면 API 호출)
    gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)
    processed_posts = []
    
    api_call_count = 0
    cache_hit_count = 0

    for post in posts:
        address = post.get('address')
        
        # 주소가 없으면 지도에 표시 불가하므로 스킵
        if not address:
            continue
        
        # [최적화] 이미 변환된 주소인지 확인
        if address in coord_cache:
            # 캐시 사용
            post['lat'] = coord_cache[address]['lat']
            post['lng'] = coord_cache[address]['lng']
            processed_posts.append(post)
            cache_hit_count += 1
            print(f"  ♻️ [캐시] 좌표 재사용: {post['title']}")
        else:
            # API 호출 필요
            try:
                geocode_result = gmaps.geocode(address)
                if geocode_result:
                    location = geocode_result[0]['geometry']['location']
                    post['lat'] = location['lat']
                    post['lng'] = location['lng']
                    processed_posts.append(post)
                    api_call_count += 1
                    print(f"  📍 [API] 좌표 변환: {post['title']}")
                else:
                    print(f"  ⚠️ 좌표 못 찾음: {post['title']} (주소: {address})")
            except Exception as e:
                print(f"  ❌ API 에러: {e}")

    # 4. 결과 요약 및 저장
    print("-" * 30)
    print(f"📊 처리 결과: 총 {len(processed_posts)}개 저장")
    print(f"   - 캐시 사용(비용절약): {cache_hit_count}건")
    print(f"   - API 호출(신규/변경): {api_call_count}건")
    print("-" * 30)

    try:
        blob = bucket.blob(FILE_NAME)
        blob.upload_from_string(
            json.dumps(processed_posts, ensure_ascii=False),
            content_type='application/json'
        )
        print(f"💾 저장 완료: gs://{BUCKET_NAME}/{FILE_NAME}")

    except Exception as e:
        print(f"❌ GCS 업로드 실패: {e}")
        exit(1)

if __name__ == "__main__":
    main()