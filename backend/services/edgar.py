"""SEC EDGAR integration via edgartools — filings, insider transactions, 13F holders."""

import json
import logging
from backend.database import get_db, is_fresh
from backend.config import ENRICHMENT_CONFIG

logger = logging.getLogger(__name__)

_EDGAR_CACHE_TTL = ENRICHMENT_CONFIG.get("insider_ttl_hours", 6)


def get_sec_filings(ticker: str, filing_types: list[str] | None = None, limit: int = 5) -> list[dict]:
    """Fetch recent SEC filings (10-K, 10-Q, 8-K) for a ticker."""
    if filing_types is None:
        filing_types = ["10-K", "10-Q", "8-K"]

    try:
        from edgar import Company

        company = Company(ticker)
        filings = company.get_filings()

        results = []
        for f in filings:
            if len(results) >= limit:
                break
            form = getattr(f, "form", "")
            if form in filing_types:
                results.append({
                    "form": form,
                    "filing_date": str(getattr(f, "filing_date", "")),
                    "description": getattr(f, "description", "") or f"{form} Filing",
                    "accession_number": getattr(f, "accession_number", ""),
                })
        return results
    except Exception as e:
        logger.warning("Failed to fetch SEC filings for %s: %s", ticker, e)
        return []


def get_insider_transactions_edgar(ticker: str) -> dict:
    """Fetch insider transactions from SEC EDGAR Form 4 filings."""
    try:
        from edgar import Company

        company = Company(ticker)
        filings = company.get_filings(form="4")

        transactions = []
        buy_count = 0
        sell_count = 0

        for f in list(filings)[:20]:
            try:
                form = f.obj()
                if not hasattr(form, "transactions"):
                    continue
                for txn in form.transactions:
                    is_buy = getattr(txn, "acquired_disposed", "") == "A"
                    shares = getattr(txn, "shares", 0) or 0
                    if is_buy:
                        buy_count += 1
                    else:
                        sell_count += 1
                    transactions.append({
                        "insider": getattr(txn, "owner_name", "Unknown"),
                        "title": getattr(txn, "owner_title", ""),
                        "type": "BUY" if is_buy else "SELL",
                        "shares": shares,
                        "date": str(getattr(f, "filing_date", "")),
                    })
            except Exception:
                continue

        if buy_count + sell_count == 0:
            sentiment = "NO DATA"
        elif buy_count > sell_count:
            sentiment = "NET BUYING"
        elif sell_count > buy_count:
            sentiment = "NET SELLING"
        else:
            sentiment = "NEUTRAL"

        return {
            "transactions": transactions[:10],
            "buy_count": buy_count,
            "sell_count": sell_count,
            "net_sentiment": sentiment,
            "source": "SEC EDGAR Form 4",
        }
    except Exception as e:
        logger.warning("Failed to fetch EDGAR insider data for %s: %s", ticker, e)
        return {"transactions": [], "net_sentiment": "UNAVAILABLE", "source": "SEC EDGAR"}


def get_institutional_holders_13f(ticker: str) -> dict:
    """Fetch top institutional holders from 13F filings via edgartools."""
    try:
        from edgar import Company

        company = Company(ticker)
        filings = company.get_filings(form="13F-HR")

        holders = []
        latest = list(filings)[:3]

        for f in latest:
            try:
                form = f.obj()
                if hasattr(form, "holdings"):
                    for h in list(form.holdings)[:15]:
                        name = getattr(h, "name", "") or getattr(h, "manager_name", "Unknown")
                        value = getattr(h, "value", 0) or 0
                        shares = getattr(h, "shares", 0) or 0
                        holders.append({
                            "fund_name": name,
                            "shares": shares,
                            "value_usd": value,
                            "filing_date": str(getattr(f, "filing_date", "")),
                        })
                    break  # Only need the latest filing
            except Exception:
                continue

        # Deduplicate and sort by value
        seen = set()
        unique = []
        for h in holders:
            key = h["fund_name"]
            if key not in seen:
                seen.add(key)
                unique.append(h)
        unique.sort(key=lambda x: x.get("value_usd", 0), reverse=True)

        return {
            "top_holders": unique[:10],
            "total_holders_found": len(unique),
            "source": "SEC EDGAR 13F-HR",
        }
    except Exception as e:
        logger.warning("Failed to fetch 13F holders for %s: %s", ticker, e)
        return {"top_holders": [], "total_holders_found": 0, "source": "SEC EDGAR"}


def get_edgar_context(ticker: str) -> dict:
    """Get combined SEC EDGAR data for deep dive context."""
    return {
        "filings": get_sec_filings(ticker),
        "insider_transactions": get_insider_transactions_edgar(ticker),
        "institutional_13f": get_institutional_holders_13f(ticker),
    }
