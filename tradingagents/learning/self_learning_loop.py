# Self-Learning Loop: Executes daily walk-forward learning and deep WHY attribution.
from typing import Dict, Any, List
import pandas as pd
import numpy as np

from tradingagents.swing_opportunity.mid_small_universe import NSE_MID_SMALL_UNIVERSE
from tradingagents.learning.feature_extractor import extract_premarket_features
from tradingagents.learning.retrospection_agent import RetrospectionAgent
from tradingagents.learning.pattern_memory import PatternMemory

class SelfLearningLoop:
    def __init__(self, df_all: pd.DataFrame, benchmark_ticker: str = 'NIFTYMIDCAP150.NS'):
        self.df_all = df_all
        self.dates = df_all.index
        self.benchmark_ticker = benchmark_ticker
        self.retrospection = RetrospectionAgent(min_gain_pct=3.0)
        self.memory = PatternMemory()
        self.midcaps = [t for t, m in NSE_MID_SMALL_UNIVERSE.items() if m.get('tier') == 'Midcap']
        self.smallcaps = [t for t, m in NSE_MID_SMALL_UNIVERSE.items() if m.get('tier') == 'Smallcap']

    def run_simulation(self, start_idx: int = 50, end_idx: int = None) -> Dict[str, Any]:
        if end_idx is None:
            end_idx = len(self.dates)

        daily_audit_log = []
        metrics = {
            'midcap': {'predictions': 0, 'top_gainer_hits': 0, 'expanded_hits': 0, 'false_positives': 0, 'missed_gainers': 0},
            'smallcap': {'predictions': 0, 'top_gainer_hits': 0, 'expanded_hits': 0, 'false_positives': 0, 'missed_gainers': 0},
        }

        for t in range(start_idx, end_idx):
            date_T = self.dates[t]
            bm_close_pit = self.df_all[(self.benchmark_ticker, 'Close')].iloc[:t].dropna()
            sma50_bm = bm_close_pit.tail(50).mean() if len(bm_close_pit) >= 50 else bm_close_pit.iloc[-1]
            is_regime_bullish = bool(bm_close_pit.iloc[-1] > sma50_bm)

            # STEP 1: PRE-MARKET PREDICTION (Strictly before 9:15 AM)
            day_candidates = {'midcap': [], 'smallcap': []}
            pre_features_cache = {}

            for tier, t_list in [('midcap', self.midcaps), ('smallcap', self.smallcaps)]:
                for ticker in t_list:
                    if (ticker, 'Close') not in self.df_all.columns: continue
                    c = self.df_all[(ticker, 'Close')].iloc[:t].dropna()
                    h = self.df_all[(ticker, 'High')].iloc[:t].dropna()
                    l = self.df_all[(ticker, 'Low')].iloc[:t].dropna()
                    o = self.df_all[(ticker, 'Open')].iloc[:t].dropna()
                    v = self.df_all[(ticker, 'Volume')].iloc[:t].dropna()

                    feats = extract_premarket_features(c, h, l, o, v, bm_close_pit)
                    if feats is None: continue
                    pre_features_cache[ticker] = feats

                    if feats['curr_close'] < 30.0: continue
                    if feats['turnover_20d_cr'] < 10.0: continue
                    if not feats['above_200sma']: continue

                    score = self.memory.score_candidate(tier, feats)
                    archetype = self.memory.classify_setup(tier, feats)

                    day_candidates[tier].append({
                        'ticker': ticker,
                        'name': NSE_MID_SMALL_UNIVERSE.get(ticker, {}).get('name', ticker),
                        'score': score,
                        'archetype': archetype,
                        'trigger': feats['trigger'],
                        'clean_air': feats['clean_air_margin'],
                        'rs_alpha': feats['composite_rs_alpha'],
                        'features': feats,
                    })

                day_candidates[tier].sort(key=lambda x: x['score'], reverse=True)

            predictions = {
                'midcap': day_candidates['midcap'][:3],
                'smallcap': day_candidates['smallcap'][:3],
            }

            # STEP 2: POST-MARKET ACTUAL RETROSPECTION (After 3:30 PM)
            actual_gainers = self.retrospection.identify_actual_gainers(self.df_all, t, top_n=3)

            # STEP 3: DEEP WHY ANALYSIS FOR EVERY ACTUAL TOP GAINER
            day_eval = {'date': date_T.strftime('%Y-%m-%d'), 'regime_bullish': is_regime_bullish, 'tiers': {}}

            for tier in ['midcap', 'smallcap']:
                pred_list = predictions[tier]
                actual_list = actual_gainers[tier]
                actual_syms = [g['ticker'] for g in actual_list]

                # Perform WHY attribution for each actual top gainer
                actual_analysis = []
                for act in actual_list:
                    sym = act['ticker']
                    feats = pre_features_cache.get(sym)
                    if feats is None:
                        c = self.df_all[(sym, 'Close')].iloc[:t].dropna()
                        h = self.df_all[(sym, 'High')].iloc[:t].dropna()
                        l = self.df_all[(sym, 'Low')].iloc[:t].dropna()
                        o = self.df_all[(sym, 'Open')].iloc[:t].dropna()
                        v = self.df_all[(sym, 'Volume')].iloc[:t].dropna()
                        feats = extract_premarket_features(c, h, l, o, v, bm_close_pit)

                    attribution = self.retrospection.attribute_cause(act, feats if feats else {})
                    self.memory.memory[tier]['total_gainer_cases'] += 1
                    if attribution['move_track'] == 'TRACK_B_TECHNICAL_FLOW':
                        self.memory.memory[tier]['track_b_cases'] += 1

                    actual_analysis.append({
                        'ticker': sym,
                        'return_pct': act['return_pct'],
                        'intraday_expansion_pct': act['intraday_expansion_pct'],
                        'why_it_moved': attribution['primary_driver'],
                        'move_track': attribution['move_track'],
                        'open_gap_pct': attribution['open_gap_pct'],
                        'clean_air_margin': attribution['clean_air_margin'],
                        'vol_ratio_20d': attribution['vol_ratio_20d'],
                        'is_nr7': attribution['is_nr7'],
                        'is_inside_day': attribution['is_inside_day'],
                        'composite_rs_alpha': attribution['composite_rs_alpha'],
                        'dist_52w_pct': attribution['dist_52w_pct'],
                    })

                hits = []
                false_positives = []
                misses = []

                for pred in pred_list:
                    sym = pred['ticker']
                    metrics[tier]['predictions'] += 1
                    c_T = float(self.df_all[(sym, 'Close')].iloc[t])
                    c_prev = float(self.df_all[(sym, 'Close')].iloc[t-1])
                    h_T = float(self.df_all[(sym, 'High')].iloc[t])
                    day_gain = round((c_T / c_prev - 1.0) * 100.0, 2)
                    max_expansion = round((h_T / c_prev - 1.0) * 100.0, 2)

                    if sym in actual_syms:
                        metrics[tier]['top_gainer_hits'] += 1
                        metrics[tier]['expanded_hits'] += 1
                        hits.append(sym)
                        self.memory.record_learning_event(tier, sym, 'HIT', pred['archetype'], 'Exact top gainer match')
                    elif max_expansion >= 3.0:
                        metrics[tier]['expanded_hits'] += 1
                        hits.append(sym)
                        self.memory.record_learning_event(tier, sym, 'HIT', pred['archetype'], 'Intraday expansion >= 3%')
                    else:
                        metrics[tier]['false_positives'] += 1
                        false_positives.append(sym)
                        self.memory.record_learning_event(tier, sym, 'FALSE_POSITIVE', pred['archetype'], f"Stalled at {day_gain:+.1f}%")

                for act in actual_list:
                    if act['ticker'] not in [p['ticker'] for p in pred_list]:
                        metrics[tier]['missed_gainers'] += 1
                        misses.append(act['ticker'])

                day_eval['tiers'][tier] = {
                    'predicted': [p['ticker'] for p in pred_list],
                    'actual': actual_syms,
                    'actual_analysis': actual_analysis,
                    'hits': hits,
                    'false_positives': false_positives,
                    'missed': misses,
                }

            daily_audit_log.append(day_eval)

        return {'metrics': metrics, 'audit_log': daily_audit_log, 'memory': self.memory.memory}
