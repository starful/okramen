import os
import time
import frontmatter
from google import genai
from google.genai import types
from dotenv import load_dotenv

# ==========================================
# ⚙️ 설정
# ==========================================
load_dotenv()

# Vertex AI 방식 (GCP 프로젝트 기반, API 키 불필요)
GCP_PROJECT  = os.environ.get("GCP_PROJECT", "starful-258005")
GCP_LOCATION = os.environ.get("GCP_LOCATION", "us-central1")

SCRIPT_DIR   = os.path.dirname(os.path.abspath(__file__))
BASE_DIR     = os.path.dirname(SCRIPT_DIR)
CONTENT_DIR  = os.path.join(BASE_DIR, 'app', 'content')
IMAGES_DIR   = os.path.join(BASE_DIR, 'app', 'static', 'images')

PROTECTED = {'logo.png', 'logo.svg', 'favicon.ico', 'default.jpg', 'default.png', 'og_image.png'}

# ==========================================
# 🖼️ Imagen 4 이미지 생성 (Vertex AI)
# ==========================================
def generate_image(image_prompt, save_path):
    """Imagen 4로 이미지를 생성하고 저장합니다."""

    # Vertex AI 클라이언트 (gcloud auth로 인증, API 키 불필요)
    client = genai.Client(
        vertexai=True,
        project=GCP_PROJECT,
        location=GCP_LOCATION,
    )

    enhanced_prompt = (
        f"{image_prompt}, "
        "photorealistic, ultra-detailed, professional food photography, "
        "shot on Sony A7R V with 85mm f/1.4 lens, "
        "natural steam rising from bowl, warm restaurant ambient lighting, "
        "shallow depth of field, bokeh background, 8K resolution"
    )

    try:
        response = client.models.generate_images(
            model='imagen-4.0-generate-001',
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
            print(f"  🖼️  생성 완료 ({size_kb:.0f}KB)")
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

    # MD 파일에서 고유한 safe_name 목록 추출
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
    print(f"   GCP 프로젝트: {GCP_PROJECT} / {GCP_LOCATION}\n")

    success = 0
    skipped = 0
    failed  = 0

    for i, safe_name in enumerate(targets, 1):
        save_path = os.path.join(IMAGES_DIR, f"{safe_name}.jpg")

        print(f"[{i:03d}/{total}] {safe_name}")

        # 이미 이미지가 있으면 스킵
        if os.path.exists(save_path) and os.path.basename(save_path) not in PROTECTED:
            print(f"  ⏭️  이미 존재 → 스킵")
            skipped += 1
            continue

        # image_prompt 추출
        image_prompt = get_image_prompt_from_md(safe_name)
        if not image_prompt:
            print(f"  ⚠️  image_prompt 없음 → 기본 프롬프트 사용")
            shop_name = safe_name.replace('_', ' ').title()
            image_prompt = (
                f"A steaming bowl of Japanese ramen at {shop_name} restaurant, "
                "rich golden broth, chashu pork, soft-boiled ajitama egg, "
                "nori seaweed, green onions, bamboo shoots"
            )

        print(f"  📝 프롬프트: {image_prompt[:60]}...")

        ok = generate_image(image_prompt, save_path)
        if ok:
            success += 1
        else:
            failed += 1

        # Imagen API 과부하 방지
        time.sleep(1.0)

    print("\n" + "─" * 50)
    print(f"🎉 이미지 생성 완료!")
    print(f"   ✅ 성공  : {success}개")
    print(f"   ⏭️  스킵  : {skipped}개 (이미 존재)")
    print(f"   ❌ 실패  : {failed}개")
    print("─" * 50)


if __name__ == "__main__":
    generate_all_images()