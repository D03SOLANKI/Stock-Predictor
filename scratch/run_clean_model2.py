import sys, math, json, pandas as pd, numpy as np
sys.stdout.reconfigure(encoding='utf-8')

df_all = pd.read_parquet('data_cache_2y.parquet')
dates = df_all.index
benchmark_ticker = 'NIFTYMIDCAP150.NS'

from tradingagents.swing_opportunity.mid_small_universe import NSE_MID_SMALL_UNIVERSE

midcaps = [t for t, m in NSE_MID_SMALL_UNIVERSE.items() if m.get('tier') == 'Midcap']
smallcaps = [t for t, m in NSE_MID_SMALL_UNIVERSE.items() if m.get('tier') == 'Smallcap']
all_tickers = sorted(midcaps + smallcaps)

def get_series(ticker, col, end_idx):
    if (ticker, col) in df_all.columns:
        return df_all[(ticker, col)].iloc[:end_idx].dropna()
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
    tier = 'midcap' if ticker in midcaps else 'smallcap'
    meta = {
        'ticker': ticker, 'tier': tier, 'name': NSE_MID_SMALL_UNIVERSE.get(ticker, {}).get('name', ticker),
        'sector': NSE_MID_SMALL_UNIVERSE.get(ticker, {}).get('sector', 'Unknown'),
        'close_prev': curr_close, 'high_prev': curr_high,
        'trigger': trigger, 'stop_loss': stop_loss, 'sl_pct': -0.022,
        'target_1': target_1, 'target_2': target_2, 'score': round(total_score, 1),
        'clean_air_margin': clean_air_margin, 'rs_alpha': round(rs_alpha, 2), 'vol_ratio': round(vol_ratio, 2)
    }
    return True, total_score, meta

def run_model2_backtest(target_tier=None):
    capital = 100000.0
    fee = 0.0025
    trades = []
    
    for t in range(375, len(dates)):
        date_T = dates[t]
        bm_close_pit = get_series(benchmark_ticker, 'Close', t)
        sma50 = bm_close_pit.tail(50).mean() if len(bm_close_pit) >= 50 else bm_close_pit.iloc[-1]
        if bm_close_pit.iloc[-1] < sma50: continue
        
        cands = []
        ticker_pool = midcaps if target_tier == 'midcap' else (smallcaps if target_tier == 'smallcap' else all_tickers)
        for sym in ticker_pool:
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
        
        # MODEL 2: POST-OPEN CANDLE PROXY (c_T >= o_T)
        if c_T < o_T: continue
        
        entry = max(trigger, o_T)
        hit_sl = (l_T <= pick['stop_loss'])
        hit_t1 = (h_T >= pick['target_1'])
        hit_t2 = (h_T >= pick['target_2'])
        
        if hit_sl and hit_t1:
            pnl_gross = pick['sl_pct']; status = 'STOPPED_OUT'
        elif hit_t2:
            pnl_gross = 0.065; status = 'TARGET_2_HIT'
        elif hit_t1:
            pnl_gross = 0.035; status = 'TARGET_1_HIT'
        elif h_T >= trigger * 1.018:
            pnl_gross = max(0.0, (c_T - entry) / entry); status = 'TRAILED_BREAKEVEN'
        elif hit_sl:
            pnl_gross = pick['sl_pct']; status = 'STOPPED_OUT'
        else:
            pnl_gross = (c_T - entry) / entry; status = 'DAY_CLOSE_EXIT'
            
        pnl_net = pnl_gross - fee
        capital *= (1.0 + pnl_net)
        trades.append({
            'date': date_T.strftime('%Y-%m-%d'),
            'ticker': sym, 'tier': pick['tier'], 'status': status,
            'pnl_net_pct': round(pnl_net * 100, 2),
            'capital': round(capital, 2)
        })
        
    n = len(trades)
    wins = [tr for tr in trades if tr['pnl_net_pct'] > 0]
    losses = [tr for tr in trades if tr['pnl_net_pct'] <= 0]
    wr = len(wins) / max(n, 1) * 100
    gp = sum(tr['pnl_net_pct'] for tr in wins)
    gl = abs(sum(tr['pnl_net_pct'] for tr in losses)) + 1e-6
    pf = gp / gl
    ret = (capital / 100000.0 - 1) * 100
    return {'n': n, 'wins': len(wins), 'losses': len(losses), 'wr': round(wr, 1), 'pf': round(pf, 2), 'ret': round(ret, 2), 'trades': trades}

res_all = run_model2_backtest(target_tier=None)
res_mid = run_model2_backtest(target_tier='midcap')
res_small = run_model2_backtest(target_tier='smallcap')

print('================================================================================')
print('MODEL 2 (c_T >= o_T PROXY) BACKTEST RESULTS: OOS WINDOW (126 TRADING DAYS)')
print('================================================================================')
print('Overall Universe: ' + str(res_all['n']) + ' Trades | ' + str(res_all['wins']) + ' Wins - ' + str(res_all['losses']) + ' Losses | WR: ' + str(res_all['wr']) + '% | PF: ' + str(res_all['pf']) + ' | Net Ret: ' + str(res_all['ret']) + '%')
print('Mid Cap Only:     ' + str(res_mid['n']) + ' Trades | ' + str(res_mid['wins']) + ' Wins - ' + str(res_mid['losses']) + ' Losses | WR: ' + str(res_mid['wr']) + '% | PF: ' + str(res_mid['pf']) + ' | Net Ret: ' + str(res_mid['ret']) + '%')
print('Small Cap Only:   ' + str(res_small['n']) + ' Trades | ' + str(res_small['wins']) + ' Wins - ' + str(res_small['losses']) + ' Losses | WR: ' + str(res_small['wr']) + '% | PF: ' + str(res_small['pf']) + ' | Net Ret: ' + str(res_small['ret']) + '%')
print('================================================================================\n')

# Pre-market predictions across Mid Cap and Small Cap
t_latest = len(dates)
bm_latest = get_series(benchmark_ticker, 'Close', t_latest)

mid_cands = []
for sym in midcaps:
    p, sc, m = evaluate_candidate(sym, t_latest, bm_latest)
    if p: mid_cands.append(m)

small_cands = []
for sym in smallcaps:
    p, sc, m = evaluate_candidate(sym, t_latest, bm_latest)
    if p: small_cands.append(m)

# Also show near-misses if hard gates filtered everything
print('--- PRE-MARKET SCREENING OUTPUT ---')
print('Mid Cap Passing Hard Gates: ' + str(len(mid_cands)))
print('Small Cap Passing Hard Gates: ' + str(len(small_cands)))

# Extract near misses for actionable trading watchlist
near_misses = []
for sym in all_tickers:
    c = get_series(sym, 'Close', t_latest)
    h = get_series(sym, 'High', t_latest)
    l = get_series(sym, 'Low', t_latest)
    v = get_series(sym, 'Volume', t_latest)
    if len(c) < 25: continue
    curr_c = float(c.iloc[-1])
    curr_h = float(h.iloc[-1])
    turnover = float((v * c).tail(20).mean()) / 10000000.0
    h_52w = float(h.tail(250).max())
    p_52w = (h_52w - curr_c) / h_52w * 100
    sma50 = float(c.tail(50).mean())
    sma200 = float(c.tail(200).mean())
    if curr_c > sma50 and curr_c > sma200 and p_52w <= 8.0:
        vol_r = float(v.iloc[-1]) / float(v.tail(20).mean() + 1e-6)
        ca_m, _ = calculate_clean_air_margin(h, c)
        raw_trig = curr_h + max(round(curr_h * 0.0010, 2), 0.10)
        trig = round(math.ceil(raw_trig / 0.05) * 0.05, 2)
        tier = 'Midcap' if sym in midcaps else 'Smallcap'
        near_misses.append({
            'ticker': sym, 'tier': tier, 'name': NSE_MID_SMALL_UNIVERSE.get(sym, {}).get('name', sym),
            'close': round(curr_c, 2), 'trigger': trig,
            'stop_loss': round(trig * (1 - 0.022), 2),
            'target_1': round(trig * 1.035, 2),
            'target_2': round(trig * 1.065, 2),
            'dist_52w': round(p_52w, 1),
            'clean_air': ca_m,
            'vol_ratio': round(vol_r, 2)
        })

near_misses.sort(key=lambda x: x['dist_52w'])
print('\nTop Technical Setups Ready for Model 2 Execution:')
for nm in near_misses:
    print('  * [' + nm['tier'] + '] ' + nm['ticker'] + ' (' + nm['name'] + '): Close Rs ' + str(nm['close']) + ' | Trigger Rs ' + str(nm['trigger']) + ' | SL Rs ' + str(nm['stop_loss']) + ' (-2.2%) | T1 Rs ' + str(nm['target_1']) + ' (+3.5%) | T2 Rs ' + str(nm['target_2']) + ' (+6.5%) | 52w Dist: ' + str(nm['dist_52w']) + '% | Clean Air: ' + str(nm['clean_air']) + '%')
