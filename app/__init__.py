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
DATA_FILE = os.path.join(STATIC_DIR, 'json', 'onsen_data.json') # 변경됨
CONTENT_DIR = os.path.join(BASE_DIR, 'content')

# [최적화] 서버 시작 시 데이터를 메모리에 로드 (Cache)
CACHED_DATA = {}
if os.path.exists(DATA_FILE):
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            CACHED_DATA = json.load(f)
            print(f"✅ Data loaded: {len(CACHED_DATA.get('onsens',[]))} items")
    except Exception as e:
        print(f"❌ Data load error: {e}")
        CACHED_DATA = {"onsens":[], "error": "Load failed"}

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

# [변경] API 엔드포인트 이름 변경
@app.route('/api/onsens')
def api_onsens():
    return jsonify(CACHED_DATA)

# [이 부분을 찾아서]
@app.route('/onsen/<onsen_id>')
def onsen_detail(onsen_id):
    md_path = os.path.join(CONTENT_DIR, f"{onsen_id}.md")
    if not os.path.exists(md_path):
        abort(404)
    with open(md_path, 'r', encoding='utf-8') as f:
        post = frontmatter.load(f)

    if isinstance(post.get('categories'), str):
        post['categories'] =[c.strip() for c in post['categories'].split(',')]

    # 💡 [핵심 수정] AI가 엔터를 안 치고 문장 중간에 '* '를 썼을 때 강제로 줄바꿈(엔터 2번) 해주는 마법의 정규식!
    fixed_content = re.sub(r'([\.!?:])\s+(\*\s)', r'\1\n\n\2', post.content)
    fixed_content = re.sub(r'([^\n])\n\*\s', r'\1\n\n* ', fixed_content)
    fixed_content = re.sub(r'([^\n])\n-\s', r'\1\n\n- ', fixed_content)

    # (버그 수정: post.content 대신 방금 정규식으로 고친 fixed_content를 넣어서 변환합니다)
    content_html = markdown.markdown(fixed_content, extensions=['tables'])
    
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
    app.run(host='0.0.0.0', port=port)