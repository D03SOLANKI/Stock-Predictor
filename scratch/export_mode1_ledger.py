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
    if turnover < 100000000.0: return False, 0, {}
    
    ema20 = float(close.ewm(span=20, adjust=False).mean().iloc[-1])
    if c < ema20: return False, 0, {}

    h_52w = float(high.tail(250).max()) if len(high) >= 250 else float(high.max())
    dist_52w = ((h_52w - c) / h_52w) * 100.0
    if dist_52w > 15.0: return False, 0, {}

    ca_margin = calculate_clean_air(high)
    avg_vol = float(vol.tail(20).mean()) + 1e-6
    vol_ratio = v / avg_vol
    
    raw_trigger = h + max(round(h * 0.0010, 2), 0.10)
    trigger = round(math.ceil(raw_trigger / 0.05) * 0.05, 2)
    sl = round(trigger * (1.0 - 0.020), 2)
    t1 = round(trigger * 1.030, 2)
    t2 = round(trigger * 1.050, 2)

    score = (15.0 - dist_52w) + (ca_margin * 2.0) + min((1.0 - vol_ratio) * 10, 10)
    tier = 'Midcap' if sym in midcaps else 'Smallcap'

    return True, score, {
        'ticker': sym,
        'name': NSE_MID_SMALL_UNIVERSE.get(sym, {}).get('name', sym),
        'tier': tier,
        'trigger': trigger,
        'stop_loss': sl,
        't1': t1,
        't2': t2,
        'close_prev': c
    }

capital = 100000.0
fee = 0.0015
trades = []

for t in range(start_idx, end_idx):
    date_T = dates[t]
    cands = []
    for sym in all_tickers:
        p, sc, meta = evaluate_intraday_candidate(sym, t)
        if p: cands.append((sc, meta))

    if not cands: continue
    cands.sort(key=lambda x: x[0], reverse=True)

    pick = cands[0][1]
    sym = pick['ticker']
    o_T = float(df_all[(sym, 'Open')].iloc[t])
    h_T = float(df_all[(sym, 'High')].iloc[t])
    l_T = float(df_all[(sym, 'Low')].iloc[t])
    c_T = float(df_all[(sym, 'Close')].iloc[t])
    trigger = pick['trigger']

    if o_T > trigger * 1.025: continue
    if o_T < pick['close_prev'] * 0.998: continue
    if h_T < trigger: continue
    if c_T < o_T: continue

    buy_price = max(trigger, o_T)
    hit_sl = (l_T <= pick['stop_loss'])
    hit_t1 = (h_T >= pick['t1'])
    hit_t2 = (h_T >= pick['t2'])

    if hit_t2:
        sell_price = pick['t2']
        pnl_gross = 0.050
        exit_reason = 'TARGET_2_HIT (+5.0%)'
    elif hit_t1:
        sell_price = pick['t1']
        pnl_gross = 0.030
        exit_reason = 'TARGET_1_HIT (+3.0%)'
    elif h_T >= trigger * 1.015:
        sell_price = c_T
        pnl_gross = max(0.0, (c_T - buy_price) / buy_price)
        exit_reason = 'TRAILED_BE (Square-Off)'
    elif hit_sl:
        sell_price = pick['stop_loss']
        pnl_gross = -0.020
        exit_reason = 'STOPPED_OUT (-2.0%)'
    else:
        sell_price = c_T
        pnl_gross = (c_T - buy_price) / buy_price
        exit_reason = 'SQUARE_OFF_3:15PM'

    pnl_net = pnl_gross - fee
    shares = int(capital / buy_price)
    cash_invested = round(shares * buy_price, 2)
    cash_returned = round(cash_invested * (1.0 + pnl_net), 2)
    profit_rupees = round(cash_returned - cash_invested, 2)

    capital *= (1.0 + pnl_net)

    trades.append({
        'date': date_T.strftime('%Y-%m-%d'),
        'ticker': sym,
        'name': pick['name'],
        'tier': pick['tier'],
        'buy_price': buy_price,
        'sell_price': round(sell_price, 2),
        'target_tp': pick['t1'],
        'target_t2': pick['t2'],
        'stop_loss': pick['stop_loss'],
        'exit_reason': exit_reason,
        'pnl_pct': round(pnl_net * 100, 2),
        'pnl_rs': profit_rupees,
        'capital_after': round(capital, 2),
    })

with open('scratch/mode1_trades_full_ledger.json', 'w', encoding='utf-8') as f:
    json.dump(trades, f, indent=2)

print('Total Trades Logged:', len(trades))
print('Final Capital: Rs', round(capital, 2))
