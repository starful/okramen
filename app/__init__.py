from flask import Flask, jsonify, render_template, abort, send_from_directory, send_file, redirect, request
from flask_compress import Compress
from flask import make_response
import json
import os
import frontmatter
import markdown
import re
import glob
import logging
from datetime import datetime, timezone
from xml.sax.saxutils import escape
import urllib.parse
from werkzeug.utils import safe_join

try:
    # Cloud Run / gunicorn package import path (app.__init__)
    from .ramen_md import loads_ramen_post
except ImportError:
    # Local script execution path (python app/__init__.py)
    from ramen_md import loads_ramen_post

app = Flask(__name__)
Compress(app)
logger = logging.getLogger(__name__)
SITE_URL = os.environ.get("SITE_URL", "https://okramen.net").rstrip("/")

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
    "https://images.unsplash.com/photo-1591814441348-73546747d96a?q=80&w=800&auto=format&fit=crop"
]

# 1. 라멘 가게 정보 캐싱
CACHED_DATA = {}
if os.path.exists(DATA_FILE):
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            CACHED_DATA = json.load(f)
    except (OSError, json.JSONDecodeError) as exc:
        logger.exception("Failed to load cached ramen data: %s", exc)
        CACHED_DATA = {"ramens":[]}

# 2. 가이드 데이터 캐싱 (날짜순 정렬 및 이미지 배정)
CACHED_GUIDES = {'en': [], 'ko': []}
def load_guides():
    if not os.path.exists(GUIDE_DIR):
        logger.warning("Guide directory does not exist: %s", GUIDE_DIR)
        return
    
    all_raw = []
    files = glob.glob(os.path.join(GUIDE_DIR, '*.md'))
    for fpath in files:
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                post = frontmatter.load(f)
                base_id = os.path.basename(fpath).rsplit('_', 1)[0]
                lang = 'en' if '_en.md' in fpath else 'ko'
                all_raw.append({
                    'base_id': base_id,
                    'lang': lang,
                    'full_id': os.path.basename(fpath).replace('.md', ''),
                    'title': post.get('title', 'Guide'),
                    'summary': post.get('summary', ''),
                    'published': str(post.get('date', '2026-01-01'))
                })
        except (OSError, ValueError) as exc:
            logger.warning("Failed to parse guide file %s: %s", fpath, exc)
            continue

    # 날짜순 정렬 기반 이미지 인덱싱
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


@app.before_request
def seo_url_normalization():
    if request.method != "GET":
        return None
    p = request.path
    if p.startswith("/static/") or p.startswith("/api/"):
        return None
    if request.headers.get("X-Forwarded-Proto", "").lower() == "http":
        return redirect(request.url.replace("http://", "https://", 1), code=301)
    args = request.args
    keys = set(args.keys())
    if p == "/guide" and keys == {"lang"} and args.get("lang") == "en":
        return redirect("/guide", code=301)
    return None


def _safe_iso_date(value, fallback):
    """Normalize date-like values to YYYY-MM-DD for sitemap lastmod."""
    if not value:
        return fallback
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y.%m.%d"):
        try:
            return datetime.strptime(text[:10], fmt).date().isoformat()
        except ValueError:
            continue
    return fallback


def _file_lastmod(path, fallback):
    if not os.path.exists(path):
        return fallback
    ts = os.path.getmtime(path)
    return datetime.fromtimestamp(ts, tz=timezone.utc).date().isoformat()


def _truncate_text(value, max_len):
    text = " ".join(str(value or "").split())
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


def _attach_seo_fields(post, suffix):
    """SERP-friendly title/description: scannable hooks + CTA without changing on-page H1."""
    title = str(post.get("title", "")).strip()
    summary = str(post.get("summary", "")).strip()
    lang = str(post.get("lang", "en") or "en").lower()
    is_ramen_page = "Japan Guide" in suffix

    if lang == "ko":
        hook = "지도·영업·추천 메뉴" if is_ramen_page else "핵심만 정리한 가이드"
        tail = (
            " OKRamen 지도에서 위치·영업·추천 메뉴를 바로 확인하세요."
            if is_ramen_page
            else " OKRamen에서 팁과 링크만 골라 읽고 일정에 넣으세요."
        )
        if title:
            post["seo_title"] = _truncate_text(f"{title} | {hook} | OKRamen", 60)
        else:
            post["seo_title"] = _truncate_text(suffix, 60)
    else:
        hook = "map, hours & what to order" if is_ramen_page else "plain-English tips"
        tail = (
            " Open OKRamen for the map, hours, and what to order before you go."
            if is_ramen_page
            else " Skim OKRamen for maps, ordering tips, and links before your trip."
        )
        if title:
            post["seo_title"] = _truncate_text(f"{title} | {hook} | OKRamen", 60)
        else:
            post["seo_title"] = _truncate_text(suffix, 60)

    core = (summary or title).strip()
    post["seo_description"] = _truncate_text(f"{core}{tail}", 155)
    return post


def build_maps_search_url(lat: float, lng: float, label: str = "") -> str:
    """Open Google Maps search near coordinates (not an official place permalink)."""
    label = (label or "").strip()
    if label:
        q = f"{label} @ {lat},{lng}"
    else:
        q = f"{lat},{lng}"
    return "https://www.google.com/maps/search/?api=1&query=" + urllib.parse.quote(q, safe="")


def _detail_trust_copy(lang: str) -> tuple[str, str]:
    """(editorial_note, illustration_note) — aligned with okcafejp item_generator."""
    if str(lang or "en").lower() == "ko":
        return (
            "본 글은 여행 계획용 에디토리얼 콘텐츠입니다. 매장 공식 페이지가 아니므로 영업 시간·위치·메뉴·가격은 방문 전 지도 링크 또는 현지에서 반드시 확인해 주세요.",
            "상단 이미지는 이해를 돕기 위한 AI 생성 예시 이미지이며, 실제 매장의 인테리어·메뉴와 다를 수 있습니다.",
        )
    return (
        "This page is editorial trip-planning content, not the venue's official site. Always confirm hours, access, menus, and prices on site or via Maps before visiting.",
        "The lead image is an AI-generated illustration and may not show this venue's real interior or offerings.",
    )


def _enrich_ramen_detail_post(post) -> None:
    """Ensure maps_url and transparency notes (okcafe-style) without requiring frontmatter on every file."""
    lang = str(post.get("lang") or "en")
    if not post.get("editorial_note") or not post.get("illustration_note"):
        ed, ill = _detail_trust_copy(lang)
        if not post.get("editorial_note"):
            post["editorial_note"] = ed
        if not post.get("illustration_note"):
            post["illustration_note"] = ill
    if post.get("maps_url"):
        return
    try:
        lat = float(post.get("lat") or 0)
        lng = float(post.get("lng") or 0)
    except (TypeError, ValueError):
        lat, lng = 0.0, 0.0
    if lat == 0.0 and lng == 0.0:
        return
    label = str(post.get("title") or "").strip()
    post["maps_url"] = build_maps_search_url(lat, lng, label)


@app.context_processor
def inject_site_url():
    return {"site_url": SITE_URL}

# --- Routes ---

@app.route('/')
def index():
    maps_api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "").strip()
    return render_template('index.html', guides=CACHED_GUIDES, maps_api_key=maps_api_key)

@app.route('/api/ramens')
def api_ramens():
    response = jsonify(CACHED_DATA)
    # Prevent raw API endpoints from being indexed as content pages.
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response

@app.route('/guide')
def guide_list_all():
    lang = request.args.get('lang', 'en')
    return render_template('guide_index.html', guides=CACHED_GUIDES, lang=lang)

@app.route('/guide/<guide_id>')
def guide_detail(guide_id):
    md_path = os.path.join(GUIDE_DIR, f"{guide_id}.md")
    if not os.path.exists(md_path):
        return redirect('/guide')
        
    with open(md_path, 'r', encoding='utf-8') as f:
        raw_text = f.read().strip()

    # Markdown 청소
    raw_text = re.sub(r'^```[a-z]*\n', '', raw_text)
    raw_text = re.sub(r'\n```$', '', raw_text)
    raw_text = re.sub(r'^(##\s*)?yaml\n', '', raw_text, flags=re.IGNORECASE)
    if '---' in raw_text and not raw_text.startswith('---'):
        raw_text = '---' + raw_text.split('---', 1)[1]

    post = frontmatter.loads(raw_text)
    
    # 💡 [핵심] 언어 전환 버튼을 위해 id를 강제 주입
    post['id'] = guide_id 
    post = _attach_seo_fields(post, "OKRamen Guide")
    
    # 이미지 동적 할당
    base_id = guide_id.rsplit('_', 1)[0]
    all_en = []
    for f in glob.glob(os.path.join(GUIDE_DIR, '*_en.md')):
        with open(f, 'r', encoding='utf-8') as tf:
            tp = frontmatter.load(tf)
            all_en.append({'bid': os.path.basename(f).rsplit('_', 1)[0], 'd': str(tp.get('date', '2026-01-01'))})
    
    sorted_ids = [x['bid'] for x in sorted(all_en, key=lambda x: x['d'], reverse=True)]
    try:
        img_idx = sorted_ids.index(base_id) % len(UNSPLASH_GUIDE_IMAGES)
        post['thumbnail'] = UNSPLASH_GUIDE_IMAGES[img_idx]
    except ValueError:
        post['thumbnail'] = UNSPLASH_GUIDE_IMAGES[0]

    content_html = markdown.markdown(post.content, extensions=['tables', 'fenced_code'])
    return render_template('guide_detail.html', post=post, content=content_html)

@app.route('/ramen/<ramen_id>')
def ramen_detail(ramen_id):
    md_path = os.path.join(CONTENT_DIR, f"{ramen_id}.md")
    if not os.path.exists(md_path): abort(404)
    
    with open(md_path, 'r', encoding='utf-8') as f:
        raw_text = f.read()

    post = loads_ramen_post(raw_text)
    
    # 💡 [핵심] 언어 전환 버튼을 위해 id를 강제 주입
    post['id'] = ramen_id 
    post = _attach_seo_fields(post, "OKRamen Japan Guide")

    cats = post.get('categories')
    if cats is None:
        post['categories'] = []
    elif isinstance(cats, str):
        post['categories'] = [c.strip() for c in cats.split(',')]

    _enrich_ramen_detail_post(post)

    content_html = markdown.markdown(post.content, extensions=['tables', 'fenced_code'])
    return render_template('detail.html', post=post, content=content_html)

@app.route('/static/images/<path:filename>')
def serve_images(filename):
    import time

    images_root = os.path.join(STATIC_DIR, 'images')
    try:
        local_path = safe_join(images_root, filename)
    except ValueError:
        abort(404)
    if local_path and os.path.isfile(local_path):
        return send_file(local_path)
    return redirect(f"https://storage.googleapis.com/ok-project-assets/okramen/{filename}?v={int(time.time())}")

@app.route('/robots.txt')
def robots_txt():
    return send_from_directory(STATIC_DIR, 'robots.txt')

@app.route('/sitemap.xml')
def sitemap_xml():
    """라멘/가이드 URL을 반영한 동적 사이트맵 생성."""
    host = SITE_URL
    pages = []
    now_iso = datetime.now(timezone.utc).date().isoformat()
    about_lastmod = _file_lastmod(os.path.join(BASE_DIR, "templates", "about.html"), now_iso)
    privacy_lastmod = _file_lastmod(os.path.join(BASE_DIR, "templates", "privacy.html"), now_iso)

    # 메인 및 정적 페이지
    pages.append({"loc": f"{host}/", "priority": "1.0", "changefreq": "daily", "lastmod": now_iso})
    pages.append({"loc": f"{host}/guide", "priority": "0.8", "changefreq": "daily", "lastmod": now_iso})
    pages.append({"loc": f"{host}/guide?lang=ko", "priority": "0.6", "changefreq": "daily", "lastmod": now_iso})
    pages.append({"loc": f"{host}/about.html", "priority": "0.4", "changefreq": "monthly", "lastmod": about_lastmod})
    pages.append({"loc": f"{host}/privacy.html", "priority": "0.3", "changefreq": "yearly", "lastmod": privacy_lastmod})

    # 라멘 가게 페이지 (CACHED_DATA 기준)
    if 'ramens' in CACHED_DATA:
        for ramen in CACHED_DATA['ramens']:
            link = ramen.get('link')
            if not link:
                continue
            ramen_lastmod = _safe_iso_date(ramen.get("published"), now_iso)
            pages.append({"loc": f"{host}{link}", "priority": "0.7", "changefreq": "weekly", "lastmod": ramen_lastmod})

    # 가이드 페이지 (CACHED_GUIDES 기준)
    for lang in ['en', 'ko']:
        for guide in CACHED_GUIDES.get(lang, []):
            guide_id = guide.get('id')
            if not guide_id:
                continue
            guide_lastmod = _safe_iso_date(guide.get("published"), now_iso)
            pages.append({"loc": f"{host}/guide/{guide_id}", "priority": "0.9", "changefreq": "weekly", "lastmod": guide_lastmod})

    lines = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for page in pages:
        lines.extend([
            "  <url>",
            f"    <loc>{escape(page['loc'])}</loc>",
            f"    <lastmod>{page['lastmod']}</lastmod>",
            f"    <changefreq>{page['changefreq']}</changefreq>",
            f"    <priority>{page['priority']}</priority>",
            "  </url>",
        ])
    lines.append("</urlset>")
    response = make_response("\n".join(lines))
    response.headers["Content-Type"] = "application/xml"
    return response

@app.route('/about.html')
def about():
    return render_template('about.html')

@app.route('/privacy.html')
def privacy():
    return render_template('privacy.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)