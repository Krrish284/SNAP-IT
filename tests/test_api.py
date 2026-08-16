"""End-to-end API tests against a real PostgreSQL instance."""

from fastapi.testclient import TestClient

TARGET = "https://example.com/some/page?q=1"


def _shorten(client: TestClient, url: str = TARGET) -> dict:
    response = client.post("/api/links", json={"url": url})
    assert response.status_code == 201, response.text
    return response.json()


def test_health_reports_database_ok(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "ok"


def test_create_returns_short_link(client: TestClient) -> None:
    data = _shorten(client)
    assert data["short_code"]
    assert data["short_url"].endswith("/" + data["short_code"])
    assert data["original_url"] == TARGET
    assert data["created_at"]


def test_missing_scheme_is_defaulted_to_https(client: TestClient) -> None:
    data = _shorten(client, "example.com/path")
    assert data["original_url"] == "https://example.com/path"


def test_invalid_urls_are_rejected(client: TestClient) -> None:
    bad_urls = [
        "not-a-url",
        "ftp://example.com/x",
        "javascript:alert(1)",
        "http://",
        "   ",
        "http://exa mple.com/x",
        "mailto:user@example.com",
    ]
    for bad in bad_urls:
        response = client.post("/api/links", json={"url": bad})
        assert response.status_code == 422, f"{bad!r} was not rejected: {response.text}"


def test_redirect_is_302_and_records_click(client: TestClient) -> None:
    data = _shorten(client)
    response = client.get(
        f"/{data['short_code']}",
        follow_redirects=False,
        headers={"Referer": "https://ref.example/from"},
    )
    assert response.status_code == 302
    assert response.headers["location"] == TARGET

    stats = client.get(f"/api/links/{data['short_code']}").json()
    assert stats["click_count"] == 1
    assert stats["last_clicked_at"] is not None

    timeline = client.get(f"/api/links/{data['short_code']}/clicks").json()
    assert timeline["total"] == 1
    assert len(timeline["daily"]) == 1


def test_unknown_codes_return_404(client: TestClient) -> None:
    assert client.get("/nope99").status_code == 404
    assert client.get("/api/links/nope99").status_code == 404
    assert client.get("/api/links/nope99/clicks").status_code == 404


def test_dashboard_reflects_real_data(client: TestClient) -> None:
    link_a = _shorten(client, "https://a.example/x")
    link_b = _shorten(client, "https://b.example/y")

    visits = [
        (link_a["short_code"], "https://r1.example/"),
        (link_b["short_code"], None),
        (link_a["short_code"], "https://r2.example/"),
    ]
    for code, referrer in visits:
        headers = {"Referer": referrer} if referrer else {}
        response = client.get(f"/{code}", follow_redirects=False, headers=headers)
        assert response.status_code == 302

    dashboard = client.get("/api/dashboard").json()
    assert dashboard["total_links"] == 2
    assert dashboard["total_clicks"] == 3

    top = dashboard["top_links"]
    assert top[0]["short_code"] == link_a["short_code"]
    assert top[0]["click_count"] == 2
    assert top[1]["short_code"] == link_b["short_code"]
    assert top[1]["click_count"] == 1

    latest = dashboard["recent_clicks"][0]
    assert latest["short_code"] == link_a["short_code"]
    assert latest["referrer"] == "https://r2.example/"
    assert latest["original_url"] == "https://a.example/x"
