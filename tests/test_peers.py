from backend.services.peers import _rank_among_peers


def test_rank_among_peers():
    """Lower PE = rank 1, higher margin = rank 1, higher growth = rank 1."""
    peers = [
        {"ticker": "AAPL", "forward_pe": 25, "operating_margin": 0.30, "revenue_growth": 0.10},
        {"ticker": "MSFT", "forward_pe": 30, "operating_margin": 0.40, "revenue_growth": 0.15},
        {"ticker": "GOOG", "forward_pe": 20, "operating_margin": 0.25, "revenue_growth": 0.20},
    ]
    result = _rank_among_peers("GOOG", peers)
    # GOOG has lowest PE -> rank 1
    assert result["pe_rank"] == 1
    # GOOG has lowest margin -> rank 3
    assert result["margin_rank"] == 3
    # GOOG has highest growth -> rank 1
    assert result["growth_rank"] == 1
    assert result["total_peers"] == 3


def test_rank_handles_none():
    """None values should not crash the ranking."""
    peers = [
        {"ticker": "AAPL", "forward_pe": 25, "operating_margin": None, "revenue_growth": 0.10},
        {"ticker": "MSFT", "forward_pe": None, "operating_margin": 0.40, "revenue_growth": None},
        {"ticker": "GOOG", "forward_pe": 20, "operating_margin": 0.25, "revenue_growth": 0.20},
    ]
    result = _rank_among_peers("GOOG", peers)
    # PE: GOOG=20, AAPL=25 (MSFT excluded) -> rank 1
    assert result["pe_rank"] == 1
    # Margin: MSFT=0.40, GOOG=0.25 (AAPL excluded) -> rank 2
    assert result["margin_rank"] == 2
    # Growth: GOOG=0.20, AAPL=0.10 (MSFT excluded) -> rank 1
    assert result["growth_rank"] == 1
    assert result["total_peers"] == 3
