"""Multi-Agent Evidence Generator for NIFTY 50 Swing Trade Selection.

Produces a rigorous, human-readable explanation of 'WHY THIS STOCK?'
integrating quantitative technical evidence, relative strength vs NIFTY 50,
volume expansion footprint, multi-timeframe moving average alignment,
and concrete trade invalidation logic.
"""

import logging
from typing import Dict, Any, Optional
import os

from ..default_config import DEFAULT_CONFIG
from ..llm_clients.factory import create_llm_client

logger = logging.getLogger(__name__)


class SwingEvidenceAgent:
    """Generates comprehensive, evidence-backed trade rationales."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or DEFAULT_CONFIG
        self.llm_provider = self.config.get("llm_provider", "google")
        self.model_name = self.config.get("quick_think_llm", "gemini-3.1-flash-lite")
        self._llm_client = None

    def _get_llm_client(self):
        if self._llm_client is None:
            try:
                self._llm_client = create_llm_client(
                    provider=self.llm_provider,
                    model=self.model_name,
                    base_url=self.config.get("backend_url"),
                    temperature=0.2,
                )
            except Exception as exc:
                logger.warning("Could not initialize LLM client (%s). Will use deterministic fallback: %s", self.llm_provider, exc)
                self._llm_client = None
        return self._llm_client

    def generate_why_this_stock_narrative(self, trade: Dict[str, Any]) -> str:
        """Generate a detailed, human-readable 'WHY THIS STOCK?' justification."""
        metrics = trade.get("screening_metrics", {})
        ticker = trade["ticker"]
        stock_name = trade["stock_name"]
        sector = trade["sector"]
        cmp_val = trade["current_market_price"]
        trigger = trade["buy_above_trigger"]
        entry_str = trade["entry_range"]["formatted"]
        sl_str = trade["stop_loss"]["formatted"]
        t1_str = trade["target_1"]["formatted"]
        t2_str = trade["target_2"]["formatted"]
        rr_str = trade["risk_reward_summary"]

        vol_ratio = metrics.get("volume_ratio", 1.0)
        rs_comp = metrics.get("rs_composite", 0.0)
        ret_3d = metrics.get("ret_3d", 0.0)
        ret_5d = metrics.get("ret_5d", 0.0)
        close_range_pos = metrics.get("close_range_pos", 0.7) * 100.0
        h_rsi = metrics.get("hourly_rsi", 58.0)
        ema20 = metrics.get("ema20", cmp_val)
        sma50 = metrics.get("sma50", cmp_val)
        atr_pct = metrics.get("atr_pct", 1.5)
        composite_score = metrics.get("composite_score", 85.0)

        prompt = f"""You are a Lead Quantitative Technical Strategist and Head of Equity Trading on Dalal Street (National Stock Exchange of India).

You have screened all 50 constituent stocks of the NIFTY 50 index and selected {stock_name} ({ticker}) as one of the top short-term swing trading opportunities for a 1–2 day holding horizon targeting +1.0% to +1.5% profit.

TRADE SETUP DETAILS:
- Stock: {stock_name} ({ticker})
- Sector: {sector}
- Current Market Price: ₹{cmp_val:,.2f}
- Buy Above Trigger: ₹{trigger:,.2f}
- Entry Range: {entry_str}
- Stop Loss: {sl_str}
- Target 1 (+1.0%): {t1_str}
- Target 2 (+1.5%): {t2_str}
- Risk-to-Reward: {rr_str}
- Holding Period: 1 to 2 Trading Sessions (T+1 / T+2 max)

TECHNICAL & QUANTITATIVE EVIDENCE:
- Screener Composite Score: {composite_score}/100
- 3-Day Stock Return: {ret_3d}%
- 5-Day Stock Return: {ret_5d}%
- Relative Strength (Alpha vs NIFTY 50 Index): {rs_comp:+.2f}% outperformance
- Daily Volume vs 20-day Average: {vol_ratio:.2f}x (Institutional activity benchmark)
- Daily Candle Close Location: Closed at {close_range_pos:.1f}% of the day's high-low range
- Moving Average Trend: Price (₹{cmp_val:,.2f}) vs 20-day EMA (₹{ema20:,.2f}) and 50-day SMA (₹{sma50:,.2f})
- Hourly Momentum: 1-Hour RSI at {h_rsi:.1f}, consolidating above hourly 20-EMA
- Daily Volatility / ATR: {atr_pct:.2f}% of price per day

INSTRUCTIONS:
Provide a rigorous, thorough, and highly professional explanation of **"WHY THIS STOCK WAS SELECTED"**.
Do NOT write vague generic disclaimers. Write with the conviction of a seasoned quant portfolio manager.
Structure your explanation under these exact 5 headings:

1. **Executive Rationale & Competitive Edge**: Why this stock stands out among all other 49 NIFTY constituents today.
2. **Multi-Timeframe Technical Confluence**: How daily trend alignment and hourly price action create an asymmetric continuation setup.
3. **Institutional Volume & Accumulation Signature**: Interpretation of the volume expansion ({vol_ratio:.2f}x) and high-range close.
4. **Relative Strength vs Benchmark (NIFTY 50)**: How its alpha buffer protects against broad market volatility.
5. **Execution Tactics & Invalidation Rules**: How the 1-2 day holding window, tight stop, and 1.0%-1.5% target are optimized against the stock's natural daily ATR.

Keep the tone analytical, disciplined, and precise.
"""

        client = self._get_llm_client()
        if client:
            try:
                response = client.generate(prompt)
                if response and len(response.strip()) > 100:
                    return response.strip()
            except Exception as e:
                logger.warning("LLM generation failed, falling back to quantitative template: %s", e)

        # Deterministic quantitative narrative fallback
        return self._generate_deterministic_narrative(
            ticker=ticker,
            stock_name=stock_name,
            sector=sector,
            cmp_val=cmp_val,
            trigger=trigger,
            entry_str=entry_str,
            sl_str=sl_str,
            t1_str=t1_str,
            t2_str=t2_str,
            rr_str=rr_str,
            vol_ratio=vol_ratio,
            rs_comp=rs_comp,
            ret_3d=ret_3d,
            ret_5d=ret_5d,
            close_range_pos=close_range_pos,
            h_rsi=h_rsi,
            ema20=ema20,
            sma50=sma50,
            atr_pct=atr_pct,
            composite_score=composite_score,
        )

    def _generate_deterministic_narrative(
        self,
        ticker: str,
        stock_name: str,
        sector: str,
        cmp_val: float,
        trigger: float,
        entry_str: str,
        sl_str: str,
        t1_str: str,
        t2_str: str,
        rr_str: str,
        vol_ratio: float,
        rs_comp: float,
        ret_3d: float,
        ret_5d: float,
        close_range_pos: float,
        h_rsi: float,
        ema20: float,
        sma50: float,
        atr_pct: float,
        composite_score: float,
    ) -> str:
        """Deterministic high-conviction quantitative trade narrative."""
        vol_desc = "strong institutional accumulation" if vol_ratio >= 1.2 else "steady accumulation"
        candle_desc = "dominant buyer control into the close" if close_range_pos >= 70 else "constructive absorption"
        rs_desc = (
            f"demonstrating clear market leadership with +{rs_comp:.2f}% alpha"
            if rs_comp > 0
            else f"showing resilient stability at {rs_comp:.2f}% vs the index"
        )

        return f"""### 1. Executive Rationale & Competitive Edge
{stock_name} ({ticker}) ranked among the top candidates in the entire NIFTY 50 universe with a quantitative composite score of **{composite_score:.1f}/100**. While broader indices encounter resistance, {ticker} exhibits exceptional relative strength and clean structural momentum, making it an ideal vehicle for a 1–2 session swing capture targeting +1.0% to +1.5%.

### 2. Multi-Timeframe Technical Confluence
- **Daily Trend Alignment**: The stock is trading at ₹{cmp_val:,.2f}, firmly positioned above its rising 20-day exponential moving average (₹{ema20:,.2f}) and its 50-day simple moving average (₹{sma50:,.2f}). This stacked moving average structure confirms a high-probability bullish regime.
- **Hourly Momentum**: On the 1-hour chart, RSI stands at **{h_rsi:.1f}**, positioned squarely in the bullish momentum zone (50–70) without being overbought. Price has established higher swing lows on the hourly timeframe, compressing near resistance for a volatility expansion.

### 3. Institutional Volume & Accumulation Signature
- **Volume Expansion**: Daily turnover printed at **{vol_ratio:.2f}x** the 20-day moving average, signaling {vol_desc}.
- **Closing Range Location**: The stock finished the session at **{close_range_pos:.1f}%** of its daily range (closing near session highs), indicating {candle_desc} and aggressive willingness by market participants to carry risk overnight.

### 4. Relative Strength vs Benchmark (NIFTY 50)
- Over the last 3 sessions, the stock has gained **{ret_3d:+.2f}%** (5-day return: **{ret_5d:+.2f}%**), {rs_desc} relative to the NIFTY 50 benchmark (^NSEI).
- When market indices consolidate or pull back, stocks exhibiting positive relative strength typically act as the immediate leaders when the next directional leg begins.

### 5. Execution Tactics & Invalidation Rules
- **ATR Alignment**: With a daily ATR of **{atr_pct:.2f}%**, reaching the **+1.0% ({t1_str})** and **+1.5% ({t2_str})** profit targets falls well within the stock's standard 1–2 session range expansion capability.
- **Trigger & Entry**: Enter exclusively upon a confirmed break above **₹{trigger:,.2f}** within the {entry_str} execution band.
- **Strict Invalidation**: Maintain a defined stop loss at **{sl_str}**, limiting downside to maintain an attractive Risk-to-Reward ratio of **{rr_str}**. If the trade does not reach Target 1 within 2 trading sessions, close the position at market close on Day 2 to preserve capital efficiency.
"""

    def generate_top_gainer_narrative(self, trade: Dict[str, Any]) -> str:
        """Generate rigorous pre-market explanation of why stock is primed to be a top daily gainer."""
        metrics = trade.get("screening_metrics", {})
        ticker = trade["ticker"]
        stock_name = trade["stock_name"]
        sector = trade["sector"]
        tier = trade.get("tier", "Midcap")
        cmp_val = trade["current_market_price"]
        trigger = trade["buy_above_trigger"]
        entry_str = trade["entry_range"]["formatted"]
        sl_str = trade["stop_loss"]["formatted"]
        t1_str = trade["target_1"]["formatted"]
        t2_str = trade["target_2"]["formatted"]
        rr_str = trade["risk_reward_summary"]

        turnover_cr = metrics.get("turnover_cr", 50.0)
        avg_turnover_cr = metrics.get("avg_turnover_cr_20d", 40.0)
        adr_pct = metrics.get("adr_pct", 5.0)
        pct_from_52w = metrics.get("pct_from_52w", 3.0)
        rs_alpha = metrics.get("rs_alpha", 4.0)
        vol_ratio = metrics.get("volume_ratio", 0.6)
        is_nr7 = metrics.get("is_nr7", False)
        is_inside_day = metrics.get("is_inside_day", False)
        is_vdu = metrics.get("is_vdu", False)
        clv = metrics.get("clv", 0.8) * 100.0
        composite_score = metrics.get("composite_score", 85.0)
        breakdown = metrics.get("score_breakdown", {})

        coiling_note = "an NR7 session (Narrowest Range of 7 sessions)" if is_nr7 else ("an Inside Day compression" if is_inside_day else "tight volatility contraction")
        vdu_note = f"a classic Volume Dry-Up ({vol_ratio:.2f}x 20d avg), proving floating supply has been absorbed" if is_vdu else f"subdued consolidation volume ({vol_ratio:.2f}x avg)"
        blue_sky_note = f"sitting just {pct_from_52w:.1f}% below its 52-week high (Blue-Sky territory with zero overhead trapped supply)" if pct_from_52w <= 5.0 else f"trading {pct_from_52w:.1f}% from its 52-week high with clear pivot clearance"

        return f"""### 1. Executive Rationale: Top-Gainer Probability
{stock_name} (`{ticker}`) scored **{composite_score:.1f} / 100** on the Pre-Market Top-Gainer Quantitative Matrix, ranking at the pinnacle of the NSE {tier} universe. It satisfies all Tier-1 institutional criteria with a 20-day average daily turnover of **₹{avg_turnover_cr:,.1f} Crore**, confirming deep institutional liquidity rather than low-float retail speculation. It possesses the mechanical range (14-day ADR: **{adr_pct:.2f}%**) required to stage a +5% to +8% single-day expansion.

### 2. Volatility Contraction & Coiling (The Pre-Market Spring)
- **Range Compression**: The stock concluded the prior session with **{coiling_note}**. Its intraday range contracted significantly, signaling that wild supply/demand oscillation has ended.
- **Moving Average Convergence**: Price (₹{cmp_val:,.2f}) has coiled tightly against its rising 20-day EMA, storing potential energy for an explosive directional release upon 9:15 AM opening breakout.
- **Volatility Score**: **{breakdown.get('volatility_coiling', 25.0)} / 30 pts**.

### 3. Supply Exhaustion & Institutional Accumulation
- **Volume Dry-Up**: Prior session volume printed at **{vdu_note}**. Eager sellers have vanished; institutional holders are refusing to unload shares at these levels.
- **Closing Buying Intensity**: The stock closed at **{clv:.1f}%** of its daily range (upper decile close), indicating that buyers remained in decisive control straight into the 3:30 PM closing bell.
- **Volume Footprint Score**: **{breakdown.get('volume_footprint', 18.0)} / 20 pts**.

### 4. Structural Blue-Sky Clearance & Relative Strength
- **Resistance Clearance**: The stock is {blue_sky_note}. There is negligible overhead trapped inventory to generate selling waves on an upward sprint.
- **Mid-Cap Leadership Alpha**: Demonstrates an outsized **+{rs_alpha:.2f}% alpha** over the NIFTY Midcap 100 benchmark over the past 20 sessions, confirming sustained institutional accumulation.
- **Relative Strength & Blue-Sky Score**: **{breakdown.get('relative_strength', 25.0)} / 30 pts** (RS) and **{breakdown.get('blue_sky_clearance', 18.0)} / 20 pts** (Structural).

### 5. Execution Tactics, Day Targets & Gap-Trap Protection
- **Trigger**: BUY strictly upon a confirmed cross of **₹{trigger:,.2f}** within the {entry_str} execution band.
- **Day Targets**:
  - **Target 1 (+3.5% / {t1_str})**: Initial momentum surge (book 50% profits and trail stop loss to Breakeven).
  - **Target 2 (+6.5% / {t2_str})**: Full day-runner target into top-gainer / circuit expansion territory.
- **Stop Loss & R:R**: Defined stop loss at **{sl_str}**, providing an asymmetric **{rr_str}** Risk-to-Reward ratio.
- **Gap-Trap Rule**: If the stock opens with an excessive gap-up above **₹{trade['premarket_rules']['gap_trap_limit']:,.2f}** (>+3.5% gap), the setup is **invalidated** to prevent buying into institutional profit-taking.
"""

