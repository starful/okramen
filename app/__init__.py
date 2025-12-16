from flask import Flask, jsonify, render_template, abort, send_from_directory
from flask_compress import Compress
import json
import os
import frontmatter
import markdown

app = Flask(__name__)
Compress(app)

# [설정] 경로 설정
BASE_DIR = app.root_path
DATA_FILE = os.path.join(BASE_DIR, 'static', 'json', 'shrines_data.json')
CONTENT_DIR = os.path.join(BASE_DIR, 'content')

@app.route('/')
def index():
    return render_template('index.html')

# ==========================================
# [추가] 개인정보처리방침 라우트
# ==========================================
@app.route('/privacy.html')
def privacy():
    return render_template('privacy.html')

@app.route('/api/shrines')
def api_shrines():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return jsonify(data)
        else:
            return jsonify({"shrines": [], "error": "Data file not found"})
    except Exception as e:
        return jsonify({"shrines": [], "error": str(e)})

@app.route('/shrine/<shrine_id>')
def shrine_detail(shrine_id):
    md_path = os.path.join(CONTENT_DIR, f"{shrine_id}.md")
    
    if not os.path.exists(md_path):
        abort(404)
        
    with open(md_path, 'r', encoding='utf-8') as f:
        post = frontmatter.load(f)
    
    content_html = markdown.markdown(post.content, extensions=['tables'])
    
    return render_template('detail.html', post=post, content=content_html)

# [핵심] content/images 이미지 서빙
@app.route('/content/images/<path:filename>')
def serve_content_images(filename):
    images_dir = os.path.join(CONTENT_DIR, 'images')
    return send_from_directory(images_dir, filename)

@app.route('/ads.txt')
def ads_txt():
    return app.send_static_file('ads.txt')

@app.route('/sitemap.xml')
def sitemap_xml():
    return app.send_static_file('sitemap.xml')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)