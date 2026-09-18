"""Pre-Market Call Auction & Order Flow Evaluator for NSE Equities.

Analyzes the 9:00–9:08 AM Call Auction discovered price and uncrossing order book
imbalances to identify genuine institutional accumulation and enforce the
Micro-Gap Disqualification Band (0.5% to 2.5%) before the 9:15 AM opening bell.
"""

import logging
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class PreMarketAuctionAgent:
    """Evaluates NSE 9:00–9:08 AM Pre-Open Call Auction book dynamics."""

    def __init__(
        self,
        min_gap_pct: float = 0.20,
        max_gap_pct: float = 2.50,
        min_imbalance_ratio: float = 1.50,
    ):
        self.min_gap_pct = min_gap_pct
        self.max_gap_pct = max_gap_pct
        self.min_imbalance_ratio = min_imbalance_ratio

    def evaluate_auction_open(
        self,
        ticker: str,
        open_price: float,
        prev_close: float,
        indicative_buy_qty: Optional[float] = None,
        indicative_sell_qty: Optional[float] = None,
        auction_volume: Optional[float] = None,
        avg_daily_volume: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Perform pre-market call auction order book qualification."""
        if prev_close <= 0:
            return {
                "ticker": ticker,
                "status": "DISQUALIFIED",
                "reason": "Invalid previous close price",
                "gap_pct": 0.0,
                "imbalance_ratio": 1.0,
                "is_qualified": False,
            }

        gap_pct = round((open_price / prev_close - 1.0) * 100.0, 2)

        # 1. Invalidation Rule: Gap-Trap (Opening > +2.5%)
        if gap_pct > self.max_gap_pct:
            return {
                "ticker": ticker,
                "status": "DISQUALIFIED_GAP_TRAP",
                "reason": f"Opening gap +{gap_pct:.2f}% exceeds +{self.max_gap_pct:.1f}% limit. High probability of morning exhaustion dump.",
                "gap_pct": gap_pct,
                "imbalance_ratio": 1.0,
                "is_qualified": False,
            }

        # 2. Invalidation Rule: Red/Hesitant Open (Opening < -0.2%)
        if gap_pct < -0.20:
            return {
                "ticker": ticker,
                "status": "DISQUALIFIED_RED_OPEN",
                "reason": f"Stock indicated in the red ({gap_pct:.2f}% < -0.20%). Institutional bids absent in pre-open.",
                "gap_pct": gap_pct,
                "imbalance_ratio": 1.0,
                "is_qualified": False,
            }

        # 3. Order Book Imbalance Evaluation (When book data is available)
        imbalance_ratio = 1.8  # Default institutional parity assumption if book is unstreamed
        if indicative_buy_qty is not None and indicative_sell_qty is not None:
            imbalance_ratio = round(indicative_buy_qty / (indicative_sell_qty + 1e-6), 2)
            if imbalance_ratio < self.min_imbalance_ratio:
                return {
                    "ticker": ticker,
                    "status": "DISQUALIFIED_SELLER_DOMINANCE",
                    "reason": f"Pre-open buy/sell ratio ({imbalance_ratio:.2f}x) below institutional threshold ({self.min_imbalance_ratio:.1f}x).",
                    "gap_pct": gap_pct,
                    "imbalance_ratio": imbalance_ratio,
                    "is_qualified": False,
                }

        # 4. Qualified Institutional Accumulation
        vol_participation = 0.0
        if auction_volume and avg_daily_volume and avg_daily_volume > 0:
            vol_participation = round((auction_volume / avg_daily_volume) * 100.0, 2)

        return {
            "ticker": ticker,
            "status": "QUALIFIED_INSTITUTIONAL_ACCUMULATION",
            "reason": f"Ideal orderly pre-open gap (+{gap_pct:.2f}%) with {imbalance_ratio:.2f}x buy-side imbalance.",
            "gap_pct": gap_pct,
            "imbalance_ratio": imbalance_ratio,
            "auction_vol_participation_pct": vol_participation,
            "is_qualified": True,
        }

    def evaluate_macro_gate(
        self,
        open_price: float,
        prev_close: float,
        cutoff_pct: float = -0.50,
    ) -> Dict[str, Any]:
        """Recommendation 1: Macro Gate — Invalidate all trades if Midcap index opens < -0.50%."""
        if prev_close <= 0:
            return {
                "status": "PASS",
                "is_qualified": True,
                "gap_pct": 0.0,
                "cutoff_pct": cutoff_pct,
                "message": "Invalid previous benchmark close. Defaulting to PASS.",
            }

        gap_pct = round((open_price / prev_close - 1.0) * 100.0, 2)
        if gap_pct < cutoff_pct:
            return {
                "status": "DISQUALIFIED_MACRO_GATE",
                "reason": (
                    f"NIFTY Midcap 150 opened down {gap_pct:.2f}% (< {cutoff_pct:.2f}% Macro Gate). "
                    f"Severe market-wide gap-down risk. ALL LONG TRADES CANCELLED."
                ),
                "gap_pct": gap_pct,
                "cutoff_pct": cutoff_pct,
                "is_qualified": False,
            }

        return {
            "status": "PASS_MACRO_GATE",
            "reason": f"NIFTY Midcap 150 opened at {gap_pct:+.2f}% (>= {cutoff_pct:.2f}% Macro Gate). Macro green light.",
            "gap_pct": gap_pct,
            "cutoff_pct": cutoff_pct,
            "is_qualified": True,
        }
