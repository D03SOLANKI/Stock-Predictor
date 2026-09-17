import sys
import os
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tradingagents.swing_opportunity import (
    CorporateCatalystAgent,
    PreMarketAuctionAgent,
    PreMarketTopGainerScreener,
    DayGainerStructurer,
)

def verify():
    print("1. Testing CorporateCatalystAgent...")
    cat_agent = CorporateCatalystAgent()
    sample_text = "Company secures major EPC order win worth Rs 1,450 Crore from Indian Railways"
    parsed = cat_agent.parse_announcement_text(sample_text)
    print("   Parsed Catalyst:", parsed["catalyst_type"], "| Score:", parsed["catalyst_score"], "| Major:", parsed["is_major_event"])
    assert parsed["has_catalyst"] == True
    assert parsed["catalyst_type"] == "ORDER_WIN"
    assert parsed["catalyst_score"] >= 85.0

    print("2. Testing PreMarketAuctionAgent...")
    auction_agent = PreMarketAuctionAgent()
    # Test valid open
    valid_res = auction_agent.evaluate_auction_open(
        ticker="BSE.NS",
        open_price=2750.0,
        prev_close=2720.0,
        indicative_buy_qty=150000,
        indicative_sell_qty=75000,
    )
    print("   Valid Open Status:", valid_res["status"], "| Gap:", valid_res["gap_pct"], "% | Imbalance:", valid_res["imbalance_ratio"], "x")
    assert valid_res["is_qualified"] == True

    # Test gap trap (> 2.5%)
    trap_res = auction_agent.evaluate_auction_open(
        ticker="VOLTAS.NS",
        open_price=1600.0,
        prev_close=1520.0,  # +5.2% gap
    )
    print("   Gap-Trap Status:", trap_res["status"], "| Gap:", trap_res["gap_pct"], "% | Qualified:", trap_res["is_qualified"])
    assert trap_res["is_qualified"] == False
    assert trap_res["status"] == "DISQUALIFIED_GAP_TRAP"

    print("3. Testing DayGainerStructurer 15m ORB Engine...")
    structurer = DayGainerStructurer(account_capital=100000.0)
    
    # Test confirmed green bar
    orb_confirmed = structurer.evaluate_15m_orb_confirmation(
        open_15m=500.0,
        high_15m=512.0,
        low_15m=498.0,
        close_15m=508.0,  # Green bar (508 > 500) & Above prev high (508 > 505)
        prev_high=505.0,
    )
    print("   ORB Confirmed Status:", orb_confirmed["status"], "| Execution Price:", orb_confirmed["execution_price"], "| Stop Loss:", orb_confirmed["confirmed_stop_loss"])
    assert orb_confirmed["is_confirmed"] == True
    assert orb_confirmed["execution_price"] == 508.0

    # Test rejected red candle trap
    orb_rejected = structurer.evaluate_15m_orb_confirmation(
        open_15m=510.0,
        high_15m=512.0,
        low_15m=496.0,
        close_15m=499.0,  # Red bar (499 < 510)
        prev_high=505.0,
    )
    print("   ORB Red Candle Trap Status:", orb_rejected["status"], "| Confirmed:", orb_rejected["is_confirmed"])
    assert orb_rejected["is_confirmed"] == False
    assert orb_rejected["status"] == "DISQUALIFIED_RED_CANDLE_TRAP"

    print("4. Testing PreMarketTopGainerScreener with cached data...")
    df_all = pd.read_parquet("data_cache_2y.parquet")
    screener = PreMarketTopGainerScreener(
        tickers=["BSE.NS", "MCX.NS", "ANGELONE.NS", "SAIL.NS"],
        min_turnover_crores=15.0,
    )
    # Test clean air margin calculation on sample series
    bse_high = df_all[("BSE.NS", "High")].dropna()
    bse_close = df_all[("BSE.NS", "Close")].dropna()
    margin, is_clean = screener.calculate_clean_air_margin(bse_high, bse_close, lookback=20)
    print(f"   BSE.NS Clean Air Margin: {margin}% | Is Clean Air: {is_clean}")
    assert isinstance(margin, float)
    assert isinstance(is_clean, (bool, np.bool_))

    print("\n[SUCCESS] All verification tests passed cleanly!")

if __name__ == "__main__":
    verify()
