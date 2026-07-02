"""GET /api/urls — the data source behind the /list dashboard."""
from datetime import datetime, timedelta, timezone

from app.models.url import URL


def _future(minutes=60):
    return datetime.now(timezone.utc) + timedelta(minutes=minutes)


def _past(minutes=60):
    return datetime.now(timezone.utc) - timedelta(minutes=minutes)


def test_list_empty_by_default(client):
    r = client.get("/api/urls")
    assert r.status_code == 200
    assert r.json() == {"items": [], "limit": 50, "offset": 0}


def test_list_includes_live_urls(client):
    client.post("/shorten", json={"url": "https://a.com/"})
    client.post("/shorten", json={"url": "https://b.com/", "expires_at": _future().isoformat()})

    r = client.get("/api/urls")
    items = r.json()["items"]
    assert len(items) == 2
    codes = {i["short_code"] for i in items}
    assert codes == {"0000001", "0000002"}
    for item in items:
        assert item["short_url"].endswith(f"/{item['short_code']}")


def test_list_excludes_expired_urls(client, db_session):
    client.post("/shorten", json={"url": "https://live.com/"})
    db_session.add(
        URL(short_code="expired1", long_url="https://gone.example/", is_custom=True, expires_at=_past())
    )
    db_session.commit()

    r = client.get("/api/urls")
    codes = {i["short_code"] for i in r.json()["items"]}
    assert codes == {"0000001"}
    assert "expired1" not in codes


def test_list_newest_first(client):
    client.post("/shorten", json={"url": "https://first.com/"})
    client.post("/shorten", json={"url": "https://second.com/"})

    items = client.get("/api/urls").json()["items"]
    assert [i["short_code"] for i in items] == ["0000002", "0000001"]


def test_list_pagination(client):
    for i in range(5):
        client.post("/shorten", json={"url": f"https://x.com/{i}"})

    page1 = client.get("/api/urls?limit=2&offset=0").json()
    page2 = client.get("/api/urls?limit=2&offset=2").json()
    assert len(page1["items"]) == 2
    assert len(page2["items"]) == 2
    assert page1["items"] != page2["items"]


def test_list_rejects_oversized_limit(client):
    r = client.get("/api/urls?limit=1000")
    assert r.status_code == 422
