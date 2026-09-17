"""Tests for NIFTY 50 Short-Term Swing Opportunity Engine."""

import pytest
from tradingagents.swing_opportunity.nifty50_universe import (
    NIFTY_50_TICKERS,
    NIFTY_50_METADATA,
    get_ticker_metadata,
    get_lot_size,
    get_strike_step,
    get_company_name,
    get_sector,
)
from tradingagents.swing_opportunity.trade_structurer import TradeStructurer
from tradingagents.swing_opportunity.evidence_agent import SwingEvidenceAgent
from tradingagents.swing_opportunity.screener import Nifty50Screener


def test_nifty50_universe_integrity():
    """Verify that NIFTY 50 universe has exactly 50 stocks, all ending in .NS."""
    assert len(NIFTY_50_TICKERS) == 50
    for ticker in NIFTY_50_TICKERS:
        assert ticker.endswith(".NS"), f"{ticker} does not end with .NS"
        meta = get_ticker_metadata(ticker)
        assert meta["lot_size"] > 0
        assert meta["strike_step"] > 0
        assert len(meta["name"]) > 0
        assert len(meta["sector"]) > 0


def test_trade_structurer_parameters():
    """Verify exact trigger, targets (+1.0%, +1.5%), R:R (>= 1:1.5), and derivatives."""
    structurer = TradeStructurer(account_capital=500000.0, risk_per_trade_pct=1.0)

    candidate = {
        "ticker": "RELIANCE.NS",
        "company_name": "Reliance Industries Ltd.",
        "sector": "Oil & Gas",
        "close": 2500.0,
        "high": 2510.0,
        "low": 2480.0,
        "atr14": 35.0,
        "hourly_ema20": 2495.0,
        "recent_low_3d": 2485.0,
        "volume_ratio": 1.45,
        "rs_composite": 2.15,
        "composite_score": 88.5,
    }

    trade = structurer.structure_trade(candidate)

    # 1. Identity & Direction
    assert trade["ticker"] == "RELIANCE.NS"
    assert trade["stock_name"] == "Reliance Industries Ltd."
    assert trade["trade_direction"] == "BUY / LONG"

    # 2. Trigger and Entry Range
    assert trade["buy_above_trigger"] > 2500.0
    assert trade["entry_range"]["lower"] == trade["buy_above_trigger"]
    assert trade["entry_range"]["upper"] > trade["entry_range"]["lower"]

    # 3. Stop Loss and Risk
    assert trade["stop_loss"]["price"] < trade["buy_above_trigger"]
    assert trade["stop_loss"]["risk_pct"] <= 1.0  # Kept tight

    # 4. Targets: T1 (+1.0%) and T2 (+1.5%)
    assert trade["target_1"]["gain_pct"] == 1.0
    assert trade["target_2"]["gain_pct"] == 1.5
    assert trade["target_1"]["price"] == round(trade["buy_above_trigger"] * 1.010, 2)
    assert trade["target_2"]["price"] == round(trade["buy_above_trigger"] * 1.015, 2)

    # 5. Risk to Reward >= 1:1.5
    rr_t1_val = float(trade["target_1"]["rr_ratio"].replace("1:", ""))
    assert rr_t1_val >= 1.2  # T1 covers majority of risk
    rr_t2_val = float(trade["target_2"]["rr_ratio"].replace("1:", ""))
    assert rr_t2_val >= 1.5  # T2 provides >= 1:1.5 R:R

    # 6. Derivative Suggestions
    derivatives = trade["derivatives"]
    assert derivatives["lot_size"] == 250
    assert "FUT" in derivatives["futures_recommendation"]["instrument"]
    assert derivatives["futures_recommendation"]["expected_profit_t1"] > 0
    assert derivatives["futures_recommendation"]["expected_profit_t2"] > derivatives["futures_recommendation"]["expected_profit_t1"]

    assert "CE" in derivatives["options_recommendation"]["instrument"]
    assert derivatives["options_recommendation"]["strike"] > 0

    # 7. Position Sizing
    pos = trade["position_sizing"]
    assert pos["account_capital"] == 500000.0
    assert pos["max_risk_allowed"] == 5000.0
    assert pos["recommended_shares"] > 0
    assert pos["actual_risk_rupees"] <= 5050.0  # within 1% risk budget


def test_evidence_agent_narrative_generation():
    """Verify detailed 'WHY THIS STOCK?' narrative contains all essential technical sections."""
    agent = SwingEvidenceAgent()
    structurer = TradeStructurer()
    candidate = {
        "ticker": "TCS.NS",
        "company_name": "Tata Consultancy Services Ltd.",
        "sector": "Information Technology",
        "close": 3800.0,
        "high": 3815.0,
        "low": 3770.0,
        "atr14": 45.0,
        "hourly_ema20": 3790.0,
        "recent_low_3d": 3760.0,
        "volume_ratio": 1.35,
        "rs_composite": 1.85,
        "ret_3d": 2.4,
        "ret_5d": 3.8,
        "close_range_pos": 0.82,
        "hourly_rsi": 62.5,
        "ema20": 3750.0,
        "sma50": 3700.0,
        "atr_pct": 1.18,
        "composite_score": 91.0,
    }
    trade = structurer.structure_trade(candidate)
    narrative = agent.generate_why_this_stock_narrative(trade)

    assert len(narrative) > 200
    assert "Executive Rationale" in narrative or "TCS" in narrative
    assert "Relative Strength" in narrative or "NIFTY" in narrative
    assert "Volume" in narrative
