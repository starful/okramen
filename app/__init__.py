from flask import Flask, jsonify, render_template, abort, send_from_directory, send_file, redirect, request, Response
from flask_compress import Compress
from flask import make_response
import json
import os
import copy
import frontmatter
import markdown
import re
import glob
import logging
import io
import urllib.request
from datetime import datetime, timezone
from xml.sax.saxutils import escape
import urllib.parse

try:
    from .content_new import enrich_item
except ImportError:
    from content_new import enrich_item
from werkzeug.utils import safe_join

try:
    # Cloud Run / gunicorn package import path (app.__init__)
    from .ramen_md import loads_ramen_post
    from .ramen_practical import apply_practical_fields, slug_to_shop_name
except ImportError:
    # Local script execution path (python app/__init__.py)
    from ramen_md import loads_ramen_post
    from ramen_practical import apply_practical_fields, slug_to_shop_name

app = Flask(__name__)
Compress(app)

try:
    from .reactions import reactions_bp
except ImportError:
    from reactions import reactions_bp

app.register_blueprint(reactions_bp)

logger = logging.getLogger(__name__)
SITE_URL = os.environ.get("SITE_URL", "https://okramen.net").rstrip("/")
GCS_ASSET_PREFIX = "okramen"


def _gcs_image_url(filename: str) -> str:
    return f"https://storage.googleapis.com/ok-project-assets/{GCS_ASSET_PREFIX}/{filename}"


def _thumbnail_cache_v(published_or_date: str | None) -> str:
    v = str(published_or_date or "").strip()[:10]
    return v if len(v) >= 8 else ""


def _thumbnail_with_v(url: str, cache_v: str | None = None) -> str:
    if not url:
        return url
    v = _thumbnail_cache_v(cache_v)
    base = url.split("?", 1)[0]
    return f"{base}?v={v}" if v else base


def _public_ramen(row: dict) -> dict:
    out = copy.deepcopy(row)
    out["thumbnail"] = _thumbnail_with_v(out.get("thumbnail", ""), out.get("published"))
    return out


def _social_image_url(base_id: str) -> str:
    safe = re.sub(r"[^a-z0-9_-]", "", base_id.lower())
    return f"{SITE_URL}/social/{safe}.jpg"


def _og_image_context(base_id: str) -> dict:
    og_image_abs = _social_image_url(base_id)
    return {
        "og_image_abs": og_image_abs,
        "og_image_width": 1200,
        "og_image_height": 630,
    }


def _card_path(ramen_id: str) -> str:
    return f"/card/{ramen_id}"


def _jpeg_bytes(img) -> bytes:
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=78, optimize=True, progressive=True)
    return buf.getvalue()


def _linkedin_inspector_url(page_url: str) -> str:
    return f"https://www.linkedin.com/post-inspector/inspect/{urllib.parse.quote(page_url, safe='')}"


def _share_context(slug: str, title: str, lang: str, page_path: str, base_id: str = "") -> dict:
    share_url = f"{SITE_URL}{page_path}"
    share_url_x = f"{SITE_URL}{_card_path(slug)}"
    if lang == "ko":
        share_tweet = f"{title} — OKRamen"
    else:
        share_tweet = f"{title} — Japan ramen guide on OKRamen"
    return {
        "share_id": slug,
        "share_url": share_url,
        "share_url_x": share_url_x,
        "share_tweet": share_tweet,
        "share_lang": lang if lang in ("en", "ko") else "en",
        "og_page_url": share_url,
        "linkedin_inspector_url": _linkedin_inspector_url(share_url),
    }

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

# 1. 라멘 가게 정보 캐싱 (JSON mtime 변경 시 자동 재로드)
CACHED_DATA = {"ramens": []}
_CACHE_MTIME: float = 0.0


def _ensure_ramen_cache() -> None:
    global CACHED_DATA, _CACHE_MTIME
    if not os.path.exists(DATA_FILE):
        return
    try:
        mtime = os.path.getmtime(DATA_FILE)
    except OSError:
        return
    if mtime <= _CACHE_MTIME:
        return
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            CACHED_DATA = json.load(f)
        _CACHE_MTIME = mtime
    except (OSError, json.JSONDecodeError) as exc:
        logger.exception("Failed to load cached ramen data: %s", exc)
        CACHED_DATA = {"ramens": []}


_ensure_ramen_cache()

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
        new_guides[g['lang']].append(enrich_item({
            'id': g['full_id'],
            'title': g['title'],
            'summary': g['summary'],
            'thumbnail': id_to_img.get(g['base_id'], UNSPLASH_GUIDE_IMAGES[0]),
            'published': g['published']
        }))
    
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


# GSC priority shops: internal linking + homepage spotlight (P1/P4)
FEATURED_RAMEN_IDS = [
    "honke_daiichi-asahi_en",
    "menya_musashi_shinjuku_en",
    "ramen_shingen_en",
    "bankara_ramen_en",
    "muteppou_kyoto_en",
    "fuunji_shinjuku_en",
]

GUIDE_RELATED_SHOPS = {
    "regional_ramen_en": [
        "honke_daiichi-asahi_en",
        "ramen_shingen_en",
        "kitakata_ramen_bannai_en",
        "menya_musashi_shinjuku_en",
    ],
    "regional_ramen_ko": [
        "honke_daiichi-asahi_ko",
        "ramen_shingen_ko",
        "kitakata_ramen_bannai_ko",
    ],
    "tonkotsu_intensity_en": [
        "muteppou_kyoto_en",
        "menya_musashi_shinjuku_en",
        "bankara_ramen_en",
    ],
    "tonkotsu_intensity_ko": ["muteppou_kyoto_ko", "bankara_ramen_ko"],
    "tsukemen_art_en": ["fuunji_shinjuku_en"],
    "tsukemen_art_ko": ["fuunji_shinjuku_ko"],
    "ramen_etiquette_en": ["fuunji_shinjuku_en", "menya_musashi_shinjuku_en"],
    "chashu_styles_en": ["honke_daiichi-asahi_en", "bankara_ramen_en"],
}


def _ramen_index_by_id():
    _ensure_ramen_cache()
    return {r["id"]: r for r in CACHED_DATA.get("ramens", []) if r.get("id")}


def _ramen_cards(ramen_ids):
    """Lightweight card dicts for templates (title truncated for UI)."""
    by_id = _ramen_index_by_id()
    cards = []
    for rid in ramen_ids:
        r = by_id.get(rid)
        if not r:
            continue
        title = str(r.get("title") or rid)
        label = slug_to_shop_name(r["id"])
        cards.append(
            enrich_item(
                {
                    "id": r["id"],
                    "link": r.get("link") or f"/ramen/{r['id']}",
                    "title": title,
                    "short_title": _truncate_text(label or title, 72),
                    "address": r.get("address", ""),
                    "thumbnail": _thumbnail_with_v(r.get("thumbnail", ""), r.get("published")),
                    "published": r.get("published", ""),
                }
            )
        )
    return cards


def _crawl_ramen_links(limit=60, lang="en"):
    """SSR link list for crawlers (homepage); priority IDs first, then newest EN."""
    by_id = _ramen_index_by_id()
    ordered_ids = []
    for rid in FEATURED_RAMEN_IDS:
        r = by_id.get(rid)
        if r and r.get("lang") == lang:
            ordered_ids.append(rid)
    newest = sorted(
        [r for r in CACHED_DATA.get("ramens", []) if r.get("lang") == lang and r.get("link")],
        key=lambda x: str(x.get("published", "")),
        reverse=True,
    )
    for r in newest:
        if r["id"] not in ordered_ids:
            ordered_ids.append(r["id"])
    links = []
    for rid in ordered_ids[:limit]:
        r = by_id[rid]
        links.append(
            {
                "link": r.get("link"),
                "label": _truncate_text(slug_to_shop_name(rid), 55),
            }
        )
    return links


def _related_ramens_for_post(post, limit=4):
    """Same-language shops in the same region (address prefix) for detail cross-links."""
    lang = str(post.get("lang") or "en")
    pid = str(post.get("id") or "")
    addr = str(post.get("address") or "")
    region = addr.split(",")[0].strip() if addr else ""
    if not region:
        return []
    matches = []
    for r in CACHED_DATA.get("ramens", []):
        if r.get("lang") != lang or r.get("id") == pid:
            continue
        if region not in str(r.get("address") or ""):
            continue
        matches.append(r)
    matches.sort(key=lambda x: str(x.get("published", "")), reverse=True)
    return _ramen_cards([r["id"] for r in matches[:limit]])


def _truncate_text(value, max_len):
    text = " ".join(str(value or "").split())
    if len(text) <= max_len:
        return text
    return text[: max_len - 1].rstrip() + "…"


def _attach_seo_fields(post, suffix):
    """SERP-friendly title/description: scannable hooks + CTA without changing on-page H1.

    Per-file overrides: if the markdown frontmatter already declares ``seo_title`` or
    ``seo_description`` we keep those verbatim. This lets us tune SERP snippets for
    individual high-impression / low-CTR pages without affecting pages that already
    perform well in Search Console.
    """
    title = str(post.get("title", "")).strip()
    summary = str(post.get("summary", "")).strip()
    lang = str(post.get("lang", "en") or "en").lower()
    is_ramen_page = "Japan Guide" in suffix

    override_title = str(post.get("seo_title", "") or "").strip()
    override_desc = str(post.get("seo_description", "") or "").strip()
    shop_name = str(post.get("shop_name") or "").strip()
    region = ""
    if is_ramen_page and post.get("address"):
        region = str(post.get("address", "")).split(",")[0].strip()

    if lang == "ko":
        hook = "지도·영업·추천 메뉴" if is_ramen_page else "핵심만 정리한 가이드"
        tail = (
            " OKRamen 지도에서 위치·영업·추천 메뉴를 바로 확인하세요."
            if is_ramen_page
            else " OKRamen에서 팁과 링크만 골라 읽고 일정에 넣으세요."
        )
        if is_ramen_page and shop_name and not override_title:
            default_title = _truncate_text(f"{shop_name} | {region} 라멘 가이드 | OKRamen", 60)
        else:
            default_title = (
                _truncate_text(f"{title} | {hook} | OKRamen", 60)
                if title
                else _truncate_text(suffix, 60)
            )
    else:
        hook = "map, hours & what to order" if is_ramen_page else "plain-English tips"
        tail = (
            " Open OKRamen for the map, hours, and what to order before you go."
            if is_ramen_page
            else " Skim OKRamen for maps, ordering tips, and links before your trip."
        )
        if is_ramen_page and shop_name and not override_title:
            default_title = _truncate_text(f"{shop_name} | {region} ramen guide | OKRamen", 60)
        else:
            default_title = (
                _truncate_text(f"{title} | {hook} | OKRamen", 60)
                if title
                else _truncate_text(suffix, 60)
            )

    post["seo_title"] = _truncate_text(override_title, 60) if override_title else default_title

    if override_desc:
        post["seo_description"] = _truncate_text(override_desc, 160)
    elif is_ramen_page and post.get("one_liner"):
        post["seo_description"] = _truncate_text(
            f"{post['one_liner']}{tail if lang == 'en' else ' OKRamen 지도에서 위치·영업·추천 메뉴를 확인하세요.'}",
            155,
        )
    else:
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
    label = str(post.get("shop_name") or post.get("title") or "").strip()
    post["maps_url"] = build_maps_search_url(lat, lng, label)


try:
    from .family_sites import cross_links_for, inject_family_context
except ImportError:
    from family_sites import cross_links_for, inject_family_context

FAMILY_SITE_ID = "okramen"


@app.context_processor
def inject_site_url():
    lang = request.args.get("lang", "en") if request else "en"
    return {
        "site_url": SITE_URL,
        **inject_family_context(FAMILY_SITE_ID, lang),
    }

# --- Routes ---

@app.route('/')
def index():
    maps_api_key = os.environ.get("GOOGLE_MAPS_API_KEY", "").strip()
    return render_template(
        "index.html",
        guides=CACHED_GUIDES,
        maps_api_key=maps_api_key,
        featured_ramens=_ramen_cards(FEATURED_RAMEN_IDS),
        crawl_ramen_links=_crawl_ramen_links(limit=60, lang="en"),
    )

@app.route('/api/ramens')
def api_ramens():
    _ensure_ramen_cache()
    payload = copy.deepcopy(CACHED_DATA)
    payload["ramens"] = [_public_ramen(r) for r in payload.get("ramens", [])]
    response = jsonify(payload)
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
    related_shops = _ramen_cards(GUIDE_RELATED_SHOPS.get(guide_id, []))
    share_ctx = _share_context(guide_id, post.get("title", "OKRamen Guide"), post.get("lang", "en"), f"/guide/{guide_id}")
    lang = post.get("lang", "en")
    return render_template(
        "guide_detail.html",
        post=post,
        content=content_html,
        related_shops=related_shops,
        cross_site_links=cross_links_for(FAMILY_SITE_ID, lang),
        **inject_family_context(FAMILY_SITE_ID, lang),
        **share_ctx,
    )

@app.route('/ramen/<ramen_id>')
def ramen_detail(ramen_id):
    md_path = os.path.join(CONTENT_DIR, f"{ramen_id}.md")
    if not os.path.exists(md_path): abort(404)
    
    with open(md_path, 'r', encoding='utf-8') as f:
        raw_text = f.read()

    post = loads_ramen_post(raw_text)
    
    # 💡 [핵심] 언어 전환 버튼을 위해 id를 강제 주입
    post['id'] = ramen_id

    cats = post.get('categories')
    if cats is None:
        post['categories'] = []
    elif isinstance(cats, str):
        post['categories'] = [c.strip() for c in cats.split(',')]

    apply_practical_fields(post, ramen_id)
    post = _attach_seo_fields(post, "OKRamen Japan Guide")
    _enrich_ramen_detail_post(post)

    base_id = ramen_id.rsplit('_', 1)[0]
    cache_v = _thumbnail_cache_v(post.get("date") or post.get("published"))
    thumb = post.get("thumbnail") or f"/static/images/{base_id}.jpg"
    post["thumbnail"] = _thumbnail_with_v(thumb, cache_v)
    content_html = markdown.markdown(post.content, extensions=['tables', 'fenced_code'])
    related_ramens = _related_ramens_for_post(post, limit=4)
    share_ctx = _share_context(
        ramen_id,
        post.get("seo_title") or post.get("shop_name") or post.get("title", "OKRamen"),
        post.get("lang", "en"),
        f"/ramen/{ramen_id}",
        base_id=base_id,
    )
    lang = post.get("lang", "en")
    return render_template(
        "detail.html",
        post=post,
        content=content_html,
        related_ramens=related_ramens,
        cross_site_links=cross_links_for(
            FAMILY_SITE_ID, lang, address=post.get("address")
        ),
        **inject_family_context(FAMILY_SITE_ID, lang),
        **_og_image_context(base_id),
        **share_ctx,
    )


@app.route('/card/<ramen_id>')
def ramen_social_card(ramen_id):
    """Lightweight share landing page for X/OG crawlers."""
    md_path = os.path.join(CONTENT_DIR, f"{ramen_id}.md")
    if not os.path.exists(md_path):
        abort(404)

    with open(md_path, 'r', encoding='utf-8') as f:
        post = loads_ramen_post(f.read())

    base_id = ramen_id.rsplit('_', 1)[0]
    lang = post.get('lang', 'en')
    apply_practical_fields(post, ramen_id)
    post = _attach_seo_fields(post, "OKRamen Japan Guide")

    page_path = f"/ramen/{ramen_id}"

    return render_template(
        'social_card.html',
        lang=lang,
        title=post.get('shop_name') or post.get('title', 'OKRamen'),
        seo_title=post.get('seo_title', 'OKRamen'),
        seo_desc=post.get('seo_description', post.get('summary', '')),
        page_url=f"{SITE_URL}{page_path}",
        card_url=f"{SITE_URL}{_card_path(ramen_id)}",
        **_og_image_context(base_id),
    )


@app.route('/social/<slug>.jpg')
def social_image(slug):
    """Serve ramen thumbnail on-site for OG/Twitter (1200×630 JPEG, no redirect)."""
    safe = re.sub(r"[^a-z0-9_-]", "", slug.lower())
    if not safe:
        abort(404)
    gcs_url = _gcs_image_url(f"{safe}.jpg")
    try:
        with urllib.request.urlopen(gcs_url, timeout=15) as resp:
            raw = resp.read()
            if not raw:
                abort(404)
    except Exception:
        abort(404)

    try:
        from PIL import Image, ImageOps

        img = Image.open(io.BytesIO(raw)).convert("RGB")
        data = _jpeg_bytes(ImageOps.fit(img, (1200, 630), Image.Resampling.LANCZOS))
    except Exception:
        data = raw

    return Response(
        data,
        mimetype="image/jpeg",
        headers={"Cache-Control": "public, max-age=86400"},
    )

@app.route('/static/images/<path:filename>')
def serve_images(filename):
    """이미지는 GCS가 기준 — okadmin 업로드 즉시 반영."""
    images_root = os.path.join(STATIC_DIR, 'images')
    if any(x in filename for x in ['favicon', 'apple-touch']):
        try:
            local_path = safe_join(images_root, filename)
        except ValueError:
            abort(404)
        if local_path and os.path.isfile(local_path):
            return send_file(local_path)
    url = f"https://storage.googleapis.com/ok-project-assets/okramen/{filename}"
    if request.query_string:
        url = f"{url}?{request.query_string.decode()}"
    return redirect(url, code=302)

@app.route('/robots.txt')
def robots_txt():
    return send_from_directory(STATIC_DIR, 'robots.txt')

@app.route('/ads.txt')
def ads_txt():
    return send_from_directory(STATIC_DIR, 'ads.txt', mimetype='text/plain')

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

    # 라멘 가게 페이지 (CACHED_DATA 기준; lastmod = md file mtime when present)
    if 'ramens' in CACHED_DATA:
        for ramen in CACHED_DATA['ramens']:
            link = ramen.get('link')
            if not link:
                continue
            ramen_id = ramen.get("id") or ""
            md_path = os.path.join(CONTENT_DIR, f"{ramen_id}.md") if ramen_id else ""
            fallback = _safe_iso_date(ramen.get("published"), now_iso)
            ramen_lastmod = _file_lastmod(md_path, fallback) if md_path else fallback
            priority = "0.85" if ramen_id in FEATURED_RAMEN_IDS else "0.7"
            pages.append({
                "loc": f"{host}{link}",
                "priority": priority,
                "changefreq": "weekly",
                "lastmod": ramen_lastmod,
            })

    # 가이드 페이지 (CACHED_GUIDES 기준)
    for lang in ['en', 'ko']:
        for guide in CACHED_GUIDES.get(lang, []):
            guide_id = guide.get('id')
            if not guide_id:
                continue
            md_path = os.path.join(GUIDE_DIR, f"{guide_id}.md")
            fallback = _safe_iso_date(guide.get("published"), now_iso)
            guide_lastmod = _file_lastmod(md_path, fallback)
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