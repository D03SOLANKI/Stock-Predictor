import json
import logging
import math
import numpy as np
import pandas as pd

def test_sl():
    df_all = pd.read_parquet('data_cache_2y.parquet')
    dates = df_all.index
    benchmark_ticker = "NIFTYMIDCAP150.NS"
    tickers = sorted(list(set([c[0] for c in df_all.columns if c[0] != benchmark_ticker])))
    
    idx_test = (375, len(dates))
    fee_per_trade = 0.0025  # 0.25% friction (slippage + brokerage + STT)
    
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
        if turnover_20d < 150000000.0:
            return False, 0.0, {}
        if curr_high == curr_low and len(close) >= 2:
            if (curr_close / float(close.iloc[-2]) - 1.0) * 100.0 >= 9.5:
                return False, 0.0, {}
        if len(close) >= 200 and curr_close < float(close.tail(200).mean()):
            return False, 0.0, {}
        if len(close) >= 50 and curr_close < float(close.tail(50).mean()):
            return False, 0.0, {}
            
        high_52w = float(high.tail(250).max()) if len(high) >= 250 else float(high.max())
        pct_from_52w = ((high_52w - curr_close) / high_52w) * 100.0
        if pct_from_52w > 8.0:
            return False, 0.0, {}
            
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
            
        clean_air_margin, is_clean_air = calculate_clean_air_margin(high, close, lookback=20)
        if not is_clean_air:
            return False, 0.0, {}
            
        rs_alpha = 0.0
        if bm_close is not None and len(bm_close) >= 20 and len(close) >= 20:
            stock_5d = (curr_close / close.iloc[-6] - 1.0) * 100 if len(close) >= 6 else 0.0
            bm_5d = (bm_close.iloc[-1] / bm_close.iloc[-6] - 1.0) * 100 if len(bm_close) >= 6 else 0.0
            stock_20d = (curr_close / close.iloc[-21] - 1.0) * 100 if len(close) >= 21 else 0.0
            bm_20d = (bm_close.iloc[-1] / bm_close.iloc[-21] - 1.0) * 100 if len(bm_close) >= 21 else 0.0
            rs_alpha = (0.6 * (stock_5d - bm_5d)) + (0.4 * (stock_20d - bm_20d))
            
        clean_air_pts = min(clean_air_margin * 7.0, 35.0)
        rs_pts = max(min(rs_alpha * 2.5 + 15.0, 35.0), 5.0)
        vdu_pts = max(min((1.0 - vol_ratio) * 20.0, 20.0), 5.0)
        total_score = clean_air_pts + rs_pts + vdu_pts
        
        raw_trigger = curr_high + max(round(curr_high * 0.0010, 2), 0.10)
        trigger = round(math.ceil(raw_trigger / 0.05) * 0.05, 2)
        
        meta = {
            "ticker": ticker,
            "close_prev": curr_close,
            "trigger": trigger,
            "score": round(total_score, 1),
        }
        return True, total_score, meta

    # We test 3 Stop Loss configurations on Out-of-Sample:
    # Config 1: Dynamic SL at -2.2% (Baseline Upgraded)
    # Config 2: Hard Price SL at -0.5% (Price drops 0.5% below entry -> exit immediately)
    # Config 3: Dynamic SL with Position Sizing capped at 0.5% Account Risk
    
    configs = {
        "Config 1 (Dynamic Price SL -2.2%)": {"price_sl_pct": 0.022, "mode": "price"},
        "Config 2 (Hard Price SL -0.5%)": {"price_sl_pct": 0.005, "mode": "price"},
        "Config 3 (Position Sized to 0.5% Account Risk)": {"price_sl_pct": 0.022, "mode": "portfolio_risk", "max_risk_pct": 0.005},
    }
    
    results = {}
    
    for cfg_name, cfg in configs.items():
        capital = 100000.0
        trades = []
        
        for t in range(idx_test[0], idx_test[1]):
            date_T = dates[t]
            bm_close_pit = get_series(benchmark_ticker, "Close", t)
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
            pick = candidates[0]
            sym = pick["ticker"]
            
            o_T = float(df_all[(sym, "Open")].iloc[t])
            h_T = float(df_all[(sym, "High")].iloc[t])
            l_T = float(df_all[(sym, "Low")].iloc[t])
            c_T = float(df_all[(sym, "Close")].iloc[t])
            trigger = pick["trigger"]
            
            if o_T > trigger * 1.025 or o_T < pick["close_prev"] * 0.998:
                continue
            if h_T < trigger:
                continue
            if c_T < o_T:
                continue
                
            entry = max(trigger, o_T)
            price_sl_pct = cfg["price_sl_pct"]
            sl_price = round(entry * (1.0 - price_sl_pct), 2)
            t1 = round(entry * 1.035, 2)
            t2 = round(entry * 1.065, 2)
            
            hit_sl = (l_T <= sl_price)
            hit_t1 = (h_T >= t1)
            hit_t2 = (h_T >= t2)
            
            # Outcome determination
            # If hit SL:
            if hit_sl and not hit_t1:
                pnl_gross = -price_sl_pct
                status = "STOPPED_OUT"
            elif hit_sl and hit_t1:
                # If target hit and SL hit on same day, conservative is hit SL
                pnl_gross = -price_sl_pct
                status = "STOPPED_OUT_DUAL"
            elif hit_t2:
                pnl_gross = 0.065
                status = "TARGET_2_HIT"
            elif hit_t1:
                pnl_gross = 0.035
                status = "TARGET_1_HIT"
            elif h_T >= entry * 1.018:
                pnl_gross = max(0.0, (c_T - entry) / entry)
                status = "TRAILED_BREAKEVEN"
            else:
                pnl_gross = (c_T - entry) / entry
                status = "DAY_CLOSE"
                
            if cfg["mode"] == "portfolio_risk":
                # Position sizing: risk per trade is strictly 0.5% of account
                # Risk = (Entry - SL) / Entry = 2.2%
                # Position size = (Account * 0.5%) / 2.2% = Account * (0.005 / 0.022) = 22.7% of Account
                position_weight = min(0.005 / price_sl_pct, 1.0)
                trade_net_pct = (pnl_gross - fee_per_trade) * position_weight
            else:
                trade_net_pct = pnl_gross - fee_per_trade
                
            capital *= (1.0 + trade_net_pct)
            trades.append({
                "date": date_T.strftime("%Y-%m-%d"),
                "ticker": sym,
                "status": status,
                "pnl_gross": round(pnl_gross * 100, 2),
                "trade_net_pct": round(trade_net_pct * 100, 2),
                "capital": round(capital, 2),
            })
            
        wins = [t for t in trades if t["trade_net_pct"] > 0]
        losses = [t for t in trades if t["trade_net_pct"] <= 0]
        win_rate = len(wins) / len(trades) * 100 if trades else 0.0
        g_profit = sum(t["pnl_gross"] for t in wins)
        g_loss = abs(sum(t["pnl_gross"] for t in losses)) + 1e-6
        pf = g_profit / g_loss
        
        results[cfg_name] = {
            "trades": len(trades),
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": round(win_rate, 1),
            "profit_factor": round(pf, 2),
            "final_capital": round(capital, 2),
            "net_return_pct": round((capital / 100000.0 - 1.0) * 100, 2),
        }
        
    print("\n" + "=" * 105)
    print(f"{'CONFIGURATION':<45} | {'TRADES':<7} | {'WIN RATE':<10} | {'PROFIT FACTOR':<14} | {'NET RETURN %':<12} | {'FINAL CAP (Rs)':<14}")
    print("=" * 105)
    for name, r in results.items():
        print(f"{name:<45} | {r['trades']:<7} | {r['win_rate']:<5.1f}%    | {r['profit_factor']:<14.2f} | {r['net_return_pct']:+10.2f}% | Rs {r['final_capital']:,.2f}")
    print("-" * 105)

if __name__ == '__main__':
    test_sl()
