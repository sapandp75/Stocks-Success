import gzip
import json
import time
import urllib.request

_cache: dict | None = None
_cache_time: float = 0
_CACHE_TTL = 3600  # 1 hour
_STALE_TTL = 86400  # 24 hours

# Symbols we extract from the j-sum response
_MCCLELLAN_SYMBOLS = {"$NYMO", "$NYSI", "$NAMO", "$NASI"}
_AD_SYMBOLS = {"$NYAD", "$NAAD", "$NYHL", "$NAHL"}
_SENTIMENT_SYMBOLS = {"$CPC", "$TRIN", "$VIX"}
_BP_INDEX_SYMBOLS = {"$BPSPX", "$BPNDX", "$BPNYA"}
_BP_SECTOR_SYMBOLS = {
    "$BPINFO", "$BPFINA", "$BPHEAL", "$BPINDY", "$BPDISC",
    "$BPSTAP", "$BPENER", "$BPMATE", "$BPREAL", "$BPCOMM", "$BPUTIL",
}

_MCCLELLAN_KEYS = {"$NYMO": "nymo", "$NYSI": "nysi", "$NAMO": "namo", "$NASI": "nasi"}
_AD_KEYS = {"$NYAD": "nyad", "$NAAD": "naad", "$NYHL": "nyhl", "$NAHL": "nahl"}
_SENTIMENT_KEYS = {"$CPC": "cpc", "$TRIN": "trin", "$VIX": "vix"}
_BP_INDEX_KEYS = {"$BPSPX": "spx", "$BPNDX": "ndx", "$BPNYA": "nya"}


def _signal_mcclellan(symbol: str, value: float) -> str:
    if symbol in ("$NYSI", "$NASI"):
        if value > 0:
            return "BULLISH"
        if value > -500:
            return "RECOVERING" if value > -250 else "BEARISH"
        return "DEEPLY_BEARISH"
    # Oscillators ($NYMO, $NAMO)
    if value > 50:
        return "OVERBOUGHT"
    if value > 20:
        return "BULLISH"
    if value > -20:
        return "RECOVERING" if value > 0 else "NEUTRAL"
    if value > -50:
        return "BEARISH"
    return "OVERSOLD"


def _signal_ad(symbol: str, value: float) -> str:
    if symbol in ("$NYHL", "$NAHL"):
        if value > 100:
            return "STRONG"
        if value > 50:
            return "HEALTHY"
        if value > -50:
            return "MARGINAL"
        return "POOR"
    # $NYAD, $NAAD
    if value > 500:
        return "ADVANCING"
    if value > 0:
        return "SLIGHTLY_ADVANCING"
    if value > -500:
        return "SLIGHTLY_DECLINING"
    return "DECLINING"


def _signal_sentiment(symbol: str, value: float) -> str:
    if symbol == "$CPC":
        if value > 1.2:
            return "EXTREME_FEAR"
        if value > 1.0:
            return "FEAR"
        if value > 0.7:
            return "NEUTRAL"
        return "COMPLACENT"
    if symbol == "$TRIN":
        if value > 2.0:
            return "PANIC_SELLING"
        if value > 1.2:
            return "BEARISH"
        if value > 0.8:
            return "NEUTRAL"
        return "BULLISH"
    # $VIX
    if value > 30:
        return "EXTREME"
    if value > 25:
        return "HIGH"
    if value > 20:
        return "ELEVATED"
    if value > 15:
        return "NORMAL"
    return "LOW"


def _signal_bp(value: float) -> str:
    if value >= 60:
        return "BULLISH"
    if value >= 40:
        return "NEUTRAL"
    return "BEARISH"


def _parse_float(s: str) -> float | None:
    if s is None:
        return None
    s = s.strip().lstrip(">").lstrip("<")
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def _collect_symbols(data: dict) -> dict:
    # Support test format (flat sym array)
    if "sym" in data:
        return {item["s"]: item for item in data["sym"]}

    # Real API format: sections containing symbol dicts with string values
    symbols = {}
    for section_name, section_data in data.items():
        if not isinstance(section_data, dict):
            continue
        for sym, item in section_data.items():
            if not isinstance(item, dict) or "close" not in item:
                continue
            symbols[sym] = item
    return symbols


def _get_value(symbols: dict, sym: str) -> tuple[float | None, float | None, str | None]:
    item = symbols.get(sym)
    if item is None:
        return None, None, None

    if "close" in item:
        return _parse_float(item["close"]), _parse_float(item.get("chg", "0")), item.get("name")
    return item.get("c"), item.get("ch", 0), item.get("n")


def _parse_response(data: dict) -> dict:
    symbols = _collect_symbols(data)

    mcclellan = {}
    for sym, key in _MCCLELLAN_KEYS.items():
        value, change, _ = _get_value(symbols, sym)
        if value is not None:
            mcclellan[key] = {
                "value": value,
                "change": change or 0,
                "signal": _signal_mcclellan(sym, value),
            }

    advance_decline = {}
    for sym, key in _AD_KEYS.items():
        value, change, _ = _get_value(symbols, sym)
        if value is not None:
            advance_decline[key] = {
                "value": value,
                "change": change or 0,
                "signal": _signal_ad(sym, value),
            }

    sentiment = {}
    for sym, key in _SENTIMENT_KEYS.items():
        value, change, _ = _get_value(symbols, sym)
        if value is not None:
            sentiment[key] = {
                "value": value,
                "change": change or 0,
                "signal": _signal_sentiment(sym, value),
            }

    bullish_pct = {}
    for sym, key in _BP_INDEX_KEYS.items():
        value, _, _ = _get_value(symbols, sym)
        if value is not None:
            bullish_pct[key] = value

    sectors = []
    for sym in sorted(_BP_SECTOR_SYMBOLS):
        value, _, name = _get_value(symbols, sym)
        if value is not None:
            sectors.append({
                "symbol": sym,
                "name": name or sym,
                "value": value,
                "signal": _signal_bp(value),
            })
    bullish_pct["sectors"] = sectors

    return {
        "mcclellan": mcclellan,
        "advance_decline": advance_decline,
        "sentiment": sentiment,
        "bullish_pct": bullish_pct,
    }


def _stale_result() -> dict | None:
    if _cache is None:
        return None
    age = time.time() - _cache_time
    if age >= _STALE_TTL:
        return None
    return _cache


def get_stockcharts_breadth() -> dict:
    global _cache, _cache_time

    now = time.time()
    if _cache is not None and (now - _cache_time) < _CACHE_TTL:
        return _cache

    try:
        url = "https://stockcharts.com/j-sum/sum?q=$NYMO"
        req = urllib.request.Request(url, headers={
            "Referer": "https://stockcharts.com/",
            "User-Agent": "Mozilla/5.0",
            "Accept-Encoding": "gzip",
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read()
            if raw[:2] == b'\x1f\x8b':
                raw = gzip.decompress(raw)
            data = json.loads(raw.decode("utf-8"))

        result = _parse_response(data)
        _cache = result
        _cache_time = time.time()
        return result
    except Exception as e:
        return {"error": str(e), "stale": _stale_result()}
