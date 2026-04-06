from fastapi.testclient import TestClient
from backend.main import app

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


def test_deep_dive_post_and_get():
    client.post("/api/deep-dive/TESTDD", json={
        "first_impression": "Looks interesting",
        "bear_case_stock": "Price decline",
        "verdict": "B1", "conviction": "HIGH",
    })
    r = client.get("/api/deep-dive/TESTDD").json()
    assert r["ai_analysis"]["first_impression"] == "Looks interesting"
    assert r["ai_analysis"]["conviction"] == "HIGH"
