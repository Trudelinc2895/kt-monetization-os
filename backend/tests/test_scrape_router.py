from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi.testclient import TestClient

from api.main import app


def test_scrape_routes_are_registered() -> None:
    paths = {route.path for route in app.routes}

    assert "/scrape" in paths
    assert "/scrape/jobs/{job_id}" in paths


def test_scrape_route_returns_sync_payload_when_enabled(monkeypatch) -> None:
    from api.routers import scrape as scrape_router

    @asynccontextmanager
    async def _noop_lifespan(_app):
        yield

    monkeypatch.setattr(app.router, "lifespan_context", _noop_lifespan)
    monkeypatch.setattr(scrape_router.settings, "SCRAPING_ENABLED", True)

    async def fake_scrape_once(req):
        return {
            "url": req.url,
            "mode": req.mode,
            "render_js": req.render_js,
            "force_refresh": req.force_refresh,
            "client_id": req.client_id,
        }

    monkeypatch.setattr(scrape_router, "scrape_once", fake_scrape_once)

    with TestClient(app) as client:
        response = client.get("/scrape", params={"url": "https://example.com/path?a=1"})

    assert response.status_code == 200
    assert response.json() == {
        "url": "https://example.com/path?a=1",
        "mode": scrape_router.settings.SCRAPING_MODE_DEFAULT,
        "render_js": False,
        "force_refresh": False,
        "client_id": "testclient",
    }


def test_scrape_route_is_404_when_disabled(monkeypatch) -> None:
    from api.routers import scrape as scrape_router

    @asynccontextmanager
    async def _noop_lifespan(_app):
        yield

    monkeypatch.setattr(app.router, "lifespan_context", _noop_lifespan)
    monkeypatch.setattr(scrape_router.settings, "SCRAPING_ENABLED", False)

    with TestClient(app) as client:
        response = client.get("/scrape", params={"url": "https://example.com"})

    assert response.status_code == 404
    assert response.json() == {"detail": "Scraping is disabled"}
