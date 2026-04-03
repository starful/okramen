import os
import csv
import re
import time
import concurrent.futures
from datetime import datetime
from google import genai
from dotenv import load_dotenv

# 1. 환경 변수 및 경로 설정
load_dotenv()
API_KEY = os.environ.get("GEMINI_API_KEY")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
CONTENT_DIR = os.path.join(BASE_DIR, 'app', 'content')

# 2. 글로벌 라멘 카테고리 설정 (Flavor & Vibe)
CATEGORIES = {
    "en": {
        "flavor": ["Tonkotsu", "Shoyu", "Miso", "Shio", "Chicken", "Tsukemen", "Vegan"],
        "vibe": ["Local Gem", "Solo Friendly", "Late Night", "Premium"]
    },
    "ko": {
        "flavor": ["돈코츠", "쇼유", "미소", "시오", "치킨라멘", "츠케멘", "비건"],
        "vibe": ["현지인맛집", "혼밥성지", "심야영업", "프리미엄"]
    }
}

def clean_ai_response(text):
    """AI가 출력한 텍스트에서 ```markdown 이나 ## yaml 같은 불필요한 태그 강제 제거"""
    text = text.strip()
    
    # 시작부분의 ```markdown 또는 ```yaml 제거
    text = re.sub(r'^```[a-z]*\n', '', text)
    # 끝부분의 ``` 제거
    text = re.sub(r'\n```$', '', text)
    # AI가 임의로 붙인 '## yaml' 또는 'yaml' 제목 제거
    text = re.sub(r'^(##\s*)?yaml\n', '', text, flags=re.IGNORECASE)
    
    # 💡 [필살기] 만약 문서 중간에 --- 가 있다면 그 앞의 모든 텍스트를 삭제 (청소 보장)
    if '---' in text and not text.startswith('---'):
        text = '---' + text.split('---', 1)[1]
        
    return text.strip()

def generate_ramen_article(safe_name, name, lat, lng, address, lang, features, agoda):
    if not API_KEY:
        print("❌ API Key is missing. Check your .env file.")
        return

    client = genai.Client(api_key=API_KEY)
    model_name = 'gemini-2.5-flash' # 깊이 있는 장문 생성을 위해 Pro 모델 사용
    
    flavor_list = ", ".join(CATEGORIES[lang]["flavor"])
    vibe_list = ", ".join(CATEGORIES[lang]["vibe"])
    
    print(f"🚀 [AI Start] Generating {lang} article for: {name}...")

    prompt = f"""
    You are a world-renowned Michelin food critic and travel journalist. 
    Write a MASTERPIECE ramen guide for '{name}'.
    The article must be extremely detailed, professional, and SEO-optimized for global travelers.

    [Target Information]
    - Shop Name: {name}
    - Location: {address}
    - Style/Features: {features}
    - Language: {lang}

    [Categorization Task]
    1. Select EXACTLY one Primary Flavor from: [{flavor_list}]
    2. Select EXACTLY one Vibe from: [{vibe_list}]

    [Strict Output Format]
    ---
    lang: {lang}
    title: "Write a breathtaking title including 'Best Ramen in {address}'"
    lat: {lat}
    lng: {lng}
    categories: ["SelectedFlavor", "SelectedVibe"]
    thumbnail: "/static/images/{safe_name}.jpg"
    address: "{address}"
    date: "{datetime.now().strftime('%Y-%m-%d')}"
    agoda: "{agoda}"
    summary: "Write a high-conversion 3-sentence summary that makes readers hungry."
    ---

    [Article Content Structure]
    - ## Philosophy & Soul: Deep dive into the owner's history and the shop's identity.
    - ## The Broth Symphony: 2,500+ characters focusing ONLY on ingredients, boiling process, and umami layers.
    - ## Noodle & Topping Craftsmanship: Analysis of hydration, texture, Chashu searing, and Ajitama quality.
    - ## The Experience & Access: Vibe, wait time tips, and how to find this hidden gem.
    
    IMPORTANT: Write with passion and vivid adjectives in {lang}. DO NOT use any code blocks like ```. Start immediately with '---'.
    """

    # 💡 503 에러 대응을 위한 자동 재시도 로직 (최대 3회)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(model=model_name, contents=prompt)
            # 결과물 청소
            final_text = clean_ai_response(response.text)

            os.makedirs(CONTENT_DIR, exist_ok=True)
            filename = f"{safe_name}_{lang}.md"
            
            with open(os.path.join(CONTENT_DIR, filename), 'w', encoding='utf-8') as f:
                f.write(final_text)
                
            print(f"✅ [Success] {filename} (Length: {len(final_text)} chars)")
            return # 성공 시 루프 탈출
            
        except Exception as e:
            if "503" in str(e) or "429" in str(e):
                wait_time = 15 * (attempt + 1)
                print(f"⏳ [Wait] Server overloaded. Retrying in {wait_time}s... ({attempt+1}/{max_retries})")
                time.sleep(wait_time)
            else:
                print(f"❌ [Error] {name}: {e}")
                break

def run_generator(limit=10):
    csv_path = os.path.join(SCRIPT_DIR, 'csv', 'ramens.csv')
    if not os.path.exists(csv_path):
        print(f"❌ CSV file not found: {csv_path}")
        return

    tasks = []
    with open(csv_path, mode='r', encoding='utf-8-sig') as file:
        reader = csv.DictReader(file)
        for row in reader:
            name = row['Name'].strip()
            # 파일명으로 쓸 수 있게 이름 변환
            safe_name = name.lower().replace(" ", "_").replace("'", "").replace(",", "")
            
            for lang in ['en', 'ko']:
                filename = f"{safe_name}_{lang}.md"
                # 이미 파일이 존재하면 건너뜀 (API 비용 및 시간 절약)
                if not os.path.exists(os.path.join(CONTENT_DIR, filename)):
                    tasks.append((safe_name, name, row['Lat'], row['Lng'], row['Address'], lang, row['Features'], row.get('Agoda', '')))
            
            if len(tasks) >= limit * 2: 
                break

    if tasks:
        print(f"🎏 Found {len(tasks)} new articles to generate.")
        # 💡 서버 부하를 줄이기 위해 max_workers를 2로 제한합니다.
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            executor.map(lambda p: generate_ramen_article(*p), tasks)
    else:
        print("✨ All articles are already up to date.")

if __name__ == "__main__":
    # 한 번에 생성할 상점의 개수를 지정 (limit=20 이면 영어/한국어 총 40개 생성)
    run_generator(limit=2)