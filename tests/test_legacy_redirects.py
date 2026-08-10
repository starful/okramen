"""Legacy redirect coverage for GSC 404 / deleted pages."""


def test_restored_pages_live(client):
    assert client.get("/guide/ramen_prices_ko").status_code == 200
    assert client.get("/guide/ramen_prices_en").status_code == 200
    assert client.get("/ramen/jinrui_mina_menrui_en").status_code == 200
    assert client.get("/ramen/jinrui_mina_menrui_ko").status_code == 200


def test_deleted_ramen_301(client):
    r = client.get("/ramen/aji_no_kura_ko", follow_redirects=False)
    assert r.status_code == 301
    assert r.headers["Location"].endswith("/guide/regional_ramen_ko")

    r = client.get("/ramen/nagahama_no_1_en", follow_redirects=False)
    assert r.status_code == 301
    assert "nagahama_no.1_en" in r.headers["Location"]

    r = client.get("/ramen/ichiran_fukuoka_main_ko", follow_redirects=False)
    assert r.status_code == 301
    assert "ichiran_shinjuku_ko" in r.headers["Location"]

    r = client.get("/ramen/nagoya_sakae_espresso_en", follow_redirects=False)
    assert r.status_code == 301
    assert r.headers["Location"].rstrip("/").endswith("/guide")


def test_card_guide_redirect(client):
    r = client.get("/card/essential_toppings_ko", follow_redirects=False)
    assert r.status_code == 301
    assert r.headers["Location"].endswith("/guide/essential_toppings_ko")

    r = client.get("/card/ramen_prices_ko", follow_redirects=False)
    assert r.status_code == 301
    assert r.headers["Location"].endswith("/guide/ramen_prices_ko")


def test_deleted_guide_301(client):
    r = client.get("/guide/instant_ramen_hacks_en", follow_redirects=False)
    assert r.status_code == 301
    assert "instant_vs_shop_en" in r.headers["Location"]

    r = client.get("/guide/LINK_TO_MAP", follow_redirects=False)
    assert r.status_code == 301
