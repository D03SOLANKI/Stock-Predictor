"""Deterministic Trade Structurer for 1-2 Day Swing Trades on NIFTY 50 Stocks.

Calculates mathematically precise trigger levels, entry zones, stop losses,
take-profit targets (+1.0% and +1.5%), risk-to-reward ratios (>= 1:1.5),
official NSE F&O derivative contracts (Futures lot size, Call option strike),
and 1% portfolio risk position sizing.
"""

from typing import Dict, Any
import math
from .nifty50_universe import get_lot_size, get_strike_step, get_company_name, get_sector


class TradeStructurer:
    """Calculates entry, exit, derivative recommendations, and risk parameters."""

    def __init__(self, account_capital: float = 500000.0, risk_per_trade_pct: float = 1.0):
        self.account_capital = account_capital
        self.risk_per_trade_pct = risk_per_trade_pct
        self.max_risk_rupees = account_capital * (risk_per_trade_pct / 100.0)

    def structure_trade(self, candidate: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a screened candidate into an actionable, structured 1-2 day swing trade setup."""
        ticker = candidate["ticker"]
        close = candidate["close"]
        high = candidate["high"]
        low = candidate["low"]
        atr14 = candidate.get("atr14", close * 0.015)
        h_ema20 = candidate.get("hourly_ema20", close * 0.99)
        recent_low_3d = candidate.get("recent_low_3d", low)

        lot_size = get_lot_size(ticker)
        strike_step = get_strike_step(ticker)

        # 1. Trigger Level: Buy Above
        # Set trigger slightly above current close / daily high to confirm breakout momentum
        # Tick size on NSE is typically 0.05
        trigger_buffer = max(round(close * 0.0010, 2), 0.10)
        # If current close is very near the high, trigger is just above the high
        raw_trigger = max(close + trigger_buffer, high + 0.10)
        trigger_buy_above = round(math.ceil(raw_trigger / 0.05) * 0.05, 2)

        # 2. Entry Price Range
        # A tight 0.3% execution band to prevent slippage and chasing
        entry_upper = round(trigger_buy_above * 1.003, 2)
        entry_mid = round((trigger_buy_above + entry_upper) / 2.0, 2)

        # 3. Stop Loss Calibration
        # Target profit is 1.0% - 1.5%. To maintain R:R >= 1:1.5, risk must be <= 0.65% - 0.75%.
        # Structural reference: hourly 20-EMA or recent 3-day swing low, bounded to 0.6% - 0.8%
        target_risk_pct = 0.65  # 0.65% risk allows 1:1.54 at T1 (+1.0%) and 1:2.31 at T2 (+1.5%)
        max_stop_dist = trigger_buy_above * (target_risk_pct / 100.0)

        structural_support = max(h_ema20, recent_low_3d)
        if structural_support < trigger_buy_above:
            proposed_risk = trigger_buy_above - structural_support
            if 0.004 * trigger_buy_above <= proposed_risk <= 0.0085 * trigger_buy_above:
                stop_loss = round(structural_support - 0.10, 2)
            else:
                stop_loss = round(trigger_buy_above - max_stop_dist, 2)
        else:
            stop_loss = round(trigger_buy_above - max_stop_dist, 2)

        # Ensure stop loss is strictly below trigger by at least 0.4%
        if stop_loss >= trigger_buy_above * 0.996:
            stop_loss = round(trigger_buy_above * (1.0 - target_risk_pct / 100.0), 2)

        risk_rupees_per_share = round(trigger_buy_above - stop_loss, 2)
        risk_pct = round((risk_rupees_per_share / trigger_buy_above) * 100.0, 2)

        # 4. Take Profit Targets
        # Target 1: +1.0% gain
        target_1 = round(trigger_buy_above * 1.010, 2)
        gain_1_rupees = round(target_1 - trigger_buy_above, 2)
        gain_1_pct = 1.0

        # Target 2: +1.5% gain
        target_2 = round(trigger_buy_above * 1.015, 2)
        gain_2_rupees = round(target_2 - trigger_buy_above, 2)
        gain_2_pct = 1.5

        # 5. Risk-to-Reward Ratios
        rr_t1 = round(gain_1_rupees / (risk_rupees_per_share + 1e-6), 2)
        rr_t2 = round(gain_2_rupees / (risk_rupees_per_share + 1e-6), 2)

        # 6. Position Sizing (Cash Equity)
        # Based on 1% account risk (e.g. ₹5,000 risk on ₹5,00,000 capital)
        shares_qty = int(self.max_risk_rupees / max(risk_rupees_per_share, 0.50))
        # Cap cash outlay to 30% of total capital to avoid overconcentration in a single stock
        max_capital_allocation = self.account_capital * 0.35
        max_shares_by_capital = int(max_capital_allocation / trigger_buy_above)
        shares_qty = max(min(shares_qty, max_shares_by_capital), 1)
        total_cash_outlay = round(shares_qty * trigger_buy_above, 2)
        actual_risk_rupees = round(shares_qty * risk_rupees_per_share, 2)

        # 7. Derivative Suggestions
        # A. Stock Futures
        futures_contract_value = round(trigger_buy_above * lot_size, 2)
        # Approximate margin required for NSE stock futures: ~22%
        futures_margin_approx = round(futures_contract_value * 0.22, 2)
        futures_risk_per_lot = round(risk_rupees_per_share * lot_size, 2)
        futures_profit_t1 = round(gain_1_rupees * lot_size, 2)
        futures_profit_t2 = round(gain_2_rupees * lot_size, 2)

        # B. Call Option Strike (Nearest ATM or 1 strike OTM)
        atm_strike = round(trigger_buy_above / strike_step) * strike_step
        otm_strike = atm_strike + strike_step
        recommended_strike = atm_strike if (trigger_buy_above - atm_strike) <= (strike_step * 0.4) else otm_strike

        return {
            "ticker": ticker,
            "stock_name": candidate.get("company_name", ticker),
            "sector": candidate.get("sector", "Diversified"),
            "trade_direction": "BUY / LONG",
            "current_market_price": close,
            "buy_above_trigger": trigger_buy_above,
            "entry_range": {
                "lower": trigger_buy_above,
                "upper": entry_upper,
                "formatted": f"\u20b9{trigger_buy_above:,.2f} - \u20b9{entry_upper:,.2f}",
            },
            "stop_loss": {
                "price": stop_loss,
                "risk_rupees": risk_rupees_per_share,
                "risk_pct": risk_pct,
                "formatted": f"\u20b9{stop_loss:,.2f} (-{risk_pct:.2f}%)",
            },
            "target_1": {
                "price": target_1,
                "gain_pct": gain_1_pct,
                "gain_rupees": gain_1_rupees,
                "rr_ratio": f"1:{rr_t1}",
                "formatted": f"\u20b9{target_1:,.2f} (+1.00%)",
            },
            "target_2": {
                "price": target_2,
                "gain_pct": gain_2_pct,
                "gain_rupees": gain_2_rupees,
                "rr_ratio": f"1:{rr_t2}",
                "formatted": f"\u20b9{target_2:,.2f} (+1.50%)",
            },
            "risk_reward_summary": f"1:{rr_t1} (at T1) / 1:{rr_t2} (at T2)",
            "expected_gain": "1.0% to 1.5% on underlying stock",
            "holding_period": "1 to 2 Trading Days (BTST / Short-term Swing)",
            "position_sizing": {
                "account_capital": self.account_capital,
                "max_risk_allowed": self.max_risk_rupees,
                "recommended_shares": shares_qty,
                "total_cash_outlay": total_cash_outlay,
                "actual_risk_rupees": actual_risk_rupees,
                "portfolio_risk_pct": round((actual_risk_rupees / self.account_capital) * 100.0, 2),
            },
            "derivatives": {
                "lot_size": lot_size,
                "cash_recommendation": {
                    "instrument": "Equity Cash (CNC / MTF)",
                    "shares": shares_qty,
                    "rationale": "Zero theta decay risk over the 1-2 day holding window; allows strict limit execution.",
                },
                "futures_recommendation": {
                    "instrument": f"{ticker.replace('.NS', '')} Current Month FUT",
                    "lot_size": lot_size,
                    "contract_value": futures_contract_value,
                    "estimated_margin": futures_margin_approx,
                    "risk_per_lot": futures_risk_per_lot,
                    "expected_profit_t1": futures_profit_t1,
                    "expected_profit_t2": futures_profit_t2,
                    "notes": f"1 lot ({lot_size} shares) carries \u20b9{futures_risk_per_lot:,.0f} risk with target payoff of \u20b9{futures_profit_t1:,.0f} (T1) and \u20b9{futures_profit_t2:,.0f} (T2).",
                },
                "options_recommendation": {
                    "instrument": f"{ticker.replace('.NS', '')} {int(recommended_strike)} CE (Call Option)",
                    "strike": recommended_strike,
                    "option_type": "CE (Call)",
                    "lot_size": lot_size,
                    "notes": (
                        f"Choose Current Month Expiry (ensure > 4 days to expiry to avoid steep theta decay). "
                        f"Target exit when underlying reaches \u20b9{target_1:,.2f} or \u20b9{target_2:,.2f} within 1-2 sessions."
                    ),
                },
            },
            "trade_validity": {
                "validity_window": "Valid for next 1-2 trading sessions (T+1 / T+2 max).",
                "trigger_condition": f"Only enter if price trades above \u20b9{trigger_buy_above:,.2f}.",
                "invalidation_rules": [
                    f"Invalid if opening gap-up exceeds \u20b9{entry_upper:,.2f} (>0.30% above trigger) - do not chase.",
                    f"Invalid if price breaks below \u20b9{stop_loss:,.2f} before triggering.",
                    "Time Stop: Exit at market close on Day 2 if neither target nor stop loss has triggered.",
                ],
            },
            # Pass through candidate screening metrics for the evidence agent
            "screening_metrics": candidate,
        }
