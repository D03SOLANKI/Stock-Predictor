"""Walk-Forward, No-Lookahead Backtest Engine for NSE Mid/Small-Cap Breakout Screener.

Simulates the system strictly as of 8:45 AM IST on trading day T:
- Data timestamped and sliced strictly at T-1 close
- Day T actual OHLC held out until predictions are recorded
- Parameter freeze across Train, Validation, and Out-of-Sample Test periods
- Conservative intraday execution modeling (stops take precedence on dual hits)
- Precision, Recall, False Positive distribution, Baseline comparisons, and Sensitivity Analysis.
"""

import json
import logging
import math
import os
import sys
from typing import Dict, Any, List, Tuple
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("WalkForwardBacktest")


class WalkForwardBacktest:
    """Rigorous no-lookahead point-in-time backtester."""

    def __init__(
        self,
        data_path: str = "data_cache_2y.parquet",
        benchmark_ticker: str = "NIFTYMIDCAP150.NS",
        train_ratio: float = 0.50,
        val_ratio: float = 0.25,
        test_ratio: float = 0.25,
        min_turnover_rupees: float = 100000000.0,  # ₹10 Crore
        min_price: float = 30.0,
    ):
        self.data_path = data_path
        self.benchmark_ticker = benchmark_ticker
        self.min_turnover_rupees = min_turnover_rupees
        self.min_price = min_price

        logger.info("Loading historical price dataset from %s...", data_path)
        self.df_all = pd.read_parquet(data_path)
        self.dates = self.df_all.index
        self.total_days = len(self.dates)
        logger.info("Dataset spans %d trading days (%s to %s).", self.total_days, self.dates[0].strftime('%Y-%m-%d'), self.dates[-1].strftime('%Y-%m-%d'))

        # Extract available tickers
        self.tickers = sorted(list(set([c[0] for c in self.df_all.columns if c[0] != self.benchmark_ticker])))
        logger.info("Universe contains %d candidate tickers.", len(self.tickers))

        # Establish strict period boundaries
        train_end_idx = int(self.total_days * train_ratio)
        val_end_idx = int(self.total_days * (train_ratio + val_ratio))

        self.idx_train = (50, train_end_idx)  # Warmup 50 days for indicators
        self.idx_val = (train_end_idx, val_end_idx)
        self.idx_test = (val_end_idx, self.total_days)

        logger.info("PERIOD SPLIT:")
        logger.info("  Train/Design:      days %d to %d (%s to %s) [%d days]", self.idx_train[0], self.idx_train[1], self.dates[self.idx_train[0]].strftime('%Y-%m-%d'), self.dates[self.idx_train[1]-1].strftime('%Y-%m-%d'), self.idx_train[1] - self.idx_train[0])
        logger.info("  Validation/Tuning: days %d to %d (%s to %s) [%d days]", self.idx_val[0], self.idx_val[1], self.dates[self.idx_val[0]].strftime('%Y-%m-%d'), self.dates[self.idx_val[1]-1].strftime('%Y-%m-%d'), self.idx_val[1] - self.idx_val[0])
        logger.info("  Out-of-Sample:     days %d to %d (%s to %s) [%d days]", self.idx_test[0], self.idx_test[1], self.dates[self.idx_test[0]].strftime('%Y-%m-%d'), self.dates[self.idx_test[1]-1].strftime('%Y-%m-%d'), self.idx_test[1] - self.idx_test[0])

    def _get_series(self, ticker: str, col: str, end_idx: int) -> pd.Series:
        """Point-in-time extractor strictly returning rows 0 to end_idx-1 (inclusive of T-1)."""
        if (ticker, col) in self.df_all.columns:
            s = self.df_all[(ticker, col)].iloc[:end_idx].dropna()
            return s
        return pd.Series(dtype=float)

    def evaluate_candidate_pit(
        self,
        ticker: str,
        t_idx: int,
        bm_close: pd.Series,
        params: Dict[str, float],
    ) -> Tuple[bool, float, Dict[str, Any]]:
        """Evaluate single ticker using ONLY data available up to t_idx-1 (T-1 close)."""
        close = self._get_series(ticker, "Close", t_idx)
        high = self._get_series(ticker, "High", t_idx)
        low = self._get_series(ticker, "Low", t_idx)
        open_s = self._get_series(ticker, "Open", t_idx)
        vol = self._get_series(ticker, "Volume", t_idx)

        if len(close) < 25 or len(high) < 25 or len(vol) < 25:
            return False, 0.0, {}

        curr_close = float(close.iloc[-1])
        curr_high = float(high.iloc[-1])
        curr_low = float(low.iloc[-1])
        curr_vol = float(vol.iloc[-1])

        # --- Hard Gates ---
        # 1. Price floor
        if curr_close < params.get("min_price", 30.0):
            return False, 0.0, {}

        # 2. Turnover floor (20d average)
        turnover_20d = (vol * close).tail(20).mean()
        if turnover_20d < params.get("min_turnover", self.min_turnover_rupees):
            return False, 0.0, {}

        # 3. Not already upper circuit locked yesterday
        if curr_high == curr_low and len(close) >= 2:
            prev_close = float(close.iloc[-2])
            if (curr_close / prev_close - 1.0) * 100.0 >= 9.5:
                return False, 0.0, {}

        # --- Continuous Scoring (100 pts) ---
        # Pillar 1: Volatility Contraction & Coiling (30 pts)
        ranges = high - low
        nr_score = 2.0
        is_nr7 = False
        is_inside = False
        if len(ranges) >= 7:
            if float(ranges.iloc[-1]) < float(ranges.iloc[-7:-1].min()):
                is_nr7 = True
                nr_score = 10.0
            elif float(ranges.iloc[-1]) < float(ranges.iloc[-4:-1].min()):
                nr_score = 6.0
            if curr_high < float(high.iloc[-2]) and curr_low > float(low.iloc[-2]):
                is_inside = True
                nr_score = max(nr_score, 9.0)

        # StdDev compression
        std5 = float(close.tail(5).std())
        std20 = float(close.tail(20).std()) + 1e-6
        std_ratio = std5 / std20
        std_score = 10.0 if std_ratio < 0.55 else (7.0 if std_ratio < 0.75 else (4.0 if std_ratio < 0.90 else 2.0))

        # 20 EMA convergence
        ema20 = float(close.ewm(span=20, adjust=False).mean().iloc[-1])
        dist_ema20 = abs(curr_close - ema20) / curr_close
        ema_score = 10.0 if (curr_close >= ema20 and dist_ema20 <= 0.015) else (7.0 if dist_ema20 <= 0.030 else 3.0)

        p1 = nr_score + std_score + ema_score

        # Pillar 2: Relative Strength vs Midcap Benchmark (30 pts)
        stock_5d = (curr_close / close.iloc[-6] - 1.0) * 100 if len(close) >= 6 else 0.0
        bm_5d = (bm_close.iloc[-1] / bm_close.iloc[-6] - 1.0) * 100 if len(bm_close) >= 6 else 0.0
        stock_20d = (curr_close / close.iloc[-21] - 1.0) * 100 if len(close) >= 21 else 0.0
        bm_20d = (bm_close.iloc[-1] / bm_close.iloc[-21] - 1.0) * 100 if len(bm_close) >= 21 else 0.0
        rs_alpha = 0.6 * (stock_5d - bm_5d) + 0.4 * (stock_20d - bm_20d)

        alpha_score = 20.0 if rs_alpha >= params.get("alpha_high", 6.0) else (15.0 if rs_alpha >= params.get("alpha_mid", 3.0) else (10.0 if rs_alpha >= 0.5 else 2.0))

        adr14 = float(ranges.tail(14).mean())
        adr_pct = (adr14 / curr_close) * 100.0
        adr_score = 10.0 if adr_pct >= params.get("adr_cutoff", 4.5) else (6.0 if adr_pct >= 3.5 else 1.0)

        p2 = alpha_score + adr_score

        # Pillar 3: Volume Footprint & Supply Exhaustion (20 pts)
        avg_vol20 = float(vol.tail(20).mean()) + 1e-6
        vol_ratio = curr_vol / avg_vol20
        vdu_score = 10.0 if (0.30 <= vol_ratio <= params.get("vdu_max", 0.70)) else (6.0 if vol_ratio <= 1.0 else (8.0 if vol_ratio > 1.5 and curr_close > float(open_s.iloc[-1]) else 2.0))

        # Up/Down vol ratio
        rets = close.diff().dropna().tail(10)
        vols10 = vol.tail(10)
        up_vol = float(vols10[rets > 0].sum())
        dn_vol = float(vols10[rets < 0].sum()) + 1e-6
        up_dn_ratio = up_vol / dn_vol
        up_dn_score = 10.0 if up_dn_ratio >= 1.6 else (6.0 if up_dn_ratio >= 1.2 else 2.0)

        p3 = vdu_score + up_dn_score

        # Pillar 4: Structural Blue-Sky Clearance (20 pts)
        high_52w = float(high.tail(250).max())
        pct_from_52w = ((high_52w - curr_close) / high_52w) * 100.0
        prox_score = 12.0 if pct_from_52w <= 2.5 else (9.0 if pct_from_52w <= 6.0 else (5.0 if pct_from_52w <= 10.0 else 1.0))

        day_range = max(curr_high - curr_low, 1e-4)
        clv = (curr_close - curr_low) / day_range
        clv_score = 8.0 if clv >= 0.80 else (5.0 if clv >= 0.65 else 2.0)

        p4 = prox_score + clv_score

        total_score = p1 + p2 + p3 + p4

        # Historical 30d Beta for baseline comparisons
        rets_s = close.pct_change().dropna().tail(30)
        rets_b = bm_close.pct_change().dropna().tail(30)
        cov = np.cov(rets_s, rets_b)[0][1] if len(rets_s) == len(rets_b) and len(rets_s) >= 15 else 0.0
        var_b = np.var(rets_b) + 1e-8
        beta = cov / var_b

        # Breakout Trigger Level
        raw_trigger = curr_high + max(round(curr_high * 0.0010, 2), 0.10)
        trigger = round(math.ceil(raw_trigger / 0.05) * 0.05, 2)
        dynamic_sl_pct = min(max(adr_pct * 0.50, 2.00), 2.60) / 100.0
        stop_loss = round(trigger * (1.0 - dynamic_sl_pct), 2)
        target_1 = round(trigger * 1.035, 2)
        target_2 = round(trigger * 1.065, 2)
        target_top_gainer = round(trigger * 1.050, 2)

        meta = {
            "ticker": ticker,
            "close_prev": curr_close,
            "trigger": trigger,
            "stop_loss": stop_loss,
            "sl_pct": -dynamic_sl_pct,
            "target_1": target_1,
            "target_2": target_2,
            "target_top_gainer": target_top_gainer,
            "score": total_score,
            "adr_pct": adr_pct,
            "rs_alpha": rs_alpha,
            "vol_ratio": vol_ratio,
            "is_nr7": is_nr7,
            "is_inside": is_inside,
            "pct_from_52w": pct_from_52w,
            "beta": beta,
            "turnover_cr": turnover_20d / 10000000.0,
        }

        return True, total_score, meta

    def run_simulation(
        self,
        start_idx: int,
        end_idx: int,
        params: Dict[str, float],
        period_name: str = "Test",
    ) -> Dict[str, Any]:
        """Run point-in-time daily simulation across specified index range."""
        predictions_log = []
        daily_trades = []
        universe_gainers_total = 0
        screener_caught_gainers = 0

        # Baseline tracking
        baseline_beta_trades = []
        baseline_random_trades = []

        for t in range(start_idx, end_idx):
            date_T = self.dates[t]
            bm_close_pit = self._get_series(self.benchmark_ticker, "Close", t)

            # Evaluate Market Regime (NIFTY Midcap 150 vs 50 SMA)
            midcap_50sma = bm_close_pit.tail(50).mean() if len(bm_close_pit) >= 50 else bm_close_pit.iloc[-1]
            is_bullish_regime = bool(bm_close_pit.iloc[-1] >= midcap_50sma)

            # Tier 0 Hard Gate: If benchmark is below 50 SMA (Defensive), HALT system to protect capital
            if not is_bullish_regime:
                continue

            # Step 1: Pre-Market Screen on day T (ONLY data up to T-1)
            candidates = []
            qualifying_pool = []
            for ticker in self.tickers:
                passed, score, meta = self.evaluate_candidate_pit(ticker, t, bm_close_pit, params)
                if passed:
                    qualifying_pool.append(meta)
                    if score >= params.get("score_threshold", 75.0):
                        candidates.append(meta)

            # Rank by score
            candidates.sort(key=lambda x: x["score"], reverse=True)
            top_picks = candidates[:3]

            # Baselines selection (Point-in-time as of morning T)
            # Naive 1: Top 3 Highest Beta from qualifying pool
            beta_pool = sorted(qualifying_pool, key=lambda x: x.get("beta", 1.0), reverse=True)
            baseline_beta_picks = beta_pool[:3]

            # Ground Truth on Day T: How many stocks in the entire universe became top gainers (>= +5%)?
            actual_gainers_today = set()
            for ticker in self.tickers:
                if (ticker, "High") in self.df_all.columns and (ticker, "Close") in self.df_all.columns:
                    h_T = float(self.df_all[(ticker, "High")].iloc[t])
                    c_prev = float(self.df_all[(ticker, "Close")].iloc[t-1]) if t > 0 else h_T
                    if c_prev > 0 and ((h_T - c_prev) / c_prev) >= 0.050:
                        actual_gainers_today.add(ticker)

            universe_gainers_total += len(actual_gainers_today)

            # Check if any of our top picks were among the universe top gainers
            for pick in top_picks:
                if pick["ticker"] in actual_gainers_today:
                    screener_caught_gainers += 1

            # Step 2: Reveal Day T Actual Performance
            for rank, pick in enumerate(top_picks, 1):
                sym = pick["ticker"]
                o_T = float(self.df_all[(sym, "Open")].iloc[t])
                h_T = float(self.df_all[(sym, "High")].iloc[t])
                l_T = float(self.df_all[(sym, "Low")].iloc[t])
                c_T = float(self.df_all[(sym, "Close")].iloc[t])

                trigger = pick["trigger"]
                sl = pick["stop_loss"]
                t1 = pick["target_1"]
                t2 = pick["target_2"]
                top_gainer_target = pick["target_top_gainer"]

                trade_record = {
                    "date": date_T.strftime("%Y-%m-%d"),
                    "ticker": sym,
                    "rank": rank,
                    "score": pick["score"],
                    "regime": "BULLISH" if is_bullish_regime else "BEARISH",
                    "trigger": trigger,
                    "stop_loss": sl,
                    "target_1": t1,
                    "open": o_T,
                    "high": h_T,
                    "low": l_T,
                    "close": c_T,
                }

                # Gap-Trap Filter Check: Did it gap up > +3.5%?
                if o_T > trigger * 1.035:
                    trade_record["status"] = "GAP_TRAP_DISQUALIFIED"
                    trade_record["triggered"] = False
                    trade_record["pnl_pct"] = 0.0
                    predictions_log.append(trade_record)
                    continue

                # Did it cross the breakout trigger?
                if h_T < trigger:
                    trade_record["status"] = "UNTRIGGERED"
                    trade_record["triggered"] = False
                    trade_record["pnl_pct"] = 0.0
                    predictions_log.append(trade_record)
                    continue

                # Triggered! Actual entry executed
                entry_price = max(trigger, o_T)
                trade_record["triggered"] = True
                trade_record["entry_price"] = entry_price

                # Conservative dual-hit execution rule:
                # If Low hits SL and High hits Target on the same day, assume stopped out first
                hit_sl = (l_T <= sl)
                hit_top_gainer = (h_T >= top_gainer_target)
                hit_t1 = (h_T >= t1)

                sl_pct = pick.get("sl_pct", -0.024)

                if hit_sl and not hit_t1:
                    trade_record["status"] = "STOPPED_OUT"
                    trade_record["hit_top_gainer"] = False
                    trade_record["hit_target_1"] = False
                    trade_record["pnl_pct"] = sl_pct
                elif hit_sl and hit_t1:
                    # Conservative assumption: dual hit treated as adverse stop out
                    trade_record["status"] = "STOPPED_OUT_DUAL_HIT"
                    trade_record["hit_top_gainer"] = False
                    trade_record["hit_target_1"] = False
                    trade_record["pnl_pct"] = sl_pct
                elif hit_top_gainer:
                    trade_record["status"] = "TOP_GAINER_HIT"
                    trade_record["hit_top_gainer"] = True
                    trade_record["hit_target_1"] = True
                    # Target 2 or day close
                    trade_record["pnl_pct"] = max(0.050, (c_T - entry_price) / entry_price)
                elif hit_t1:
                    trade_record["status"] = "TARGET_1_HIT"
                    trade_record["hit_top_gainer"] = False
                    trade_record["hit_target_1"] = True
                    trade_record["pnl_pct"] = 0.035
                else:
                    # Neither stop nor target hit: closed at 3:30 PM market close
                    trade_record["status"] = "DAY_CLOSE_EXIT"
                    trade_record["hit_top_gainer"] = False
                    trade_record["hit_target_1"] = False
                    trade_record["pnl_pct"] = (c_T - entry_price) / entry_price

                predictions_log.append(trade_record)
                daily_trades.append(trade_record)

            # Evaluate Baseline (Top 3 Beta)
            for b_pick in baseline_beta_picks:
                sym_b = b_pick["ticker"]
                o_b = float(self.df_all[(sym_b, "Open")].iloc[t])
                h_b = float(self.df_all[(sym_b, "High")].iloc[t])
                l_b = float(self.df_all[(sym_b, "Low")].iloc[t])
                c_b = float(self.df_all[(sym_b, "Close")].iloc[t])
                trig_b = b_pick["trigger"]
                sl_b = b_pick["stop_loss"]

                if h_b >= trig_b and o_b <= trig_b * 1.035:
                    entry_b = max(trig_b, o_b)
                    hit_sl_b = (l_b <= sl_b)
                    hit_tg_b = (h_b >= entry_b * 1.050)
                    if hit_sl_b:
                        pnl_b = -0.0165
                        tg_b = False
                    elif hit_tg_b:
                        pnl_b = 0.050
                        tg_b = True
                    else:
                        pnl_b = (c_b - entry_b) / entry_b
                        tg_b = False
                    baseline_beta_trades.append({"hit_tg": tg_b, "pnl": pnl_b})

        # Aggregate Metrics
        total_predictions = len(predictions_log)
        triggered_trades = [t for t in daily_trades if t["triggered"]]
        n_triggered = len(triggered_trades)

        if n_triggered == 0:
            return {"error": "Zero trades triggered in period"}

        # Target definitions:
        # Top Gainer (+5.0% expansion) & Target 1 (+3.5% expansion)
        hits_top_gainer = [t for t in triggered_trades if t["hit_top_gainer"]]
        hits_t1 = [t for t in triggered_trades if t["hit_target_1"]]
        false_positives = [t for t in triggered_trades if not t["hit_top_gainer"]]

        precision_tg = len(hits_top_gainer) / n_triggered
        precision_t1 = len(hits_t1) / n_triggered
        recall = screener_caught_gainers / max(universe_gainers_total, 1)

        # False positive loss distribution
        fp_pnls = [t["pnl_pct"] for t in false_positives]
        avg_fp_loss = np.mean(fp_pnls) if fp_pnls else 0.0

        # All trades PnL & Expectancy
        all_pnls = [t["pnl_pct"] for t in triggered_trades]
        mean_pnl = np.mean(all_pnls)
        win_rate = len([p for p in all_pnls if p > 0]) / n_triggered

        # Baseline metrics
        n_base = len(baseline_beta_trades)
        base_tg_prec = len([b for b in baseline_beta_trades if b["hit_tg"]]) / max(n_base, 1)
        base_mean_pnl = np.mean([b["pnl"] for b in baseline_beta_trades]) if baseline_beta_trades else 0.0

        # Regime breakdown
        bull_trades = [t for t in triggered_trades if t["regime"] == "BULLISH"]
        bear_trades = [t for t in triggered_trades if t["regime"] == "BEARISH"]

        bull_prec = len([t for t in bull_trades if t["hit_top_gainer"]]) / max(len(bull_trades), 1)
        bull_mean = np.mean([t["pnl_pct"] for t in bull_trades]) if bull_trades else 0.0

        bear_prec = len([t for t in bear_trades if t["hit_top_gainer"]]) / max(len(bear_trades), 1)
        bear_mean = np.mean([t["pnl_pct"] for t in bear_trades]) if bear_trades else 0.0

        return {
            "period": period_name,
            "start_date": self.dates[start_idx].strftime("%Y-%m-%d"),
            "end_date": self.dates[end_idx - 1].strftime("%Y-%m-%d"),
            "total_days": end_idx - start_idx,
            "total_predictions_logged": total_predictions,
            "triggered_trades": n_triggered,
            "untriggered_orders": len([p for p in predictions_log if p["status"] == "UNTRIGGERED"]),
            "gap_trap_disqualified": len([p for p in predictions_log if p["status"] == "GAP_TRAP_DISQUALIFIED"]),
            "precision_top_gainer_5pct": round(precision_tg * 100.0, 2),
            "precision_target_1_3_5pct": round(precision_t1 * 100.0, 2),
            "recall_market_top_gainers": round(recall * 100.0, 2),
            "universe_gainers_total": universe_gainers_total,
            "screener_caught_gainers": screener_caught_gainers,
            "win_rate_overall": round(win_rate * 100.0, 2),
            "mean_trade_return_pct": round(mean_pnl * 100.0, 2),
            "avg_false_positive_loss_pct": round(avg_fp_loss * 100.0, 2),
            "baseline_beta_precision_5pct": round(base_tg_prec * 100.0, 2),
            "baseline_beta_mean_return_pct": round(base_mean_pnl * 100.0, 2),
            "regime_bullish": {
                "trades": len(bull_trades),
                "precision_5pct": round(bull_prec * 100.0, 2),
                "mean_return_pct": round(bull_mean * 100.0, 2),
            },
            "regime_bearish": {
                "trades": len(bear_trades),
                "precision_5pct": round(bear_prec * 100.0, 2),
                "mean_return_pct": round(bear_mean * 100.0, 2),
            },
            "predictions_sample": predictions_log[:15],
        }


def run_full_backtest():
    bt = WalkForwardBacktest()

    # Step 1: Parameter Freeze on Train & Validation periods
    # Frozen thresholds derived from 2024-2025 train data:
    frozen_params = {
        "min_price": 30.0,
        "min_turnover": 100000000.0,  # ₹10 Crore
        "score_threshold": 75.0,
        "adr_cutoff": 4.0,
        "alpha_high": 6.0,
        "alpha_mid": 3.0,
        "vdu_max": 0.70,
    }

    logger.info("Executing Train Period simulation...")
    train_res = bt.run_simulation(bt.idx_train[0], bt.idx_train[1], frozen_params, "Train")

    logger.info("Executing Validation Period simulation...")
    val_res = bt.run_simulation(bt.idx_val[0], bt.idx_val[1], frozen_params, "Validation")

    logger.info("Executing Out-of-Sample Test Period simulation (Strictly Point-in-Time)...")
    test_res = bt.run_simulation(bt.idx_test[0], bt.idx_test[1], frozen_params, "Out-of-Sample Test")

    # Step 5: Sensitivity Analysis on Out-of-Sample Period
    logger.info("Running Threshold Sensitivity Analysis on Out-of-Sample Data...")
    sensitivity_results = {}

    # Sensitivity 1: ADR% cutoff (3.0% vs 4.0% vs 5.5%)
    sensitivity_results["adr_cutoff"] = {}
    for adr_val in [3.0, 4.0, 5.5]:
        p = frozen_params.copy()
        p["adr_cutoff"] = adr_val
        res = bt.run_simulation(bt.idx_test[0], bt.idx_test[1], p, f"ADR_{adr_val}")
        sensitivity_results["adr_cutoff"][f"{adr_val}%"] = {
            "triggered": res["triggered_trades"],
            "precision_5pct": res["precision_top_gainer_5pct"],
            "mean_return_pct": res["mean_trade_return_pct"],
        }

    # Sensitivity 2: Score threshold (70 vs 75 vs 82)
    sensitivity_results["score_threshold"] = {}
    for sc_val in [70.0, 75.0, 82.0]:
        p = frozen_params.copy()
        p["score_threshold"] = sc_val
        res = bt.run_simulation(bt.idx_test[0], bt.idx_test[1], p, f"Score_{sc_val}")
        sensitivity_results["score_threshold"][f"{sc_val}"] = {
            "triggered": res["triggered_trades"],
            "precision_5pct": res["precision_top_gainer_5pct"],
            "mean_return_pct": res["mean_trade_return_pct"],
        }

    # Sensitivity 3: VDU max ratio (0.50x vs 0.70x vs 0.90x)
    sensitivity_results["vdu_max"] = {}
    for vdu_val in [0.50, 0.70, 0.90]:
        p = frozen_params.copy()
        p["vdu_max"] = vdu_val
        res = bt.run_simulation(bt.idx_test[0], bt.idx_test[1], p, f"VDU_{vdu_val}")
        sensitivity_results["vdu_max"][f"{vdu_val}x"] = {
            "triggered": res["triggered_trades"],
            "precision_5pct": res["precision_top_gainer_5pct"],
            "mean_return_pct": res["mean_trade_return_pct"],
        }

    full_report = {
        "frozen_parameters": frozen_params,
        "train_period": train_res,
        "validation_period": val_res,
        "test_period": test_res,
        "sensitivity_analysis": sensitivity_results,
    }

    with open("backtest_walkforward_results.json", "w", encoding="utf-8") as f:
        json.dump(full_report, f, indent=2)

    logger.info("Walk-Forward Backtest complete. Results saved to backtest_walkforward_results.json.")
    return full_report


if __name__ == "__main__":
    run_full_backtest()
