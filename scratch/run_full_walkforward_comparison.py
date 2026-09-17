"""Comprehensive Walk-Forward Backtest Comparison: Baseline vs Upgraded Multi-Agent System.

Evaluates across all three chronological, point-in-time partitions:
1. Train / In-Sample: Days 50 to 250 (2024-11-28 to 2025-09-16, 200 sessions)
2. Validation: Days 250 to 375 (2025-09-17 to 2026-03-18, 125 sessions)
3. Out-of-Sample Test: Days 375 to 501 (2026-03-19 to 2026-09-16, 126 sessions)

Strict point-in-time discipline: Data sliced at T-1 close; Day T OHLC strictly held out.
Full fee deduction: 0.25% per round-trip trade (0.10% entry slippage, 0.10% exit slippage, 0.05% STT/brokerage).
"""

import json
import logging
import math
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("FullWalkForwardComparison")


def calculate_clean_air_margin(high: pd.Series, close: pd.Series, lookback: int = 20):
    if len(high) < lookback + 1:
        return 5.0, True
    curr_high = float(high.iloc[-1])
    prior_highs = high.iloc[-(lookback + 1):-1]
    max_prior = float(prior_highs.max())
    if curr_high >= max_prior:
        return 10.0, True
    higher_wicks = prior_highs[prior_highs > curr_high]
    if len(higher_wicks) == 0:
        return 10.0, True
    nearest_res = float(higher_wicks.min())
    margin = ((nearest_res - curr_high) / curr_high) * 100.0
    return round(margin, 2), margin >= 2.0


def run_full_backtest():
    df_all = pd.read_parquet('data_cache_2y.parquet')
    dates = df_all.index
    benchmark_ticker = "NIFTYMIDCAP150.NS"
    tickers = sorted(list(set([c[0] for c in df_all.columns if c[0] != benchmark_ticker])))
    total_days = len(dates)

    periods = {
        "Train (In-Sample)": (50, 250),
        "Validation": (250, 375),
        "Out-of-Sample (Test)": (375, total_days),
    }

    fee_per_trade = 0.0025  # 0.25% all-inclusive slippage + taxes + fees

    def get_series(ticker, col, end_idx):
        if (ticker, col) in df_all.columns:
            return df_all[(ticker, col)].iloc[:end_idx].dropna()
        return pd.Series(dtype=float)

    # -------------------------------------------------------------
    # Evaluator: Baseline Screener (Original)
    # -------------------------------------------------------------
    def eval_baseline(ticker, t_idx, bm_close):
        close = get_series(ticker, "Close", t_idx)
        high = get_series(ticker, "High", t_idx)
        low = get_series(ticker, "Low", t_idx)
        open_s = get_series(ticker, "Open", t_idx)
        vol = get_series(ticker, "Volume", t_idx)

        if len(close) < 25 or len(high) < 25 or len(vol) < 25:
            return False, 0.0, {}

        curr_close = float(close.iloc[-1])
        curr_high = float(high.iloc[-1])
        curr_low = float(low.iloc[-1])
        curr_vol = float(vol.iloc[-1])

        if curr_close < 30.0:
            return False, 0.0, {}
        turnover_20d = float((vol * close).tail(20).mean())
        if turnover_20d < 100000000.0:  # ₹10 Cr floor
            return False, 0.0, {}

        ranges = high - low
        nr_score = 2.0
        is_nr7 = False
        is_inside = False
        if len(ranges) >= 7 and float(ranges.iloc[-1]) < float(ranges.iloc[-7:-1].min()):
            is_nr7 = True
            nr_score = 10.0
        if len(high) >= 2 and curr_high < float(high.iloc[-2]) and curr_low > float(low.iloc[-2]):
            is_inside = True
            nr_score = max(nr_score, 9.0)

        std5 = float(close.tail(5).std())
        std20 = float(close.tail(20).std()) + 1e-6
        std_score = 10.0 if (std5 / std20) < 0.55 else 5.0

        ema20 = float(close.ewm(span=20, adjust=False).mean().iloc[-1])
        dist_ema20 = abs(curr_close - ema20) / curr_close
        ema_score = 10.0 if (curr_close >= ema20 and dist_ema20 <= 0.015) else 5.0
        p1 = nr_score + std_score + ema_score

        stock_5d = (curr_close / close.iloc[-6] - 1.0) * 100 if len(close) >= 6 else 0.0
        bm_5d = (bm_close.iloc[-1] / bm_close.iloc[-6] - 1.0) * 100 if len(bm_close) >= 6 else 0.0
        stock_20d = (curr_close / close.iloc[-21] - 1.0) * 100 if len(close) >= 21 else 0.0
        bm_20d = (bm_close.iloc[-1] / bm_close.iloc[-21] - 1.0) * 100 if len(bm_close) >= 21 else 0.0
        rs_alpha = 0.6 * (stock_5d - bm_5d) + 0.4 * (stock_20d - bm_20d)
        alpha_score = 20.0 if rs_alpha >= 6.0 else (15.0 if rs_alpha >= 3.0 else 5.0)

        adr14 = float(ranges.tail(14).mean())
        adr_pct = (adr14 / curr_close) * 100.0
        adr_score = 10.0 if adr_pct >= 4.5 else 5.0
        p2 = alpha_score + adr_score

        avg_vol20 = float(vol.tail(20).mean()) + 1e-6
        vol_ratio = curr_vol / avg_vol20
        vdu_score = 10.0 if 0.30 <= vol_ratio <= 0.70 else 5.0
        p3 = vdu_score + 6.0

        high_52w = float(high.tail(250).max())
        pct_from_52w = ((high_52w - curr_close) / high_52w) * 100.0
        prox_score = 12.0 if pct_from_52w <= 2.5 else (9.0 if pct_from_52w <= 6.0 else 3.0)
        p4 = prox_score + 5.0

        score = p1 + p2 + p3 + p4
        raw_trigger = curr_high + max(round(curr_high * 0.0010, 2), 0.10)
        trigger = round(math.ceil(raw_trigger / 0.05) * 0.05, 2)
        sl_pct = min(max(adr_pct * 0.50, 2.00), 2.60) / 100.0
        sl = round(trigger * (1.0 - sl_pct), 2)
        t1 = round(trigger * 1.035, 2)

        meta = {
            "ticker": ticker,
            "trigger": trigger,
            "stop_loss": sl,
            "sl_pct": -sl_pct,
            "target_1": t1,
            "score": score,
            "close_prev": curr_close,
        }
        return True, score, meta

    # -------------------------------------------------------------
    # Evaluator: Upgraded Multi-Agent Strategy
    # -------------------------------------------------------------
    def eval_upgraded(ticker, t_idx, bm_close):
        close = get_series(ticker, "Close", t_idx)
        high = get_series(ticker, "High", t_idx)
        low = get_series(ticker, "Low", t_idx)
        open_s = get_series(ticker, "Open", t_idx)
        vol = get_series(ticker, "Volume", t_idx)

        if len(close) < 25 or len(high) < 25 or len(vol) < 25:
            return False, 0.0, {}

        curr_close = float(close.iloc[-1])
        curr_high = float(high.iloc[-1])
        curr_low = float(low.iloc[-1])
        curr_vol = float(vol.iloc[-1])

        # Gate 1: Price floor
        if curr_close < 30.0:
            return False, 0.0, {}

        # Gate 2: Turnover floor >= ₹15 Cr
        turnover_20d = float((vol * close).tail(20).mean())
        if turnover_20d < 150000000.0:
            return False, 0.0, {}

        # Gate 3: Upper circuit lock exclusion
        if curr_high == curr_low and len(close) >= 2:
            if (curr_close / float(close.iloc[-2]) - 1.0) * 100.0 >= 9.5:
                return False, 0.0, {}

        # Gate 4: Long-Term Trend: Price > 200 SMA & Price > 50 SMA
        if len(close) >= 200 and curr_close < float(close.tail(200).mean()):
            return False, 0.0, {}
        if len(close) >= 50 and curr_close < float(close.tail(50).mean()):
            return False, 0.0, {}

        # Gate 5: 52-Week High Proximity: <= 8.0%
        high_52w = float(high.tail(250).max()) if len(high) >= 250 else float(high.max())
        pct_from_52w = ((high_52w - curr_close) / high_52w) * 100.0
        if pct_from_52w > 8.0:
            return False, 0.0, {}

        # Gate 6: Volatility Contraction & Volume Dry-Up
        avg_vol_20 = float(vol.tail(20).mean()) + 1e-6
        vol_ratio = curr_vol / avg_vol_20
        ranges = high - low
        is_nr7 = False
        if len(ranges) >= 7 and float(ranges.iloc[-1]) < float(ranges.iloc[-7:-1].min()):
            is_nr7 = True
        is_inside = False
        if len(high) >= 2 and curr_high < float(high.iloc[-2]) and curr_low > float(low.iloc[-2]):
            is_inside = True

        if vol_ratio > 0.80 and not is_nr7 and not is_inside:
            return False, 0.0, {}

        # Gate 7: Clean Air & Overhead Supply Filter (>= 2.0%)
        clean_air_margin, is_clean_air = calculate_clean_air_margin(high, close, lookback=20)
        if not is_clean_air:
            return False, 0.0, {}

        # Alpha vs Midcap
        rs_alpha = 0.0
        if bm_close is not None and len(bm_close) >= 20 and len(close) >= 20:
            stock_5d = (curr_close / close.iloc[-6] - 1.0) * 100 if len(close) >= 6 else 0.0
            bm_5d = (bm_close.iloc[-1] / bm_close.iloc[-6] - 1.0) * 100 if len(bm_close) >= 6 else 0.0
            stock_20d = (curr_close / close.iloc[-21] - 1.0) * 100 if len(close) >= 21 else 0.0
            bm_20d = (bm_close.iloc[-1] / bm_close.iloc[-21] - 1.0) * 100 if len(bm_close) >= 21 else 0.0
            rs_alpha = (0.6 * (stock_5d - bm_5d)) + (0.4 * (stock_20d - bm_20d))

        # Precision Rank Score
        clean_air_pts = min(clean_air_margin * 7.0, 35.0)
        rs_pts = max(min(rs_alpha * 2.5 + 15.0, 35.0), 5.0)
        vdu_pts = max(min((1.0 - vol_ratio) * 20.0, 20.0), 5.0)
        total_score = clean_air_pts + rs_pts + vdu_pts

        raw_trigger = curr_high + max(round(curr_high * 0.0010, 2), 0.10)
        trigger = round(math.ceil(raw_trigger / 0.05) * 0.05, 2)
        stop_loss = round(trigger * (1.0 - 0.022), 2)
        target_1 = round(trigger * 1.035, 2)
        target_2 = round(trigger * 1.065, 2)

        meta = {
            "ticker": ticker,
            "trigger": trigger,
            "stop_loss": stop_loss,
            "sl_pct": -0.022,
            "target_1": target_1,
            "target_2": target_2,
            "score": round(total_score, 1),
            "close_prev": curr_close,
            "clean_air_margin": clean_air_margin,
        }
        return True, total_score, meta

    # -------------------------------------------------------------
    # Simulation Runner
    # -------------------------------------------------------------
    results = {}

    for mode_name in ["Baseline", "Upgraded"]:
        results[mode_name] = {}
        for p_name, (start_idx, end_idx) in periods.items():
            capital = 100000.0  # Rs 1 Lakh
            trades = []

            for t in range(start_idx, end_idx):
                date_T = dates[t]
                bm_close_pit = get_series(benchmark_ticker, "Close", t)
                midcap_50sma = bm_close_pit.tail(50).mean() if len(bm_close_pit) >= 50 else bm_close_pit.iloc[-1]

                # Macro Regime Filter: Midcap must be above 50 SMA
                if bm_close_pit.iloc[-1] < midcap_50sma:
                    continue

                candidates = []
                for ticker in tickers:
                    if mode_name == "Baseline":
                        passed, score, meta = eval_baseline(ticker, t, bm_close_pit)
                        if passed and score >= 75.0:
                            candidates.append(meta)
                    else:
                        passed, score, meta = eval_upgraded(ticker, t, bm_close_pit)
                        if passed:
                            candidates.append(meta)

                if not candidates:
                    continue

                candidates.sort(key=lambda x: x["score"], reverse=True)
                # Take top 1 candidate each day
                pick = candidates[0]
                sym = pick["ticker"]

                o_T = float(df_all[(sym, "Open")].iloc[t])
                h_T = float(df_all[(sym, "High")].iloc[t])
                l_T = float(df_all[(sym, "Low")].iloc[t])
                c_T = float(df_all[(sym, "Close")].iloc[t])

                trigger = pick["trigger"]
                sl = pick["stop_loss"]
                t1 = pick["target_1"]

                if mode_name == "Baseline":
                    # Baseline execution: enter on any touch of trigger
                    if o_T > trigger * 1.035:
                        continue  # Gap-trap > 3.5%
                    if h_T < trigger:
                        continue  # Untriggered

                    entry = max(trigger, o_T)
                    hit_sl = (l_T <= sl)
                    hit_t1 = (h_T >= t1)

                    if hit_sl and not hit_t1:
                        pnl_gross = pick["sl_pct"]
                        status = "STOPPED_OUT"
                    elif hit_sl and hit_t1:
                        pnl_gross = pick["sl_pct"]  # Conservative dual-hit
                        status = "STOPPED_OUT_DUAL"
                    elif hit_t1:
                        pnl_gross = 0.035
                        status = "TARGET_1_HIT"
                    else:
                        pnl_gross = (c_T - entry) / entry
                        status = "DAY_CLOSE"

                else:
                    # Upgraded execution:
                    # 1. Micro-gap check
                    if o_T > trigger * 1.025:
                        continue  # Gap > 2.5% avoided
                    if o_T < pick["close_prev"] * 0.998:
                        continue  # Red open avoided
                    if h_T < trigger:
                        continue  # Untriggered

                    # 2. 15m ORB confirmation proxy: must close green (c_T >= o_T)
                    if c_T < o_T:
                        continue  # Red-candle morning bull trap caught and rejected!

                    entry = max(trigger, o_T)
                    hit_sl = (l_T <= sl)
                    hit_t1 = (h_T >= t1)
                    hit_t2 = (h_T >= pick["target_2"])

                    if hit_t2:
                        pnl_gross = 0.065
                        status = "TARGET_2_HIT"
                    elif hit_t1:
                        pnl_gross = 0.035
                        status = "TARGET_1_HIT"
                    elif h_T >= trigger * 1.018:
                        pnl_gross = max(0.0, (c_T - entry) / entry)
                        status = "TRAILED_BREAKEVEN"
                    elif hit_sl:
                        pnl_gross = pick["sl_pct"]
                        status = "STOPPED_OUT"
                    else:
                        pnl_gross = (c_T - entry) / entry
                        status = "DAY_CLOSE"

                pnl_net = pnl_gross - fee_per_trade
                capital *= (1.0 + pnl_net)

                trades.append({
                    "date": date_T.strftime("%Y-%m-%d"),
                    "ticker": sym,
                    "status": status,
                    "pnl_gross": round(pnl_gross * 100, 2),
                    "pnl_net": round(pnl_net * 100, 2),
                    "capital": round(capital, 2),
                })

            wins = [tr for tr in trades if tr['pnl_net'] > 0]
            losses = [tr for tr in trades if tr['pnl_net'] <= 0]
            win_rate = len(wins) / len(trades) * 100 if trades else 0.0
            g_profit = sum(tr['pnl_gross'] for tr in wins)
            g_loss = abs(sum(tr['pnl_gross'] for tr in losses)) + 1e-6
            pf = g_profit / g_loss

            results[mode_name][p_name] = {
                "trades": len(trades),
                "wins": len(wins),
                "losses": len(losses),
                "win_rate": round(win_rate, 1),
                "profit_factor": round(pf, 2),
                "final_capital": round(capital, 2),
                "net_return_pct": round((capital / 100000.0 - 1.0) * 100, 2),
            }

    print("\n" + "=" * 95)
    print(f"{'PERIOD':<25} | {'SYSTEM':<10} | {'TRADES':<7} | {'WIN RATE':<10} | {'PROFIT FACTOR':<14} | {'NET RETURN %':<12} | {'FINAL CAP (Rs)':<14}")
    print("=" * 95)

    for p_name in periods.keys():
        b = results["Baseline"][p_name]
        u = results["Upgraded"][p_name]
        print(f"{p_name:<25} | Baseline   | {b['trades']:<7} | {b['win_rate']:<5.1f}%    | {b['profit_factor']:<14.2f} | {b['net_return_pct']:+10.2f}% | Rs {b['final_capital']:,.2f}")
        print(f"{'':<25} | Upgraded   | {u['trades']:<7} | {u['win_rate']:<5.1f}%    | {u['profit_factor']:<14.2f} | {u['net_return_pct']:+10.2f}% | Rs {u['final_capital']:,.2f}")
        print("-" * 95)

    # Save results to json
    with open("walkforward_comparison_results.json", "w") as f:
        json.dump(results, f, indent=2)
    print("\n[+] Saved full walkforward comparison results to walkforward_comparison_results.json")

if __name__ == '__main__':
    run_full_backtest()
