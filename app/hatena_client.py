# hatena_client.py
import os
import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import base64
import hashlib
from datetime import datetime, timezone
import random
import re

# 환경 변수
HATENA_USERNAME = os.getenv('HATENA_USERNAME')
HATENA_BLOG_ID = os.getenv('HATENA_BLOG_ID')
HATENA_API_KEY = os.getenv('HATENA_API_KEY')

def create_wsse_header(username, api_key):
    nonce = hashlib.sha1(str(random.random()).encode()).digest()
    created = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    digest_base = nonce + created.encode() + api_key.encode()
    digest = hashlib.sha1(digest_base).digest()
    return f'UsernameToken Username="{username}", PasswordDigest="{base64.b64encode(digest).decode()}", Nonce="{base64.b64encode(nonce).decode()}", Created="{created}"'

def get_all_posts():
    print("🔎 하테나 블로그 데이터 수집 시작...")
    posts = []
    url = f"https://blog.hatena.ne.jp/{HATENA_USERNAME}/{HATENA_BLOG_ID}/atom/entry"
    
    max_pages = 20 
    current_page = 0
    
    # 기본 썸네일 경로
    DEFAULT_THUMBNAIL = "/static/images/JinjaMapLogo_Horizontal.png"

    while url and current_page < max_pages:
        headers = {'X-WSSE': create_wsse_header(HATENA_USERNAME, HATENA_API_KEY)}
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
        except Exception as e:
            print(f"❌ API 요청 실패: {e}")
            break

        try:
            root = ET.fromstring(response.content)
            ns = {'atom': 'http://www.w3.org/2005/Atom', 'app': 'http://www.w3.org/2007/app'}
        except ET.ParseError:
            break
        
        entries = root.findall('atom:entry', ns)
        
        for entry in entries:
            # 1. 비공개 글 제외
            control = entry.find('app:control', ns)
            if control is not None:
                draft = control.find('app:draft', ns)
                if draft is not None and draft.text == 'yes':
                    continue

            # 2. 기본 정보
            title_tag = entry.find('atom:title', ns)
            title = title_tag.text if title_tag is not None else "No Title"
            
            link_tag = entry.find('atom:link[@rel="alternate"]', ns)
            link = link_tag.get('href') if link_tag is not None else ""
            
            categories = [cat.get('term') for cat in entry.findall('atom:category', ns)]
            
            published_tag = entry.find('atom:published', ns)
            published_date = published_tag.text[:10] if published_tag is not None else ""

            content_tag = entry.find('atom:content', ns)
            content_html = content_tag.text if content_tag is not None else ""
            
            soup = BeautifulSoup(content_html, 'html.parser')
            content_text = soup.get_text(separator=" ")

            # 3. 이미지 추출
            thumbnail = DEFAULT_THUMBNAIL
            
            # (1단계) HTML <img> 태그 검색
            images = soup.find_all('img')
            for img in images:
                src = img.get('src')
                if src and "f.st-hatena.com" in src and "icon" not in src:
                    thumbnail = src
                    break
            
            # (2단계) 하테나 문법 [f:id:...] 파싱
            if thumbnail == DEFAULT_THUMBNAIL:
                match = re.search(r'\[f:id:([^:]+):([0-9]{14})([a-z])?:.*?\]', content_text)
                if match:
                    h_user = match.group(1)
                    h_time = match.group(2)
                    h_type = match.group(3)
                    h_date = h_time[:8]
                    ext = 'png' if h_type == 'p' else 'gif' if h_type == 'g' else 'jpg'
                    thumbnail = f"https://cdn-ak.f.st-hatena.com/images/fotolife/{h_user[0]}/{h_user}/{h_date}/{h_time}.{ext}"

            # 4. 본문 요약
            clean_summary = re.sub(r'\[f:id:[^\]]+\]', '', content_text)
            clean_summary = re.sub(r'\s+', ' ', clean_summary).strip()
            summary = clean_summary[:180] + "..." if len(clean_summary) > 180 else clean_summary

            # 5. [주소 추출 로직 개선]
            address = None
            addr_match = re.search(r'(소재지|주소|위치|Address)\s*[:：]?\s*([^\n\r]+)', content_text)
            if addr_match:
                candidate = addr_match.group(2).strip()
                
                # [수정됨] 마크다운 표 문법(|) 및 볼드체(**) 기호 제거
                candidate = candidate.replace('|', '').replace('*', '').strip()
                
                if len(candidate) < 60 and ('〒' in candidate or any(x in candidate for x in ['도', '시', '구', '현', '町', '県', '市', '区'])):
                    address = candidate
            
            # 주소가 없으면 제목을 기반으로 추측 (마지막 수단)
            if not address:
                clean_title = re.sub(r'\[.*?\]', '', title)
                clean_title = re.split(r'[:：|\-–~]', clean_title)[0].strip()
                clean_title = re.sub(r'\(.*?\)', '', clean_title).strip()
                clean_title = clean_title.replace("를 찾아서", "").replace("방문", "").replace("여행", "").replace("후기", "").strip()
                
                if 1 < len(clean_title) < 30:
                    address = clean_title
                else:
                    continue

            posts.append({
                "title": title,
                "link": link,
                "published": published_date,
                "categories": categories,
                "thumbnail": thumbnail, 
                "address": address, 
                "summary": summary
            })

        next_link = root.find('atom:link[@rel="next"]', ns)
        url = next_link.get('href') if next_link is not None else None
        current_page += 1
        
    return posts