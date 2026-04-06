from backend.services.regime_checker import determine_regime, classify_direction, calculate_vix_tax


def test_classify_full_uptrend():
    d = classify_direction(500, 495, 490, 470)
    assert d == "FULL_UPTREND"


def test_classify_full_downtrend():
    d = classify_direction(400, 420, 440, 470)
    assert d == "FULL_DOWNTREND"


def test_determine_regime_deploy():
    spy = {"direction": "FULL_UPTREND"}
    qqq = {"direction": "FULL_UPTREND"}
    result = determine_regime(spy, qqq, vix=15.0)
    assert result["verdict"] == "DEPLOY"
    assert result["max_new_positions"] == 5


def test_determine_regime_cash_on_downtrend():
    spy = {"direction": "FULL_DOWNTREND"}
    qqq = {"direction": "FULL_DOWNTREND"}
    result = determine_regime(spy, qqq, vix=30.0)
    assert result["verdict"] == "CASH"
    assert result["max_new_positions"] == 0


def test_determine_regime_vix_override():
    spy = {"direction": "FULL_UPTREND"}
    qqq = {"direction": "FULL_UPTREND"}
    result = determine_regime(spy, qqq, vix=36.0)
    assert result["verdict"] == "CASH"


def test_vix_tax_at_normal():
    tax = calculate_vix_tax(15.0)
    assert tax["premium_premium_pct"] == 0


def test_vix_tax_at_elevated():
    tax = calculate_vix_tax(25.0)
    assert tax["premium_premium_pct"] > 0
    assert "elevated" in tax["note"].lower() or "above" in tax["note"].lower()
