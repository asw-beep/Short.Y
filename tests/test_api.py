def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_shorten_returns_full_url(client):
    r = client.post("/shorten", json={"url": "https://example.com/foo"})
    assert r.status_code == 201
    body = r.json()
    assert body["short_code"] == "0000001"
    assert body["short_url"].endswith("/0000001")
    assert body["long_url"] == "https://example.com/foo"


def test_shorten_custom_alias(client):
    r = client.post(
        "/shorten",
        json={"url": "https://example.com/", "custom_alias": "my-alias"},
    )
    assert r.status_code == 201
    assert r.json()["short_code"] == "my-alias"


def test_shorten_custom_alias_conflict(client):
    client.post("/shorten", json={"url": "https://a.com/", "custom_alias": "taken1"})
    r = client.post("/shorten", json={"url": "https://b.com/", "custom_alias": "taken1"})
    assert r.status_code == 409


def test_shorten_reserved_alias(client):
    r = client.post("/shorten", json={"url": "https://a.com/", "custom_alias": "admin"})
    assert r.status_code == 400


def test_shorten_rejects_non_http_scheme(client):
    r = client.post("/shorten", json={"url": "ftp://example.com/"})
    assert r.status_code == 422


def test_shorten_rejects_javascript_scheme(client):
    r = client.post("/shorten", json={"url": "javascript:alert(1)"})
    assert r.status_code == 422


def test_redirect_hit(client):
    create = client.post("/shorten", json={"url": "https://example.com/dest"})
    code = create.json()["short_code"]
    r = client.get(f"/{code}", follow_redirects=False)
    assert r.status_code == 301
    assert r.headers["location"] == "https://example.com/dest"


def test_redirect_miss(client):
    r = client.get("/missing", follow_redirects=False)
    assert r.status_code == 404
