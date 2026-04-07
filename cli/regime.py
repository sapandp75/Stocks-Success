#!/usr/bin/env python3
"""Standalone CLI: Market Regime Check (Gate 0).

Usage:
    python cli/regime.py          # Human-readable output
    python cli/regime.py --json   # Machine-readable JSON
"""
import argparse
import json
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.services.regime_checker import get_full_regime, calculate_market_breadth


def main():
    parser = argparse.ArgumentParser(description="Market Regime Check — Gate 0")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--breadth", action="store_true", help="Include market breadth (slower)")
    args = parser.parse_args()

    regime_data = get_full_regime()
    regime = regime_data["regime"]
    spy = regime_data["spy"]
    qqq = regime_data["qqq"]

    breadth = None
    if args.breadth:
        breadth = calculate_market_breadth()

    if args.json:
        output = {**regime_data}
        if breadth:
            output["breadth"] = breadth
        print(json.dumps(output, indent=2, default=str))
        return

    # Human-readable output
    verdict = regime["verdict"]
    verdict_colors = {"DEPLOY": "\033[92m", "CAUTIOUS": "\033[93m",
                      "DEFENSIVE": "\033[91m", "CASH": "\033[91m"}
    reset = "\033[0m"
    color = verdict_colors.get(verdict, "")

    print(f"\n{'='*50}")
    print(f" MARKET REGIME: {color}{verdict}{reset}")
    print(f" Max New Positions: {regime['max_new_positions']}")
    print(f"{'='*50}")
    print(f"\n SPY: {spy['direction']}")
    print(f"   Price: ${spy['price']:.2f}  |  EMA20: ${spy['ema20']:.2f}  |  SMA50: ${spy['sma50']:.2f}  |  SMA200: ${spy['sma200']:.2f}")
    print(f"\n QQQ: {qqq['direction']}")
    print(f"   Price: ${qqq['price']:.2f}  |  EMA20: ${qqq['ema20']:.2f}  |  SMA50: ${qqq['sma50']:.2f}  |  SMA200: ${qqq['sma200']:.2f}")
    print(f"\n VIX: {regime['vix']}")
    vix_tax = regime.get("vix_tax", {})
    if vix_tax.get("premium_premium_pct", 0) > 0:
        print(f"   VIX Tax: +{vix_tax['premium_premium_pct']}% premium above normal")
    print(f"   {vix_tax.get('note', '')}")
    print(f"\n Score: {regime['score']}")

    if breadth:
        print(f"\n Market Breadth:")
        print(f"   Above 200d SMA: {breadth.get('pct_above_200d', 'N/A')}%")
        print(f"   Above 50d SMA: {breadth.get('pct_above_50d', 'N/A')}%")
        print(f"   Signal: {breadth.get('breadth_signal', 'UNKNOWN')}")
        print(f"   Sample: {breadth.get('sample_size', 0)} stocks")

    if verdict in ("DEFENSIVE", "CASH"):
        print(f"\n{color} *** NO NEW POSITIONS — regime gate CLOSED ***{reset}")
    elif verdict == "CAUTIOUS":
        print(f"\n{color} *** Max 2 new positions — high conviction B1 only ***{reset}")

    print()


if __name__ == "__main__":
    main()
