import os
import time
import random
import frontmatter
from google import genai
from google.genai import types
from dotenv import load_dotenv

# ==========================================
# ⚙️ 설정
# ==========================================
load_dotenv()

GCP_PROJECT  = os.environ.get("GCP_PROJECT", "starful-258005")
GCP_LOCATION = os.environ.get("GCP_LOCATION", "us-central1")

SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
BASE_DIR    = os.path.dirname(SCRIPT_DIR)
CONTENT_DIR = os.path.join(BASE_DIR, 'app', 'content')
IMAGES_DIR  = os.path.join(BASE_DIR, 'app', 'static', 'images')

PROTECTED = {'logo.png', 'logo.svg', 'favicon.ico', 'default.jpg', 'default.png', 'og_image.png'}

# ==========================================
# 🎨 다양성을 위한 랜덤 변수 풀
# ==========================================
CAMERA_ANGLES = [
    "overhead flat-lay shot, 90-degree top-down",
    "dramatic 45-degree angle shot",
    "side profile close-up, eye-level with the bowl",
    "low angle shot looking up at the bowl",
    "three-quarter view from above",
]

MOODS = [
    "dark moody izakaya atmosphere, dim warm Edison bulb lighting",
    "bright minimalist Japanese restaurant, clean white counter",
    "warm rustic wooden interior, natural window light",
    "dramatic neon-lit late night ramen shop, vivid colors",
    "authentic street-side counter seat, cozy and intimate",
    "high-end modern restaurant, dramatic spotlight lighting",
]

LENS_STYLES = [
    "shot on 85mm f/1.4 lens, extreme shallow depth of field, creamy bokeh",
    "shot on 50mm f/1.8 lens, natural perspective, soft background blur",
    "shot on 100mm macro lens, ultra close-up details, water droplets visible",
    "shot on 35mm f/2 lens, environmental context visible in background",
]

EXTRAS = [
    "steam gently rising from the broth",
    "condensation on the bowl rim, dewy fresh toppings",
    "chopsticks resting on the bowl edge",
    "small side dish of pickled ginger visible in background",
    "broth surface shimmering with golden oil droplets",
]

def get_random_style():
    """매번 다른 촬영 스타일 조합을 반환합니다."""
    return (
        random.choice(CAMERA_ANGLES),
        random.choice(MOODS),
        random.choice(LENS_STYLES),
        random.choice(EXTRAS),
    )

# ==========================================
# 🖼️ Imagen 이미지 생성 (Vertex AI)
# ==========================================
def generate_image(image_prompt, save_path):
    client = genai.Client(
        vertexai=True,
        project=GCP_PROJECT,
        location=GCP_LOCATION,
    )

    angle, mood, lens, extra = get_random_style()

    enhanced_prompt = (
        f"{image_prompt}. "
        f"Composition: {angle}. "
        f"Atmosphere: {mood}. "
        f"{lens}. "
        f"Detail: {extra}. "
        "Photorealistic, ultra-detailed, professional food photography, 8K resolution, "
        "award-winning food photo, no text, no watermark."
    )

    try:
        response = client.models.generate_images(
            model='imagen-4.0-fast-generate-001',
            prompt=enhanced_prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                aspect_ratio="16:9",
                output_mime_type='image/jpeg',
                person_generation="dont_allow",
            )
        )

        if response.generated_images:
            image_bytes = response.generated_images[0].image.image_bytes
            with open(save_path, 'wb') as f:
                f.write(image_bytes)
            size_kb = len(image_bytes) / 1024
            print(f"  🖼️  생성 완료 ({size_kb:.0f}KB) | {angle[:30]}... | {mood[:25]}...")
            return True
        else:
            print(f"  ⚠️  이미지 생성 결과 없음")
            return False

    except Exception as e:
        print(f"  ❌ 생성 실패: {e}")
        return False


# ==========================================
# 🔍 MD 파일에서 image_prompt 추출
# ==========================================
def get_image_prompt_from_md(safe_name):
    for lang in ['en', 'ko']:
        md_path = os.path.join(CONTENT_DIR, f"{safe_name}_{lang}.md")
        if os.path.exists(md_path):
            try:
                with open(md_path, 'r', encoding='utf-8') as f:
                    post = frontmatter.load(f)
                prompt = post.get('image_prompt', '')
                if prompt:
                    return str(prompt).strip()
            except Exception as e:
                print(f"  ⚠️  MD 읽기 오류: {e}")
    return None


# ==========================================
# 🚀 메인 실행
# ==========================================
def generate_all_images():
    os.makedirs(IMAGES_DIR, exist_ok=True)

    # MD 파일 기준 safe_name 추출
    safe_names = set()
    if os.path.exists(CONTENT_DIR):
        for fname in os.listdir(CONTENT_DIR):
            if fname.endswith('.md'):
                base = fname.replace('.md', '')
                for lang in ['_ko', '_en', '_ja']:
                    if base.endswith(lang):
                        safe_names.add(base[:-len(lang)])
                        break

    targets = sorted(safe_names)
    total = len(targets)
    print(f"\n🍜  총 {total}개 라멘집 이미지 확인 시작...")
    print(f"   GCP: {GCP_PROJECT} / {GCP_LOCATION}")
    print(f"   모델: imagen-4.0-fast-generate-001\n")

    success = 0
    skipped = 0
    failed  = 0

    for i, safe_name in enumerate(targets, 1):
        save_path = os.path.join(IMAGES_DIR, f"{safe_name}.jpg")

        print(f"[{i:03d}/{total}] {safe_name}")

        if os.path.exists(save_path) and os.path.basename(save_path) not in PROTECTED:
            print(f"  ⏭️  이미 존재 → 스킵")
            skipped += 1
            continue

        image_prompt = get_image_prompt_from_md(safe_name)
        if not image_prompt:
            print(f"  ⚠️  image_prompt 없음 → 기본 프롬프트 사용")
            shop_name = safe_name.replace('_', ' ').title()
            # 기본 프롬프트도 랜덤 요소 추가
            broths = ["rich milky tonkotsu", "clear golden shoyu", "deep red miso", "light delicate shio"]
            toppings = ["thick chashu pork slices", "char siu pork", "crispy kakuni pork belly"]
            image_prompt = (
                f"A bowl of Japanese ramen at {shop_name}, "
                f"{random.choice(broths)} broth, "
                f"{random.choice(toppings)}, soft-boiled ajitama egg, "
                f"nori seaweed, green onions, bamboo shoots"
            )

        ok = generate_image(image_prompt, save_path)
        if ok:
            success += 1
        else:
            failed += 1

        time.sleep(1.0)

    print("\n" + "─" * 50)
    print(f"🎉 이미지 생성 완료!")
    print(f"   ✅ 성공  : {success}개")
    print(f"   ⏭️  스킵  : {skipped}개")
    print(f"   ❌ 실패  : {failed}개")
    print("─" * 50)


if __name__ == "__main__":
    generate_all_images()