# OKRamen

Interactive ramen discovery platform for Japan with map-based browsing, bilingual content, and markdown-first publishing.

Live: [https://okramen.net](https://okramen.net)

## What This Project Does

- Serves ramen shop data through a Flask API and renders an interactive Google Map on the homepage.
- Supports bilingual ramen and guide content (`en` / `ko`) with language-aware links.
- Uses markdown files with frontmatter as the source of truth (no database).
- Builds static JSON (`app/static/json/ramen_data.json`) from markdown for fast read performance.
- Provides operational scripts for AI content generation, image generation/fetch/optimization, and deployment.

## Tech Stack

- Backend: Python, Flask, Gunicorn, Flask-Compress
- Frontend: Jinja templates + Vanilla JavaScript (ES modules)
- Content: Markdown + YAML frontmatter
- AI tooling: Gemini-based generation scripts
- Infra: Docker, Google Cloud Build, Cloud Run

## Quick Start

### 1) Install

```bash
git clone https://github.com/starful/okramen.git
cd okramen
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Configure Environment Variables

Create `.env` in repository root:

```env
GEMINI_API_KEY=your_gemini_api_key
GOOGLE_MAPS_API_KEY=your_google_maps_js_api_key
SITE_URL=https://okramen.net
PORT=8080
```

Notes:
- `GOOGLE_MAPS_API_KEY` is required for map rendering on `/`.
- `SITE_URL` is used by the dynamic sitemap endpoint (`/sitemap.xml`).
- `PORT` defaults to `8080` if not set.

### 3) Build Data + Run App

```bash
python script/build_data.py
python app/__init__.py
```

Open `http://localhost:8080`.

### 4) Run Tests

```bash
pytest -q
```

## Main Runtime Flow

1. Markdown files are stored in `app/content`.
2. `script/build_data.py` compiles ramen markdown into `app/static/json/ramen_data.json`.
3. Flask loads cached ramen/guide data at startup (`app/__init__.py`).
4. Frontend requests `/api/ramens` and renders map/list via `app/static/js/main.js`.
5. SEO/Index routes are exposed through `robots.txt` and dynamic `sitemap.xml`.

## Key Directories

```text
app/
  __init__.py              Flask app, routes, caching, sitemap
  content/                 Markdown source content (ramen + guides)
  static/
    css/                   Styles
    images/                Static image assets
    js/main.js             Frontend app logic
    json/ramen_data.json   Built data file
    robots.txt             Crawl policy
  templates/               Jinja templates
script/
  build_data.py            Markdown -> JSON compiler
  ramen_generator.py       Ramen markdown generation
  guide_generator.py       Guide markdown generation
  generate_images.py       AI image generation
  fetch_images.py          Remote image fetching helpers
  optimize_images.py       Compression/resize pipeline
Dockerfile                 Container runtime config
cloudbuild.yaml            Cloud Build pipeline
deploy.sh                  Deployment helper script
```

## Useful Commands

```bash
# Rebuild ramen JSON from markdown
python script/build_data.py

# Run local server
python app/__init__.py

# Run tests
pytest -q
```

## Deployment

- Production runtime uses `gunicorn` in `Dockerfile`.
- Cloud deployment is configured via `cloudbuild.yaml` (Cloud Build -> Cloud Run).
- `deploy.sh` contains project-specific automation flow.

Before deploy:
- Ensure `GOOGLE_MAPS_API_KEY` and `SITE_URL` are set in runtime environment.
- Rebuild JSON (`python script/build_data.py`) if content changed.

## SEO and Indexing

- `app/static/robots.txt` points crawlers to `/sitemap.xml`.
- `/sitemap.xml` is dynamically generated from cached ramen and guide data.
- Templates include canonical and robots metadata for primary pages.

## Development Notes

- The app currently relies on startup-time in-memory caches.
- If markdown content changes while server is running, restart the app to refresh caches.
- Keep markdown frontmatter consistent (`id`, `lang`, `title`, `summary`, etc.) for stable rendering.

## License

© 2026 OKRamen Project. All rights reserved.
