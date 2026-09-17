"""End-to-End Swing Opportunity Engine for NIFTY 50.

Orchestrates multi-timeframe screening, deterministic trade structuring,
and multi-agent evidence generation for 1-2 day swing trades on NSE India.
"""

from dataclasses import dataclass, field
import datetime
import json
import logging
import os
from typing import Dict, Any, List, Optional

from .screener import Nifty50Screener
from .trade_structurer import TradeStructurer
from .evidence_agent import SwingEvidenceAgent
from .nifty50_universe import NIFTY_50_TICKERS

logger = logging.getLogger(__name__)


@dataclass
class SwingTradeOpportunity:
    """Dataclass holding complete structured trade plan and evidence."""
    ticker: str
    stock_name: str
    sector: str
    trade_direction: str
    current_market_price: float
    buy_above_trigger: float
    entry_range: str
    stop_loss: str
    target_1: str
    target_2: str
    expected_gain: str
    risk_reward: str
    holding_period: str
    position_sizing: Dict[str, Any]
    derivatives: Dict[str, Any]
    trade_validity: Dict[str, Any]
    why_this_stock: str
    screening_metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "stock_name": self.stock_name,
            "sector": self.sector,
            "trade_direction": self.trade_direction,
            "current_market_price": self.current_market_price,
            "buy_above_trigger": self.buy_above_trigger,
            "entry_range": self.entry_range,
            "stop_loss": self.stop_loss,
            "target_1": self.target_1,
            "target_2": self.target_2,
            "expected_gain": self.expected_gain,
            "risk_reward": self.risk_reward,
            "holding_period": self.holding_period,
            "position_sizing": self.position_sizing,
            "derivatives": self.derivatives,
            "trade_validity": self.trade_validity,
            "why_this_stock": self.why_this_stock,
            "screening_metrics": self.screening_metrics,
        }


class SwingOpportunityEngine:
    """Main workflow engine for NIFTY 50 swing trade discovery."""

    def __init__(
        self,
        account_capital: float = 500000.0,
        risk_per_trade_pct: float = 1.0,
        benchmark_ticker: str = "^NSEI",
        reports_dir: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ):
        self.account_capital = account_capital
        self.risk_per_trade_pct = risk_per_trade_pct
        self.benchmark_ticker = benchmark_ticker
        self.reports_dir = reports_dir or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "results",
            "swing_reports",
        )
        os.makedirs(self.reports_dir, exist_ok=True)

        self.screener = Nifty50Screener(benchmark_ticker=benchmark_ticker)
        self.structurer = TradeStructurer(
            account_capital=account_capital,
            risk_per_trade_pct=risk_per_trade_pct,
        )
        self.evidence_agent = SwingEvidenceAgent(config=config)

    def run(self, top_n: int = 3) -> List[SwingTradeOpportunity]:
        """Execute complete scan, trade structuring, and rationale generation."""
        print(f"\n" + "=" * 80)
        print(f"[*] INITIATING NIFTY 50 SWING OPPORTUNITY SCANNER (1-2 DAY HOLDING)")
        print(f"[*] Target Profit: ~1.0% to 1.5% | Capital: \u20b9{self.account_capital:,.0f} | Risk/Trade: {self.risk_per_trade_pct}%")
        print(f"[*] Universe: 50 NIFTY Constituent Stocks (.NS) | Benchmark: {self.benchmark_ticker}")
        print("=" * 80 + "\n")

        # Step 1: Screen universe
        print(f"[*] Phase 1: Ingesting Daily & Hourly Market Data for all 50 stocks...")
        ranked_candidates = self.screener.scan(top_n=top_n)
        if not ranked_candidates:
            print("[!] No matching opportunities found that satisfy risk-reward criteria.")
            return []

        print(f"[+] Phase 1 Complete. Top {len(ranked_candidates)} candidates isolated:")
        for idx, cand in enumerate(ranked_candidates, 1):
            print(f"    {idx}. {cand['stock_name']} ({cand['ticker']}) - Score: {cand['composite_score']}/100 | CMP: \u20b9{cand['close']:,.2f}")

        # Step 2: Structure trades and generate evidence
        opportunities: List[SwingTradeOpportunity] = []
        print(f"\n[*] Phase 2: Structuring Trades & Generating Multi-Agent 'WHY' Evidence...")

        for idx, cand in enumerate(ranked_candidates, 1):
            ticker = cand["ticker"]
            print(f"\n--- Processing Candidate {idx}/{len(ranked_candidates)}: {ticker} ---")
            
            structured = self.structurer.structure_trade(cand)
            
            print(f"[*] Synthesizing deep technical evidence and rationale for {ticker}...")
            why_narrative = self.evidence_agent.generate_why_this_stock_narrative(structured)

            opp = SwingTradeOpportunity(
                ticker=ticker,
                stock_name=structured["stock_name"],
                sector=structured["sector"],
                trade_direction=structured["trade_direction"],
                current_market_price=structured["current_market_price"],
                buy_above_trigger=structured["buy_above_trigger"],
                entry_range=structured["entry_range"]["formatted"],
                stop_loss=structured["stop_loss"]["formatted"],
                target_1=structured["target_1"]["formatted"],
                target_2=structured["target_2"]["formatted"],
                expected_gain=structured["expected_gain"],
                risk_reward=structured["risk_reward_summary"],
                holding_period=structured["holding_period"],
                position_sizing=structured["position_sizing"],
                derivatives=structured["derivatives"],
                trade_validity=structured["trade_validity"],
                why_this_stock=why_narrative,
                screening_metrics=cand,
            )
            opportunities.append(opp)

        # Step 3: Print formatted trade cards
        self._print_trade_cards(opportunities)

        # Step 4: Save markdown report
        report_file = self._save_markdown_report(opportunities)
        print(f"\n[+] Full Swing Opportunity Report saved to: {report_file}\n")

        return opportunities

    def _print_trade_cards(self, opportunities: List[SwingTradeOpportunity]):
        """Render beautiful trade cards in terminal."""
        for idx, opp in enumerate(opportunities, 1):
            fut = opp.derivatives.get("futures_recommendation", {})
            opt = opp.derivatives.get("options_recommendation", {})
            pos = opp.position_sizing

            border = "#" * 80
            print(f"\n{border}")
            print(f"  OPPORTUNITY #{idx}: {opp.stock_name} ({opp.ticker})")
            print(f"  Sector: {opp.sector} | Direction: {opp.trade_direction}")
            print(f"{border}")
            print(f"  Current Market Price (CMP):  \u20b9{opp.current_market_price:,.2f}")
            print(f"  BUY Above Trigger Level:     \u20b9{opp.buy_above_trigger:,.2f}")
            print(f"  Entry Price Band:            {opp.entry_range}")
            print(f"  Stop Loss (SL):              {opp.stop_loss}")
            print(f"  Target 1 (T1 - 50% Exit):    {opp.target_1}")
            print(f"  Target 2 (T2 - Full Exit):   {opp.target_2}")
            print(f"  Expected Gain (Underlying):  {opp.expected_gain}")
            print(f"  Risk-to-Reward Ratio:        {opp.risk_reward}")
            print(f"  Holding Window:              {opp.holding_period}")
            print(f"{'-' * 80}")
            print(f"  POSITION SIZING (Based on \u20b9{pos['account_capital']:,.0f} Account & {self.risk_per_trade_pct}% Risk):")
            print(f"  - Cash Shares Quantity:      {pos['recommended_shares']} shares")
            print(f"  - Capital Outlay:            \u20b9{pos['total_cash_outlay']:,.2f}")
            print(f"  - Max Rupee Risk:            \u20b9{pos['actual_risk_rupees']:,.2f} ({pos['portfolio_risk_pct']:.2f}% of portfolio)")
            print(f"{'-' * 80}")
            print(f"  DERIVATIVE RECOMMENDATIONS:")
            print(f"  1. Stock Futures:            {fut.get('instrument', 'N/A')}")
            print(f"     - NSE Lot Size:           {fut.get('lot_size')} shares")
            print(f"     - Estimated Margin:       \u20b9{fut.get('estimated_margin', 0):,.2f}")
            print(f"     - 1 Lot Payoff:           T1: +\u20b9{fut.get('expected_profit_t1', 0):,.0f} | T2: +\u20b9{fut.get('expected_profit_t2', 0):,.0f} (Risk: \u20b9{fut.get('risk_per_lot', 0):,.0f})")
            print(f"  2. Call Option:              {opt.get('instrument', 'N/A')}")
            print(f"     - Execution Caveat:       {opt.get('notes', 'N/A')}")
            print(f"{'-' * 80}")
            print(f"  TRADE VALIDITY & INVALIDATION:")
            print(f"  - Trigger Condition:         {opp.trade_validity.get('trigger_condition')}")
            for rule in opp.trade_validity.get("invalidation_rules", []):
                print(f"  - Invalidation:              {rule}")
            print(f"{'-' * 80}")
            print(f"  MOST IMPORTANT: WHY THIS STOCK? (EVIDENCE & RATIONALE)")
            print(f"{'-' * 80}")
            print(opp.why_this_stock)
            print(f"{border}\n")

    def _save_markdown_report(self, opportunities: List[SwingTradeOpportunity]) -> str:
        """Write a comprehensive markdown report for audit and record-keeping."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"nifty50_swing_opportunities_{timestamp}.md"
        filepath = os.path.join(self.reports_dir, filename)

        md_content = []
        md_content.append(f"# NIFTY 50 Short-Term Swing Trading Opportunities")
        md_content.append(f"**Generated Date/Time:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S IST')}  ")
        md_content.append(f"**Strategy Profile:** 1–2 Trading Day Holding (BTST / Short-term Swing)  ")
        md_content.append(f"**Target Return:** ~1.0% to 1.5% profit on underlying equity  ")
        md_content.append(f"**Account Capital Base:** \u20b9{self.account_capital:,.2f} (Risk per trade: {self.risk_per_trade_pct}%)  ")
        md_content.append(f"**Market Universe:** All 50 NIFTY Constituent Stocks (National Stock Exchange of India)  ")
        md_content.append(f"**Benchmark Index:** {self.benchmark_ticker} (NIFTY 50)\n")
        md_content.append("---\n")

        for idx, opp in enumerate(opportunities, 1):
            fut = opp.derivatives.get("futures_recommendation", {})
            opt = opp.derivatives.get("options_recommendation", {})
            pos = opp.position_sizing
            metrics = opp.screening_metrics

            md_content.append(f"## Opportunity #{idx}: {opp.stock_name} (`{opp.ticker}`)")
            md_content.append(f"- **Sector:** {opp.sector}")
            md_content.append(f"- **Trade Direction:** {opp.trade_direction}")
            md_content.append(f"- **Current Market Price (CMP):** \u20b9{opp.current_market_price:,.2f}")
            md_content.append(f"- **BUY Above Trigger Level:** **\u20b9{opp.buy_above_trigger:,.2f}**")
            md_content.append(f"- **Entry Price Band:** {opp.entry_range}")
            md_content.append(f"- **Stop Loss (SL):** **{opp.stop_loss}**")
            md_content.append(f"- **Target 1 (+1.0%):** **{opp.target_1}** (Book 50% profit, trail stop to breakeven)")
            md_content.append(f"- **Target 2 (+1.5%):** **{opp.target_2}** (Full exit)")
            md_content.append(f"- **Expected Gain:** {opp.expected_gain}")
            md_content.append(f"- **Risk-to-Reward Ratio:** {opp.risk_reward}")
            md_content.append(f"- **Holding Horizon:** {opp.holding_period}\n")

            md_content.append("### Position Sizing & Capital Allocation")
            md_content.append(f"- **Cash Shares:** {pos['recommended_shares']} shares")
            md_content.append(f"- **Total Outlay:** \u20b9{pos['total_cash_outlay']:,.2f}")
            md_content.append(f"- **Risk Allocation:** \u20b9{pos['actual_risk_rupees']:,.2f} ({pos['portfolio_risk_pct']:.2f}% of capital)\n")

            md_content.append("### Derivative Contracts (NSE F&O)")
            md_content.append(f"1. **Stock Futures:** `{fut.get('instrument')}`")
            md_content.append(f"   - **Lot Size:** {fut.get('lot_size')} shares")
            md_content.append(f"   - **Contract Value:** \u20b9{fut.get('contract_value', 0):,.2f}")
            md_content.append(f"   - **Estimated Margin (~22%):** \u20b9{fut.get('estimated_margin', 0):,.2f}")
            md_content.append(f"   - **Payoff Profile:** Target 1: +\u20b9{fut.get('expected_profit_t1', 0):,.0f} | Target 2: +\u20b9{fut.get('expected_profit_t2', 0):,.0f} (Max Risk: \u20b9{fut.get('risk_per_lot', 0):,.0f})")
            md_content.append(f"2. **Call Option:** `{opt.get('instrument')}`")
            md_content.append(f"   - **Guidance:** {opt.get('notes')}\n")

            md_content.append("### Trade Validity & Invalidation Criteria")
            md_content.append(f"- **Trigger Rule:** {opp.trade_validity.get('trigger_condition')}")
            for r in opp.trade_validity.get("invalidation_rules", []):
                md_content.append(f"- **Invalidation:** {r}")
            md_content.append("")

            md_content.append("### Quantitative Screener Scorecard")
            md_content.append(f"| Metric | Value | Threshold / Note |")
            md_content.append(f"| :--- | :--- | :--- |")
            md_content.append(f"| **Composite Score** | **{metrics.get('composite_score', 'N/A')}/100** | Top tier setup |")
            md_content.append(f"| **Alpha vs NIFTY 50** | {metrics.get('rs_composite', 0.0):+.2f}% | 3d/5d composite relative strength |")
            md_content.append(f"| **Volume Expansion** | {metrics.get('volume_ratio', 1.0):.2f}x | vs 20-day average volume |")
            md_content.append(f"| **Daily Range Close** | {metrics.get('close_range_pos', 0.0)*100:.1f}% | Closing location in daily bar |")
            md_content.append(f"| **Hourly RSI (14)** | {metrics.get('hourly_rsi', 50.0):.1f} | Momentum zone |")
            md_content.append(f"| **Daily ATR (14)** | {metrics.get('atr_pct', 1.5):.2f}% | Daily range expansion room |\n")

            md_content.append("### Most Importantly: WHY This Stock?")
            md_content.append(f"{opp.why_this_stock}\n")
            md_content.append("---\n")

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(md_content))

        return filepath
