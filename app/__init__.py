from flask import Flask, jsonify, render_template, abort
from flask_compress import Compress
import json
import os
import frontmatter
import markdown

app = Flask(__name__)
Compress(app)

# [설정] 데이터 파일 경로
# 주의: 이 경로에 실제 'shrines_data.json' 파일이 존재해야 지도가 나옵니다.
DATA_FILE = os.path.join(app.root_path, 'static', 'json', 'shrines_data.json')
CONTENT_DIR = os.path.join(app.root_path, 'content')

@app.route('/')
def index():
    # HTML에서 비동기(fetch)로 데이터를 가져오므로, 여기선 그냥 템플릿만 렌더링합니다.
    return render_template('index.html')

@app.route('/api/shrines')
def api_shrines():
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return jsonify(data)
        else:
            # 파일이 없을 경우 빈 배열 반환 (에러 방지)
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
    
    # 마크다운 변환 (테이블 확장 기능 포함)
    content_html = markdown.markdown(post.content, extensions=['tables'])
    
    return render_template('detail.html', post=post, content=content_html)

@app.route('/ads.txt')
def ads_txt():
    # 경로가 맞는지 확인 필요 (보통 static 폴더나 root에 둠)
    return app.send_static_file('ads.txt')

@app.route('/sitemap.xml')
def sitemap_xml():
    return app.send_static_file('sitemap.xml')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)