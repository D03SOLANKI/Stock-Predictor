# Feature Extractor for Pre-Market Historical Top-Gainer Learning.
import math
from typing import Dict, Any, Optional
import numpy as np
import pandas as pd

def calculate_clean_air_margin(high: pd.Series, lookback: int = 20) -> float:
    if len(high) < lookback + 1:
        return 5.0
    curr_high = float(high.iloc[-1])
    prior_highs = high.iloc[-(lookback + 1):-1]
    max_prior = float(prior_highs.max())
    if curr_high >= max_prior:
        return 10.0
    higher_wicks = prior_highs[prior_highs > curr_high]
    if len(higher_wicks) == 0:
        return 10.0
    nearest_res = float(higher_wicks.min())
    margin = ((nearest_res - curr_high) / curr_high) * 100.0
    return round(margin, 2)

def extract_premarket_features(
    close: pd.Series,
    high: pd.Series,
    low: pd.Series,
    open_s: pd.Series,
    vol: pd.Series,
    bm_close: Optional[pd.Series] = None,
) -> Optional[Dict[str, Any]]:
    if len(close) < 25 or len(high) < 25 or len(vol) < 25:
        return None

    curr_close = float(close.iloc[-1])
    curr_high = float(high.iloc[-1])
    curr_low = float(low.iloc[-1])
    curr_vol = float(vol.iloc[-1])
    curr_open = float(open_s.iloc[-1]) if len(open_s) >= 1 else curr_close

    sma50 = float(close.tail(50).mean()) if len(close) >= 50 else float(close.mean())
    sma200 = float(close.tail(200).mean()) if len(close) >= 200 else float(close.mean())
    above_50sma = bool(curr_close > sma50)
    above_200sma = bool(curr_close > sma200)
    dist_50sma_pct = round((curr_close / sma50 - 1.0) * 100.0, 2)
    dist_200sma_pct = round((curr_close / sma200 - 1.0) * 100.0, 2)

    high_52w = float(high.tail(250).max()) if len(high) >= 250 else float(high.max())
    dist_52w_pct = round(((high_52w - curr_close) / high_52w) * 100.0, 2)

    ranges = high - low
    curr_range = float(ranges.iloc[-1]) if len(ranges) >= 1 else 1.0
    adr14 = float(ranges.tail(14).mean()) if len(ranges) >= 14 else curr_range
    adr_pct = round((adr14 / curr_close) * 100.0, 2)

    is_nr7 = bool(len(ranges) >= 7 and curr_range < float(ranges.iloc[-7:-1].min()))
    is_inside_day = bool(len(high) >= 2 and curr_high < float(high.iloc[-2]) and curr_low > float(low.iloc[-2]))
    range_compression = round(curr_range / (adr14 + 1e-6), 2)

    avg_vol_20 = float(vol.tail(20).mean()) + 1e-6
    vol_ratio_20d = round(curr_vol / avg_vol_20, 2)
    vol_dryup = bool(vol_ratio_20d <= 0.80)
    turnover_20d_cr = round(float((vol * close).tail(20).mean()) / 10000000.0, 2)

    clean_air_margin = calculate_clean_air_margin(high, lookback=20)
    has_clean_air = bool(clean_air_margin >= 2.0)

    rs_alpha_5d = 0.0
    rs_alpha_20d = 0.0
    composite_rs_alpha = 0.0
    if bm_close is not None and len(bm_close) >= 20 and len(close) >= 20:
        stock_5d = (curr_close / close.iloc[-6] - 1.0) * 100 if len(close) >= 6 else 0.0
        bm_5d = (bm_close.iloc[-1] / bm_close.iloc[-6] - 1.0) * 100 if len(bm_close) >= 6 else 0.0
        stock_20d = (curr_close / close.iloc[-21] - 1.0) * 100 if len(close) >= 21 else 0.0
        bm_20d = (bm_close.iloc[-1] / bm_close.iloc[-21] - 1.0) * 100 if len(bm_close) >= 21 else 0.0
        rs_alpha_5d = round(stock_5d - bm_5d, 2)
        rs_alpha_20d = round(stock_20d - bm_20d, 2)
        composite_rs_alpha = round(0.6 * rs_alpha_5d + 0.4 * rs_alpha_20d, 2)

    raw_trigger = curr_high + max(round(curr_high * 0.0010, 2), 0.10)
    trigger = round(math.ceil(raw_trigger / 0.05) * 0.05, 2)

    return {
        "curr_close": curr_close,
        "curr_high": curr_high,
        "curr_low": curr_low,
        "curr_vol": curr_vol,
        "trigger": trigger,
        "turnover_20d_cr": turnover_20d_cr,
        "above_50sma": above_50sma,
        "above_200sma": above_200sma,
        "dist_50sma_pct": dist_50sma_pct,
        "dist_200sma_pct": dist_200sma_pct,
        "dist_52w_pct": dist_52w_pct,
        "near_52w_high": bool(dist_52w_pct <= 8.0),
        "adr_pct": adr_pct,
        "is_nr7": is_nr7,
        "is_inside_day": is_inside_day,
        "range_compression": range_compression,
        "vol_ratio_20d": vol_ratio_20d,
        "vol_dryup": vol_dryup,
        "clean_air_margin": clean_air_margin,
        "has_clean_air": has_clean_air,
        "rs_alpha_5d": rs_alpha_5d,
        "rs_alpha_20d": rs_alpha_20d,
        "composite_rs_alpha": composite_rs_alpha,
    }
