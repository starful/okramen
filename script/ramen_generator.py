import os
import csv
import re
import concurrent.futures
from datetime import datetime
from google import genai
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()
API_KEY = os.environ.get("GEMINI_API_KEY")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
CONTENT_DIR = os.path.join(BASE_DIR, 'app', 'content')

# 글로벌 라멘 카테고리 설정
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
    """AI가 출력한 텍스트에서 ```markdown 이나 ## yaml 같은 쓰레기 텍스트 제거"""
    text = text.strip()
    text = re.sub(r'^```[a-z]*\n', '', text)
    text = re.sub(r'\n```$', '', text)
    text = re.sub(r'^(##\s*)?yaml\n', '', text, flags=re.IGNORECASE)
    if '---' in text and not text.startswith('---'):
        text = '---' + text.split('---', 1)[1]
    return text.strip()

def generate_ramen_article(safe_name, name, lat, lng, address, lang, features, agoda):
    if not API_KEY:
        print("❌ API Key missing")
        return

    client = genai.Client(api_key=API_KEY)
    model_name = 'gemini-flash-latest'

    flavor_list = ", ".join(CATEGORIES[lang]["flavor"])
    vibe_list = ", ".join(CATEGORIES[lang]["vibe"])

    print(f"🚀 [AI] Generating {lang} article for: {name}...")

    prompt = f"""
    You are an elite Michelin-star food critic. Write a MASTERPIECE ramen guide for '{name}'.
    The article must be extremely long (8,000+ characters), professional, and SEO-optimized.

    [Target Info]
    - Shop Name: {name}
    - Location: {address}
    - Style: {features}
    - Language: {lang}

    [Categorization Task]
    1. Select EXACTLY one Flavor from: [{flavor_list}]
    2. Select EXACTLY one Vibe from: [{vibe_list}]

    [Output Format - STRICT]
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
    summary: "High-conversion 3-sentence summary (single line)"
    image_prompt: "Write a single-line Imagen 3 prompt IN ENGLISH for a photorealistic close-up food photo of this ramen bowl. Include: broth color/texture, toppings (chashu, ajitama, nori, menma), steam rising, dark moody restaurant background, shallow depth of field, shot on 85mm lens, professional food photography, high detail"
    ---

    [Article Content Structure]
    - ## The Soul of the Shop: History and Philosophy.
    - ## The Broth Analysis: Deep dive into ingredients and complexity (2,000+ chars).
    - ## Noodle & Topping Harmony: Texture, Chashu, and Ajitama analysis.
    - ## The Experience: Vibe, wait time, and neighborhood guide.

    IMPORTANT: DO NOT use markdown code blocks (```). Start directly with '---'.
    IMPORTANT: image_prompt must be a single line inside double quotes, no line breaks.
    """

    try:
        response = client.models.generate_content(model=model_name, contents=prompt)
        final_text = clean_ai_response(response.text)

        os.makedirs(CONTENT_DIR, exist_ok=True)
        filename = f"{safe_name}_{lang}.md"
        with open(os.path.join(CONTENT_DIR, filename), 'w', encoding='utf-8') as f:
            f.write(final_text)

        print(f"✅ [Done] {filename} ({len(final_text)} chars)")
    except Exception as e:
        print(f"❌ [Failed] {name}: {e}")

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
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            executor.map(lambda p: generate_ramen_article(*p), tasks)

if __name__ == "__main__":
    run_generator(limit=2)
