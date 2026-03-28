import os
import csv
import time
import concurrent.futures
from datetime import datetime
from google import genai
from dotenv import load_dotenv

# 설정 로드
load_dotenv()
API_KEY = os.environ.get("GEMINI_API_KEY")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
CONTENT_DIR = os.path.join(BASE_DIR, 'app', 'content')

# 2단계 필터 정의
CATEGORIES = {
    "en": {
        "flavor": ["Tonkotsu", "Shoyu", "Miso", "Shio", "Chicken", "Tsukemen", "Vegan"],
        "vibe": ["Local Gem", "Premium"] # 바이브는 2순위로 축소
    },
    "ko": {
        "flavor": ["돈코츠", "쇼유", "미소", "시오", "치킨라멘", "츠케멘", "비건"],
        "vibe": ["현지인맛집", "프리미엄"]
    }
}

def generate_ramen_article(safe_name, name, lat, lng, address, lang, features, agoda):
    if not API_KEY:
        print("❌ API Key missing")
        return False

    client = genai.Client(api_key=API_KEY)
    model_name = 'gemini-2.5-pro' 
    
    flavor_list = ", ".join(CATEGORIES[lang]["flavor"])
    vibe_list = ", ".join(CATEGORIES[lang]["vibe"])
    
    print(f"🚀 [AI] '{name}' ({lang}) 고해상도 메가 콘텐츠 생성 시작...")

    prompt = f"""
    You are an elite Michelin-star food critic and professional travel journalist.
    Your mission is to write a MASTERPIECE ramen guide for '{name}'.
    The article must be extremely long, detailed, and captivating (at least 7,000 to 8,000 characters).

    [Target Info]
    - Shop Name: {name}
    - Location: {address}
    - Original Features: {features}
    - Language: {lang}

    [Categorization Task]
    1. Select EXACTLY one Primary Flavor from: [{", ".join(CATEGORIES[lang]["flavor"])}]
    2. Select EXACTLY one Vibe from: [{", ".join(CATEGORIES[lang]["vibe"])}]

    [Output Format: Markdown + YAML Frontmatter]
    ---
    lang: {lang}
    title: "Write a breathtaking, SEO-optimized title in {lang}"
    lat: {lat}
    lng: {lng}
    categories: ["SelectedFlavor", "SelectedVibe"]
    thumbnail: "/static/images/{safe_name}.jpg"
    address: "{address}"
    date: "{datetime.now().strftime('%Y-%m-%d')}"
    agoda: "{agoda}"
    summary: "Write a high-conversion 3-sentence summary in {lang}"
    image_prompt: "Detailed Midjourney prompt for a photorealistic shot of this ramen bowl"
    ---

    [Article Content Structure]
    1. ## The Culinary Philosophy: Deep dive into the owner's history and the shop's soul.
    2. ## Architectural Vibe & Ambiance: Describe the interior, the wait, and the sensory experience.
    3. ## The Broth (The Golden Liquid): 2,000+ characters focusing ONLY on the soup's complexity, ingredients, and boiling process.
    4. ## The Noodle Craftsmanship: Detailed analysis of hydration levels, texture, and wheat sourcing.
    5. ## Toppings & Orchestration: Chashu, marinated eggs, and the harmony of garnishes.
    6. ## Secret Ordering Tips: How to customize (firmness, oil level) and hidden menu items.
    7. ## Local Guide & Access: Deep exploration of the surrounding neighborhood and precise directions.
    
    Write with passion, authority, and vivid adjectives in {lang}. Use bold text and bullet points.
    """

    try:
        response = client.models.generate_content(model=model_name, contents=prompt)
        raw_text = response.text.strip()
        
        # 정제
        if raw_text.startswith("```"):
            raw_text = "\n".join(raw_text.split("\n")[1:-1])

        os.makedirs(CONTENT_DIR, exist_ok=True)
        filename = f"{safe_name}_{lang}.md"
        with open(os.path.join(CONTENT_DIR, filename), 'w', encoding='utf-8') as f:
            f.write(raw_text)
            
        print(f"✅ [완료] {filename} (길이: {len(raw_text)}자)")
        return True
    except Exception as e:
        print(f"❌ [실패] {name}: {e}")
        return False

def run_generator(limit=10):
    csv_path = os.path.join(SCRIPT_DIR, 'csv', 'ramens.csv')
    if not os.path.exists(csv_path): return

    tasks = []
    with open(csv_path, mode='r', encoding='utf-8-sig') as file:
        reader = csv.DictReader(file)
        for row in reader:
            name = row['Name'].strip()
            safe_name = name.lower().replace(" ", "_").replace("'", "").replace(",", "")
            for lang in ['en', 'ko']:
                if not os.path.exists(os.path.join(CONTENT_DIR, f"{safe_name}_{lang}.md")):
                    tasks.append((safe_name, name, row['Lat'], row['Lng'], row['Address'], lang, row['Features'], row.get('Agoda', '')))
            if len(tasks) >= limit * 2: break

    if tasks:
        # 유료 API의 경우 할당량이 넉넉하므로 병렬 작업 수행 (max_workers 조절)
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            executor.map(lambda p: generate_ramen_article(*p), tasks)

if __name__ == "__main__":
    run_generator(limit=3) # 한 번에 20곳(40개 파일) 생성