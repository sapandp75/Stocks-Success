#!/usr/bin/env python3
"""
Deep Dive Bridge — CLI tool for Claude Code to POST analysis to the local API.

Usage (from Claude Code):
    python bridge/deep_dive_worker.py ADBE --post

This script:
1. Reads a JSON payload from stdin (piped from Claude Code)
2. POSTs it to http://localhost:8000/api/deep-dive/ADBE
3. The dashboard then renders the AI analysis in the 8-section view

Example JSON payload (Claude Code generates this):
{
    "first_impression": "...",
    "bear_case_stock": "...",
    "bear_case_business": "...",
    "bull_case_rebuttal": "...",
    "bull_case_upside": "...",
    "whole_picture": "...",
    "self_review": "...",
    "verdict": "B1 — HIGH conviction",
    "conviction": "HIGH",
    "entry_grid": [...],
    "exit_playbook": "..."
}
"""
import sys
import json
import argparse
import httpx

API_BASE = "http://localhost:8000"


def post_analysis(ticker: str, payload: dict):
    url = f"{API_BASE}/api/deep-dive/{ticker}"
    response = httpx.post(url, json=payload, timeout=10)
    if response.status_code == 200:
        print(f"Analysis saved for {ticker}. Refresh dashboard to view.")
    else:
        print(f"Error: {response.status_code} — {response.text}", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Deep Dive Bridge for Claude Code")
    parser.add_argument("ticker", help="Stock ticker (e.g. ADBE)")
    parser.add_argument("--post", action="store_true", help="POST analysis from stdin")
    parser.add_argument("--get", action="store_true", help="GET current data for ticker")
    args = parser.parse_args()

    ticker = args.ticker.upper()

    if args.get:
        response = httpx.get(f"{API_BASE}/api/deep-dive/{ticker}", timeout=30)
        print(json.dumps(response.json(), indent=2, default=str))

    elif args.post:
        print(f"Reading analysis JSON from stdin for {ticker}...")
        payload = json.load(sys.stdin)
        post_analysis(ticker, payload)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
