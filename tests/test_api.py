from fastapi.testclient import TestClient
from backend.database import init_db
from backend.main import app

init_db()
client = TestClient(app)


def test_health():
    assert client.get("/api/health").json()["status"] == "ok"


def test_watchlist_crud():
    client.post("/api/watchlist", json={"ticker": "TEST", "bucket": "B1"})
    wl = client.get("/api/watchlist").json()
    assert any(w["ticker"] == "TEST" for w in wl)
    client.delete("/api/watchlist/TEST")
    wl = client.get("/api/watchlist").json()
    assert not any(w["ticker"] == "TEST" for w in wl)


def test_position_add_and_close():
    r = client.post("/api/positions", json={
        "ticker": "ADBE", "position_type": "option", "strike": 270,
        "expiry": "2026-07-17", "premium_paid": 5.50, "contracts": 1,
    })
    pid = r.json()["id"]
    client.put(f"/api/positions/{pid}/close", json={"exit_price": 22.0, "exit_reason": "4x target"})
    summary = client.get("/api/positions/summary").json()
    assert summary["total_trades"] >= 1


def test_deep_dive_post_and_get(monkeypatch):
    from backend.routers import deep_dive as deep_dive_router
    from backend.services.providers import DataResult

    monkeypatch.setattr(
        deep_dive_router,
        "get_stock_fundamentals",
        lambda ticker: DataResult(
            value={
                "ticker": ticker,
                "total_revenue": None,
                "shares_outstanding": None,
                "price": None,
                "free_cash_flow": None,
            },
            source="test",
            missing_fields=["price"],
        ),
    )
    monkeypatch.setattr(deep_dive_router, "get_fcf_3yr_average", lambda ticker: None)
    monkeypatch.setattr(deep_dive_router, "get_sbc", lambda ticker: None)
    monkeypatch.setattr(deep_dive_router, "get_net_debt", lambda ticker: None)

    ticker = "TSTDD"
    client.post(f"/api/deep-dive/{ticker}", json={
        "first_impression": "Looks interesting",
        "bear_case_stock": "Price decline",
        "verdict": "B1", "conviction": "HIGH",
    })
    r = client.get(f"/api/deep-dive/{ticker}").json()
    assert r["ai_analysis"]["first_impression"] == "Looks interesting"
    assert r["ai_analysis"]["conviction"] == "HIGH"


def test_regime_endpoint_returns_structured_breadth(monkeypatch):
    from backend.routers import regime as regime_router

    monkeypatch.setattr(
        regime_router,
        "get_full_regime",
        lambda: {
            "spy": {"ticker": "SPY"},
            "qqq": {"ticker": "QQQ"},
            "regime": {"verdict": "CAUTIOUS"},
            "breadth": {
                "method": "full_universe",
                "confidence": "HIGH",
                "coverage_pct": 95.0,
                "sample_size": 480,
                "universe_size": 503,
                "pct_above_200d": 55.0,
                "pct_above_50d": 49.0,
                "pct_above_20d": 44.0,
                "breadth_signal": "HEALTHY",
                "notes": [],
            },
        },
    )

    data = client.get("/api/regime").json()
    assert data["breadth"]["method"] == "full_universe"
    assert data["breadth"]["confidence"] == "HIGH"
