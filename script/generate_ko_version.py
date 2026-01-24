import os
import frontmatter
import google.generativeai as genai
import time
import re
from dotenv import load_dotenv

# 설정
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
CONTENT_DIR = os.path.join(BASE_DIR, 'app', 'content')

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-flash-latest")

CAT_MAP = {
    "Wealth": "재물", "Love": "사랑", "Health": "건강",
    "Success": "성공", "Safety": "안전", "History": "역사"
}

def generate_ko_expanded():
    # 1. 모든 md 파일 목록
    all_files = os.listdir(CONTENT_DIR)
    # 2. 영어 원본 파일 추출 (접미사가 없는 파일)
    en_files = [f for f in all_files if f.endswith('.md') and not ('_ko.md' in f or '_ja.md' in f)]
    
    print(f"🚀 한국어 확장 생성 시작 (대상: {len(en_files)}개)")

    for filename in en_files:
        ko_filename = filename.replace('.md', '_ko.md')
        ko_filepath = os.path.join(CONTENT_DIR, ko_filename)
        
        # [조건] 한국어 버전이 없을 때만 실행
        if os.path.exists(ko_filepath):
            # print(f"⏩ Skip: {ko_filename} (이미 존재함)")
            continue

        print(f"🇰🇷 내용 확장 및 번역 중: {filename} -> {ko_filename}")
        
        en_path = os.path.join(CONTENT_DIR, filename)
        post = frontmatter.load(en_path)

        # 7,000자 확장을 위한 정교한 프롬프트
        prompt = f"""
        Role: 일본 역사와 신토(Shinto)에 정통한 전문 여행 작가.
        Task: 아래 영어 신사 가이드를 바탕으로 **한국 독자를 위한 약 5,000~7,000자 분량의 초고화질 상세 가이드**를 작성하라.

        [지침 - 중요: 가독성 및 줄바꿈]
        1. 모든 주요 항목(`*`로 시작하는 리스트)은 **반드시 새로운 행**에서 시작하라.
        2. 리스트 항목 간에는 **반드시 빈 줄(Empty Line)**을 한 줄 추가하여 가독성을 높여라.
        3. 문단이 바뀔 때마다 엔터를 두 번 입력하여 문단을 확실히 구분하라.
        4. 정보가 한 줄에 뭉치지 않도록(Clumping) 소제목(`###`)을 적극적으로 활용하라.

        [내용 확장 지침]
        1. 단순 번역이 아닌 '내용 확장': 기존 내용을 바탕으로 역사적 배경, 신화 속 이야기, 풍수지리적 파워스폿의 의미, 건축 양식의 특징을 매우 상세히 추가할 것.
        2. 구성:
           - 서론: 해당 신사의 분위기와 방문해야 하는 이유 (감성적 서술)
           - 역사와 유래: 창건 설화, 시대별 변천사 (매우 상세히)
           - 신사 경내 탐방 가이드: 도리이부터 본전까지, 각 구역의 의미와 볼거리
           - 파워스폿 포인트: 어디서 어떤 기운을 받아야 하는지 구체적 안내
           - 고슈인 및 오마모리: 이곳에서만 구할 수 있는 특별한 물건 소개
           - 주변 여행 팁: 맛집, 로컬 상점, 산책로 정보 추가
           - 접근성 및 실용 정보: 표 형식 유지
           - 온천 섹션: 주변 온천 정보 확장
        3. 말투: 친절하고 전문적인 구어체 (~해요, ~입니다).
        4. 분량: 한국어 기준 공백 포함 최소 5,000자 이상, 7,000자 내외로 매우 풍부하게 작성할 것.
        5. 형식: 마크다운 구조(H1, H2, H3, 테이블)를 엄격히 지킬 것.


        [Original Title]: {post.get('title')}
        [Original Content]:
        {post.content}
        """

        try:
            response = model.generate_content(prompt)
            ko_content = response.text.strip()

            new_post = frontmatter.Post(ko_content)
            new_post.metadata = post.metadata.copy()
            
            title_match = re.search(r'^#\s+(.+)$', ko_content, re.MULTILINE)
            new_post['title'] = title_match.group(1).strip() if title_match else post.get('title')
            
            new_post['lang'] = 'ko'
            
            # 태그 확장 및 번역
            tag_prompt = f"이 신사와 관련된 한국어 검색 태그 10개를 쉼표로 구분해 작성해줘. (예: 도쿄여행, 신사참배...): {post.get('title')}"
            tag_resp = model.generate_content(tag_prompt)
            new_post['tags'] = [t.strip() for t in tag_resp.text.split(',')]
            
            new_post['categories'] = [CAT_MAP.get(c, c) for c in post.get('categories', [])]
            
            summary_prompt = f"위 내용을 바탕으로 SEO용 한국어 요약문(120자 내외)을 작성해줘:\n{ko_content[:500]}"
            summary_resp = model.generate_content(summary_prompt)
            new_post['excerpt'] = summary_resp.text.strip()

            with open(ko_filepath, 'wb') as f:
                frontmatter.dump(new_post, f)
            
            print(f"✅ 완료: {ko_filename} (대량 콘텐츠 생성됨)")
            time.sleep(5) # 분량 증가로 인한 처리 시간 확보

        except Exception as e:
            print(f"❌ 에러 ({filename}): {e}")

if __name__ == "__main__":
    generate_ko_expanded()