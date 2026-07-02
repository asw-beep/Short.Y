"""Frontend tests: the two HTML pages, the static asset, and the reserved route."""


def test_index_page_serves_html(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "shorten-form" in r.text


def test_list_page_serves_html(client):
    r = client.get("/list")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "/api/urls" in r.text


def test_static_css_served(client):
    r = client.get("/static/style.css")
    assert r.status_code == 200
    assert "text/css" in r.headers["content-type"]


def test_list_is_a_reserved_alias(client):
    r = client.post("/shorten", json={"url": "https://a.com/", "custom_alias": "list"})
    assert r.status_code == 400
