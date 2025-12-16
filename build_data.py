import os
import json
import frontmatter
from datetime import datetime

CONTENT_DIR = 'app/content'
OUTPUT_FILE = 'app/static/json/shrines_data.json' 

def main():
    print("🔨 로컬 마크다운 데이터 빌드 시작...")
    
    shrines = []
    
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    if not os.path.exists(CONTENT_DIR):
        os.makedirs(CONTENT_DIR)

    for filename in os.listdir(CONTENT_DIR):
        if not filename.endswith('.md'):
            continue
            
        filepath = os.path.join(CONTENT_DIR, filename)
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                post = frontmatter.load(f)
                
                if not post.get('lat') or not post.get('lng'):
                    continue

                shrine = {
                    "id": filename.replace('.md', ''),
                    "title": post.get('title', 'No Title'),
                    "lat": post.get('lat'),
                    "lng": post.get('lng'),
                    "categories": post.get('categories', []),
                    "thumbnail": post.get('thumbnail', '/static/images/default.png'),
                    "address": post.get('address', ''),
                    # 날짜 형식 통일 (YYYY-MM-DD)
                    "published": str(post.get('date', datetime.now().strftime('%Y-%m-%d'))), 
                    "summary": post.get('summary', post.content[:100] + '...'),
                    "link": f"/shrine/{filename.replace('.md', '')}" 
                }
                shrines.append(shrine)

        except Exception as e:
            print(f"❌ 에러 발생 ({filename}): {e}")

    # ==================================================
    # [추가] 여기서 날짜(published) 기준 내림차순(최신순) 정렬
    # ==================================================
    shrines.sort(key=lambda x: x['published'], reverse=True)

    final_data = {
        "last_updated": datetime.now().strftime("%Y.%m.%d"),
        "shrines": shrines
    }

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n🎉 빌드 완료! 총 {len(shrines)}개 (최신순 정렬됨)")

if __name__ == "__main__":
    main()