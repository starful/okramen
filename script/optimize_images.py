import os
from PIL import Image

# ==========================================
# ⚙️ 설정 (Configuration)
# ==========================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
IMAGES_DIR = os.path.join(BASE_DIR, 'app', 'static', 'images')

EXCLUDE_FILES =[
    'logo.png', 'logo.svg', 'favicons.ico', 
    'onsen_marker.png', 'og_image.png', 'default.png'
]

MAX_WIDTH = 800  
QUALITY = 75     

def get_size_kb(filepath):
    return os.path.getsize(filepath) / 1024

def optimize_images():
    print(f"📸 이미지 최적화 시작... 폴더: {IMAGES_DIR}")
    print("-" * 50)
    
    if not os.path.exists(IMAGES_DIR):
        print("❌ 이미지 폴더를 찾을 수 없습니다.")
        return

    success_count = 0
    skip_count = 0
    
    for filename in os.listdir(IMAGES_DIR):
        if filename in EXCLUDE_FILES:
            continue
            
        ext = os.path.splitext(filename)[1].lower()
        if ext not in['.jpg', '.jpeg', '.png', '.webp']:
            continue

        filepath = os.path.join(IMAGES_DIR, filename)
        
        try:
            with Image.open(filepath) as img:
                # 💡 [핵심 추가] 이미 가로 크기가 800px 이하이고 포맷이 JPG라면?
                # 다시 저장할 필요가 없으므로 날짜 보존을 위해 스킵합니다.
                if img.width <= MAX_WIDTH and ext == '.jpg':
                    print(f"⏭️  이미 최적화됨 (날짜 보존): {filename}")
                    skip_count += 1
                    continue

                # 최적화 로직 시작
                rgb_img = img.convert("RGB")
                if rgb_img.width > MAX_WIDTH:
                    ratio = MAX_WIDTH / rgb_img.width
                    new_height = int(rgb_img.height * ratio)
                    rgb_img = rgb_img.resize((MAX_WIDTH, new_height), Image.Resampling.LANCZOS)
            
            # 파일 저장 (이 시점에 파일 날짜가 현재 시간으로 바뀝니다)
            new_filename = os.path.splitext(filename)[0] + '.jpg'
            new_filepath = os.path.join(IMAGES_DIR, new_filename)
            
            rgb_img.save(new_filepath, 'JPEG', quality=QUALITY, optimize=True)
            
            # 원본이 png 등 다른 확장자였다면 삭제
            if filename != new_filename:
                os.remove(filepath)
            
            print(f"✅ 최적화 완료: {filename} -> {new_filename}")
            success_count += 1
            
        except Exception as e:
            print(f"❌ 에러 발생 ({filename}): {e}")

    print("-" * 50)
    print(f"🎉 작업 완료: 최적화 {success_count}개 / 스킵(날짜 보존) {skip_count}개")

if __name__ == '__main__':
    optimize_images()