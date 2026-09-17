# Retrospection Agent: Identifies actual top gainers on Day T and performs causal attribution.
from typing import Dict, Any, List, Tuple
import pandas as pd
from tradingagents.swing_opportunity.mid_small_universe import NSE_MID_SMALL_UNIVERSE

class RetrospectionAgent:
    def __init__(self, min_gain_pct: float = 3.5):
        self.min_gain_pct = min_gain_pct
        self.midcaps = [t for t, m in NSE_MID_SMALL_UNIVERSE.items() if m.get('tier') == 'Midcap']
        self.smallcaps = [t for t, m in NSE_MID_SMALL_UNIVERSE.items() if m.get('tier') == 'Smallcap']

    def identify_actual_gainers(
        self,
        df_all: pd.DataFrame,
        t_idx: int,
        top_n: int = 3,
    ) -> Dict[str, List[Dict[str, Any]]]:
        date_T = df_all.index[t_idx]
        date_prev = df_all.index[t_idx - 1]

        results = {'midcap': [], 'smallcap': []}

        for tier, ticker_list in [('midcap', self.midcaps), ('smallcap', self.smallcaps)]:
            tier_gains = []
            for ticker in ticker_list:
                if (ticker, 'Close') not in df_all.columns:
                    continue
                c_T = float(df_all[(ticker, 'Close')].iloc[t_idx])
                c_prev = float(df_all[(ticker, 'Close')].iloc[t_idx - 1])
                o_T = float(df_all[(ticker, 'Open')].iloc[t_idx])
                h_T = float(df_all[(ticker, 'High')].iloc[t_idx])
                l_T = float(df_all[(ticker, 'Low')].iloc[t_idx])
                v_T = float(df_all[(ticker, 'Volume')].iloc[t_idx])

                if pd.isna(c_T) or pd.isna(c_prev) or c_prev <= 0:
                    continue

                return_pct = round((c_T / c_prev - 1.0) * 100.0, 2)
                intraday_expansion_pct = round((h_T / c_prev - 1.0) * 100.0, 2)
                open_gap_pct = round((o_T / c_prev - 1.0) * 100.0, 2)

                tier_gains.append({
                    'ticker': ticker,
                    'name': NSE_MID_SMALL_UNIVERSE.get(ticker, {}).get('name', ticker),
                    'sector': NSE_MID_SMALL_UNIVERSE.get(ticker, {}).get('sector', 'Unknown'),
                    'tier': tier,
                    'close_T': c_T,
                    'close_prev': c_prev,
                    'open_T': o_T,
                    'high_T': h_T,
                    'low_T': l_T,
                    'volume_T': v_T,
                    'return_pct': return_pct,
                    'intraday_expansion_pct': intraday_expansion_pct,
                    'open_gap_pct': open_gap_pct,
                })

            tier_gains.sort(key=lambda x: x['return_pct'], reverse=True)
            qualified = [g for g in tier_gains if g['return_pct'] >= self.min_gain_pct][:top_n]
            results[tier] = qualified

        return results

    def attribute_cause(self, gainer: Dict[str, Any], pre_features: Dict[str, Any]) -> Dict[str, Any]:
        open_gap = gainer.get('open_gap_pct', 0.0)
        near_52w = pre_features.get('near_52w_high', False)
        vol_dryup = pre_features.get('vol_dryup', False)
        clean_air = pre_features.get('has_clean_air', False)
        rs_alpha = pre_features.get('composite_rs_alpha', 0.0)
        is_nr7 = pre_features.get('is_nr7', False)
        is_inside = pre_features.get('is_inside_day', False)

        if open_gap > 2.5:
            move_track = 'TRACK_A_EVENT_OR_GAP'
            primary_driver = f"Large pre-open auction gap (+{open_gap:.2f}%). Driven by unscheduled news/corporate filing."
        elif (near_52w and clean_air and (vol_dryup or is_nr7 or is_inside)):
            move_track = 'TRACK_B_TECHNICAL_FLOW'
            primary_driver = (
                f"Multi-day compression breakout. Clean air {pre_features.get('clean_air_margin', 0):.1f}%, "
                f"vol ratio {pre_features.get('vol_ratio_20d', 0):.2f}x, RS Alpha {rs_alpha:+.1f}%."
            )
        else:
            move_track = 'TRACK_C_SPECULATIVE_OR_UNCLEAR'
            primary_driver = "Intraday momentum surge without textbook prior-day technical compression."

        return {
            'move_track': move_track,
            'primary_driver': primary_driver,
            'open_gap_pct': open_gap,
            'clean_air_margin': pre_features.get('clean_air_margin', 0.0),
            'vol_ratio_20d': pre_features.get('vol_ratio_20d', 1.0),
            'is_nr7': is_nr7,
            'is_inside_day': is_inside,
            'composite_rs_alpha': rs_alpha,
            'dist_52w_pct': pre_features.get('dist_52w_pct', 10.0),
        }
