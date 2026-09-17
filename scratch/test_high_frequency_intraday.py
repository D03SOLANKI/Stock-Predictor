import sys, math, json, pandas as pd, numpy as np
sys.stdout.reconfigure(encoding='utf-8')

df_all = pd.read_parquet('data_cache_2y.parquet')
dates = df_all.index
benchmark_ticker = 'NIFTYMIDCAP150.NS'

from tradingagents.swing_opportunity.mid_small_universe import NSE_MID_SMALL_UNIVERSE

midcaps = [t for t, m in NSE_MID_SMALL_UNIVERSE.items() if m.get('tier') == 'Midcap']
smallcaps = [t for t, m in NSE_MID_SMALL_UNIVERSE.items() if m.get('tier') == 'Smallcap']
all_tickers = sorted(midcaps + smallcaps)

start_idx = len(dates) - 200
end_idx = len(dates)

def get_series(ticker, col, idx):
    if (ticker, col) in df_all.columns:
        return df_all[(ticker, col)].iloc[:idx].dropna()
    return pd.Series(dtype=float)

def calculate_clean_air(high, lookback=20):
    if len(high) < lookback + 1: return 5.0
    curr_high = float(high.iloc[-1])
    prior_highs = high.iloc[-(lookback + 1):-1]
    max_prior = float(prior_highs.max())
    if curr_high >= max_prior: return 10.0
    higher_wicks = prior_highs[prior_highs > curr_high]
    if len(higher_wicks) == 0: return 10.0
    nearest_res = float(higher_wicks.min())
    return round(((nearest_res - curr_high) / curr_high) * 100.0, 2)

def evaluate_intraday_candidate(sym, t):
    close = get_series(sym, 'Close', t)
    high = get_series(sym, 'High', t)
    low = get_series(sym, 'Low', t)
    vol = get_series(sym, 'Volume', t)
    if len(close) < 25 or len(high) < 25 or len(vol) < 25: return False, 0, {}
    c = float(close.iloc[-1])
    h = float(high.iloc[-1])
    l = float(low.iloc[-1])
    v = float(vol.iloc[-1])

    if c < 30.0: return False, 0, {}
    turnover = float((vol * close).tail(20).mean())
    if turnover < 100000000.0: return False, 0, {} # 10 Cr floor
    
    # Active intraday trend: Price > 20 EMA
    ema20 = float(close.ewm(span=20, adjust=False).mean().iloc[-1])
    if c < ema20: return False, 0, {}

    # Distance to 52w high relaxed to 15% (for higher trade frequency)
    h_52w = float(high.tail(250).max()) if len(high) >= 250 else float(high.max())
    dist_52w = ((h_52w - c) / h_52w) * 100.0
    if dist_52w > 15.0: return False, 0, {}

    ca_margin = calculate_clean_air(high)
    avg_vol = float(vol.tail(20).mean()) + 1e-6
    vol_ratio = v / avg_vol
    
    # Relative strength score
    raw_trigger = h + max(round(h * 0.0010, 2), 0.10)
    trigger = round(math.ceil(raw_trigger / 0.05) * 0.05, 2)
    sl = round(trigger * (1.0 - 0.020), 2) # -2.0% stop
    t1 = round(trigger * 1.030, 2) # +3.0% target
    t2 = round(trigger * 1.050, 2) # +5.0% target

    score = (15.0 - dist_52w) + (ca_margin * 2.0) + min((1.0 - vol_ratio) * 10, 10)
    tier = 'Midcap' if sym in midcaps else 'Smallcap'

    return True, score, {
        'ticker': sym, 'tier': tier, 'trigger': trigger, 'stop_loss': sl,
        't1': t1, 't2': t2, 'close_prev': c
    }

def run_intraday_backtest(trades_per_day=1, enforce_regime=False):
    capital = 100000.0
    fee = 0.0015 # Intraday STT + brokerage (much lower than delivery!)
    trades = []

    for t in range(start_idx, end_idx):
        date_T = dates[t]
        if enforce_regime:
            bm_close_pit = get_series(benchmark_ticker, 'Close', t)
            sma50 = bm_close_pit.tail(50).mean() if len(bm_close_pit) >= 50 else bm_close_pit.iloc[-1]
            if bm_close_pit.iloc[-1] < sma50: continue

        cands = []
        for sym in all_tickers:
            p, sc, meta = evaluate_intraday_candidate(sym, t)
            if p: cands.append((sc, meta))

        if not cands: continue
        cands.sort(key=lambda x: x[0], reverse=True)

        picks = [c[1] for c in cands[:trades_per_day]]
        alloc = 1.0 / len(picks)

        for pick in picks:
            sym = pick['ticker']
            o_T = float(df_all[(sym, 'Open')].iloc[t])
            h_T = float(df_all[(sym, 'High')].iloc[t])
            l_T = float(df_all[(sym, 'Low')].iloc[t])
            c_T = float(df_all[(sym, 'Close')].iloc[t])
            trigger = pick['trigger']

            # Call auction check (9:08 AM)
            if o_T > trigger * 1.025: continue
            if o_T < pick['close_prev'] * 0.998: continue
            if h_T < trigger: continue
            if c_T < o_T: continue # 15m ORB proxy

            entry = max(trigger, o_T)
            hit_sl = (l_T <= pick['stop_loss'])
            hit_t1 = (h_T >= pick['t1'])
            hit_t2 = (h_T >= pick['t2'])

            if hit_t2: pnl_gross = 0.050; status = 'T2_HIT (+5%)'
            elif hit_t1: pnl_gross = 0.030; status = 'T1_HIT (+3%)'
            elif h_T >= trigger * 1.015:
                pnl_gross = max(0.0, (c_T - entry) / entry); status = 'TRAILED_BE'
            elif hit_sl: pnl_gross = -0.020; status = 'STOPPED_OUT (-2%)'
            else: pnl_gross = (c_T - entry) / entry; status = 'SQUARE_OFF_3:15PM'

            pnl_net = pnl_gross - fee
            capital *= (1.0 + pnl_net * alloc)
            trades.append({
                'date': date_T.strftime('%Y-%m-%d'), 'ticker': sym,
                'status': status, 'pnl_net_pct': round(pnl_net * 100, 2),
                'capital': round(capital, 2)
            })

    n = len(trades)
    wins = [tr for tr in trades if tr['pnl_net_pct'] > 0]
    losses = [tr for tr in trades if tr['pnl_net_pct'] <= 0]
    wr = len(wins) / max(n, 1) * 100
    gp = sum(tr['pnl_net_pct'] for tr in wins)
    gl = abs(sum(tr['pnl_net_pct'] for tr in losses)) + 1e-6
    pf = gp / gl
    ret = (capital / 100000.0 - 1.0) * 100.0
    return {'trades': n, 'wins': len(wins), 'losses': len(losses), 'wr': round(wr, 1), 'pf': round(pf, 2), 'ret': round(ret, 2), 'final_cap': round(capital, 2)}

print('================================================================================')
print('SAME-DAY INTRADAY BUY & SELL BACKTEST (PAST 200 TRADING DAYS)')
print('Strict Same-Day Square-Off at 3:15 PM IST | Lower Intraday Taxes (0.015% STT)')
print('================================================================================\n')

cfg1 = run_intraday_backtest(trades_per_day=1, enforce_regime=False)
cfg2 = run_intraday_backtest(trades_per_day=2, enforce_regime=False)
cfg3 = run_intraday_backtest(trades_per_day=3, enforce_regime=False)

print('Mode 1: Daily Single Best Pick (Trade Every Available Day):')
print('  Trades: ' + str(cfg1['trades']) + ' | Wins: ' + str(cfg1['wins']) + ' | Losses: ' + str(cfg1['losses']) + ' | Win Rate: ' + str(cfg1['wr']) + '% | PF: ' + str(cfg1['pf']) + ' | Net Return: +' + str(cfg1['ret']) + '% | Cap: Rs ' + str(cfg1['final_cap']))

print('\nMode 2: Top 2 Picks Daily (Split 50/50 Allocation):')
print('  Trades: ' + str(cfg2['trades']) + ' | Wins: ' + str(cfg2['wins']) + ' | Losses: ' + str(cfg2['losses']) + ' | Win Rate: ' + str(cfg2['wr']) + '% | PF: ' + str(cfg2['pf']) + ' | Net Return: +' + str(cfg2['ret']) + '% | Cap: Rs ' + str(cfg2['final_cap']))

print('\nMode 3: Top 3 Picks Daily (Split 33% Allocation):')
print('  Trades: ' + str(cfg3['trades']) + ' | Wins: ' + str(cfg3['wins']) + ' | Losses: ' + str(cfg3['losses']) + ' | Win Rate: ' + str(cfg3['wr']) + '% | PF: ' + str(cfg3['pf']) + ' | Net Return: +' + str(cfg3['ret']) + '% | Cap: Rs ' + str(cfg3['final_cap']))
