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
