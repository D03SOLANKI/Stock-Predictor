import sys, math, json, pandas as pd, numpy as np
sys.stdout.reconfigure(encoding='utf-8')

df_all = pd.read_parquet('data_cache_2y.parquet')
dates = df_all.index
benchmark_ticker = 'NIFTYMIDCAP150.NS'

from tradingagents.swing_opportunity.mid_small_universe import NSE_MID_SMALL_UNIVERSE

midcaps = [t for t, m in NSE_MID_SMALL_UNIVERSE.items() if m.get('tier') == 'Midcap']
smallcaps = [t for t, m in NSE_MID_SMALL_UNIVERSE.items() if m.get('tier') == 'Smallcap']
all_tickers = sorted(midcaps + smallcaps)

# Past 200 trading days
start_idx = len(dates) - 200
end_idx = len(dates)

start_date = dates[start_idx].strftime('%Y-%m-%d')
end_date = dates[end_idx - 1].strftime('%Y-%m-%d')

print('================================================================================')
print('200-DAY POINT-IN-TIME BACKTEST & CAPITAL GROWTH SIMULATION')
print('Window: ' + start_date + ' to ' + end_date + ' (' + str(end_idx - start_idx) + ' Trading Days)')
print('================================================================================\n')

def get_series(ticker, col, idx):
    if (ticker, col) in df_all.columns:
        return df_all[(ticker, col)].iloc[:idx].dropna()
    return pd.Series(dtype=float)

def calculate_clean_air_margin(high, close, lookback=20):
    if len(high) < lookback + 1: return 5.0, True
    curr_high = float(high.iloc[-1])
    prior_highs = high.iloc[-(lookback + 1):-1]
    max_prior = float(prior_highs.max())
    if curr_high >= max_prior: return 10.0, True
    higher_wicks = prior_highs[prior_highs > curr_high]
    if len(higher_wicks) == 0: return 10.0, True
    nearest_res = float(higher_wicks.min())
    margin = ((nearest_res - curr_high) / curr_high) * 100.0
    return round(margin, 2), margin >= 2.0

def evaluate_candidate(ticker, t_idx, bm_close):
    close = get_series(ticker, 'Close', t_idx)
    high = get_series(ticker, 'High', t_idx)
    low = get_series(ticker, 'Low', t_idx)
    vol = get_series(ticker, 'Volume', t_idx)
    if len(close) < 25 or len(high) < 25 or len(vol) < 25: return False, 0.0, {}
    curr_close = float(close.iloc[-1])
    curr_high = float(high.iloc[-1])
    curr_low = float(low.iloc[-1])
    curr_vol = float(vol.iloc[-1])
    if curr_close < 30.0: return False, 0.0, {}
    turnover_20d = float((vol * close).tail(20).mean())
    if turnover_20d < 150000000.0: return False, 0.0, {}
    if curr_high == curr_low and len(close) >= 2:
        if (curr_close / float(close.iloc[-2]) - 1.0) * 100.0 >= 9.5: return False, 0.0, {}
    if len(close) >= 200 and curr_close < float(close.tail(200).mean()): return False, 0.0, {}
    if len(close) >= 50 and curr_close < float(close.tail(50).mean()): return False, 0.0, {}
    high_52w = float(high.tail(250).max()) if len(high) >= 250 else float(high.max())
    pct_from_52w = ((high_52w - curr_close) / high_52w) * 100.0
    if pct_from_52w > 8.0: return False, 0.0, {}
    avg_vol_20 = float(vol.tail(20).mean()) + 1e-6
    vol_ratio = curr_vol / avg_vol_20
    ranges = high - low
    is_nr7 = len(ranges) >= 7 and float(ranges.iloc[-1]) < float(ranges.iloc[-7:-1].min())
    is_inside = len(high) >= 2 and curr_high < float(high.iloc[-2]) and curr_low > float(low.iloc[-2])
    if vol_ratio > 0.80 and not is_nr7 and not is_inside: return False, 0.0, {}
    clean_air_margin, is_clean_air = calculate_clean_air_margin(high, close, lookback=20)
    if not is_clean_air: return False, 0.0, {}
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
    stop_loss = round(trigger * (1.0 - 0.022), 2)
    target_1 = round(trigger * 1.035, 2)
    target_2 = round(trigger * 1.065, 2)
    tier = 'Midcap' if ticker in midcaps else 'Smallcap'
    meta = {
        'ticker': ticker, 'tier': tier, 'name': NSE_MID_SMALL_UNIVERSE.get(ticker, {}).get('name', ticker),
        'close_prev': curr_close, 'high_prev': curr_high,
        'trigger': trigger, 'stop_loss': stop_loss, 'sl_pct': -0.022,
        'target_1': target_1, 'target_2': target_2, 'score': round(total_score, 1),
    }
    return True, total_score, meta

def run_simulation(initial_capital):
    capital = float(initial_capital)
    fee = 0.0025
    trades = []
    
    for t in range(start_idx, end_idx):
        date_T = dates[t]
        bm_close_pit = get_series(benchmark_ticker, 'Close', t)
        sma50 = bm_close_pit.tail(50).mean() if len(bm_close_pit) >= 50 else bm_close_pit.iloc[-1]
        if bm_close_pit.iloc[-1] < sma50:
            continue
            
        cands = []
        for sym in all_tickers:
            passed, score, meta = evaluate_candidate(sym, t, bm_close_pit)
            if passed: cands.append(meta)
            
        if not cands: continue
        cands.sort(key=lambda x: x['score'], reverse=True)
        pick = cands[0]
        sym = pick['ticker']
        
        o_T = float(df_all[(sym, 'Open')].iloc[t])
        h_T = float(df_all[(sym, 'High')].iloc[t])
        l_T = float(df_all[(sym, 'Low')].iloc[t])
        c_T = float(df_all[(sym, 'Close')].iloc[t])
        trigger = pick['trigger']
        
        if o_T > trigger * 1.025: continue
        if o_T < pick['close_prev'] * 0.998: continue
        if h_T < trigger: continue
        
        # MODEL 2: Candle Confirmation Proxy (c_T >= o_T)
        if c_T < o_T: continue
        
        entry = max(trigger, o_T)
        hit_sl = (l_T <= pick['stop_loss'])
        hit_t1 = (h_T >= pick['target_1'])
        hit_t2 = (h_T >= pick['target_2'])
        
        if hit_sl and hit_t1:
            pnl_gross = pick['sl_pct']; status = 'STOPPED_OUT'
        elif hit_t2:
            pnl_gross = 0.065; status = 'TARGET_2_HIT (+6.5%)'
        elif hit_t1:
            pnl_gross = 0.035; status = 'TARGET_1_HIT (+3.5%)'
        elif h_T >= trigger * 1.018:
            pnl_gross = max(0.0, (c_T - entry) / entry); status = 'TRAILED_BREAKEVEN'
        elif hit_sl:
            pnl_gross = pick['sl_pct']; status = 'STOPPED_OUT (-2.2%)'
        else:
            pnl_gross = (c_T - entry) / entry; status = 'DAY_CLOSE_EXIT'
            
        pnl_net = pnl_gross - fee
        capital *= (1.0 + pnl_net)
        trades.append({
            'date': date_T.strftime('%Y-%m-%d'),
            'ticker': sym,
            'tier': pick['tier'],
            'status': status,
            'pnl_net_pct': round(pnl_net * 100, 2),
            'capital_after': round(capital, 2)
        })
        
    return capital, trades

# 1. Standard ₹1 Lakh (₹1,00,000)
cap_1lakh, trades_1lakh = run_simulation(100000.0)

# 2. ₹1,00,000 Lakhs = 100,000 * 1,00,000 = ₹1,000 Crore (₹10,00,00,00,000)
cap_1000cr, _ = run_simulation(10000000000.0)

n = len(trades_1lakh)
wins = [tr for tr in trades_1lakh if tr['pnl_net_pct'] > 0]
losses = [tr for tr in trades_1lakh if tr['pnl_net_pct'] <= 0]
wr = len(wins) / max(n, 1) * 100
gp = sum(tr['pnl_net_pct'] for tr in wins)
gl = abs(sum(tr['pnl_net_pct'] for tr in losses)) + 1e-6
pf = gp / gl
total_return_pct = (cap_1lakh / 100000.0 - 1.0) * 100.0

print('--- PERFORMANCE METRICS OVER PAST 200 TRADING DAYS ---')
print('Total Trading Days Evaluated: 200')
print('Total Trades Taken:           ' + str(n))
print('Wins / Losses:                ' + str(len(wins)) + ' Wins / ' + str(len(losses)) + ' Losses')
print('Win Rate:                     ' + str(round(wr, 1)) + '%')
print('Profit Factor:                ' + str(round(pf, 2)))
print('Total Net Return:             +' + str(round(total_return_pct, 2)) + '%\n')

print('--- CAPITAL GROWTH RESULTS ---')
print('1. If you invested ₹1,00,000 (1 Lakh):')
print('   -> Initial Capital: ₹1,00,000')
print('   -> Final Capital:   ₹' + str(round(cap_1lakh, 2)) + ' (+' + str(round(cap_1lakh - 100000, 2)) + ' Net Profit)')

print('\n2. If you invested "100,000 Lakhs" (₹1,000 Crore):')
print('   -> Initial Capital: ₹10,00,00,00,000 (1,000 Cr)')
print('   -> Final Capital:   ₹' + str(round(cap_1000cr, 2)) + ' (+' + str(round(cap_1000cr - 10000000000, 2)) + ' Net Profit)')

print('\n--- COMPLETE 200-DAY TRADE AUDIT LOG ---')
for i, tr in enumerate(trades_1lakh):
    m = 'WIN ' if tr['pnl_net_pct'] > 0 else 'LOSS'
    print('  ' + str(i+1).rjust(2) + '. ' + m + ' | ' + tr['date'] + ' | ' + tr['ticker'].ljust(14) + ' | ' + tr['tier'].ljust(8) + ' | ' + tr['status'].ljust(22) + ' | Net: ' + str(tr['pnl_net_pct']) + '% | Cap: ₹' + str(tr['capital_after']))
