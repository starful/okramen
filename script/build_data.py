import os, json, frontmatter, re
from datetime import datetime

# 경로 설정
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT_DIR = os.path.join(BASE_DIR, 'app', 'content')
OUTPUT_PATH = os.path.join(BASE_DIR, 'app', 'static', 'json', 'ramen_data.json')

def clean_markdown_content(text):
    """AI가 넣은 불필요한 태그들을 제거하는 청소 함수"""
    text = text.strip()
    # 1. 시작부분의 ```markdown 이나 ```yaml 제거
    text = re.sub(r'^```[a-z]*\n', '', text)
    # 2. 끝부분의 ``` 제거
    text = re.sub(r'\n```$', '', text)
    # 3. AI가 제목으로 넣은 ## yaml 또는 yaml 제거
    text = re.sub(r'^(##\s*)?yaml\n', '', text, flags=re.IGNORECASE)
    # 4. 강제로 첫 번째 --- 앞의 모든 텍스트 제거
    if '---' in text and not text.startswith('---'):
        text = '---' + text.split('---', 1)[1]
    return text

def main():
    print("🔨 Building OKRamen Production Data with Safe Parser...")
    ramens = []
    
    if not os.path.exists(CONTENT_DIR):
        print("❌ Content directory not found.")
        return

    for filename in os.listdir(CONTENT_DIR):
        if not filename.endswith('.md'): continue
        
        try:
            with open(os.path.join(CONTENT_DIR, filename), 'r', encoding='utf-8') as f:
                raw_text = f.read()
                
            # 💡 청소 로직 적용
            cleaned_text = clean_markdown_content(raw_text)
            post = frontmatter.loads(cleaned_text)
            
            # 카테고리 정규화
            cats = post.get('categories', [])
            if isinstance(cats, str): 
                cats = [c.strip() for c in cats.split(',')]
            
            # 요약문 (없으면 본문에서 추출)
            summary = post.get('summary', '')
            if not summary:
                # 본문에서 HTML 태그나 특수문자 제외하고 앞부분만 추출
                content_only = re.sub(r'[#*`-]', '', post.content).strip()
                summary = content_only[:180].replace('\n', ' ') + '...'

            ramens.append({
                "id": filename.replace('.md', ''),
                "lang": post.get('lang', 'en'),
                "title": post.get('title', 'Untitled'),
                "lat": post.get('lat'),
                "lng": post.get('lng'),
                "categories": cats,
                "thumbnail": post.get('thumbnail', '/static/images/default.png'),
                "address": post.get('address', 'Japan'),
                "published": str(post.get('date', datetime.now().strftime('%Y-%m-%d'))),
                "summary": summary,
                "link": f"/ramen/{filename.replace('.md', '')}"
            })
        except Exception as e:
            print(f"❌ Skip {filename} due to error: {e}")

    # 최신순 정렬
    ramens.sort(key=lambda x: x['published'], reverse=True)

    final_json = {
        "last_updated": datetime.now().strftime("%Y.%m.%d"),
        "total_count": len(ramens),
        "ramens": ramens
    }

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(final_json, f, ensure_ascii=False, indent=2)

    print(f"🎉 Success: {len(ramens)} entries compiled into ramen_data.json")

if __name__ == "__main__":
    main()