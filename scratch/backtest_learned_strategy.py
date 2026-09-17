# Backtest the Self-Learning Model vs the Fixed Baseline
import json
import math
import sys
import pandas as pd
import numpy as np

from tradingagents.swing_opportunity.mid_small_universe import NSE_MID_SMALL_UNIVERSE
from tradingagents.learning.feature_extractor import extract_premarket_features
from tradingagents.learning.pattern_memory import PatternMemory

sys.stdout.reconfigure(encoding='utf-8')

df_all = pd.read_parquet('data_cache_2y.parquet')
dates = df_all.index
benchmark_ticker = 'NIFTYMIDCAP150.NS'

periods = [
    (50, 250, 'Train (In-Sample, Days 50-250)'),
    (250, 375, 'Validation (Days 250-375)'),
    (375, len(dates), 'Out-of-Sample Test (Days 375-501)'),
]

midcaps = [t for t, m in NSE_MID_SMALL_UNIVERSE.items() if m.get('tier') == 'Midcap']
smallcaps = [t for t, m in NSE_MID_SMALL_UNIVERSE.items() if m.get('tier') == 'Smallcap']
all_tickers = sorted(midcaps + smallcaps)

def run_backtest_engine(use_learned_memory=True):
    capital = 100000.0
    fee = 0.0025
    trades = []
    period_results = {}

    memory = PatternMemory()

    for p_start, p_end, p_label in periods:
        p_trades = []
        cap_start = capital

        for t in range(p_start, p_end):
            date_T = dates[t]
            bm_close_pit = df_all[(benchmark_ticker, 'Close')].iloc[:t].dropna()
            sma50_bm = bm_close_pit.tail(50).mean() if len(bm_close_pit) >= 50 else bm_close_pit.iloc[-1]
            if bm_close_pit.iloc[-1] < sma50_bm:
                continue

            cands = []
            for ticker in all_tickers:
                if (ticker, 'Close') not in df_all.columns: continue
                c = df_all[(ticker, 'Close')].iloc[:t].dropna()
                h = df_all[(ticker, 'High')].iloc[:t].dropna()
                l = df_all[(ticker, 'Low')].iloc[:t].dropna()
                o = df_all[(ticker, 'Open')].iloc[:t].dropna()
                v = df_all[(ticker, 'Volume')].iloc[:t].dropna()

                feats = extract_premarket_features(c, h, l, o, v, bm_close_pit)
                if feats is None: continue

                if feats['curr_close'] < 30.0: continue
                if feats['turnover_20d_cr'] < 10.0: continue
                if not feats['above_200sma'] or not feats['above_50sma']: continue
                if feats['dist_52w_pct'] > 8.0: continue
                if feats['vol_ratio_20d'] > 0.80 and not feats['is_nr7'] and not feats['is_inside_day']: continue
                if feats['clean_air_margin'] < 2.0: continue

                tier = 'midcap' if ticker in midcaps else 'smallcap'

                if use_learned_memory:
                    score = memory.score_candidate(tier, feats)
                    archetype = memory.classify_setup(tier, feats)
                else:
                    ca_pts = min(feats['clean_air_margin'] * 7.0, 35.0)
                    rs_pts = max(min(feats['composite_rs_alpha'] * 2.5 + 15.0, 35.0), 5.0)
                    vdu_pts = max(min((1.0 - feats['vol_ratio_20d']) * 20.0, 20.0), 5.0)
                    score = ca_pts + rs_pts + vdu_pts
                    archetype = 'BASELINE'

                cands.append({
                    'ticker': ticker,
                    'tier': tier,
                    'score': score,
                    'archetype': archetype,
                    'trigger': feats['trigger'],
                    'close_prev': feats['curr_close'],
                    'sl_pct': -0.022,
                    't1': round(feats['trigger'] * 1.035, 2),
                    't2': round(feats['trigger'] * 1.065, 2),
                    'sl': round(feats['trigger'] * (1.0 - 0.022), 2),
                })

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
            if c_T < o_T: continue

            entry = max(trigger, o_T)
            hit_sl = (l_T <= pick['sl'])
            hit_t1 = (h_T >= pick['t1'])
            hit_t2 = (h_T >= pick['t2'])

            if hit_t2: pnl_gross = 0.065; status = 'TARGET_2_HIT'
            elif hit_t1: pnl_gross = 0.035; status = 'TARGET_1_HIT'
            elif h_T >= trigger * 1.018: pnl_gross = max(0.0, (c_T - entry) / entry); status = 'TRAILED_BREAKEVEN'
            elif hit_sl: pnl_gross = pick['sl_pct']; status = 'STOPPED_OUT'
            else: pnl_gross = (c_T - entry) / entry; status = 'DAY_CLOSE_EXIT'

            pnl_net = pnl_gross - fee
            capital *= (1.0 + pnl_net)

            if use_learned_memory:
                outcome = 'HIT' if pnl_net > 0 else 'FALSE_POSITIVE'
                memory.record_learning_event(pick['tier'], sym, outcome, pick['archetype'], status)

            trade_record = {
                'date': date_T.strftime('%Y-%m-%d'),
                'ticker': sym,
                'tier': pick['tier'],
                'archetype': pick['archetype'],
                'status': status,
                'pnl_net_pct': round(pnl_net * 100, 2),
                'capital_after': round(capital, 2),
            }
            trades.append(trade_record)
            p_trades.append(trade_record)

        n = len(p_trades)
        wins = [tr for tr in p_trades if tr['pnl_net_pct'] > 0]
        losses = [tr for tr in p_trades if tr['pnl_net_pct'] <= 0]
        wr = len(wins) / max(n, 1) * 100
        gp = sum(tr['pnl_net_pct'] for tr in wins)
        gl = abs(sum(tr['pnl_net_pct'] for tr in losses)) + 1e-6
        pf = gp / gl
        p_ret = (capital / cap_start - 1.0) * 100

        period_results[p_label] = {
            'trades': n, 'wins': len(wins), 'losses': len(losses),
            'wr': round(wr, 1), 'pf': round(pf, 2), 'ret': round(p_ret, 2),
            'cap_end': round(capital, 2),
        }

    tot_ret = (capital / 100000.0 - 1.0) * 100
    return {'periods': period_results, 'total_trades': len(trades), 'final_capital': round(capital, 2), 'total_return': round(tot_ret, 2), 'trades': trades}

print('================================================================================')
print('WALK-FORWARD BACKTEST: FIXED BASELINE vs CONTINUOUSLY SELF-LEARNING AGENT')
print('================================================================================\n')

res_baseline = run_backtest_engine(use_learned_memory=False)
res_learned = run_backtest_engine(use_learned_memory=True)

print('Period                              | Baseline (WR / PF / Ret)   | Self-Learning (WR / PF / Ret)')
print('-' * 95)

for p_label in res_baseline['periods']:
    b = res_baseline['periods'][p_label]
    l = res_learned['periods'][p_label]
    b_str = str(b['trades']) + 't | ' + str(b['wr']) + '% | PF ' + str(b['pf']) + ' | ' + str(b['ret']) + '%'
    l_str = str(l['trades']) + 't | ' + str(l['wr']) + '% | PF ' + str(l['pf']) + ' | ' + str(l['ret']) + '%'
    print(p_label.ljust(35) + ' | ' + b_str.ljust(26) + ' | ' + l_str)

print('=' * 95)
print('Overall 2-Year Capital: Baseline Rs ' + str(res_baseline['final_capital']) + ' (' + str(res_baseline['total_return']) + '%) | Learned Rs ' + str(res_learned['final_capital']) + ' (' + str(res_learned['total_return']) + '%)')

print('\n--- Out-of-Sample Trades Taken by the Self-Learning Agent ---')
oos_trades = [tr for tr in res_learned['trades'] if tr['date'] >= '2026-03-19']
for i, tr in enumerate(oos_trades):
    m = 'WIN ' if tr['pnl_net_pct'] > 0 else 'LOSS'
    print('  ' + str(i+1).rjust(2) + '. ' + m + ' | ' + tr['date'] + ' | ' + tr['ticker'].ljust(14) + ' | ' + tr['tier'].ljust(8) + ' | ' + tr['archetype'].ljust(28) + ' | ' + tr['status'].ljust(18) + ' | Net: ' + str(tr['pnl_net_pct']) + '% | Cap: Rs ' + str(tr['capital_after']))
