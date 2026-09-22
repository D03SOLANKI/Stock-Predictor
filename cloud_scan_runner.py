#!/usr/bin/env python3
"""Cloud scan runner for GitHub Actions.
Runs the pre-market scan and saves results to results/latest_scan.json
so the local dashboard can pick it up when the PC turns on.
"""
import sys
import os
import json
import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tradingagents.swing_opportunity.premarket_screener import PreMarketTopGainerScreener
from tradingagents.swing_opportunity.day_gainer_structurer import DayGainerStructurer

os.makedirs("results", exist_ok=True)

print("=" * 65)
print("  NSE PRE-MARKET AUTO-SCAN (GitHub Actions Cloud Run)")
print("  Time: " + datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC") + " = 8:45 AM IST")
print("=" * 65)

screener = PreMarketTopGainerScreener(min_turnover_crores=10.0)
results = screener.scan(top_n=3, bypass_regime_halt=True)

candidates = results.get("candidates", [])
regime = results.get("regime", {})

structurer = DayGainerStructurer(account_capital=100000.0, risk_per_trade_pct=2.0)

output = {
    "scan_date": datetime.datetime.utcnow().strftime("%Y-%m-%d"),
    "scan_time_utc": datetime.datetime.utcnow().strftime("%H:%M"),
    "scan_time_ist": "08:45",
    "regime": regime,
    "candidates": candidates,
    "structured_trades": []
}

summary_lines = [
    "NSE PRE-MARKET SCAN - " + datetime.datetime.utcnow().strftime("%Y-%m-%d") + " (8:45 AM IST)",
    "=" * 55,
    "Market Regime: " + regime.get("regime_label", regime.get("regime", "Unknown")),
    ""
]

if not candidates:
    summary_lines.append("No qualifying candidates found today.")
    print("No candidates found.")
else:
    labels = ["#1 PRIMARY PICK", "#2 FALLBACK PICK", "#3 STANDBY RUNNER"]
    for i, c in enumerate(candidates, 1):
        trade = structurer.structure_trade(c, risk_multiplier=regime.get("risk_multiplier", 1.0))
        output["structured_trades"].append(trade)

        label = labels[i-1] if i <= 3 else ("#" + str(i))
        name = c["stock_name"]
        ticker = c["ticker"].replace(".NS", "").upper()
        score = c["composite_score"]
        cmp = c.get("close", c.get("prev_close", 0))
        trigger = trade["buy_above_trigger"]
        sl = trade["stop_loss"]["price"]
        sl_pct = trade["stop_loss"]["risk_pct"]
        t1 = trade["target_1"]["price"]
        t1_pct = trade["target_1"]["gain_pct"]
        t2 = trade["target_2"]["price"]
        t2_pct = trade["target_2"]["gain_pct"]
        sector = c.get("sector", "N/A")
        shares = trade["position_sizing"]["recommended_shares"]
        outlay = trade["position_sizing"]["total_cash_outlay"]

        line = (
            label + ": " + name + " (NSE:" + ticker + ")\n"
            + "  Score   : " + str(score) + "/100  |  Sector: " + sector + "\n"
            + "  CMP     : Rs" + "{:.2f}".format(cmp) + "\n"
            + "  TRIGGER : Rs" + "{:.2f}".format(trigger) + "  <- Buy above this\n"
            + "  HARD SL : Rs" + "{:.2f}".format(sl) + "  (-" + "{:.1f}".format(sl_pct) + "%)\n"
            + "  TARGET 1: Rs" + "{:.2f}".format(t1) + "  (+" + "{:.1f}".format(t1_pct) + "%)\n"
            + "  TARGET 2: Rs" + "{:.2f}".format(t2) + "  (+" + "{:.1f}".format(t2_pct) + "%)\n"
            + "  Shares  : " + str(shares) + " @ Rs" + "{:,.0f}".format(outlay) + " outlay\n"
        )
        summary_lines.append(line)
        print(line)

summary_text = "\n".join(summary_lines)
with open("results/latest_scan.json", "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, default=str)

with open("results/latest_scan_summary.txt", "w", encoding="utf-8") as f:
    f.write(summary_text)

print("Results saved to results/latest_scan.json and results/latest_scan_summary.txt")
