"""Multi-Timeframe Screener for NIFTY 50 Short-Term Swing Opportunities.

Scans all 50 constituent stocks of the NIFTY 50 index using daily and hourly
OHLCV data. Evaluates Relative Strength vs NIFTY 50 (^NSEI), volume accumulation,
daily closing strength, multi-timeframe moving average alignment, and ATR-based
volatility to isolate the top 1-3 highest-probability 1-2 day swing candidates.
"""

import logging
from typing import Dict, Any, List, Optional
import numpy as np
import pandas as pd
import yfinance as yf

from .nifty50_universe import (
    NIFTY_50_TICKERS,
    get_ticker_metadata,
    get_company_name,
    get_sector,
)

logger = logging.getLogger(__name__)


class Nifty50Screener:
    """Scans and ranks NIFTY 50 stocks for 1-2 day swing / BTST setups."""

    def __init__(
        self,
        tickers: Optional[List[str]] = None,
        benchmark_ticker: str = "^NSEI",
    ):
        self.tickers = tickers or NIFTY_50_TICKERS
        self.benchmark_ticker = benchmark_ticker

    def _extract_series(self, df: pd.DataFrame, ticker: str, col: str) -> Optional[pd.Series]:
        """Safely extract a single price series from multi-ticker or single-ticker DataFrame."""
        try:
            if isinstance(df.columns, pd.MultiIndex):
                # Try (ticker, col) or (col, ticker)
                if (ticker, col) in df.columns:
                    s = df[(ticker, col)]
                elif (col, ticker) in df.columns:
                    s = df[(col, ticker)]
                else:
                    return None
            else:
                if col in df.columns:
                    s = df[col]
                else:
                    return None
            return s.dropna()
        except Exception:
            return None

    def _calculate_atr(self, high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> float:
        """Compute the Average True Range (ATR)."""
        if len(close) < period + 1:
            return float((high - low).mean()) if len(close) > 0 else 0.0
        prev_close = close.shift(1)
        tr1 = high - low
        tr2 = (high - prev_close).abs()
        tr3 = (low - prev_close).abs()
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(period).mean().iloc[-1]
        return float(atr) if not np.isnan(atr) else float(tr.mean())

    def _calculate_rsi(self, series: pd.Series, period: int = 14) -> float:
        """Compute the Relative Strength Index (RSI)."""
        if len(series) < period + 1:
            return 50.0
        delta = series.diff().dropna()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / (loss + 1e-9)
        rsi = 100 - (100 / (1 + rs))
        val = rsi.iloc[-1]
        return float(val) if not np.isnan(val) else 50.0

    def fetch_market_data(self) -> Dict[str, Any]:
        """Fetch daily and 1-hour OHLCV data for all tickers and benchmark in parallel."""
        all_symbols = list(set(self.tickers + [self.benchmark_ticker]))
        logger.info("Fetching daily data for %d symbols...", len(all_symbols))
        df_daily = yf.download(
            all_symbols,
            period="3mo",
            interval="1d",
            group_by="ticker",
            progress=False,
            auto_adjust=False,
        )

        logger.info("Fetching 1-hour data for %d tickers...", len(self.tickers))
        df_hourly = yf.download(
            self.tickers,
            period="5d",
            interval="1h",
            group_by="ticker",
            progress=False,
            auto_adjust=False,
        )

        return {"daily": df_daily, "hourly": df_hourly}

    def evaluate_ticker(
        self,
        ticker: str,
        df_daily: pd.DataFrame,
        df_hourly: pd.DataFrame,
        benchmark_returns: Dict[str, float],
    ) -> Optional[Dict[str, Any]]:
        """Evaluate a single ticker against quantitative swing criteria."""
        # Extract daily series
        d_close = self._extract_series(df_daily, ticker, "Close")
        d_high = self._extract_series(df_daily, ticker, "High")
        d_low = self._extract_series(df_daily, ticker, "Low")
        d_vol = self._extract_series(df_daily, ticker, "Volume")

        if d_close is None or len(d_close) < 20:
            return None

        curr_close = float(d_close.iloc[-1])
        curr_high = float(d_high.iloc[-1])
        curr_low = float(d_low.iloc[-1])
        curr_vol = float(d_vol.iloc[-1])

        # 1. Moving Averages
        ema20_series = d_close.ewm(span=20, adjust=False).mean()
        sma50_series = d_close.rolling(window=50, min_periods=20).mean()
        ema20 = float(ema20_series.iloc[-1])
        sma50 = float(sma50_series.iloc[-1])

        trend_score = 0.0
        if curr_close > ema20:
            trend_score += 15.0
        if ema20 > sma50:
            trend_score += 10.0
        elif curr_close > sma50:
            trend_score += 5.0

        # 2. Relative Strength vs Benchmark (^NSEI)
        # 3-day and 5-day percentage returns
        ret_3d = float((curr_close / d_close.iloc[-4] - 1.0) * 100) if len(d_close) >= 4 else 0.0
        ret_5d = float((curr_close / d_close.iloc[-6] - 1.0) * 100) if len(d_close) >= 6 else 0.0

        bm_3d = benchmark_returns.get("ret_3d", 0.0)
        bm_5d = benchmark_returns.get("ret_5d", 0.0)

        rs_3d = ret_3d - bm_3d
        rs_5d = ret_5d - bm_5d
        rs_composite = (0.6 * rs_3d) + (0.4 * rs_5d)

        rs_score = 0.0
        if rs_composite > 2.0:
            rs_score = 25.0
        elif rs_composite > 1.0:
            rs_score = 20.0
        elif rs_composite > 0.0:
            rs_score = 15.0
        elif rs_composite > -1.0:
            rs_score = 8.0
        else:
            rs_score = 0.0

        # 3. Volume Expansion
        avg_vol_20 = float(d_vol.tail(20).mean())
        vol_ratio = (curr_vol / (avg_vol_20 + 1e-6))
        vol_score = 0.0
        if vol_ratio >= 1.5:
            vol_score = 20.0
        elif vol_ratio >= 1.2:
            vol_score = 16.0
        elif vol_ratio >= 1.0:
            vol_score = 12.0
        elif vol_ratio >= 0.8:
            vol_score = 8.0
        else:
            vol_score = 4.0

        # 4. Daily Candle Quality (Close near high of day)
        day_range = max(curr_high - curr_low, 1e-4)
        close_range_pos = (curr_close - curr_low) / day_range
        candle_score = 0.0
        if close_range_pos >= 0.75:
            candle_score = 15.0
        elif close_range_pos >= 0.60:
            candle_score = 11.0
        elif close_range_pos >= 0.50:
            candle_score = 7.0
        else:
            candle_score = 2.0

        # 5. Volatility / ATR Check
        atr14 = self._calculate_atr(d_high, d_low, d_close, period=14)
        atr_pct = (atr14 / curr_close) * 100.0

        # 6. Hourly Timeframe Analysis
        h_close = self._extract_series(df_hourly, ticker, "Close")
        h_rsi = 50.0
        h_ema20 = curr_close
        hourly_score = 7.5
        hourly_trend_ok = False

        if h_close is not None and len(h_close) >= 14:
            h_rsi = self._calculate_rsi(h_close, period=14)
            h_ema20 = float(h_close.ewm(span=20, adjust=False).mean().iloc[-1])
            hourly_trend_ok = (curr_close >= h_ema20)

            # Sweet spot for 1-2 day swing continuation: 52 to 70 RSI
            if 52.0 <= h_rsi <= 72.0:
                hourly_score = 15.0 if hourly_trend_ok else 11.0
            elif 45.0 <= h_rsi < 52.0 and hourly_trend_ok:
                hourly_score = 10.0
            elif h_rsi > 72.0:
                hourly_score = 8.0  # extended, slight risk of immediate pullback
            else:
                hourly_score = 3.0

        # Total Composite Score (Max 100)
        composite_score = trend_score + rs_score + vol_score + candle_score + hourly_score

        # Daily Resistance & Recent Swings
        recent_high_3d = float(d_high.tail(3).max())
        recent_low_3d = float(d_low.tail(3).min())

        return {
            "ticker": ticker,
            "stock_name": get_company_name(ticker),
            "company_name": get_company_name(ticker),
            "sector": get_sector(ticker),
            "close": round(curr_close, 2),
            "high": round(curr_high, 2),
            "low": round(curr_low, 2),
            "volume": int(curr_vol),
            "volume_ratio": round(vol_ratio, 2),
            "ret_3d": round(ret_3d, 2),
            "ret_5d": round(ret_5d, 2),
            "rs_composite": round(rs_composite, 2),
            "ema20": round(ema20, 2),
            "sma50": round(sma50, 2),
            "atr14": round(atr14, 2),
            "atr_pct": round(atr_pct, 2),
            "close_range_pos": round(close_range_pos, 2),
            "hourly_rsi": round(h_rsi, 1),
            "hourly_ema20": round(h_ema20, 2),
            "hourly_trend_bullish": hourly_trend_ok,
            "recent_high_3d": round(recent_high_3d, 2),
            "recent_low_3d": round(recent_low_3d, 2),
            "composite_score": round(composite_score, 1),
            "score_breakdown": {
                "trend": trend_score,
                "relative_strength": rs_score,
                "volume": vol_score,
                "candle_strength": candle_score,
                "hourly_momentum": hourly_score,
            },
        }

    def scan(self, top_n: int = 3) -> List[Dict[str, Any]]:
        """Run the full multi-factor scan and return the top N opportunities."""
        data = self.fetch_market_data()
        df_daily = data["daily"]
        df_hourly = data["hourly"]

        # Calculate benchmark returns
        bm_close = self._extract_series(df_daily, self.benchmark_ticker, "Close")
        benchmark_returns = {"ret_3d": 0.0, "ret_5d": 0.0}
        if bm_close is not None and len(bm_close) >= 6:
            bm_curr = float(bm_close.iloc[-1])
            benchmark_returns["ret_3d"] = float((bm_curr / bm_close.iloc[-4] - 1.0) * 100)
            benchmark_returns["ret_5d"] = float((bm_curr / bm_close.iloc[-6] - 1.0) * 100)
            logger.info(
                "Benchmark %s returns: 3-day=%.2f%%, 5-day=%.2f%%",
                self.benchmark_ticker,
                benchmark_returns["ret_3d"],
                benchmark_returns["ret_5d"],
            )

        candidates = []
        for ticker in self.tickers:
            try:
                cand = self.evaluate_ticker(ticker, df_daily, df_hourly, benchmark_returns)
                if cand is not None:
                    candidates.append(cand)
            except Exception as exc:
                logger.warning("Failed to evaluate %s: %s", ticker, exc)

        # Sort descending by composite score
        candidates.sort(key=lambda x: x["composite_score"], reverse=True)

        logger.info(
            "Screened %d stocks. Top candidate: %s with score %.1f",
            len(candidates),
            candidates[0]["ticker"] if candidates else "None",
            candidates[0]["composite_score"] if candidates else 0.0,
        )

        return candidates[:top_n]
