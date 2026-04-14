from flask import Flask, jsonify, render_template, abort, send_from_directory, redirect, request
from flask_compress import Compress
import json
import os
import frontmatter
import markdown
import re
import glob

app = Flask(__name__)
Compress(app)

# [설정] 경로 설정
BASE_DIR = app.root_path
STATIC_DIR = os.path.join(BASE_DIR, 'static')
DATA_FILE = os.path.join(STATIC_DIR, 'json', 'ramen_data.json') 
CONTENT_DIR = os.path.join(BASE_DIR, 'content')
GUIDE_DIR = os.path.join(CONTENT_DIR, 'guides')

# 📸 고정된 13장의 Unsplash 이미지 리스트
UNSPLASH_GUIDE_IMAGES = [
    "https://images.unsplash.com/photo-1552611052-33e04de081de?q=80&w=800&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1569718212165-3a8278d5f624?q=80&w=800&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1555126634-323283e090fa?q=80&w=800&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1511910849309-0dffb8785146?q=80&w=800&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1534604973900-c43ab4c2e0ab?q=80&w=800&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1526318896980-cf78c088247c?q=80&w=800&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1503764654157-72d979d9af2f?q=80&w=800&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1455619452474-d2be8b1e70cd?q=80&w=800&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1553621042-f6e147245754?q=80&w=800&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1467003909585-2f8a72700288?q=80&w=800&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1506368249639-73a05d6f6488?q=80&w=800&auto=format&fit=crop",
    "https://images.unsplash.com/photo-1525755662778-989d0524087e?q=80&w=800&auto=format&fit=crop",
]

# [캐싱] 라멘 가게 정보 로드
CACHED_DATA = {}
if os.path.exists(DATA_FILE):
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            CACHED_DATA = json.load(f)
    except:
        CACHED_DATA = {"ramens":[]}

# [캐싱] 가이드 데이터 동적 로드 (날짜순 정렬 및 이미지 배정)
CACHED_GUIDES = {'en': [], 'ko': []}

def load_guides():
    if not os.path.exists(GUIDE_DIR): return
    
    all_raw = []
    files = glob.glob(os.path.join(GUIDE_DIR, '*.md'))
    for fpath in files:
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                post = frontmatter.load(f)
                base_id = os.path.basename(fpath).split('_')[0]
                lang = 'en' if '_en.md' in fpath else 'ko'
                all_raw.append({
                    'base_id': base_id,
                    'lang': lang,
                    'full_id': os.path.basename(fpath).replace('.md', ''),
                    'title': post.get('title', 'Guide'),
                    'summary': post.get('summary', ''),
                    'published': str(post.get('date', '2026-01-01'))
                })
        except: continue

    # 날짜순으로 정렬하여 이미지 인덱스 고정 (최신글이 0번 이미지)
    ref_en = sorted([g for g in all_raw if g['lang'] == 'en'], key=lambda x: x['published'], reverse=True)
    id_to_img = {g['base_id']: UNSPLASH_GUIDE_IMAGES[i % len(UNSPLASH_GUIDE_IMAGES)] for i, g in enumerate(ref_en)}

    new_guides = {'en': [], 'ko': []}
    for g in all_raw:
        new_guides[g['lang']].append({
            'id': g['full_id'],
            'title': g['title'],
            'summary': g['summary'],
            'thumbnail': id_to_img.get(g['base_id'], UNSPLASH_GUIDE_IMAGES[0]),
            'published': g['published']
        })
    
    for l in ['en', 'ko']:
        new_guides[l].sort(key=lambda x: x['published'], reverse=True)
    
    global CACHED_GUIDES
    CACHED_GUIDES = new_guides

load_guides()

# --- Routes ---

@app.route('/')
def index():
    # 메인 페이지 (템플릿에서 가이드 최신 3개만 슬라이싱해서 보여줌)
    return render_template('index.html', guides=CACHED_GUIDES)

@app.route('/api/ramens')
def api_ramens():
    return jsonify(CACHED_DATA)

@app.route('/guide')
def guide_list_all():
    lang = request.args.get('lang', 'en') # URL에서 ?lang= 추출
    return render_template('guide_index.html', guides=CACHED_GUIDES, lang=lang)

@app.route('/guide/<guide_id>')
def guide_detail(guide_id):
    md_path = os.path.join(GUIDE_DIR, f"{guide_id}.md")
    if not os.path.exists(md_path): abort(404)
    
    with open(md_path, 'r', encoding='utf-8') as f:
        raw_text = f.read().strip()

    # Markdown 청소 로직
    raw_text = re.sub(r'^```[a-z]*\n', '', raw_text)
    raw_text = re.sub(r'\n```$', '', raw_text)
    raw_text = re.sub(r'^(##\s*)?yaml\n', '', raw_text, flags=re.IGNORECASE)
    if '---' in raw_text and not raw_text.startswith('---'):
        raw_text = '---' + raw_text.split('---', 1)[1]

    post = frontmatter.loads(raw_text)
    
    # 이미지 동적 매칭 (목록과 동일한 인덱스 계산)
    base_id = guide_id.split('_')[0]
    all_en = []
    for f in glob.glob(os.path.join(GUIDE_DIR, '*_en.md')):
        with open(f, 'r', encoding='utf-8') as tf:
            tp = frontmatter.load(tf)
            all_en.append({'bid': os.path.basename(f).split('_')[0], 'd': str(tp.get('date', '2026-01-01'))})
    
    sorted_ids = [x['bid'] for x in sorted(all_en, key=lambda x: x['d'], reverse=True)]
    try:
        img_idx = sorted_ids.index(base_id) % len(UNSPLASH_GUIDE_IMAGES)
        post['thumbnail'] = UNSPLASH_GUIDE_IMAGES[img_idx]
    except:
        post['thumbnail'] = UNSPLASH_GUIDE_IMAGES[0]

    content_html = markdown.markdown(post.content, extensions=['tables', 'fenced_code'])
    return render_template('detail.html', post=post, content=content_html)

@app.route('/ramen/<ramen_id>')
def ramen_detail(ramen_id):
    md_path = os.path.join(CONTENT_DIR, f"{ramen_id}.md")
    if not os.path.exists(md_path): abort(404)
    
    with open(md_path, 'r', encoding='utf-8') as f:
        raw_text = f.read().strip()

    raw_text = re.sub(r'^```[a-z]*\n', '', raw_text)
    raw_text = re.sub(r'\n```$', '', raw_text)
    raw_text = re.sub(r'^(##\s*)?yaml\n', '', raw_text, flags=re.IGNORECASE)
    if '---' in raw_text and not raw_text.startswith('---'):
        raw_text = '---' + raw_text.split('---', 1)[1]

    post = frontmatter.loads(raw_text)
    if isinstance(post.get('categories'), str):
        post['categories'] = [c.strip() for c in post['categories'].split(',')]

    content_html = markdown.markdown(post.content, extensions=['tables', 'fenced_code'])
    return render_template('detail.html', post=post, content=content_html)

@app.route('/static/images/<path:filename>')
def serve_images(filename):
    import time
    return redirect(f"https://storage.googleapis.com/ok-project-assets/okramen/{filename}?v={int(time.time())}")

@app.route('/robots.txt')
def robots_txt():
    return send_from_directory(STATIC_DIR, 'robots.txt')

@app.route('/sitemap.xml')
def sitemap_xml():
    return send_from_directory(STATIC_DIR, 'sitemap.xml')

@app.route('/about.html')
def about():
    return render_template('about.html')

@app.route('/privacy.html')
def privacy():
    return render_template('privacy.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)