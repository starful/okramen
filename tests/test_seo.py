"""SEO and X card regression tests."""


def test_ramen_detail_has_social_meta(client):
    response = client.get("/ramen/tenkaippin_main_shop_en")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "share-bar" in html
    assert "share-btn-x" in html
    assert "/social/tenkaippin_main_shop.jpg" in html
    assert 'name="twitter:image"' in html
    assert "card/tenkaippin_main_shop_en" in html


def test_guide_detail_has_social_meta(client):
    response = client.get("/guide/ramen_etiquette_en")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert "share-bar" in html
    assert 'name="twitter:image"' in html
    assert "/guide/ramen_etiquette_en" in html
    assert "The Art of the Slurp" in html


def test_konbini_ramen_how_to_guides_render(client):
    en = client.get("/guide/konbini-ramen-how-to_en")
    assert en.status_code == 200
    en_html = en.get_data(as_text=True)
    assert "Convenience Store Ramen" in en_html
    assert "/guide/top_5_convenience_store_ramen_en" in en_html

    ko = client.get("/guide/konbini-ramen-how-to_ko")
    assert ko.status_code == 200
    ko_html = ko.get_data(as_text=True)
    assert "편의점 라멘" in ko_html
    assert "/guide/top_5_convenience_store_ramen_ko" in ko_html


def test_social_image_endpoint(client):
    response = client.get("/social/tenkaippin_main_shop.jpg")
    assert response.status_code == 200
    assert response.headers.get("Content-Type", "").startswith("image/jpeg")
    assert len(response.get_data()) > 1000


def test_social_card_page(client):
    response = client.get("/card/tenkaippin_main_shop_en")
    assert response.status_code == 200
    html = response.get_data(as_text=True)
    assert 'property="og:url" content="https://okramen.net/card/tenkaippin_main_shop_en"' in html
    assert "/social/tenkaippin_main_shop.jpg" in html
    assert "View ramen guide" in html
