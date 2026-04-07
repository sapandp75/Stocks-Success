#!/usr/bin/env python3
"""Standalone CLI: Options Scanner for contrarian B1 candidates.

Usage:
    python cli/options_scan.py ADBE MSFT CRM          # Scan specific tickers
    python cli/options_scan.py ADBE --json             # JSON output
    python cli/options_scan.py ADBE --regime           # Include regime check first
"""
import argparse
import json
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.options_scanner import scan_tickers
from backend.services.regime_checker import get_full_regime
from backend.config import OPTIONS_PARAMS


def main():
    parser = argparse.ArgumentParser(description="Contrarian Options Scanner")
    parser.add_argument("tickers", nargs="+", help="Tickers to scan (e.g. ADBE MSFT)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--regime", action="store_true", help="Check regime first (Gate 0)")
    args = parser.parse_args()

    tickers = [t.strip().upper() for t in args.tickers]

    # Gate 0: regime check
    if args.regime:
        regime_data = get_full_regime()
        regime = regime_data["regime"]
        verdict = regime["verdict"]

        if not args.json:
            print(f"\n Gate 0 — Regime: {verdict} (Max positions: {regime['max_new_positions']})")

        if verdict in ("DEFENSIVE", "CASH"):
            if args.json:
                print(json.dumps({"error": f"Regime is {verdict} — no new positions", "regime": regime}, indent=2))
            else:
                print(f" *** BLOCKED: Regime is {verdict}. No new options positions. ***\n")
            sys.exit(1)

        if not args.json:
            vix_tax = regime.get("vix_tax", {})
            if vix_tax.get("premium_premium_pct", 0) > 0:
                print(f"   VIX Tax: +{vix_tax['premium_premium_pct']}% above normal premiums")
            print()

    # Scan
    results = scan_tickers(tickers)

    # Separate errors from valid results
    errors = [r for r in results if "error" in r]
    contracts = [r for r in results if "error" not in r]

    if args.json:
        output = {
            "scanned_tickers": tickers,
            "qualifying_contracts": contracts,
            "errors": errors,
            "filters": OPTIONS_PARAMS,
        }
        print(json.dumps(output, indent=2, default=str))
        return

    # Human-readable output
    print(f"\n{'='*70}")
    print(f" OPTIONS SCAN: {', '.join(tickers)}")
    print(f" Filters: {OPTIONS_PARAMS['min_dte']}-{OPTIONS_PARAMS['max_dte']} DTE | "
          f"Delta {OPTIONS_PARAMS['min_delta']}-{OPTIONS_PARAMS['max_delta']} | "
          f"OI >{OPTIONS_PARAMS['min_oi']} | "
          f"Premium <=${OPTIONS_PARAMS['max_premium_usd']}")
    print(f"{'='*70}")

    if errors:
        print(f"\n Errors:")
        for e in errors:
            print(f"   {e['ticker']}: {e['error']}")

    if not contracts:
        print(f"\n No qualifying contracts found.\n")
        return

    print(f"\n {len(contracts)} qualifying contract(s):\n")
    print(f" {'Ticker':<7} {'Strike':>8} {'Expiry':<12} {'DTE':>4} {'Delta':>6} "
          f"{'Ask':>6} {'GBP':>8} {'4x':>6} {'Move%':>7} {'OI':>6} {'Warnings'}")
    print(f" {'-'*7} {'-'*8} {'-'*12} {'-'*4} {'-'*6} {'-'*6} {'-'*8} {'-'*6} {'-'*7} {'-'*6} {'-'*15}")

    for c in contracts:
        warnings_str = ", ".join(c.get("warnings", [])) or "-"
        print(f" {c['ticker']:<7} {c['strike']:>8.1f} {c['expiry']:<12} {c['dte']:>4} "
              f"{c['delta']:>6.3f} {c['premium_usd']:>6.2f} "
              f"£{c['premium_gbp']:>6.2f} {c['target_4x']:>6.2f} "
              f"{c['required_move_pct']*100:>6.1f}% {c['open_interest']:>6} {warnings_str}")

    print()


if __name__ == "__main__":
    main()
