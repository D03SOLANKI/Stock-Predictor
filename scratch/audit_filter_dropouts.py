import sys, pandas as pd, numpy as np
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

dropouts = {
    'total_days_evaluated': 200,
    'days_trade_executed': 0,
    'no_stocks_passed_premarket_screener': 0,
    'rejected_by_gap_trap (>2.5% gap)': 0,
    'rejected_by_red_open (<0% gap)': 0,
    'did_not_reach_trigger_price': 0,
    'rejected_by_model2_red_candle (c_T < o_T)': 0,
}

for t in range(start_idx, end_idx):
    date_T = dates[t]
    cands = []
    for sym in all_tickers:
        close = get_series(sym, 'Close', t)
        high = get_series(sym, 'High', t)
        low = get_series(sym, 'Low', t)
        vol = get_series(sym, 'Volume', t)
        if len(close) < 25 or len(high) < 25 or len(vol) < 25: continue
        c = float(close.iloc[-1])
        h = float(high.iloc[-1])
        v = float(vol.iloc[-1])
        if c < 30.0: continue
        turnover = float((vol * close).tail(20).mean())
        if turnover < 100000000.0: continue
        ema20 = float(close.ewm(span=20, adjust=False).mean().iloc[-1])
        if c < ema20: continue
        h_52w = float(high.tail(250).max()) if len(high) >= 250 else float(high.max())
        dist_52w = ((h_52w - c) / h_52w) * 100.0
        if dist_52w > 15.0: continue

        ca_margin = calculate_clean_air(high)
        avg_vol = float(vol.tail(20).mean()) + 1e-6
        vol_ratio = v / avg_vol
        import math
        raw_trigger = h + max(round(h * 0.0010, 2), 0.10)
        trigger = round(math.ceil(raw_trigger / 0.05) * 0.05, 2)
        score = (15.0 - dist_52w) + (ca_margin * 2.0) + min((1.0 - vol_ratio) * 10, 10)
        cands.append((score, sym, trigger, c))

    if not cands:
        dropouts['no_stocks_passed_premarket_screener'] += 1
        continue

    cands.sort(key=lambda x: x[0], reverse=True)
    pick = cands[0]
    sym = pick[1]
    trigger = pick[2]
    c_prev = pick[3]

    o_T = float(df_all[(sym, 'Open')].iloc[t])
    h_T = float(df_all[(sym, 'High')].iloc[t])
    c_T = float(df_all[(sym, 'Close')].iloc[t])

    # Check why it did not execute
    if o_T > trigger * 1.025:
        dropouts['rejected_by_gap_trap (>2.5% gap)'] += 1
    elif o_T < c_prev * 0.998:
        dropouts['rejected_by_red_open (<0% gap)'] += 1
    elif h_T < trigger:
        dropouts['did_not_reach_trigger_price'] += 1
    elif c_T < o_T:
        dropouts['rejected_by_model2_red_candle (c_T < o_T)'] += 1
    else:
        dropouts['days_trade_executed'] += 1

print('=== DROPOUT FUNNEL ACROSS 200 TRADING SESSIONS ===')
for k, v in dropouts.items():
    print(k.ljust(45) + ': ' + str(v))
