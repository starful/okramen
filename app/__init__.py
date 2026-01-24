from flask import Flask, jsonify, render_template, abort, send_from_directory
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
DATA_FILE = os.path.join(STATIC_DIR, 'json', 'shrines_data.json')
CONTENT_DIR = os.path.join(BASE_DIR, 'content')

# [최적화] 서버 시작 시 데이터를 메모리에 로드 (Cache)
# 매 요청마다 파일을 읽지 않으므로 성능이 향상됩니다.
CACHED_DATA = {}
if os.path.exists(DATA_FILE):
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            CACHED_DATA = json.load(f)
            print(f"✅ Data loaded: {len(CACHED_DATA.get('shrines', []))} items")
    except Exception as e:
        print(f"❌ Data load error: {e}")
        CACHED_DATA = {"shrines": [], "error": "Load failed"}

@app.route('/')
def index():
    return render_template('index.html')

# [최적화] 정적 파일 서빙 (Ads.txt)
@app.route('/ads.txt')
def ads_txt():
    return send_from_directory(STATIC_DIR, 'ads.txt')

# [최적화] 정적 파일 서빙 (Sitemap)
@app.route('/sitemap.xml')
def sitemap_xml():
    return send_from_directory(STATIC_DIR, 'sitemap.xml')

@app.route('/about.html')
def about():
    return render_template('about.html')

@app.route('/privacy.html')
def privacy():
    return render_template('privacy.html')

@app.route('/api/shrines')
def api_shrines():
    # 메모리에 있는 데이터를 즉시 반환
    return jsonify(CACHED_DATA)

@app.route('/shrine/<shrine_id>')
def shrine_detail(shrine_id):
    md_path = os.path.join(CONTENT_DIR, f"{shrine_id}.md")
    if not os.path.exists(md_path):
        abort(404)
    with open(md_path, 'r', encoding='utf-8') as f:
        post = frontmatter.load(f)

    # [추가] 렌더링 직전에 줄바꿈 보정 로직 실행
    # 리스트(* 혹은 -) 앞에 빈 줄이 없으면 강제로 두 번 줄바꿈을 넣어줍니다.
    fixed_content = re.sub(r'([^\n])\n\*\s', r'\1\n\n* ', post.content)
    fixed_content = re.sub(r'([^\n])\n-\s', r'\1\n\n- ', fixed_content)

    content_html = markdown.markdown(post.content, extensions=['tables'])
    return render_template('detail.html', post=post, content=content_html)

@app.route('/content/images/<path:filename>')
def serve_content_images(filename):
    images_dir = os.path.join(CONTENT_DIR, 'images')
    return send_from_directory(images_dir, filename)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)