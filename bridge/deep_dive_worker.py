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
    parser.add_argument("--context", action="store_true", help="Print research context for Claude to use in analysis")
    parser.add_argument("--tv", action="store_true", help="Include TradingView indicator snapshot in context (requires MCP servers)")
    args = parser.parse_args()

    ticker = args.ticker.upper()

    if args.tv:
        print(f"=== TradingView Indicator Snapshot for {ticker} ===")
        try:
            from tradingview_ta import TA_Handler, Interval
            handler = TA_Handler(
                symbol=ticker, screener="america", exchange="NASDAQ",
                interval=Interval.INTERVAL_1_DAY,
            )
            analysis = handler.get_analysis()
            print(f"Summary: BUY={analysis.summary['BUY']} SELL={analysis.summary['SELL']} NEUTRAL={analysis.summary['NEUTRAL']}")
            print(f"Recommendation: {analysis.summary['RECOMMENDATION']}")
            indicators = analysis.indicators
            for key in ["RSI", "MACD.macd", "MACD.signal", "Stoch.K", "Stoch.D",
                         "ADX", "CCI20", "ATR", "Volatility.D", "EMA20", "SMA50", "SMA200",
                         "BB.upper", "BB.lower", "Pivot.M.Classic.S1", "Pivot.M.Classic.R1"]:
                val = indicators.get(key)
                if val is not None:
                    print(f"  {key}: {val}")
        except Exception as e:
            # Try NYSE if NASDAQ fails
            try:
                handler = TA_Handler(
                    symbol=ticker, screener="america", exchange="NYSE",
                    interval=Interval.INTERVAL_1_DAY,
                )
                analysis = handler.get_analysis()
                print(f"Summary: BUY={analysis.summary['BUY']} SELL={analysis.summary['SELL']} NEUTRAL={analysis.summary['NEUTRAL']}")
                print(f"Recommendation: {analysis.summary['RECOMMENDATION']}")
                indicators = analysis.indicators
                for key in ["RSI", "MACD.macd", "MACD.signal", "Stoch.K", "Stoch.D",
                             "ADX", "CCI20", "ATR", "EMA20", "SMA50", "SMA200",
                             "BB.upper", "BB.lower", "Pivot.M.Classic.S1", "Pivot.M.Classic.R1"]:
                    val = indicators.get(key)
                    if val is not None:
                        print(f"  {key}: {val}")
            except Exception as e2:
                print(f"TradingView data unavailable: {e2}", file=sys.stderr)
        # --tv can combine with --context
        if not args.context and not args.get and not args.post:
            return

    if args.context:
        from backend.services.research import get_research_for_claude
        from backend.services.transcripts import get_transcript_for_claude
        context = get_research_for_claude(ticker)
        transcript = get_transcript_for_claude(ticker)
        print(context)
        if transcript:
            print("\n" + transcript)

        # Enriched context: technicals, financials, insider, analyst, peers
        try:
            from backend.services.technicals import get_full_technicals
            tech = get_full_technicals(ticker)
            print(f"\n=== Technical Analysis for {ticker} ===")
            print(f"Direction: {tech.get('direction')} | RSI: {tech.get('rsi')} | ADX: {tech.get('adx')}")
            print(f"MACD: {tech.get('macd_value')} (signal: {tech.get('macd_signal')}, crossover: {tech.get('macd_crossover')})")
            print(f"Bollinger %B: {tech.get('bollinger_pct_b')} | Volume: {tech.get('volume_trend')} (rel: {tech.get('volume_relative')})")
            print(f"Support: {tech.get('support')} | Resistance: {tech.get('resistance')}")
            print(f"RS vs SPY: 20d={tech.get('rs_vs_spy_20d')}, 60d={tech.get('rs_vs_spy_60d')}")
        except Exception:
            pass

        try:
            from backend.services.financial_history import get_financial_history
            fh = get_financial_history(ticker)
            print(f"\n=== 5-Year Financial History for {ticker} ===")
            for metric in ["revenue", "operating_margin", "net_margin", "free_cash_flow", "debt_to_equity"]:
                entries = fh.get(metric, [])
                if entries:
                    vals = ", ".join(f"{e['year']}: {e['value']}" for e in entries[:5])
                    print(f"  {metric}: {vals}")
        except Exception:
            pass

        try:
            from backend.services.institutional import get_insider_activity, get_institutional_summary
            ins = get_insider_activity(ticker)
            inst = get_institutional_summary(ticker)
            print(f"\n=== Insider & Institutional for {ticker} ===")
            print(f"Insider sentiment: {ins.get('net_sentiment')}")
            for n in ins.get("notable", [])[:3]:
                print(f"  Notable: {n.get('name')} — {n.get('shares')} shares (${n.get('value', 0):,.0f})")
            print(f"Institutional %: {inst.get('institutional_pct')}% | Trend: {inst.get('trend')}")
        except Exception:
            pass

        try:
            from backend.services.sentiment import get_analyst_data
            a = get_analyst_data(ticker)
            print(f"\n=== Analyst Data for {ticker} ===")
            print(f"Consensus: {a.get('consensus')} | Target: ${a.get('target_low')}-${a.get('target_high')} (mean ${a.get('target_mean')})")
            print(f"Contrarian signal: {a.get('contrarian_signal')}")
        except Exception:
            pass

        return

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
