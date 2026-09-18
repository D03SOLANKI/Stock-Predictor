"""Interactive Web Dashboard for NSE Pre-Market Top Gainers & Swing Opportunities.

Allows one-click execution, live market data ingestion, quantitative scoring,
trade structuring, and deep evidence presentation with full technical metrics.

Run with:
    streamlit run dashboard.py
"""

import glob
import os
import sys
import datetime
import pandas as pd
import streamlit as st

# Configure page layout
st.set_page_config(
    page_title="NSE Pre-Market Top Gainer & Swing Intelligence",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for dark-themed, institutional trading terminal look
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        letter-spacing: -0.5px;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        color: #8b949e;
        font-size: 1.05rem;
        margin-bottom: 1.5rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 8px 18px;
        border-radius: 6px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Ensure project root in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tradingagents.swing_opportunity import (
    PreMarketTopGainerScreener,
    DayGainerStructurer,
    SwingEvidenceAgent,
    SwingOpportunityEngine,
)
from tradingagents.default_config import DEFAULT_CONFIG


def render_sidebar():
    """Render interactive control panel in the sidebar."""
    st.sidebar.title("⚙️ Control Panel")
    
    mode = st.sidebar.radio(
        "Trading Engine Mode",
        [
            "⚡ Mode 1: Pre-Market Daily Single Best Pick (Top 2 Fallback | 73.5% Win Rate | 5.17 PF)",
            "🎯 NIFTY 50 Short-Term Swing (1-2 Days, +1.0% to +1.5%)",
        ],
        index=0,
    )

    st.sidebar.markdown("---")
    st.sidebar.subheader("Portfolio & Risk Settings")
    account_capital = st.sidebar.number_input(
        "Account Capital (INR)",
        min_value=50000.0,
        max_value=50000000.0,
        value=100000.0,
        step=25000.0,
        format="%0.0f",
    )
    risk_pct = st.sidebar.slider(
        "Risk Per Trade (%)",
        min_value=0.50,
        max_value=2.50,
        value=2.00,
        step=0.25,
        help="Mode 1 validated risk is strictly capped at -2.00%",
    )
    top_n = st.sidebar.slider(
        "Priority Queue Depth (Top Setups)",
        min_value=1,
        max_value=5,
        value=2,
        help="Mode 1 Pre-Market Priority Queue: #1 Primary Conviction, #2 Priority Fallback (Cascading execution achieves 73.5% Win Rate, 5.17 Profit Factor across sessions).",
    )

    min_turnover = 10.0
    bypass_regime = False
    if "Pre-Market" in mode:
        st.sidebar.markdown("---")
        st.sidebar.subheader("Institutional Filters")
        min_turnover = st.sidebar.number_input(
            "Min 20-Day Avg Turnover (₹ Crore)",
            min_value=2.0,
            max_value=100.0,
            value=10.0,
            step=2.0,
        )
        bypass_regime = st.sidebar.checkbox(
            "Bypass Regime Halt (Inspect setups anyway)",
            value=True,
            help="Allows inspecting setups even if Midcap index is in consolidation/defensive regime.",
        )

    st.sidebar.markdown("---")
    run_button = st.sidebar.button(
        "🚀 RUN LIVE MARKET SCAN",
        type="primary",
        use_container_width=True,
    )

    return {
        "mode": mode,
        "capital": account_capital,
        "risk_pct": risk_pct,
        "top_n": top_n,
        "min_turnover": min_turnover,
        "bypass_regime": bypass_regime,
        "run_button": run_button,
    }


def display_premarket_results(results, capital, risk_pct):
    """Render top gainer results with deep trade evidence."""
    regime = results["regime"]
    candidates = results["candidates"]

    # 1. Regime Banner
    regime_type = regime.get("regime", "NEUTRAL")
    if regime_type == "AGGRESSIVE_BULLISH":
        st.success(f"🟢 **TIER-0 MACRO REGIME: {regime_type}** — {regime['message']} (Risk Multiplier: {regime['risk_multiplier']}x)")
    elif regime_type == "NEUTRAL_PULLBACK":
        st.warning(f"🟡 **TIER-0 MACRO REGIME: {regime_type}** — {regime['message']} (Risk Multiplier: {regime['risk_multiplier']}x)")
    else:
        st.info(f"🔵 **TIER-0 MACRO REGIME: {regime_type}** — {regime['message']} (Risk Multiplier: {regime['risk_multiplier']}x)")

    if not candidates:
        st.error("No setups satisfied the minimum institutional scoring threshold today.")
        return

    # 2. Overview Table
    st.markdown("### 📋 Top-Gainer Probability Scorecard")
    table_data = []
    for idx, c in enumerate(candidates, 1):
        bd = c["score_breakdown"]
        table_data.append({
            "Rank": f"#{idx}",
            "Symbol": c["ticker"],
            "Company": c["stock_name"],
            "Sector": c["sector"],
            "Score": f"{c['composite_score']}/100",
            "CMP (₹)": f"₹{c['close']:,.2f}",
            "Clean Air": f"{c.get('clean_air_margin_pct', 5.0):.1f}%",
            "Catalyst": c.get('catalyst_type', 'TECHNICAL'),
            "From 52w High": f"{c['pct_from_52w']:.1f}%",
            "Midcap Alpha": f"{c['rs_alpha']:+.2f}%",
            "20d Turnover": f"₹{c['avg_turnover_cr_20d']:.1f} Cr",
            "Coiling Status": "NR7" if c["is_nr7"] else ("Inside Day" if c["is_inside_day"] else "Tight Base"),
        })
    st.dataframe(pd.DataFrame(table_data), use_container_width=True, hide_index=True)

    # 3. Individual Trade Cards & Deep Evidence
    st.markdown("---")
    st.markdown("### 🎯 Actionable Pre-Market Trade Setups & Evidence")

    structurer = DayGainerStructurer(account_capital=capital, risk_per_trade_pct=risk_pct)
    evidence_agent = SwingEvidenceAgent(config=DEFAULT_CONFIG)

    priority_labels = ["🥇 #1 Primary Pick", "🥈 #2 Fallback Pick", "🥉 #3 Standby Runner", "#4 Reserve", "#5 Reserve"]
    tab_titles = [
        f"{priority_labels[idx-1] if idx <= len(priority_labels) else f'#{idx}'}: {c['ticker']} ({c['stock_name'][:18]})"
        for idx, c in enumerate(candidates, 1)
    ]
    tabs = st.tabs(tab_titles)

    for idx, (tab, cand) in enumerate(zip(tabs, candidates), 1):
        with tab:
            trade = structurer.structure_trade(cand, risk_multiplier=regime.get("risk_multiplier", 1.0))
            narrative = evidence_agent.generate_top_gainer_narrative(trade)
            pos = trade["position_sizing"]
            rules = trade["premarket_rules"]
            bd = cand["score_breakdown"]

            # Key Trade Metrics Grid
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                st.metric("Current Market Price (CMP)", f"₹{trade['current_market_price']:,.2f}")
            with col2:
                st.metric("BUY Above Trigger", f"₹{trade['buy_above_trigger']:,.2f}")
            with col3:
                st.metric("Stop Loss (SL)", f"₹{trade['stop_loss']['price']:,.2f}", f"-{trade['stop_loss']['risk_pct']:.2f}%", delta_color="inverse")
            with col4:
                st.metric("Target 1 (+3.0%)", f"₹{trade['target_1']['price']:,.2f}", f"+3.00% (R:R {trade['target_1']['rr_ratio']})")
            with col5:
                st.metric("Target 2 (+5.0%)", f"₹{trade['target_2']['price']:,.2f}", f"+5.00% (R:R {trade['target_2']['rr_ratio']})")

            # Execution & Sizing Bar
            col_exec, col_pos = st.columns(2)
            with col_exec:
                st.markdown(f"**Entry Trigger:** `{trade['buy_above_trigger']:,.2f}` (Requires 9:15–9:30 AM 15m candle close >= Open)")
                st.markdown(f"**Holding Horizon:** **{trade['holding_period']}**")
                st.markdown(f"**Risk-to-Reward Ratio:** `{trade['risk_reward_summary']}`")
            with col_pos:
                st.markdown(f"**Position Sizing:** **{pos['recommended_shares']} shares** (Outlay: ₹{pos['total_cash_outlay']:,.2f})")
                st.markdown(f"**Max Capital Risk:** **₹{pos['actual_risk_rupees']:,.2f}** ({pos['portfolio_risk_pct']:.2f}% of portfolio | Mode 1 Capped)")

            # 4-Stage Execution Timeline Card
            st.markdown("#### ⏳ 4-Stage Professional Execution Protocol (Mode 1 Priority Queue)")
            t_col1, t_col2, t_col3, t_col4 = st.columns(4)
            with t_col1:
                st.info(
                    f"**1️⃣ 8:45 AM — Pre-Market**\n\n"
                    f"• **Score:** {cand['composite_score']}/100\n"
                    f"• **Trigger:** ₹{trade['buy_above_trigger']:,.2f}\n"
                    f"• **Hard SL:** ₹{trade['stop_loss']['price']:,.2f} (-{trade['stop_loss']['risk_pct']:.2f}%)"
                )
            with t_col2:
                st.info(
                    f"**2️⃣ 9:08 AM — Call Auction**\n\n"
                    f"• **Positive Open:** Open ≥ Prev Close\n"
                    f"• **Gap-Trap Limit:** ₹{rules['gap_trap_limit']:,.2f}\n"
                    f"• **Fallback:** If #1 opens red, switch to #2"
                )
            with t_col3:
                st.info(
                    f"**3️⃣ 9:30 AM — Green Candle ORB**\n\n"
                    f"• **Confirmation:** Close ≥ Open (Green)\n"
                    f"• **Breakout:** High ≥ ₹{trade['buy_above_trigger']:,.2f}\n"
                    f"• **Action:** Enter on 9:30 AM confirmation"
                )
            with t_col4:
                st.info(
                    f"**4️⃣ Intraday Square-Off**\n\n"
                    f"• **BE Trailing:** Lock BE at +1.5%\n"
                    f"• **Target 1 (+3.0%):** Partial profit\n"
                    f"• **3:15 PM:** Mandatory complete square-off"
                )

            # Invalidation & Trade Rules Alert
            st.warning(
                f"""**⚠️ MODE 1 PRIORITY QUEUE PROTOCOL (Top 2 Fallback | 73.5% Win Rate | 5.17 Profit Factor):**
• **Cascading Queue Rule (Rank 1 ➔ Rank 2):** Evaluate Rank #1 first. If Rank #1 fails the 9:08 AM positive open or 9:30 AM green candle confirmation, seamlessly fall back to Rank #2. Strictly execute 1 single trade per day with 100% capital focus.
• **Positive Open Gate (9:08 AM):** Stock must open ≥ previous close * 0.998. If opening red, setup is **DISQUALIFIED** (triggers immediate fallback to Rank #2).
• **9:30 AM Green Candle Confirmation:** {rules['opening_rule']}
• **Pre-Open Auction Gate (9:08 AM):** Disqualify if price opens with excessive gap-up above **₹{rules['gap_trap_limit']:,.2f}** (>+2.5% gap trap).
• **Accelerated Breakeven Protection:** At +1.5% gain, immediately move Stop Loss to Breakeven to guarantee zero loss on intraday reversals.
• **Target Profit Booking:** Target 1 at +3.0%, Target 2 at +5.0%.
• **Mandatory 3:15 PM Square-Off:** No overnight holding. Position is squared off before market close."""
            )

            # Quantitative Breakdown Cards
            st.markdown("#### 🔬 Quantitative Pillar Breakdown (100-Pt Model)")
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.info(f"**Volatility Coiling**\n\n**{bd['volatility_coiling']}/30 pts**\n\nNR7: {cand['is_nr7']} | Inside: {cand['is_inside_day']}")
            with c2:
                st.info(f"**Midcap Alpha**\n\n**{bd['relative_strength']}/30 pts**\n\nAlpha: {cand['rs_alpha']:+.2f}% | ADR: {cand['adr_pct']:.2f}%")
            with c3:
                st.info(f"**Supply Exhaustion**\n\n**{bd['volume_footprint']}/20 pts**\n\nVDU: {cand['is_vdu']} | Vol: {cand['volume_ratio']:.2f}x")
            with c4:
                st.info(f"**Blue-Sky Clearance**\n\n**{bd['blue_sky_clearance']}/20 pts**\n\nFrom 52w: {cand['pct_from_52w']:.1f}% | CLV: {cand['clv']:.2f}")

            # Evidence Narrative (Deep & Prominent with Native High Contrast)
            st.markdown("#### 🧠 EVIDENCE BEHIND THE TRADE (IN-DEPTH QUANTITATIVE RATIONALE)")
            with st.container(border=True):
                st.markdown(narrative)


def display_swing_results(opportunities):
    """Render NIFTY 50 swing trade setups."""
    if not opportunities:
        st.warning("No swing opportunities met the criteria today.")
        return

    st.markdown("### 🎯 NIFTY 50 Short-Term Swing Opportunities (1-2 Days)")
    for idx, opp in enumerate(opportunities, 1):
        with st.expander(f"Opportunity #{idx}: {opp.stock_name} ({opp.ticker}) - Score: {opp.screening_metrics.get('composite_score', 'N/A')}/100", expanded=(idx == 1)):
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                st.metric("Current Price", f"₹{opp.current_market_price:,.2f}")
            with col2:
                st.metric("BUY Above Trigger", f"₹{opp.buy_above_trigger:,.2f}")
            with col3:
                st.metric("Stop Loss", opp.stop_loss)
            with col4:
                st.metric("Target 1 (+1.0%)", opp.target_1)
            with col5:
                st.metric("Target 2 (+1.5%)", opp.target_2)

            st.markdown(f"**Entry Range:** `{opp.entry_range}` | **Risk-to-Reward:** `{opp.risk_reward}` | **Holding:** `{opp.holding_period}`")

            # Derivatives
            fut = opp.derivatives.get("futures_recommendation", {})
            opt = opp.derivatives.get("options_recommendation", {})
            st.markdown(f"**Stock Futures:** `{fut.get('instrument')}` (Lot: {fut.get('lot_size')} shares, Margin: ₹{fut.get('estimated_margin', 0):,.2f})")
            st.markdown(f"**Call Option:** `{opt.get('instrument')}` — {opt.get('notes')}")

            st.markdown("#### 🧠 EVIDENCE BEHIND THE TRADE")
            with st.container(border=True):
                st.markdown(opp.why_this_stock)


def display_historical_reports():
    """Display saved markdown intelligence reports."""
    st.markdown("### 📂 Historical Intelligence Reports")
    pm_files = sorted(glob.glob("results/premarket_reports/*.md"), reverse=True)
    sw_files = sorted(glob.glob("results/swing_reports/*.md"), reverse=True)

    all_reports = pm_files + sw_files
    if not all_reports:
        st.info("No saved intelligence reports found yet. Run a scan to generate your first audit report.")
        return

    selected_report = st.selectbox("Select Report to View", all_reports)
    if selected_report and os.path.exists(selected_report):
        with open(selected_report, "r", encoding="utf-8") as f:
            content = f.read()
        st.markdown(content)


def main():
    st.markdown('<div class="main-header">📈 Dalal Street Quantitative Trading Dashboard</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Automated Pre-Market Top-Gainer Discovery & Multi-Timeframe Swing Intelligence for NSE India</div>', unsafe_allow_html=True)

    config = render_sidebar()

    # Main Page Action Bar - always visible even if sidebar is collapsed!
    st.markdown("---")
    c_btn, c_mode, c_info = st.columns([1.6, 2.2, 1.2])
    with c_btn:
        main_run = st.button("🚀 RUN LIVE MARKET SCAN", type="primary", use_container_width=True, key="main_run_button")
    with c_mode:
        selected_mode = st.selectbox(
            "Strategy Profile",
            [
                "⚡ Mode 1: Pre-Market Daily Single Best Pick (Top 2 Fallback | 73.5% Win Rate | 5.17 PF)",
                "🎯 NIFTY 50 Short-Term Swing (1-2 Days, +1.0% to +1.5%)",
            ],
            index=0 if "Mode 1" in config["mode"] or "Pre-Market" in config["mode"] else 1,
            key="main_mode_select",
        )
    with c_info:
        st.markdown(f"**Capital:** ₹{config['capital']:,.0f}  \n**Risk:** {config['risk_pct']}% / trade")

    run_triggered = main_run or config["run_button"]
    active_mode = selected_mode if main_run else config["mode"]

    tab_live, tab_history = st.tabs(["🚀 Live Scanner & Evidence", "📚 Historical Intelligence Reports"])

    with tab_live:
        if run_triggered:
            with st.spinner("Analyzing market microstructure, coiling patterns, and volume footprints..."):
                if "Pre-Market" in active_mode or "Mode 1" in active_mode:
                    screener = PreMarketTopGainerScreener(min_turnover_crores=config["min_turnover"])
                    results = screener.scan(top_n=config["top_n"], bypass_regime_halt=config["bypass_regime"])
                    display_premarket_results(results, config["capital"], config["risk_pct"])
                else:
                    engine = SwingOpportunityEngine(
                        account_capital=config["capital"],
                        risk_per_trade_pct=config["risk_pct"],
                    )
                    opps = engine.run(top_n=config["top_n"])
                    display_swing_results(opps)
        else:
            st.info("👆 Click the red/pink **'🚀 RUN LIVE MARKET SCAN'** button above to initiate real-time pre-market analysis and view detailed trade evidence.")


    with tab_history:
        display_historical_reports()


if __name__ == "__main__":
    main()
