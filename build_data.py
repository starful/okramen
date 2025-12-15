import os
import json
import frontmatter
from datetime import datetime

# [수정] 데이터가 저장될 새로운 경로
CONTENT_DIR = 'app/content'
OUTPUT_FILE = 'app/static/json/shrines_data.json' 

def main():
    print("🔨 로컬 마크다운 데이터 빌드 시작...")
    
    shrines = []
    
    # [추가] json 폴더가 없으면 생성 (에러 방지)
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
                    print(f"⚠️ 좌표 없음 (건너뜀): {filename}")
                    continue

                shrine = {
                    "id": filename.replace('.md', ''),
                    "title": post.get('title', 'No Title'),
                    "lat": post.get('lat'),
                    "lng": post.get('lng'),
                    "categories": post.get('categories', []),
                    "thumbnail": post.get('thumbnail', '/static/images/default.png'),
                    "address": post.get('address', ''),
                    "published": str(post.get('published', datetime.now().strftime('%Y-%m-%d'))),
                    "summary": post.get('summary', post.content[:100] + '...'),
                    "link": f"/shrine/{filename.replace('.md', '')}" 
                }
                shrines.append(shrine)
                print(f"✅ 추가됨: {shrine['title']}")

        except Exception as e:
            print(f"❌ 에러 발생 ({filename}): {e}")

    final_data = {
        "last_updated": datetime.now().strftime("%Y.%m.%d"),
        "shrines": shrines
    }

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n🎉 빌드 완료! {OUTPUT_FILE}에 저장되었습니다.")

if __name__ == "__main__":
    main()