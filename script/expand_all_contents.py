import os
import frontmatter
import google.generativeai as genai
import time
import re
from dotenv import load_dotenv

# --- 1. 설정 ---
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
CONTENT_DIR = os.path.join(BASE_DIR, 'app', 'content')

load_dotenv()
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-1.5-flash-latest")

def expand_content():
    all_files = [f for f in os.listdir(CONTENT_DIR) if f.endswith('.md')]
    
    print(f"🚀 전체 콘텐츠 확장 및 결론(Conclusion) 체크 시작 (대상: {len(all_files)}개)")

    for filename in all_files:
        filepath = os.path.join(CONTENT_DIR, filename)
        post = frontmatter.load(filepath)
        
        current_len = len(post.content)
        lang = post.get('lang', 'en')
        
        # 이미 7,000자 근처이고 결론 섹션이 있다면 건너뛰기 (선택 사항)
        if current_len > 6500 and "## 6. ✨ Conclusion:" in post.content:
            # print(f"⏩ 스킵: {filename} (이미 충분함)")
            continue

        print(f"📝 작업 중 [{lang.upper()}]: {filename} (현재 {current_len}자)")

        # 언어별 프롬프트 구성 (공통 지침: 결론 섹션 강제 포함)
        conclusion_instruction = "\n**[CRITICAL]**: Ensure the article ends with a section titled '## 6. ✨ Conclusion:' followed by a thoughtful summary."

        if lang == 'ko':
            prompt = f"""
            Task: 아래 신사 가이드를 한국 독자를 위한 '초고화질 상세 가이드'로 확장하라.
            목표 분량: 공백 포함 약 6,000~7,000자 내외.
            
            [지침]
            1. 기존 내용을 삭제하지 말고 기반으로 내용을 대폭 보강하라.
            2. 역사, 신화, 건축 양식, 계절별 풍경, 참배객의 감상 등을 매우 상세히 묘사하라.
            3. 주변 맛집 및 로컬 정보를 4곳 이상 구체적으로 추가하라.
            4. **반드시 글 마지막에 '## 6. ✨ Conclusion:' 섹션을 추가하고 감동적인 마무리 문구를 작성하라.**
            5. 리스트(* 혹은 -) 항목 전후에는 반드시 빈 줄을 삽입하여 레이아웃을 유지하라.
            
            [Original Content]:
            {post.content}
            """
        elif lang == 'ja':
            prompt = f"""
            Task: 以下の神社ガイドを基に、日本人読者のための「究極の解説記事」を作成せよ。
            目標文字数：約6,000〜7,000文字。
            
            [指針]
            1. 既存の内容を土台に、圧倒的な情報量で補筆・拡張すること。
            2. 御祭神の由来、社殿の歴史的価値、境内の見どころ（摂社・末社等）を網羅せよ。
            3. 周辺の老舗グルメや散策ルート情報を詳細に記載せよ。
            4. **必ず記事の最後に '## 6. ✨ Conclusion:' セクションを追加し、まとめの言葉を記述すること。**
            5. リ스트(* や -) の前後には必ず空行を入れ、可読性を確保せよ。
            
            [Original Content]:
            {post.content}
            """
        else: # English (en)
            prompt = f"""
            Task: Expand the following shrine guide into a "Grand Tour Guide" for global travelers.
            Target Length: Approx 6,000 ~ 7,000 characters.
            
            [Instructions]
            1. Enrich the storytelling regarding mythology, architecture, and festivals.
            2. Add a dedicated "Local Life" section with 4+ authentic nearby spots.
            3. **You MUST include a section titled '## 6. ✨ Conclusion:' at the end of the article.**
            4. Ensure there is an 'empty line' before and after every list item (* or -).
            
            [Original Content]:
            {post.content}
            """

        try:
            response = model.generate_content(prompt)
            expanded_content = response.text.strip()

            # 1. 리스트 레이아웃 보정 정규식
            expanded_content = re.sub(r'([^\n])\n\*\s', r'\1\n\n* ', expanded_content)
            expanded_content = re.sub(r'([^\n])\n-\s', r'\1\n\n- ', expanded_content)

            # 2. 결론 섹션 강제 확인 및 자동 삽입 (AI가 실수할 경우 대비)
            if "## 6. ✨ Conclusion:" not in expanded_content:
                print(f"⚠️ 결론 섹션 누락 감지, 강제 추가 중...")
                default_conclusions = {
                    'ko': "\n\n## 6. ✨ Conclusion:\n신사의 고요한 분위기 속에서 일상의 소중함을 되찾는 시간이 되길 바랍니다. 여러분의 소원이 이곳의 맑은 기운과 함께 이루어지기를 진심으로 기원합니다.",
                    'ja': "\n\n## 6. ✨ Conclusion:\n神社の静寂の中で、日常の喧騒を忘れ、心が癒やされるひとときをお過ごしください。皆様の願いが神様に届き、良きご縁に恵まれることを心よりお祈り申し上げます。",
                    'en': "\n\n## 6. ✨ Conclusion:\nWe hope that your visit to this sacred site brings peace to your heart and clarity to your mind. May the blessings of the deities follow you on your continued journey through Japan."
                }
                expanded_content += default_conclusions.get(lang, default_conclusions['en'])

            # 3. 데이터 업데이트 및 저장
            post.content = expanded_content
            with open(filepath, 'wb') as f:
                frontmatter.dump(post, f)
            
            print(f"✅ 완료: {filename} (확장 후: {len(expanded_content)}자)")
            time.sleep(5) 

        except Exception as e:
            print(f"❌ 에러 발생 ({filename}): {e}")

if __name__ == "__main__":
    expand_content()