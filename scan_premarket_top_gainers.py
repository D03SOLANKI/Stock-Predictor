#!/usr/bin/env python3
"""Pre-Market NSE Mid-Cap & Small-Cap Top Gainer Discovery Scanner (10/10 Architecture).

Analyzes the NSE Mid-Cap & Small-Cap universe before the Indian market opens
(8:00 AM – 9:15 AM IST). Evaluates:
- Tier 0: Market Regime Gate on NIFTY Midcap 100
- Tier 1: Hard Disqualification Gates (Series EQ, >= ₹10 Cr Turnover, Circuit Headroom)
- Tier 2: Continuous 100-Point Scoring (VCP coiling, supply dry-up, midcap alpha, blue-sky)
Structures exact day-runner breakout levels (+3.5% & +6.5% targets), stop loss,
and comprehensive multi-pillar technical evidence.

Usage:
    python scan_premarket_top_gainers.py
    python scan_premarket_top_gainers.py --top-n 3 --capital 500000 --risk 1.0
"""

import argparse
import datetime
import os
import sys

# Ensure UTF-8 output on Windows terminals
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

from tradingagents.swing_opportunity import (
    PreMarketTopGainerScreener,
    DayGainerStructurer,
    SwingEvidenceAgent,
)
from tradingagents.default_config import DEFAULT_CONFIG


def run_premarket_scan(
    top_n: int = 3,
    account_capital: float = 500000.0,
    risk_per_trade_pct: float = 1.0,
    min_turnover_cr: float = 10.0,
    bypass_regime: bool = False,
):
    print("\n" + "=" * 85)
    print("  DALAL STREET PRE-MARKET TOP-GAINER DISCOVERY ENGINE (10/10 ARCHITECTURE)")
    print(f"  Target Profile: Day Top Gainers (+3.5% to +7.0% Explosive Momentum)")
    print(f"  Universe: NSE Mid-Cap & Small-Cap Active Leaders | Series: EQ Only")
    print(f"  Liquidity Floor: \u2265 \u20b9{min_turnover_cr:.1f} Crore Daily Turnover | Risk Budget: {risk_per_trade_pct}% of \u20b9{account_capital:,.0f}")
    print("=" * 85 + "\n")

    screener = PreMarketTopGainerScreener(
        min_turnover_crores=min_turnover_cr,
    )
    structurer = DayGainerStructurer(
        account_capital=account_capital,
        risk_per_trade_pct=risk_per_trade_pct,
    )
    evidence_agent = SwingEvidenceAgent(config=DEFAULT_CONFIG)

    # 1. Screen Universe
    print("[*] Phase 1: Ingesting Daily OHLCV data & evaluating Tier-0 Macro Regime...")
    scan_results = screener.scan(top_n=top_n, bypass_regime_halt=bypass_regime)

    regime = scan_results["regime"]
    print(f"\n[+] TIER-0 MARKET REGIME STATUS: [{regime['regime']}]")
    print(f"    {regime['message']}")
    print(f"    Risk Multiplier: {regime['risk_multiplier']}x | Min Score Required: {regime['min_score_required']}/100")

    macro_gate = scan_results.get("macro_gate", {})
    if macro_gate:
        print(f"\n[+] TIER-0 MACRO GATE (Recommendation 1): [{macro_gate.get('status', 'PASS')}]")
        print(f"    {macro_gate.get('message', '')}")

    if scan_results.get("halted"):
        print(f"\n[!] SYSTEM HALT: {scan_results.get('reason')}")
        print("[!] To bypass and inspect setups anyway, run with --bypass-regime\n")
        return []

    candidates = scan_results["candidates"]
    total_screened = scan_results.get("total_screened", len(screener.tickers))
    passed_gates = scan_results.get("passed_hard_gates", len(candidates))

    print(f"\n[+] TIER-1 HARD GATES: {passed_gates}/{total_screened} stocks passed \u2265\u20b910 Cr turnover & EQ-series checks.")
    print(f"[+] TIER-2 SCORING (PRIORITY QUEUE): Top {len(candidates)} high-probability candidates isolated:")
    for idx, c in enumerate(candidates, 1):
        queue_role = "Rank 1 (Primary)" if idx == 1 else f"Rank {idx} (Fallback)"
        print(f"    {idx}. [{queue_role}] {c['stock_name']} ({c['ticker']}) - Score: {c['composite_score']}/100 | CMP: \u20b9{c['close']:,.2f} | 20d Turnover: \u20b9{c['avg_turnover_cr_20d']:,.1f} Cr")

    # 2. Structure Trades & Generate Narratives
    print(f"\n[*] Phase 2: Structuring Day-Runner Trade Setups & Generating Evidence...")
    structured_trades = []

    for c in candidates:
        structured = structurer.structure_trade(c, risk_multiplier=regime["risk_multiplier"])
        narrative = evidence_agent.generate_top_gainer_narrative(structured)
        structured["why_this_stock"] = narrative
        structured_trades.append(structured)

    # 3. Render Pre-Market Trade Cards
    for idx, trade in enumerate(structured_trades, 1):
        c = trade["screening_metrics"]
        bd = c["score_breakdown"]
        pos = trade["position_sizing"]
        rules = trade["premarket_rules"]
        queue_header = "PRIMARY TRADE CANDIDATE (RANK 1)" if idx == 1 else f"FALLBACK TRADE CANDIDATE (RANK {idx})"

        border = "#" * 85
        print(f"\n{border}")
        print(f"  PRE-MARKET PICK #{idx} [{queue_header}]: {trade['stock_name']} ({trade['ticker']}) - [{trade['tier']}]")
        print(f"  Sector: {trade['sector']} | Composite Score: {c['composite_score']} / 100")
        print(f"{border}")
        print(f"  Current Market Price (CMP):     \u20b9{trade['current_market_price']:,.2f}")
        print(f"  BUY Above Trigger Level:        \u20b9{trade['buy_above_trigger']:,.2f} (Breakout of Previous High)")
        print(f"  Execution Entry Zone:           {trade['entry_range']['formatted']}")
        print(f"  Structural Stop Loss (SL):      {trade['stop_loss']['formatted']}")
        print(f"  Target 1 (+{trade['target_1']['gain_pct']:.1f}%):               {trade['target_1']['formatted']} (R:R {trade['target_1']['rr_ratio']})")
        print(f"  Target 2 (+{trade['target_2']['gain_pct']:.1f}%):               {trade['target_2']['formatted']} (R:R {trade['target_2']['rr_ratio']})")
        if "trailing_stop" in trade:
            print(f"  Trailing Stop (Rec 3):          {trade['trailing_stop']['formatted']}")
        print(f"  Risk-to-Reward Summary:         {trade['risk_reward_summary']}")
        print(f"  Holding Window:                 {trade['holding_period']}")
        print(f"{'-' * 85}")
        print(f"  QUANTITATIVE PILLAR SCORECARD (100-PT MODEL):")
        print(f"  - Volatility Contraction (VCP/NR7):  {bd['volatility_coiling']} / 30 pts (NR7: {c['is_nr7']}, Inside Bar: {c['is_inside_day']})")
        print(f"  - Relative Strength (Midcap Alpha):  {bd['relative_strength']} / 30 pts (Alpha: {c['rs_alpha']:+.2f}%, 14d ADR: {c['adr_pct']:.2f}%)")
        print(f"  - Volume & Supply Exhaustion (VDU):  {bd['volume_footprint']} / 20 pts (VDU: {c['is_vdu']}, 20d Turnover: \u20b9{c['avg_turnover_cr_20d']} Cr)")
        print(f"  - Blue-Sky Clearance (Resistance):   {bd['blue_sky_clearance']} / 20 pts (From 52w High: {c['pct_from_52w']:.1f}%, CLV: {c['clv']:.2f})")
        print(f"{'-' * 85}")
        print(f"  POSITION SIZING (1% Risk Budget = \u20b9{pos['max_risk_allowed']:,.0f}):")
        print(f"  - Recommended Shares:           {pos['recommended_shares']} shares")
        print(f"  - Capital Outlay:               \u20b9{pos['total_cash_outlay']:,.2f}")
        print(f"  - Max Downside Risk:            \u20b9{pos['actual_risk_rupees']:,.2f} ({pos['portfolio_risk_pct']:.2f}% of portfolio)")
        print(f"{'-' * 85}")
        print(f"  PRE-MARKET RULES & GAP-TRAP INVALIDATION:")
        print(f"  - Opening Action:               {rules['opening_rule']}")
        for rule in rules["invalidation_rules"]:
            print(f"  - {rule}")
        print(f"{'-' * 85}")
        print(f"  EVIDENCE BEHIND THE TRADE: WHY THIS STOCK WILL BE A TOP GAINER TODAY")
        print(f"{'-' * 85}")
        print(trade["why_this_stock"])
        print(f"{border}\n")

    # 4. Save Markdown Report
    reports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results", "premarket_reports")
    os.makedirs(reports_dir, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(reports_dir, f"premarket_top_gainers_{timestamp}.md")

    md_lines = [
        f"# NSE Mid & Small-Cap Pre-Market Top-Gainer Intelligence Report",
        f"**Generated Date/Time:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}  ",
        f"**Market Regime:** {regime['regime']} ({regime['message']})  ",
        f"**Strategy Profile:** Day Top Gainer (+3.5% to +6.5% Intraday Expansion)  ",
        f"**Account Capital Base:** \u20b9{account_capital:,.2f} | **Risk Budget:** {risk_per_trade_pct}%  ",
        f"**Liquidity Floor:** \u2265 \u20b9{min_turnover_cr:.1f} Crore Daily Turnover | **Series:** EQ Only\n",
        "---\n",
    ]

    for idx, trade in enumerate(structured_trades, 1):
        c = trade["screening_metrics"]
        pos = trade["position_sizing"]
        rules = trade["premarket_rules"]

        md_lines.append(f"## Top Pick #{idx}: {trade['stock_name']} (`{trade['ticker']}`)")
        md_lines.append(f"- **Sector:** {trade['sector']} | **Tier:** {trade['tier']}")
        md_lines.append(f"- **Current Market Price (CMP):** \u20b9{trade['current_market_price']:,.2f}")
        md_lines.append(f"- **BUY Above Trigger:** **\u20b9{trade['buy_above_trigger']:,.2f}**")
        md_lines.append(f"- **Execution Entry Band:** {trade['entry_range']['formatted']}")
        md_lines.append(f"- **Stop Loss:** **{trade['stop_loss']['formatted']}**")
        md_lines.append(f"- **Target 1 (+3.5%):** **{trade['target_1']['formatted']}** (Book 50%, trail SL to cost)")
        md_lines.append(f"- **Target 2 (+6.5%):** **{trade['target_2']['formatted']}** (Full day-runner target)")
        md_lines.append(f"- **Risk-to-Reward Ratio:** {trade['risk_reward_summary']}")
        md_lines.append(f"- **Position Allocation:** {pos['recommended_shares']} shares (\u20b9{pos['total_cash_outlay']:,.2f} outlay, max risk \u20b9{pos['actual_risk_rupees']:,.2f})\n")

        md_lines.append("### Quantitative Pillar Scorecard")
        md_lines.append("| Metric | Value | Threshold / Note |")
        md_lines.append("| :--- | :--- | :--- |")
        md_lines.append(f"| **Composite Score** | **{c['composite_score']}/100** | Top gainer probability |")
        md_lines.append(f"| **20-Day Avg Turnover** | \u20b9{c['avg_turnover_cr_20d']:.1f} Cr | High institutional liquidity (\u2265\u20b910 Cr) |")
        md_lines.append(f"| **14-Day ADR%** | {c['adr_pct']:.2f}% | High expansion capacity |")
        md_lines.append(f"| **From 52-Week High** | {c['pct_from_52w']:.1f}% | Blue-sky clearance |")
        md_lines.append(f"| **Alpha vs Midcap 100** | {c['rs_alpha']:+.2f}% | Relative strength leadership |")
        md_lines.append(f"| **Volume Dry-Up (VDU)** | {c['volume_ratio']:.2f}x | Supply exhaustion signature |\n")

        md_lines.append("### Pre-Market Rules & Invalidation")
        for r in rules["invalidation_rules"]:
            md_lines.append(f"- {r}")
        md_lines.append("")

        md_lines.append("### Evidence Narrative: WHY This Stock Will Be a Top Gainer Today")
        md_lines.append(f"{trade['why_this_stock']}\n")
        md_lines.append("---\n")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(md_lines))

    print(f"[+] Complete Pre-Market Intelligence Report saved to: {filepath}\n")
    return structured_trades


def main():
    parser = argparse.ArgumentParser(
        description="Pre-Market NSE Mid & Small-Cap Top Gainer Discovery Scanner"
    )
    parser.add_argument("--top-n", type=int, default=3, help="Number of top gainers to select (default: 3)")
    parser.add_argument("--capital", type=float, default=500000.0, help="Account capital in INR (default: 500,000)")
    parser.add_argument("--risk", type=float, default=1.0, help="Portfolio risk percentage per trade (default: 1.0%%)")
    parser.add_argument("--min-turnover", type=float, default=10.0, help="Minimum 20-day avg turnover in Crore (default: 10.0)")
    parser.add_argument("--bypass-regime", action="store_true", help="Bypass Tier-0 regime halt to inspect setups")

    args = parser.parse_args()
    run_premarket_scan(
        top_n=args.top_n,
        account_capital=args.capital,
        risk_per_trade_pct=args.risk,
        min_turnover_cr=args.min_turnover,
        bypass_regime=args.bypass_regime,
    )


if __name__ == "__main__":
    main()
