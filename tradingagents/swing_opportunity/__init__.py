"""TradingAgents Swing & Pre-Market Opportunity Package.

Automated quantitative scanners and structured trade engines:
1. NIFTY 50 Short-Term Swing (1-2 day holding, 1-1.5% target)
2. Pre-Market NSE Mid & Small-Cap Top Gainer Discovery (Day momentum, +3.5% to +7.0% target)
"""

from .engine import SwingOpportunityEngine, SwingTradeOpportunity
from .nifty50_universe import NIFTY_50_TICKERS, NIFTY_50_METADATA
from .screener import Nifty50Screener
from .trade_structurer import TradeStructurer
from .evidence_agent import SwingEvidenceAgent

# Pre-Market Mid/Small-Cap Top Gainer Engine
from .mid_small_universe import (
    NSE_MID_SMALL_TICKERS,
    NSE_MID_SMALL_UNIVERSE,
    get_mid_small_tickers,
    get_mid_small_metadata,
)
from .premarket_screener import PreMarketTopGainerScreener
from .day_gainer_structurer import DayGainerStructurer
from .catalyst_agent import CorporateCatalystAgent
from .premarket_auction_agent import PreMarketAuctionAgent

__all__ = [
    "SwingOpportunityEngine",
    "SwingTradeOpportunity",
    "NIFTY_50_TICKERS",
    "NIFTY_50_METADATA",
    "Nifty50Screener",
    "TradeStructurer",
    "SwingEvidenceAgent",
    "NSE_MID_SMALL_TICKERS",
    "NSE_MID_SMALL_UNIVERSE",
    "get_mid_small_tickers",
    "get_mid_small_metadata",
    "PreMarketTopGainerScreener",
    "DayGainerStructurer",
    "CorporateCatalystAgent",
    "PreMarketAuctionAgent",
]
