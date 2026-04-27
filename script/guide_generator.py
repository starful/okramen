import os
import csv
import re
import sys
import concurrent.futures
from datetime import datetime
from google import genai
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()
API_KEY = os.environ.get("GEMINI_API_KEY")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
GUIDE_CONTENT_DIR = os.path.join(BASE_DIR, 'app', 'content', 'guides')

def clean_ai_response(text):
    """AI 출력물에서 불필요한 태그 제거"""
    text = text.strip()
    text = re.sub(r'^```[a-z]*\n', '', text)
    text = re.sub(r'\n```$', '', text)
    text = re.sub(r'^(##\s*)?yaml\n', '', text, flags=re.IGNORECASE)
    if '---' in text and not text.startswith('---'):
        text = '---' + text.split('---', 1)[1]
    return text.strip()

def generate_guide_article(guide_id, topic, lang, keywords):
    if not API_KEY:
        print("❌ API Key missing")
        return

    client = genai.Client(api_key=API_KEY)
    model_name = 'gemini-2.5-flash'

    print(f"🚀 [Guide AI] Generating {lang} article for: {topic}...")

    prompt = f"""
    You are a professional travel blogger and Japanese food expert. 
    Write a high-quality, SEO-optimized educational guide about Japanese Ramen.
    
    [Topic]
    - Subject: {topic}
    - Language: {lang}
    - SEO Keywords: {keywords}

    [Output Format - STRICT]
    ---
    lang: {lang}
    title: "Write a catchy, SEO-friendly title in {lang}"
    date: "{datetime.now().strftime('%Y-%m-%d')}"
    summary: "Write a 2-sentence summary that encourages clicks (single line)."
    ---

    [Article Requirements]
    1. Introduction: Hook the reader.
    2. Main Content: Use descriptive H2 and H3 headers.
    3. Formatting: Use bullet points, bold text for key terms.
    4. Length: Minimum 4,000 characters for deep SEO.
    5. Conclusion: End with a link back to our map to find a shop.

    IMPORTANT: DO NOT use markdown code blocks (```). Start directly with '---'.
    """

    try:
        response = client.models.generate_content(model=model_name, contents=prompt)
        final_text = clean_ai_response(response.text)

        os.makedirs(GUIDE_CONTENT_DIR, exist_ok=True)
        filename = f"{guide_id}_{lang}.md"
        with open(os.path.join(GUIDE_CONTENT_DIR, filename), 'w', encoding='utf-8') as f:
            f.write(final_text)

        print(f"✅ [Done] {filename}")
    except Exception as e:
        print(f"❌ [Failed] {guide_id}: {e}")

def run_guide_generator(limit=3):
    csv_path = os.path.join(SCRIPT_DIR, 'csv', 'guides.csv')
    if not os.path.exists(csv_path):
        print(f"❌ CSV not found: {csv_path}")
        return

    tasks = []
    created_count = 0

    with open(csv_path, mode='r', encoding='utf-8-sig') as file:
        reader = csv.DictReader(file)
        for row in reader:
            guide_id = row['id'].strip()
            keywords = row['keywords'].strip()
            
            # 해당 ID의 파일(en, ko 둘 다)이 이미 있는지 확인
            en_exists = os.path.exists(os.path.join(GUIDE_CONTENT_DIR, f"{guide_id}_en.md"))
            ko_exists = os.path.exists(os.path.join(GUIDE_CONTENT_DIR, f"{guide_id}_ko.md"))

            # 하나라도 없으면 생성 대상으로 추가
            if not en_exists or not ko_exists:
                tasks.append((guide_id, row['topic_en'], 'en', keywords))
                tasks.append((guide_id, row['topic_ko'], 'ko', keywords))
                created_count += 1
            
            # 설정한 limit(3개 주제)에 도달하면 멈춤
            if created_count >= limit:
                break

    if not tasks:
        print("✨ All guides are already generated or no new topics found.")
        return

    print(f"🔔 Found {created_count} new topics to generate. (Total {len(tasks)} files)")

    # 병렬 실행 (최대 3개 작업 동시 진행)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        executor.map(lambda p: generate_guide_article(*p), tasks)

if __name__ == "__main__":
    # 기본 3개 주제(영어+한국어 총 6개 파일), 인자/환경변수로 오버라이드 가능
    env_limit = os.environ.get("GUIDE_LIMIT")
    arg_limit = sys.argv[1] if len(sys.argv) > 1 else None
    try:
        run_limit = int(arg_limit or env_limit or 3)
    except ValueError:
        run_limit = 3
    run_guide_generator(limit=run_limit)