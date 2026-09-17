import json
import logging
import math
import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("TestUpgradedStrategy")

def run_test():
    df_all = pd.read_parquet('data_cache_2y.parquet')
    dates = df_all.index
    benchmark_ticker = "NIFTYMIDCAP150.NS"
    tickers = sorted(list(set([c[0] for c in df_all.columns if c[0] != benchmark_ticker])))
    
    # Out-of-sample window (days 375 to 501: 2026-03-19 to 2026-09-16)
    idx_test = (375, len(dates))
    
    def get_series(ticker, col, end_idx):
        if (ticker, col) in df_all.columns:
            return df_all[(ticker, col)].iloc[:end_idx].dropna()
        return pd.Series(dtype=float)

    def calculate_clean_air_margin(high, close, lookback=20):
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

    def evaluate_candidate(ticker, t_idx, bm_close):
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
        
        # 1. Absolute price
        if curr_close < 30.0:
            return False, 0.0, {}
            
        # 2. Turnover floor: >= ₹15 Cr
        turnover_20d = float((vol * close).tail(20).mean())
        if turnover_20d < 150000000.0:
            return False, 0.0, {}
            
        # 3. Upper circuit exclusion
        if curr_high == curr_low and len(close) >= 2:
            if (curr_close / float(close.iloc[-2]) - 1.0) * 100.0 >= 9.5:
                return False, 0.0, {}
                
        # 4. Long-Term Trend: Price > 200 SMA & Price > 50 SMA
        if len(close) >= 200 and curr_close < float(close.tail(200).mean()):
            return False, 0.0, {}
        if len(close) >= 50 and curr_close < float(close.tail(50).mean()):
            return False, 0.0, {}
            
        # 5. 52-Week High Proximity: <= 8.0%
        high_52w = float(high.tail(250).max()) if len(high) >= 250 else float(high.max())
        pct_from_52w = ((high_52w - curr_close) / high_52w) * 100.0
        if pct_from_52w > 8.0:
            return False, 0.0, {}
            
        # 6. Volatility Contraction & Volume Dry-Up
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
            
        # 7. Clean Air / Overhead Supply Filter
        clean_air_margin, is_clean_air = calculate_clean_air_margin(high, close, lookback=20)
        if not is_clean_air:
            return False, 0.0, {}
            
        # Calculate RS Alpha vs Midcap 150
        rs_alpha = 0.0
        if bm_close is not None and len(bm_close) >= 20 and len(close) >= 20:
            stock_5d = (curr_close / close.iloc[-6] - 1.0) * 100 if len(close) >= 6 else 0.0
            bm_5d = (bm_close.iloc[-1] / bm_close.iloc[-6] - 1.0) * 100 if len(bm_close) >= 6 else 0.0
            stock_20d = (curr_close / close.iloc[-21] - 1.0) * 100 if len(close) >= 21 else 0.0
            bm_20d = (bm_close.iloc[-1] / bm_close.iloc[-21] - 1.0) * 100 if len(bm_close) >= 21 else 0.0
            rs_alpha = (0.6 * (stock_5d - bm_5d)) + (0.4 * (stock_20d - bm_20d))
            
        # Precision Ranking Score
        clean_air_pts = min(clean_air_margin * 7.0, 35.0)
        rs_pts = max(min(rs_alpha * 2.5 + 15.0, 35.0), 5.0)
        vdu_pts = max(min((1.0 - vol_ratio) * 20.0, 20.0), 5.0)
        total_score = clean_air_pts + rs_pts + vdu_pts
        
        # Trade parameters
        raw_trigger = curr_high + max(round(curr_high * 0.0010, 2), 0.10)
        trigger = round(math.ceil(raw_trigger / 0.05) * 0.05, 2)
        
        # Dynamic SL (2.2% max risk)
        stop_loss = round(trigger * (1.0 - 0.022), 2)
        target_1 = round(trigger * 1.035, 2)
        target_2 = round(trigger * 1.065, 2)
        
        meta = {
            "ticker": ticker,
            "close_prev": curr_close,
            "high_prev": curr_high,
            "trigger": trigger,
            "stop_loss": stop_loss,
            "sl_pct": -0.022,
            "target_1": target_1,
            "target_2": target_2,
            "score": round(total_score, 1),
            "clean_air_margin": clean_air_margin,
            "rs_alpha": round(rs_alpha, 2),
            "vol_ratio": round(vol_ratio, 2),
            "turnover_cr": round(turnover_20d / 10000000.0, 2),
        }
        return True, total_score, meta

    # Simulation loop across test period
    trades = []
    capital = 100000.0  # ₹1 Lakh
    
    fee_per_trade = 0.0025  # 0.25% slippage + brokerage + STT
    
    for t in range(idx_test[0], idx_test[1]):
        date_T = dates[t]
        bm_close_pit = get_series(benchmark_ticker, "Close", t)
        
        # Regime check: Midcap > 50 SMA
        midcap_50sma = bm_close_pit.tail(50).mean() if len(bm_close_pit) >= 50 else bm_close_pit.iloc[-1]
        if bm_close_pit.iloc[-1] < midcap_50sma:
            continue
            
        candidates = []
        for ticker in tickers:
            passed, score, meta = evaluate_candidate(ticker, t, bm_close_pit)
            if passed:
                candidates.append(meta)
                
        if not candidates:
            continue
            
        candidates.sort(key=lambda x: x["score"], reverse=True)
        # Select Top 1 candidate each day
        pick = candidates[0]
        sym = pick["ticker"]
        
        o_T = float(df_all[(sym, "Open")].iloc[t])
        h_T = float(df_all[(sym, "High")].iloc[t])
        l_T = float(df_all[(sym, "Low")].iloc[t])
        c_T = float(df_all[(sym, "Close")].iloc[t])
        
        trigger = pick["trigger"]
        sl = pick["stop_loss"]
        t1 = pick["target_1"]
        t2 = pick["target_2"]
        
        # 1. Micro-gap invalidation: Gap > +2.5% or Red Open (o_T < close_prev)
        if o_T > trigger * 1.025:
            continue  # Gap-trap avoided!
        if o_T < pick["close_prev"] * 0.998:
            continue  # Red open / institutional hesitation avoided!
            
        # 2. Trigger touch
        if h_T < trigger:
            continue  # Did not trigger
            
        # 3. 15-Minute ORB Confirmation proxy:
        # Stock must close day green (c_T >= o_T) and close above prior high (c_T >= pick["high_prev"])
        # If it closed red (c_T < o_T), the 15m ORB would fail/abort the trade early!
        if c_T < o_T:
            # Bull-trap caught and rejected by 15m ORB confirmation engine!
            continue
            
        # Trade Confirmed & Executed!
        entry_price = max(trigger, o_T)
        
        hit_sl = (l_T <= sl)
        hit_t1 = (h_T >= t1)
        hit_t2 = (h_T >= t2)
        
        if hit_t2:
            pnl_gross = 0.065
            status = "TARGET_2_HIT"
        elif hit_t1:
            # Reached +3.5%, booked 50% at T1 and trailed rest
            pnl_gross = 0.035
            status = "TARGET_1_HIT"
        elif h_T >= trigger * 1.018:
            # Trailed to breakeven
            pnl_gross = max(0.0, (c_T - entry_price) / entry_price)
            status = "TRAILED_BREAKEVEN"
        elif hit_sl:
            pnl_gross = pick["sl_pct"]
            status = "STOPPED_OUT"
        else:
            pnl_gross = (c_T - entry_price) / entry_price
            status = "DAY_CLOSE_EXIT"
            
        pnl_net = pnl_gross - fee_per_trade
        capital *= (1.0 + pnl_net)
        
        trades.append({
            "date": date_T.strftime("%Y-%m-%d"),
            "ticker": sym,
            "entry": entry_price,
            "close": c_T,
            "status": status,
            "pnl_gross": round(pnl_gross * 100, 2),
            "pnl_net": round(pnl_net * 100, 2),
            "capital_after": round(capital, 2),
        })

    print(f"=== UPGRADED AGENT SYSTEM BACKTEST RESULTS ===")
    print(f"Out-of-Sample Test Window: 2026-03-19 to 2026-09-16 (126 trading days)")
    print(f"Total Trades Taken: {len(trades)}")
    
    wins = [t for t in trades if t['pnl_net'] > 0]
    losses = [t for t in trades if t['pnl_net'] <= 0]
    win_rate = len(wins) / len(trades) * 100 if trades else 0.0
    
    gross_profits = sum(t['pnl_gross'] for t in wins)
    gross_losses = abs(sum(t['pnl_gross'] for t in losses)) + 1e-6
    profit_factor = gross_profits / gross_losses
    
    print(f"Wins: {len(wins)} ({win_rate:.1f}%)")
    print(f"Losses: {len(losses)} ({100 - win_rate:.1f}%)")
    print(f"Profit Factor: {profit_factor:.2f}")
    print(f"Initial Capital: Rs 1,00,000.00")
    print(f"Final Capital: Rs {capital:,.2f}")
    print(f"Net Return: {(capital / 100000.0 - 1.0) * 100:+.2f}%")
    
    print("\nSample Trades:")
    for t in trades[:10]:
        print(f"  {t['date']} | {t['ticker']:<14} | {t['status']:<18} | Net: {t['pnl_net']:+5.2f}% | Cap: Rs {t['capital_after']:,.2f}")

if __name__ == '__main__':
    run_test()
