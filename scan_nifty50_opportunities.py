#!/usr/bin/env python3
"""Run NIFTY 50 Short-Term Swing Opportunity Scanner.

Analyzes all 50 constituent stocks of the NIFTY 50 index (NSE India),
identifies the top 1–3 strongest short-term swing trading opportunities
(1–2 trading day holding period, ~1.0% to 1.5% profit target),
structures exact trigger levels, stop losses, derivative suggestions,
and generates deep, human-readable evidence on 'WHY THIS STOCK?'.

Usage:
    python scan_nifty50_opportunities.py
    python scan_nifty50_opportunities.py --top-n 3 --capital 500000 --risk 1.0
"""

import argparse
import sys
import os

# Fix UTF-8 encoding on Windows terminals for Indian Rupee symbol
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure project root is in python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

from tradingagents.swing_opportunity import SwingOpportunityEngine
from tradingagents.default_config import DEFAULT_CONFIG


def main():
    parser = argparse.ArgumentParser(
        description="Scan NIFTY 50 for 1-2 Day Swing Trade Setups (~1.0% to 1.5% Target)"
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=3,
        help="Number of top opportunities to select (default: 3)",
    )
    parser.add_argument(
        "--capital",
        type=float,
        default=500000.0,
        help="Account trading capital in INR (default: 500,000)",
    )
    parser.add_argument(
        "--risk",
        type=float,
        default=1.0,
        help="Portfolio risk percentage per trade (default: 1.0%%)",
    )
    parser.add_argument(
        "--benchmark",
        type=str,
        default="^NSEI",
        help="Benchmark index ticker (default: ^NSEI)",
    )

    args = parser.parse_args()

    engine = SwingOpportunityEngine(
        account_capital=args.capital,
        risk_per_trade_pct=args.risk,
        benchmark_ticker=args.benchmark,
        config=DEFAULT_CONFIG,
    )

    opportunities = engine.run(top_n=args.top_n)

    if not opportunities:
        print("[!] No high-conviction swing opportunities met the criteria today.")
        sys.exit(0)

    print(f"[+] Successfully identified and structured {len(opportunities)} NIFTY 50 swing trade setups.")


if __name__ == "__main__":
    main()
