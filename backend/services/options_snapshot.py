"""
Options snapshot for deep dive: put/call ratio, short interest, and LEAPS premiums.
"""
import math
import yfinance as yf
from datetime import datetime, timedelta
from scipy.stats import norm


def _safe_float(val, default=0.0):
    """Convert to float, treating None/NaN as default."""
    if val is None:
        return default
    try:
        f = float(val)
        return default if math.isnan(f) else f
    except (TypeError, ValueError):
        return default


def _bs_delta(S, K, T, r, sigma):
    """Black-Scholes call delta."""
    if T <= 0 or sigma <= 0 or S <= 0:
        return 0.0
    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    return float(norm.cdf(d1))


def get_options_snapshot(ticker: str) -> dict:
    """Fetch put/call ratio + LEAPS OTM calls for deep dive."""
    stock = yf.Ticker(ticker)
    info = stock.info or {}
    price = info.get("currentPrice") or info.get("regularMarketPrice") or 0

    result = {
        "put_call_ratio_oi": None,
        "put_call_ratio_vol": None,
        "total_call_oi": None,
        "total_put_oi": None,
        "short_interest": info.get("sharesShort"),
        "short_pct_float": info.get("shortPercentOfFloat"),
        "short_ratio_days": info.get("shortRatio"),
        "leaps": [],
    }

    try:
        expirations = stock.options
    except Exception:
        return result

    if not expirations:
        return result

    now = datetime.now()
    total_call_oi = 0
    total_put_oi = 0
    total_call_vol = 0
    total_put_vol = 0

    # Find LEAPS expiry: closest to 1 year out (280-400 DTE)
    leaps_expiry = None
    leaps_dte = None
    for exp in expirations:
        exp_dt = datetime.strptime(exp, "%Y-%m-%d")
        dte = (exp_dt - now).days
        if 250 <= dte <= 420:
            if leaps_expiry is None or abs(dte - 365) < abs(leaps_dte - 365):
                leaps_expiry = exp
                leaps_dte = dte

    for exp in expirations:
        exp_dt = datetime.strptime(exp, "%Y-%m-%d")
        dte = (exp_dt - now).days
        if dte < 1:
            continue

        try:
            chain = stock.option_chain(exp)
        except Exception:
            continue

        calls_df = chain.calls
        puts_df = chain.puts

        call_oi = int(calls_df["openInterest"].sum()) if "openInterest" in calls_df else 0
        put_oi = int(puts_df["openInterest"].sum()) if "openInterest" in puts_df else 0
        call_vol = int(calls_df["volume"].fillna(0).sum()) if "volume" in calls_df else 0
        put_vol = int(puts_df["volume"].fillna(0).sum()) if "volume" in puts_df else 0

        total_call_oi += call_oi
        total_put_oi += put_oi
        total_call_vol += call_vol
        total_put_vol += put_vol

        # Extract LEAPS calls
        if exp == leaps_expiry and price > 0:
            T = dte / 365.0
            for _, row in calls_df.iterrows():
                strike = row.get("strike", 0)
                if strike <= 0 or strike <= price:
                    continue  # skip ITM
                otm_pct = (strike - price) / price
                if otm_pct > 0.60:
                    continue  # skip very far OTM

                raw_bid = row.get("bid", 0)
                raw_ask = row.get("ask", 0)
                bid = _safe_float(raw_bid)
                ask = _safe_float(raw_ask)
                last = _safe_float(row.get("lastPrice", 0))

                # Derive mid; estimate bid/ask from lastPrice if missing
                if bid > 0 and ask > 0:
                    mid = (bid + ask) / 2
                elif last > 0:
                    mid = last
                    # Estimate bid/ask with ~5% spread around lastPrice
                    bid = round(last * 0.975, 2) if bid == 0 else bid
                    ask = round(last * 1.025, 2) if ask == 0 else ask
                else:
                    continue  # no usable price data

                oi = int(_safe_float(row.get("openInterest", 0)))
                vol = int(_safe_float(row.get("volume", 0)))
                raw_iv = _safe_float(row.get("impliedVolatility", 0))

                # IV < 15% for equity LEAPS is almost certainly stale; use 35% fallback
                iv = raw_iv if raw_iv > 0.15 else 0.35
                delta = _bs_delta(price, strike, T, 0.04, iv)

                if oi < 50:
                    continue  # skip illiquid

                premium_usd = mid * 100  # per contract
                result["leaps"].append({
                    "expiry": exp,
                    "dte": dte,
                    "strike": strike,
                    "otm_pct": round(otm_pct * 100, 1),
                    "bid": bid,
                    "ask": ask,
                    "mid": round(mid, 2),
                    "premium_per_contract": round(premium_usd, 0),
                    "oi": oi,
                    "volume": vol,
                    "iv": round(iv * 100, 1),
                    "delta": round(delta, 3),
                })

    # Compute ratios
    if total_call_oi > 0:
        result["put_call_ratio_oi"] = round(total_put_oi / total_call_oi, 3)
    if total_call_vol > 0:
        result["put_call_ratio_vol"] = round(total_put_vol / total_call_vol, 3)
    result["total_call_oi"] = total_call_oi
    result["total_put_oi"] = total_put_oi

    # Sort LEAPS by strike
    result["leaps"].sort(key=lambda x: x["strike"])

    return result
