from flask import Flask, jsonify, render_template, abort, send_from_directory, redirect
from flask_compress import Compress
import json
import os
import frontmatter
import markdown
import re

app = Flask(__name__)
Compress(app)

# [설정] 경로 설정
BASE_DIR = app.root_path
STATIC_DIR = os.path.join(BASE_DIR, 'static')
# 명칭 통일: onsen_data.json -> ramen_data.json
DATA_FILE = os.path.join(STATIC_DIR, 'json', 'ramen_data.json') 
CONTENT_DIR = os.path.join(BASE_DIR, 'content')

# [최적화] 서버 시작 시 데이터를 메모리에 로드 (Cache)
CACHED_DATA = {}
if os.path.exists(DATA_FILE):
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            CACHED_DATA = json.load(f)
            # 명칭 통일: onsens -> ramens
            print(f"✅ Data loaded: {len(CACHED_DATA.get('ramens',[]))} items")
    except Exception as e:
        print(f"❌ Data load error: {e}")
        CACHED_DATA = {"ramens":[], "error": "Load failed"}

@app.route('/static/images/<path:filename>')
def serve_images(filename):
    import time
    # ok-project-assets/okramen 폴더를 바라보게 설정
    return redirect(f"https://storage.googleapis.com/ok-project-assets/okramen/{filename}?v={int(time.time())}")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ads.txt')
def ads_txt():
    return send_from_directory(STATIC_DIR, 'ads.txt')

@app.route('/sitemap.xml')
def sitemap_xml():
    return send_from_directory(STATIC_DIR, 'sitemap.xml')

@app.route('/about.html')
def about():
    return render_template('about.html')

@app.route('/privacy.html')
def privacy():
    return render_template('privacy.html')

# [변경] API 엔드포인트 이름 명칭 통일
@app.route('/api/ramens')
def api_ramens():
    return jsonify(CACHED_DATA)

# [수정] 상세 페이지 로직 (AI의 마크다운 실수 보정 추가)
@app.route('/ramen/<ramen_id>')
def ramen_detail(ramen_id):
    md_path = os.path.join(CONTENT_DIR, f"{ramen_id}.md")
    if not os.path.exists(md_path):
        abort(404)
        
    with open(md_path, 'r', encoding='utf-8') as f:
        raw_text = f.read().strip()

    # 💡 [핵심 추가] AI가 넣은 불필요한 '## yaml'이나 '```markdown' 코드 블록 청소
    # 1. 시작 부분의 코드 블록 기호 제거
    raw_text = re.sub(r'^```[a-z]*\n', '', raw_text)
    # 2. 끝 부분의 코드 블록 기호 제거
    raw_text = re.sub(r'\n```$', '', raw_text)
    # 3. '## yaml' 또는 'yaml'이라는 불필요한 제목 제거
    raw_text = re.sub(r'^(##\s*)?yaml\n', '', raw_text, flags=re.IGNORECASE)
    # 4. 만약 문서 중간에 --- 가 있다면 그 앞의 쓰레기 텍스트 모두 제거
    if '---' in raw_text and not raw_text.startswith('---'):
        raw_text = '---' + raw_text.split('---', 1)[1]

    # 청소된 텍스트로 frontmatter 로드
    post = frontmatter.loads(raw_text)

    if isinstance(post.get('categories'), str):
        post['categories'] = [c.strip() for c in post['categories'].split(',')]

    # 💡 [기존 로직 유지] 문장 중간 리스트 줄바꿈 보정
    content_to_fix = post.content if post.content else ""
    fixed_content = re.sub(r'([\.!?:])\s+(\*\s)', r'\1\n\n\2', content_to_fix)
    fixed_content = re.sub(r'([^\n])\n\*\s', r'\1\n\n* ', fixed_content)
    fixed_content = re.sub(r'([^\n])\n-\s', r'\1\n\n- ', fixed_content)

    # 변환
    content_html = markdown.markdown(fixed_content, extensions=['tables', 'fenced_code'])
    
    return render_template('detail.html', post=post, content=content_html)

@app.route('/content/images/<path:filename>')
def serve_content_images(filename):
    images_dir = os.path.join(CONTENT_DIR, 'images')
    return send_from_directory(images_dir, filename)

@app.route('/robots.txt')
def robots_txt():
    return send_from_directory(STATIC_DIR, 'robots.txt')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)