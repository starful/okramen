# OK Ramen SPEC

개발 사양. 비즈니스 요건(목적·독자·하지 말 것·우선순위)은 기획서
`Google Drive AI/okramen/okramen 기획서.html`, 화면은 Claude Design 캔버스
「okramen 화면 설계」(https://claude.ai/artifact/MENBaJSYNrQEM8DtDqSP5M).

- 운영: https://okramen.net · 저장소 `starful/okramen` · 로컬 `/opt/work/okramen`
- 런타임: Python 3.10 · Flask + Gunicorn · Jinja · Vanilla JS
- 데이터베이스 없음: 마크다운이 원본, 빌드 때 JSON으로 컴파일

## 1. 폴더 구조

```text
app/
  __init__.py            Flask 앱 · 라우트 · 시작 시 캐시 · sitemap · visitlog 등록
  content/               가게 마크다운 <id>_en.md / <id>_ko.md
  content/guides/        가이드 마크다운 <id>_en.md / <id>_ko.md
  templates/             index · detail · guide_index · guide_detail · compare · about · privacy · contact · social_card
  templates/partials/    share_bar · a8_banners(제휴 박스) · cross_site_links · family_sites · reactions · compare_bar …
  static/css/style.css
  static/js/             main.js(지도·목록·필터) · compare.js · share.js · article.js · visit_track.js
  static/json/ramen_data.json   build_data.py 출력 (커밋됨)
  static/images/         가게·가이드 이미지 (원본은 GCS)
  ramen_service.py       가게 로드·카드·관련 가게
  guide_service.py       가이드 로드·렌더
  ramen_md.py            가게 마크다운 파서
  ramen_practical.py     Quick visit guide 필드(스타일 라벨 en/ko, 주문·추천 대상)
  seo_service.py         seo_title(60자) · seo_description(155–160자) 계산
  legacy_redirects.py    예전 URL → 301
  agoda_partners.py      Agoda Partners CID 링크 (좌표 → 가까운 도시)
  a8_affiliate.py        제휴 박스 컨텍스트 (이름만 a8, 내용은 Agoda)
  amazon_affiliate.py    Amazon JP 검색 링크 (kind: shop · guide · instant)
  family_sites.py        OK 시리즈 상호 링크 레지스트리
  reactions.py           「도움이 됐나요」 (Firestore)
script/
  build_data.py          content/*.md → static/json/ramen_data.json
  build_sitemap.py       static/sitemap.xml
  ramen_generator.py     가게 페이지 생성 (Gemini 2.5 Flash, Google Places)
  guide_generator.py     가이드 생성 (Gemini 2.5 Flash)
  content_quality.py     품질 게이트 (아래 4장)
  fetch_images.py · generate_images.py(Vertex) · optimize_images.py
  fill_missing_pairs.py  en/ko 짝 채우기
  enrich_ramen_frontmatter.py · rewrite_ramen_practical.py · rewrite_ai_gsc.py · shrink_gsc.py · gsc_cleanup_plan.py
  csv/README.md          토픽은 okadmin data/topic_banks/okramen/ (여기 추가 금지)
visitkit/                HQ 이용자 보기용 익명 방문 로그 패키지
tests/                   pytest (app · build_data · content_quality · legacy_redirects · seo)
Dockerfile · cloudbuild.yaml   로컬 전용 (.gitignore, 저장소에 없음)
deploy.sh
```

실행 데이터 `data/visitlog.sqlite3` 등은 커밋하지 않는다 (`data/a8/` 제휴 CSV만 커밋되어 있음).

## 2. 라우트

| 경로 | 내용 |
|---|---|
| `/` | 지도 홈. `GOOGLE_MAPS_API_KEY` 필요. 편집자 픽 `FEATURED_RAMEN_IDS`, 크롤 링크 60개 |
| `/api/ramens` | 지도용 JSON (`X-Robots-Tag: noindex, nofollow`) |
| `/ramen/<id>` | 가게 상세. 없으면 `resolve_ramen_redirect` 301 |
| `/guide` · `/guide/<id>` | 가이드 목록·상세. 관련 가게 `GUIDE_RELATED_SHOPS` |
| `/compare?ids=a,b,c&lang=` | 최대 3곳 비교 |
| `/card/<id>` · `/social/<slug>.jpg` | X 공유 카드 · OG 이미지 |
| `/sitemap.xml` · `/robots.txt` · `/ads.txt` | SEO · AdSense |
| `/about.html` · `/privacy.html` · `/contact` | 정책 페이지 |
| `/events` · `/hq/api/users` | visitkit (6장) |

언어: 파일 id 끝 `_en` / `_ko`. 목록 페이지는 `?lang=ko`.

## 3. 글 파일 형식 (front matter)

### 3-1. 가게 `app/content/<slug>_<lang>.md`

```yaml
---
shop_name: Afuri Harajuku
title: Afuri Harajuku — 3-63-1 Sendagaya Shio ramen guide
lang: en                     # en | ko
date: '2026-03-28'
address: 3-63-1 Sendagaya, Shibuya City, Tokyo 151-0051, Japan
lat: 35.6715
lng: 139.7032
categories: [Shio, Premium]  # 아래 태그만
thumbnail: /static/images/afuri_harajuku.jpg
summary: "..."               # 카드·메타 설명
one_liner: "..."             # 상세 상단 한 줄
what_to_order: "..."         # Quick visit guide
good_for: "..."              # Quick visit guide
youtube_id: bAGMpLn0rt4      # 선택
seo_title: "..."             # 선택, 60자로 자름
seo_description: "..."       # 선택, 160자로 자름
---
## Overview
...
```

- `categories` 허용값: Tonkotsu · Shoyu · Miso · Shio · Tsukemen · Chicken · Vegan · Local Gem · Premium · Late Night · Solo Friendly (ko 라벨은 `ramen_practical._STYLE_KO`)
- `lat`/`lng`/`address` 필수 (`has_real_shop_data`)
- slug: 영어 소문자 `_` 구분 (okcaddie는 `-`)
- 이미지 파일명 = slug (`<slug>.jpg`)

### 3-2. 가이드 `app/content/guides/<id>_<lang>.md`

```yaml
---
lang: en
title: "..."
date: '2026-05-28'
summary: "..."
seo_title: "..."        # 선택
seo_description: "..."  # 선택
---
```

본문은 H2부터 (H1 금지).

## 4. 품질 게이트 (`script/content_quality.py`)

| 규칙 | 값 |
|---|---|
| 최소 길이 | 가이드 4,000자 · 가게 3,500자 · 짝 채우기 5,000자 |
| H2 | 3개 이상 |
| 금지 문구 | `BANNED_PHRASES` (best ramen in, definitive guide, world-class bowl, 미슐랭 스타 …) |
| 틀 소제목 | `FORBIDDEN_HEADINGS` 2개 이상이면 실패 |
| 언어 비율 | ko: 한글 ≥ 8% · en: 한글 ≤ 12% |
| 라멘 여부 | `RAMEN_THEME_MARKERS` 필요, `FOREIGN_THEME_MARKERS`(cafe, onsen, golf …) slug 차단 |
| 차단 id | `guide_seed_*` · `guide_expand_*` |
| 가게 데이터 | 실제 좌표 + 주소 |

테스트: `tests/test_content_quality.py`.

## 5. 빌드 · 배포

- 로컬: `python script/build_data.py && python app/__init__.py` → http://localhost:8080 · 테스트 `pytest -q`
- Docker: `python:3.10-slim`, 빌드 중 `build_data.py` + `build_sitemap.py`, `gunicorn --workers 2 --threads 8 --timeout 120 app:app`
- `cloudbuild.yaml` (프로젝트 `starful-258005`, us-central1):
  1. `okramen-repo/okramen:latest` 캐시 pull
  2. docker build → push (Artifact Registry `us-central1-docker.pkg.dev/starful-258005/okramen-repo/okramen`)
  3. `gcloud run deploy okramen` — port 8080 · memory 1Gi · unauthenticated
     - env: `SITE_URL=${_SITE_URL}` (기본 https://okramen.net), `STORE_BACKEND=firestore`, `FIRESTORE_COLLECTION=okramen`
     - secrets: `GOOGLE_MAPS_API_KEY=OKRAMEN_GOOGLE_MAPS_API_KEY`, `VISITLOG_SECRET=VISITLOG_SECRET`
- 배포는 okadmin Deploy 탭 또는 HQ 배포 (main 기준). `deploy.sh`는 생성→이미지→GCS 동기화→커밋 도우미
- 이미지 원본: `gs://ok-project-assets/okramen/`

## 6. 설정값

| 이름 | 용도 | 기본 |
|---|---|---|
| `SITE_URL` | sitemap · canonical · 공유 | https://okramen.net |
| `PORT` | 서버 포트 | 8080 |
| `GOOGLE_MAPS_API_KEY` | 지도 JS | (Secret) |
| `GOOGLE_PLACES_API_KEY` | 생성기 · 사진 | 로컬 .env |
| `GEMINI_API_KEY` · `GCP_PROJECT` · `GCP_LOCATION` | 글·이미지 생성 | 로컬 .env |
| `AGODA_PARTNERS_CID` | Agoda 링크 | 1976212 |
| `AFFILIATE_OKRAMEN_ENABLED` (구 `A8_OKRAMEN_ENABLED`) | 제휴 박스 on/off | 1 |
| `AMAZON_JP_TAG` · `AMAZON_OKRAMEN_ENABLED` | Amazon 링크 | starful06-22 |
| `REACTIONS_COLLECTION` | 반응 Firestore 컬렉션 | okramen |
| `STORE_BACKEND` · `FIRESTORE_COLLECTION` · `FIRESTORE_PROJECT` | visitlog 저장소 | sqlite (운영 firestore) |
| `VISITLOG_SECRET` (또는 `SESSION_SECRET`) · `VISITLOG_HQ_TOKEN` · `VISITLOG_DB` | visitlog | — |
| `RAMEN_MAX_WORKERS` · `GUIDE_MAX_WORKERS` · `CONTENT_LIMIT` · `FILL_HALF` | 생성 병렬·개수 | — |

`.env`는 커밋하지 않는다. Agoda 도시 ID는 파트너 확인된 값만 (`AGODA_CITIES`).

## 7. HQ 연동

`/opt/work/sites.yaml`의 `okramen` 항목 (HQ가 읽음, 이 저장소에서 바꾸지 않음):

```yaml
- id: okramen
  path: okramen
  analytics: {gsc_site_url: "sc-domain:okramen.net", ga4_property_id: "530015360"}
  gcs: {bucket: ok-project-assets, prefix: okramen/, search_type: [restaurant, food]}
  hq:
    office: playground   # 2층
    order: 10
    enabled: true
    visitlog: true       # 이용자 보기 = visitkit
    content: poi         # HQ poicontent Kit("ramen shop", ramen_generator.run_generator)
    posts_rel: app/content
    images_rel: app/static/images
    flat: true
    youtube: {...}       # 디자인 탭 YouTube 모드
```

- 글쓰기: HQ `app/content/poicontent.py` Kit `okramen` — Places 타입 `ramen_restaurant` 등, 필드 Name·Lat·Lng·Address·Thumbnail·Features, slug 검사 `is_non_ramen_slug`
- visitlog: `register_visitlog(app, site_id="okramen", db_path=data/visitlog.sqlite3)` · 이벤트 pv·click·cta·outbound·affiliate · HQ는 `GET /hq/api/users`를 Bearer 토큰으로 읽음
- URL별 숫자: HQ `app/url_stats.py`가 GSC/GA4에서 페이지별 조회·노출·CTR·순위를 가져옴 (제목 꼬리 「| OKRamen」「- OKRamen」 제거)
- 회의: HQ `app/office/meeting.py`가 이 사이트의 이미 있는 글 목록을 프롬프트에 넣음. 기획서 본문 + URL별 숫자 + 최근 회의 결정·실행 결과는 starful-hq #12 (머지 대기)
- 토픽: okadmin `data/topic_banks/okramen/`

## 8. 테스트

`pytest -q` — test_app(라우트) · test_build_data · test_content_quality · test_legacy_redirects · test_seo.
