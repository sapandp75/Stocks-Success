from unittest.mock import patch
from backend.services.sentiment import _format_sentiment, _build_analyst_data


def test_format_sentiment_bearish_is_high_interest():
    """Contrarian rule: bearish crowd = high interest."""
    result = _format_sentiment({
        "av_sentiment_score": -0.4,
        "av_sentiment_label": "Bearish",
        "finnhub_consensus": "sell",
        "finnhub_recent_change": "downgrade",
        "finnhub_target_mean": None,
        "finnhub_target_high": None,
        "finnhub_target_low": None,
    })
    assert result["contrarian_rating"] == "HIGH_INTEREST"
    assert "NEGATIVE_SENTIMENT" in result["contrarian_signals"]
    assert "ANALYSTS_BEARISH" in result["contrarian_signals"]


def test_format_sentiment_bullish_is_consensus():
    """Contrarian rule: bullish crowd = less edge."""
    result = _format_sentiment({
        "av_sentiment_score": 0.5,
        "av_sentiment_label": "Bullish",
        "finnhub_consensus": "buy",
        "finnhub_recent_change": "upgrade",
        "finnhub_target_mean": None,
        "finnhub_target_high": None,
        "finnhub_target_low": None,
    })
    assert result["contrarian_rating"] == "CONSENSUS"
    assert len(result["contrarian_signals"]) == 0


def test_format_sentiment_downgrade_is_moderate():
    """Downgrade alone = moderate interest."""
    result = _format_sentiment({
        "av_sentiment_score": 0.1,
        "av_sentiment_label": "Neutral",
        "finnhub_consensus": "hold",
        "finnhub_recent_change": "downgrade",
        "finnhub_target_mean": None,
        "finnhub_target_high": None,
        "finnhub_target_low": None,
    })
    assert result["contrarian_rating"] == "MODERATE_INTEREST"
    assert "RECENT_DOWNGRADE" in result["contrarian_signals"]


def test_research_for_claude_returns_string():
    """Bridge context should be a formatted string."""
    with patch("backend.services.research.get_all_research") as mock:
        mock.return_value = {
            "seeking_alpha": [{"title": "Test Article", "summary": "Good read", "published_date": "2026-04-01"}],
            "substack": [],
            "total_items": 1,
        }
        from backend.services.research import get_research_for_claude
        result = get_research_for_claude("AAPL")
        assert "Test Article" in result
        assert "Research Context for AAPL" in result


def test_analyst_data_contrarian_signal_bearish():
    """Sell consensus -> ANALYSTS_BEARISH contrarian signal."""
    data = {
        "current_price": 150,
        "target_mean": 180,
        "consensus": "sell",
    }
    result = _build_analyst_data(data)
    assert result["contrarian_signal"] == "ANALYSTS_BEARISH"
    assert result["price_vs_target"] is not None


def test_analyst_data_contrarian_signal_consensus():
    """Buy consensus -> CONSENSUS contrarian signal."""
    data = {
        "current_price": 150,
        "target_mean": 200,
        "consensus": "buy",
    }
    result = _build_analyst_data(data)
    assert result["contrarian_signal"] == "CONSENSUS"
