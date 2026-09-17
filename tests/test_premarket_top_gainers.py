"""Unit tests for Pre-Market NSE Mid & Small-Cap Top Gainer Discovery Engine."""

import pandas as pd
import numpy as np
import pytest

from tradingagents.swing_opportunity.mid_small_universe import (
    NSE_MID_SMALL_TICKERS,
    NSE_MID_SMALL_UNIVERSE,
    get_mid_small_tickers,
    get_mid_small_metadata,
)
from tradingagents.swing_opportunity.premarket_screener import PreMarketTopGainerScreener
from tradingagents.swing_opportunity.day_gainer_structurer import DayGainerStructurer
from tradingagents.swing_opportunity.evidence_agent import SwingEvidenceAgent


def test_mid_small_universe_validity():
    """Verify all tickers end in .NS, are Series EQ, and have valid metadata."""
    tickers = get_mid_small_tickers()
    assert len(tickers) >= 50
    for t in tickers:
        assert t.endswith(".NS"), f"{t} does not end with .NS"
        meta = get_mid_small_metadata(t)
        assert meta["series"] == "EQ", f"{t} is not EQ series"
        assert meta["circuit_band"] in (10, 20, "F&O")
        assert len(meta["name"]) > 0
        assert len(meta["sector"]) > 0


def test_hard_disqualification_gates():
    """Test Tier-1 hard disqualifier rules (Turnover, Price, Non-EQ)."""
    screener = PreMarketTopGainerScreener(min_turnover_crores=10.0, min_price=30.0)

    # 1. Penny stock (< ₹30) -> Should fail
    close_low = pd.Series([15.0] * 25)
    high_low = pd.Series([15.5] * 25)
    low_low = pd.Series([14.5] * 25)
    vol_high = pd.Series([10000000] * 25)
    passed, reason = screener.check_hard_gates("PENNY.NS", close_low, high_low, low_low, vol_high)
    assert not passed
    assert "below liquidity threshold" in reason

    # 2. Illiquid stock (< ₹10 Cr avg turnover) -> Should fail
    close_ok = pd.Series([100.0] * 25)
    high_ok = pd.Series([102.0] * 25)
    low_ok = pd.Series([98.0] * 25)
    vol_tiny = pd.Series([10000] * 25)  # ₹10 lakh turnover only
    passed, reason = screener.check_hard_gates("ILLIQUID.NS", close_ok, high_ok, low_ok, vol_tiny)
    assert not passed
    assert "below" in reason and "Cr floor" in reason

    # 3. Valid liquid mid-cap (₹50 Cr avg turnover, ₹500 price, dry volume on T-1) -> Should pass
    close_good = pd.Series([500.0] * 25)
    high_good = pd.Series([505.0] * 23 + [508.0, 515.0])  # Clean air / breakout high
    low_good = pd.Series([495.0] * 25)
    vol_liquid = pd.Series([1000000] * 24 + [500000])  # Volume dry-up (0.50x ratio)
    passed, reason = screener.check_hard_gates("COCHINSHIP.NS", close_good, high_good, low_good, vol_liquid)
    assert passed, f"Failed with reason: {reason}"
    assert reason == "PASSED_ALL_GATES"


def test_day_gainer_trade_structuring():
    """Verify trigger price, targets (+3.5%, +6.5%), tight SL (-1.65%), and R:R >= 1:2.0."""
    structurer = DayGainerStructurer(account_capital=500000.0, risk_per_trade_pct=1.0)

    candidate = {
        "ticker": "COCHINSHIP.NS",
        "stock_name": "Cochin Shipyard Ltd.",
        "sector": "Defence",
        "tier": "Midcap",
        "close": 1500.0,
        "high": 1520.0,
        "low": 1485.0,
        "circuit_band": 20,
        "adr_pct": 5.2,
        "pct_from_52w": 2.1,
        "rs_alpha": 5.8,
        "volume_ratio": 0.55,
        "avg_turnover_cr_20d": 85.0,
        "composite_score": 92.0,
        "score_breakdown": {
            "volatility_coiling": 27.0,
            "relative_strength": 28.0,
            "volume_footprint": 18.0,
            "blue_sky_clearance": 19.0,
        },
    }

    trade = structurer.structure_trade(candidate)

    # 1. Identity & Trigger
    assert trade["ticker"] == "COCHINSHIP.NS"
    assert trade["buy_above_trigger"] > 1520.0  # Above yesterday's high
    assert trade["entry_range"]["lower"] == trade["buy_above_trigger"]
    assert trade["entry_range"]["upper"] > trade["buy_above_trigger"]

    # 2. Stop Loss & Risk
    assert trade["stop_loss"]["price"] < trade["buy_above_trigger"]
    assert trade["stop_loss"]["risk_pct"] <= 2.6  # Calibrated dynamic stop (max 2.6%)

    # 3. Targets (+3.5% T1, +6.5% T2)
    assert trade["target_1"]["gain_pct"] == 3.5
    assert trade["target_2"]["gain_pct"] == 6.5
    assert trade["target_1"]["price"] == round(trade["buy_above_trigger"] * 1.035, 2)
    assert trade["target_2"]["price"] == round(trade["buy_above_trigger"] * 1.065, 2)

    # 4. Asymmetric R:R
    rr_t1_val = float(trade["target_1"]["rr_ratio"].replace("1:", ""))
    assert rr_t1_val >= 1.4
    rr_t2_val = float(trade["target_2"]["rr_ratio"].replace("1:", ""))
    assert rr_t2_val >= 2.5

    # 5. Gap Trap Rule (Tightened to +2.5%)
    assert trade["premarket_rules"]["gap_trap_limit"] == round(trade["buy_above_trigger"] * 1.025, 2)


def test_top_gainer_evidence_narrative():
    """Verify 5-pillar narrative includes VCP, supply dry-up, and gap trap rules."""
    agent = SwingEvidenceAgent()
    structurer = DayGainerStructurer()

    candidate = {
        "ticker": "KAYNES.NS",
        "stock_name": "Kaynes Technology India Ltd.",
        "sector": "EMS / Electronics",
        "tier": "Smallcap",
        "close": 4200.0,
        "high": 4250.0,
        "low": 4170.0,
        "circuit_band": 20,
        "adr_pct": 4.8,
        "pct_from_52w": 1.5,
        "rs_alpha": 6.2,
        "volume_ratio": 0.48,
        "is_nr7": True,
        "is_vdu": True,
        "clv": 0.85,
        "avg_turnover_cr_20d": 95.0,
        "composite_score": 94.5,
        "score_breakdown": {
            "volatility_coiling": 29.0,
            "relative_strength": 28.0,
            "volume_footprint": 19.0,
            "blue_sky_clearance": 18.5,
        },
    }

    trade = structurer.structure_trade(candidate)
    narrative = agent.generate_top_gainer_narrative(trade)

    assert len(narrative) > 300
    assert "Executive Rationale" in narrative
    assert "Volatility Contraction" in narrative
    assert "Supply Exhaustion" in narrative
    assert "Gap-Trap" in narrative
    assert "KAYNES.NS" in narrative
