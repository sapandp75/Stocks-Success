from backend.services.institutional import _classify_insider_sentiment


def test_insider_sentiment_buying():
    """Net positive change > 0.3 ratio -> BUYING."""
    transactions = [
        {"change": 10000},
        {"change": 5000},
        {"change": -1000},
    ]
    assert _classify_insider_sentiment(transactions) == "BUYING"


def test_insider_sentiment_selling():
    """Net negative change < -0.3 ratio -> SELLING."""
    transactions = [
        {"change": -10000},
        {"change": -5000},
        {"change": 1000},
    ]
    assert _classify_insider_sentiment(transactions) == "SELLING"


def test_insider_sentiment_quiet():
    """Empty transaction list -> QUIET."""
    assert _classify_insider_sentiment([]) == "QUIET"


def test_insider_sentiment_mixed():
    """Equal buys and sells -> MIXED."""
    transactions = [
        {"change": 5000},
        {"change": -5000},
    ]
    assert _classify_insider_sentiment(transactions) == "MIXED"
