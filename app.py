# app.py
from flask import Flask, jsonify, send_from_directory, Response
from google.cloud import storage
import json
import os

# 정적 파일 경로 설정
app = Flask(__name__, static_url_path='/assets', static_folder='assets', template_folder='.')

BUCKET_NAME = "jinjamap-data" 
FILE_NAME = "shrines_data.json"

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

# [추가됨] 1. 검색 엔진 로봇 허용 설정 (robots.txt)
@app.route('/robots.txt')
def robots():
    txt = "User-agent: *\nAllow: /"
    return Response(txt, mimetype='text/plain')

# [추가됨] 2. 사이트 구조 맵 (sitemap.xml)
@app.route('/sitemap.xml')
def sitemap():
    # 사이트가 업데이트되는 빈도(changefreq)와 우선순위(priority) 설정
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
    <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
        <url>
            <loc>https://jinjamap.com/</loc>
            <lastmod>2023-10-27</lastmod>
            <changefreq>daily</changefreq>
            <priority>1.0</priority>
        </url>
    </urlset>"""
    return Response(xml_content, mimetype='application/xml')

@app.route('/api/shrines')
def api_shrines():
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(FILE_NAME)
        
        data = blob.download_as_text()
        return jsonify(json.loads(data))
    except Exception as e:
        print(f"데이터 로드 실패: {e}")
        return jsonify([]), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)