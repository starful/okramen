from flask import Flask, jsonify, send_from_directory, render_template, request
from google.cloud import storage
from flask_compress import Compress
import json
import os
import time

app = Flask(__name__)

Compress(app)

# 설정 변수
BUCKET_NAME = "jinjamap-data" 
FILE_NAME = "shrines_data.json"

# 캐싱 전역 변수 (API 데이터용)
cache_data = None
last_fetch_time = 0
CACHE_DURATION = 3600  # 1시간

# [최적화] 정적 파일(이미지, CSS, JS) 브라우저 캐시 설정 (1년)
@app.after_request
def add_header(response):
    # 요청 파일이 static 폴더에 있다면 캐시 기간을 길게 설정
    if request.path.startswith("/static"):
        # public: 모든 캐시 서버 저장 가능, max-age=31536000 (1년)
        response.headers['Cache-Control'] = 'public, max-age=31536000'
    return response

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/ads.txt')
def ads_txt():
    return send_from_directory(app.template_folder, 'ads.txt')

@app.route('/privacy.html')
def privacy():
    return render_template('privacy.html')

@app.route('/sitemap.xml')
def sitemap_xml():
    return send_from_directory(app.template_folder, 'sitemap.xml', mimetype='application/xml')

@app.route('/api/shrines')
def api_shrines():
    global cache_data, last_fetch_time
    current_time = time.time()

    # 메모리 캐시 확인
    if cache_data and (current_time - last_fetch_time < CACHE_DURATION):
        return jsonify(cache_data)

    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(FILE_NAME)
        
        data_str = blob.download_as_text()
        json_data = json.loads(data_str)
        
        cache_data = json_data
        last_fetch_time = current_time
        return jsonify(json_data)
        
    except Exception as e:
        print(f"❌ 데이터 로드 실패: {e}")
        return jsonify(cache_data if cache_data else {'shrines': []}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)