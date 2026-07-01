from pathlib import Path
import sys

import pytest

ROOT_DIR = Path(__file__).resolve().parents[1]
APP_DIR = ROOT_DIR / "app"
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from __init__ import app as flask_app


@pytest.fixture()
def client():
    flask_app.config["TESTING"] = True
    with flask_app.test_client() as test_client:
        yield test_client


def test_api_ramens_returns_json(client):
    response = client.get("/api/ramens")
    assert response.status_code == 200
    payload = response.get_json()
    assert isinstance(payload, dict)
    assert "ramens" in payload


def test_sitemap_xml_is_well_formed_and_contains_core_urls(client):
    response = client.get("/sitemap.xml")
    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("application/xml")
    body = response.get_data(as_text=True)
    assert "<urlset" in body
    assert "<loc>https://okramen.net/</loc>" in body
    assert "<loc>https://okramen.net/guide</loc>" in body


def test_index_does_not_embed_hardcoded_google_maps_key(client):
    response = client.get("/")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "AIza" not in html


def test_ramen_detail_parses_frontmatter_without_closing_delimiter(client):
    """Regression: some *.md omit the closing --- before the first ## heading."""
    response = client.get("/ramen/tenkaippin_main_shop_en")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Tenkaippin Main Shop" in html
    assert "/static/images/tenkaippin_main_shop.jpg" in html


def test_ramen_detail_shows_practical_guide_layout(client):
    response = client.get("/ramen/ganso_sapporo_ramen_yokocho_en")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "Quick visit guide" in html
    assert "Ganso Sapporo Ramen Yokocho" in html
    assert "Why Ganso Sapporo Ramen Yokocho Still Serves" not in html
    assert "What to order" in html


def test_reactions_api(client):
    response = client.get("/api/reactions/test-slug")
    assert response.status_code == 200
    data = response.get_json()
    assert "likes" in data
    assert "dislikes" in data


def test_ramen_detail_has_reaction_panel(client):
    response = client.get("/ramen/tenkaippin_main_shop_en")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "reaction-panel" in html
    assert "/api/reactions/" in html
    assert "share-bar" in html
