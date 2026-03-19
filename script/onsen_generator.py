import os
import csv
import time
from datetime import datetime
from google import genai
from dotenv import load_dotenv
import concurrent.futures  # 💡 [핵심] 동시 작업을 위한 멀티스레딩 라이브러리 추가

# ==========================================
# ⚙️ 설정 (Configuration)
# ==========================================
load_dotenv()
API_KEY = os.environ.get("GEMINI_API_KEY")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
CONTENT_DIR = os.path.join(BASE_DIR, 'app', 'content')
IMAGES_DIR = os.path.join(BASE_DIR, 'app', 'static', 'images')

TARGET_LANGS =['en', 'ko']

CATEGORIES = {
    "en":["Private Bath", "Tattoo OK", "Great View", "Luxury", "Local"],
    "ko":["가족탕", "타투 허용", "절경", "고급 료칸", "로컬"],
    "ja":["貸切風呂", "タトゥーOK", "絶景", "高級", "秘湯"]
}

def generate_onsen_md(safe_name, name, lat, lng, address, thumbnail, lang, features, agoda_link):
    """Gemini API를 호출하여 마크다운을 생성하는 함수 (스레드에서 개별 실행됨)"""
    if not API_KEY:
        return False

    client = genai.Client(api_key=API_KEY)
    
    current_date = datetime.now().strftime('%Y-%m-%d')
    allowed_categories = ", ".join(CATEGORIES.get(lang, CATEGORIES["en"]))
    filename = f"{safe_name}_{lang}.md"
    
    print(f"🚀 [시작] '{name}' ({lang}) 메가 콘텐츠 생성 중...")

    prompt = f"""
    You are an elite travel journalist and SEO expert specializing in Japanese Onsens and luxury Ryokans.
    Your task is to write an EXTREMELY comprehensive, deeply detailed, and highly engaging travel guide about the following onsen. 
    The total length of your response MUST be very long, aiming for 7,000 to 8,000 characters.[Target Onsen Information]
    - Name: {name}
    - Location: {address}
    - Key Features: {features}
    - Target Language: {lang} (ko=Korean, en=English)[Instructions]
    1. The output MUST be a valid Markdown file containing YAML frontmatter.
    2. Do NOT wrap the output in ```markdown blocks, just output the raw text.
    3. VERY IMPORTANT: You MUST wrap the values for 'title', 'summary', and 'image_prompt' in double quotes (""). Do NOT use line breaks inside the quotes.
    4. The YAML frontmatter must be exactly in this format (pay attention to the spaces after colons):
    ---
    lang: {lang}
    title: "Write a highly catchy, emotional, and attractive SEO title here (single line)"
    lat: {lat}
    lng: {lng}
    categories: [{allowed_categories}]
    thumbnail: "{thumbnail}"
    address: "{address}"
    date: "{current_date}"
    agoda: "{agoda_link}"
    summary: "Write a 3-sentence highly engaging summary here (single line)"
    image_prompt: "Write a highly detailed Midjourney image generation prompt IN ENGLISH here (single line)"
    ---

    5. After the frontmatter, write the body of the blog post in the Target Language ({lang}).
    6. VERY IMPORTANT: Translate all 'Key Features' into the Target Language. Do NOT use the original language of the 'Key Features' in the body text.
    7. To reach the 7,000 - 8,000 character goal, you MUST include the following deeply detailed sections using Markdown headings (##, ###):
       - **Introduction:** Deep dive into the vibe, the first impression, and why this onsen is special.
       - **History & Tradition:** The rich history of the ryokan or the local hot spring town.
       - **Deep Dive into the Baths:** Detailed description of the open-air baths (rotemburo), private baths (kashikiri), water quality, minerals, health benefits, and the exact view from the bath.
       - **Rooms & Accommodation:** A vivid description of the traditional tatami rooms, western-style beds, architecture, and wabi-sabi aesthetics.
       - **Gastronomy (Kaiseki Dinner):** A mouth-watering description of the traditional multi-course dinner, local seasonal ingredients, and breakfast.
       - **Things to Do Around the Area:** Detailed guide to nearby tourist spots, nature walks, or local streets.
       - **Access Guide:** Step-by-step instructions on how to get there from major cities or airports.
       - **FAQ & Practical Tips:** Tattoo policy, best season to visit, and booking tips.
       - **Conclusion:** A powerful closing statement.
       - Use markdown headings (##, ###) and bullet points.
       - VERY IMPORTANT: When using bullet points (* or -), you MUST start them on a NEW LINE. Never put a bullet point in the middle of a sentence or paragraph.
       - Add a concluding recommendation.
       
    8. Write eloquently, passionately, and informatively. Expand on details rather than repeating the same points. Use bold text for emphasis.
    """

    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
        )
        content = response.text.strip()
        
        if content.startswith("```markdown"): content = content[11:]
        elif content.startswith("```"): content = content[3:]
        if content.endswith("```"): content = content[:-3]
        content = content.strip()

        filepath = os.path.join(CONTENT_DIR, filename)
        os.makedirs(CONTENT_DIR, exist_ok=True)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
            
        print(f"✅ [완료] {filename} (약 {len(content)}자)")
        return True

    except Exception as e:
        print(f"❌ [에러] ({name} - {lang}): {e}")
        return False


def process_csv_auto(csv_filename="onsens.csv", limit=5):
    csv_path = os.path.join(SCRIPT_DIR, 'csv', csv_filename)
    
    if not os.path.exists(csv_path):
        print(f"❌ 오류: {csv_path} 파일을 찾을 수 없습니다.")
        return

    processed_onsen_names = set()
    skipped_files_count = 0   
    tasks =[] # 동시에 실행할 작업(Task) 목록

    # 1. CSV를 읽어서 생성해야 할 작업(Task) 목록을 먼저 추려냅니다.
    with open(csv_path, mode='r', encoding='utf-8-sig') as file:
        reader = csv.DictReader(file)
        
        for row in reader:
            if len(processed_onsen_names) >= limit:
                break
            
            name = (row.get('Name') or '').strip()
            if not name: continue
            
            safe_name = name.lower().replace(" ", "_").replace("'", "").replace(",", "")
            
            lat = (row.get('Lat') or '').strip()
            lng = (row.get('Lng') or '').strip()
            address = (row.get('Address') or '').strip()
            features = (row.get('Features') or '').strip()
            agoda_link = (row.get('Agoda') or '').strip()

            thumbnail = ""
            for ext in ['.jpg', '.jpeg', '.png', '.webp']:
                img_path = os.path.join(IMAGES_DIR, f"{safe_name}{ext}")
                if os.path.exists(img_path):
                    thumbnail = f"/static/images/{safe_name}{ext}"
                    break 
            
            if not thumbnail:
                thumbnail = f"/static/images/{safe_name}.jpg"

            needs_generation = False

            # 영어, 한국어 생성 체크
            for lang in TARGET_LANGS:
                filename = f"{safe_name}_{lang}.md"
                filepath = os.path.join(CONTENT_DIR, filename)
                
                if os.path.exists(filepath):
                    skipped_files_count += 1
                else:
                    # 파일이 없으면 '작업 목록'에 추가
                    tasks.append((safe_name, name, lat, lng, address, thumbnail, lang, features, agoda_link))
                    needs_generation = True
            
            # 하나라도 생성해야 할 언어가 있다면 온천 카운트 증가
            if needs_generation:
                processed_onsen_names.add(safe_name)
                
    if not tasks:
        print("💡 모두 생성되어 새로 작업할 파일이 없습니다.")
        return

    # 2. 💡 [핵심] 준비된 작업(Task)들을 동시에 여러 스레드로 발사합니다!
    print(f"\n⚡️ 유료 API 초고속 모드 가동! 총 {len(tasks)}개의 작업을 동시에 처리합니다...\n")
    
    total_files_generated = 0
    start_time = time.time()
    
    # 최대 10개의 스레드를 띄워서 한꺼번에 구글 API에 요청을 보냅니다.
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        # submit으로 함수와 인자들을 병렬로 전달
        futures =[executor.submit(generate_onsen_md, *task) for task in tasks]
        
        # 작업이 끝나는 대로 결과를 받아옵니다.
        for future in concurrent.futures.as_completed(futures):
            if future.result():
                total_files_generated += 1

    end_time = time.time()
            
    print("-" * 50)
    print(f"🎉 초고속 생성 완료! (소요 시간: {end_time - start_time:.2f}초)")
    print(f"   - 이번에 처리된 온천 장소: {len(processed_onsen_names)} 곳")
    print(f"   - 이번에 새로 생성된 파일: {total_files_generated} 개")
    print(f"   - 이미 있어서 건너뛴 파일: {skipped_files_count} 개")


if __name__ == "__main__":
    print("\n♨️ OKOnsen 메가 콘텐츠 한/영 자동 생성 봇 (유료 API 고속 모드) ♨️")
    print("-" * 50)
    
    if not API_KEY:
        print("⚠️ 경고: .env 파일에서 GEMINI_API_KEY를 읽어오지 못했습니다!\n")
    else:
        # 한 번 실행 시 온천 5곳(10개 파일)을 동시에 처리
        # 만약 한 번에 더 많이 만들고 싶다면 limit=10 등으로 수정하시면 됩니다!
        process_csv_auto(csv_filename="onsens.csv", limit=5)