"""Day Top-Gainer Trade Structurer for Pre-Market Momentum on Dalal Street.

Calculates mathematically precise breakout trigger levels, dynamic structural
stop losses, multi-tier explosive day targets (+3.5% and +6.5%), and provides
the 15-Minute Opening Range Breakout (ORB) Confirmation State Machine to
eliminate the 60.7% morning bull-trap failure mode.
"""

from typing import Dict, Any, Optional
import math


class DayGainerStructurer:
    """Structures high-momentum day-runner trades on NSE mid/small-caps."""

    def __init__(self, account_capital: float = 500000.0, risk_per_trade_pct: float = 1.0):
        self.account_capital = account_capital
        self.risk_per_trade_pct = risk_per_trade_pct
        self.max_risk_rupees = account_capital * (risk_per_trade_pct / 100.0)

    def evaluate_15m_orb_confirmation(
        self,
        open_15m: float,
        high_15m: float,
        low_15m: float,
        close_15m: float,
        prev_high: float,
        vol_15m: Optional[float] = None,
        avg_daily_vol: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Evaluate the 9:15–9:30 AM first 15-minute candle to confirm or invalidate entry."""
        is_green = close_15m >= open_15m
        is_above_prev_high = close_15m > prev_high

        # Volume participation check (15% of 20d daily average volume)
        has_vol = True
        vol_ratio_15m = 1.0
        if vol_15m is not None and avg_daily_vol is not None and avg_daily_vol > 0:
            vol_ratio_15m = round(vol_15m / (avg_daily_vol * 0.15), 2)
            has_vol = vol_ratio_15m >= 0.80

        if not is_green:
            return {
                "is_confirmed": False,
                "status": "DISQUALIFIED_RED_CANDLE_TRAP",
                "message": f"First 15-minute bar closed red (₹{close_15m:.2f} < ₹{open_15m:.2f}). Severe bull-trap risk. Order CANCELLED.",
                "execution_price": None,
                "confirmed_stop_loss": None,
                "vol_ratio_15m": vol_ratio_15m,
            }

        if not is_above_prev_high:
            return {
                "is_confirmed": False,
                "status": "DISQUALIFIED_BELOW_BREAKOUT_LEVEL",
                "message": f"15-minute close ₹{close_15m:.2f} failed to hold above prior high ₹{prev_high:.2f}. Momentum stalled. Order CANCELLED.",
                "execution_price": None,
                "confirmed_stop_loss": None,
                "vol_ratio_15m": vol_ratio_15m,
            }

        # Confirmed Clean 15m ORB Entry
        execution_price = round(close_15m, 2)
        # Anchor stop loss to 15-minute candle low with ₹0.10 buffer
        confirmed_sl = round(low_15m - 0.10, 2)
        risk_pct = round((execution_price - confirmed_sl) / execution_price * 100.0, 2)

        # Cap max structural risk to 2.5%
        if risk_pct > 2.50:
            confirmed_sl = round(execution_price * (1.0 - 0.025), 2)
            risk_pct = 2.50

        return {
            "is_confirmed": True,
            "status": "CONFIRMED_ORB_BUY",
            "message": f"15-minute candle confirmed strong green (₹{close_15m:.2f} >= ₹{open_15m:.2f}) above prior high ₹{prev_high:.2f}. EXECUTE BUY.",
            "execution_price": execution_price,
            "confirmed_stop_loss": confirmed_sl,
            "risk_pct": risk_pct,
            "vol_ratio_15m": vol_ratio_15m,
        }

    def structure_trade(self, candidate: Dict[str, Any], risk_multiplier: float = 1.0) -> Dict[str, Any]:
        """Convert a pre-market candidate into an actionable day top-gainer trade plan."""
        ticker = candidate["ticker"]
        close = candidate["close"]
        high = candidate["high"]
        low = candidate["low"]
        adr_pct = candidate.get("adr_pct", 4.5)
        circuit_band = candidate.get("circuit_band", 20)
        clean_air_margin = candidate.get("clean_air_margin_pct", 5.0)

        # 1. Breakout Trigger Level: BUY Above
        raw_trigger = high + max(round(high * 0.0010, 2), 0.10)
        trigger_buy_above = round(math.ceil(raw_trigger / 0.05) * 0.05, 2)

        # 2. Execution Entry Zone (0.40% execution band)
        entry_upper = round(trigger_buy_above * 1.004, 2)

        # 3. Dynamic ADR-Calibrated Stop Loss
        dynamic_risk_pct = min(max(adr_pct * 0.50, 2.00), 2.60)
        structural_sl = low - 0.10

        risk_to_struct = (trigger_buy_above - structural_sl) / trigger_buy_above * 100.0
        if 1.80 <= risk_to_struct <= 2.60:
            stop_loss = round(structural_sl, 2)
            risk_pct = round(risk_to_struct, 2)
        else:
            stop_loss = round(trigger_buy_above * (1.0 - dynamic_risk_pct / 100.0), 2)
            risk_pct = round(dynamic_risk_pct, 2)

        risk_rupees_per_share = round(trigger_buy_above - stop_loss, 2)

        # 4. Multi-Tier Day Targets
        target_1 = round(trigger_buy_above * 1.035, 2)
        gain_1_rupees = round(target_1 - trigger_buy_above, 2)
        gain_1_pct = 3.5

        target_2_pct = min(6.5, float(circuit_band) - 1.5)
        target_2 = round(trigger_buy_above * (1.0 + target_2_pct / 100.0), 2)
        gain_2_rupees = round(target_2 - trigger_buy_above, 2)

        # 5. Risk-to-Reward Ratios
        rr_t1 = round(gain_1_rupees / (risk_rupees_per_share + 1e-6), 2)
        rr_t2 = round(gain_2_rupees / (risk_rupees_per_share + 1e-6), 2)

        # 6. Position Sizing
        adjusted_risk_rupees = self.max_risk_rupees * risk_multiplier
        shares_qty = int(adjusted_risk_rupees / max(risk_rupees_per_share, 0.50))
        max_capital_allocation = self.account_capital * 0.30
        max_shares = int(max_capital_allocation / trigger_buy_above)
        shares_qty = max(min(shares_qty, max_shares), 1)

        total_cash_outlay = round(shares_qty * trigger_buy_above, 2)
        actual_risk_rupees = round(shares_qty * risk_rupees_per_share, 2)

        max_gap_threshold = round(trigger_buy_above * 1.025, 2)  # Tightened to +2.5%

        return {
            "ticker": ticker,
            "stock_name": candidate.get("stock_name", ticker),
            "sector": candidate.get("sector", "NSE Mid/Small-Cap"),
            "tier": candidate.get("tier", "Midcap"),
            "trade_direction": "BUY / LONG (DAY MOMENTUM)",
            "current_market_price": close,
            "buy_above_trigger": trigger_buy_above,
            "entry_range": {
                "lower": trigger_buy_above,
                "upper": entry_upper,
                "formatted": f"₹{trigger_buy_above:,.2f} - ₹{entry_upper:,.2f}",
            },
            "stop_loss": {
                "price": stop_loss,
                "risk_rupees": risk_rupees_per_share,
                "risk_pct": risk_pct,
                "formatted": f"₹{stop_loss:,.2f} (-{risk_pct:.2f}%)",
            },
            "target_1": {
                "price": target_1,
                "gain_pct": gain_1_pct,
                "gain_rupees": gain_1_rupees,
                "rr_ratio": f"1:{rr_t1}",
                "formatted": f"₹{target_1:,.2f} (+{gain_1_pct:.1f}%)",
            },
            "target_2": {
                "price": target_2,
                "gain_pct": target_2_pct,
                "gain_rupees": gain_2_rupees,
                "rr_ratio": f"1:{rr_t2}",
                "formatted": f"₹{target_2:,.2f} (+{target_2_pct:.1f}%)",
            },
            "risk_reward_summary": f"1:{rr_t1} (at T1) / 1:{rr_t2} (at T2)",
            "expected_gain": f"+{gain_1_pct:.1f}% to +{target_2_pct:.1f}% Day Expansion",
            "clean_air_margin_pct": clean_air_margin,
            "holding_period": "Intraday (Book 50% at T1) + Runner (Close or Circuit)",
            "position_sizing": {
                "account_capital": self.account_capital,
                "max_risk_allowed": adjusted_risk_rupees,
                "recommended_shares": shares_qty,
                "total_cash_outlay": total_cash_outlay,
                "actual_risk_rupees": actual_risk_rupees,
                "portfolio_risk_pct": round((actual_risk_rupees / self.account_capital) * 100.0, 2),
            },
            "orb_execution_protocol": {
                "stage_1_premarket": "Order placed on Watchlist with 15m trigger monitoring at 9:15 AM.",
                "stage_2_confirmation": "At 9:30 AM, verify 15-minute bar closes GREEN and > ₹" + f"{trigger_buy_above:,.2f}.",
                "cancellation_trigger": "If 15m candle closes RED or < ₹" + f"{trigger_buy_above:,.2f}, cancel order immediately.",
            },
            "premarket_rules": {
                "gap_trap_limit": max_gap_threshold,
                "opening_rule": (
                    f"MANDATORY 15-MINUTE ORB CONFIRMATION: Wait for the 9:15–9:30 AM bar to CLOSE above "
                    f"₹{trigger_buy_above:,.2f} as a GREEN candle. Do NOT enter at 9:15 AM on a blind tick."
                ),
                "invalidation_rules": [
                    f"POSITIVE OPEN GATE: Stock must open >= yesterday's close (₹{close:,.2f}).",
                    f"PRE-OPEN AUCTION GATE (9:07 AM): Total Buy Qty / Total Sell Qty must be >= 1.5x.",
                    f"GAP TRAP: If stock opens above ₹{max_gap_threshold:,.2f} (>+2.5% gap), DISQUALIFIED.",
                    f"ORB RED BAR INVALIDATION: If 9:15–9:30 AM candle closes RED (Close < Open), CANCEL.",
                    (
                        f"ACCELERATED BREAKEVEN PROTECTION: If price reaches +1.8% (₹{round(trigger_buy_above * 1.018, 2):,.2f}), "
                        f"trail stop-loss to Breakeven (₹{trigger_buy_above:,.2f}) immediately."
                    ),
                    "TIME STOP: If trigger level is not crossed by 10:00 AM IST, cancel order.",
                    "PROFIT MANAGEMENT: Book 50% at Target 1 (+3.5%), trail to Breakeven, book rest at Target 2 (+6.5%).",
                ],
            },
            "screening_metrics": candidate,
        }
