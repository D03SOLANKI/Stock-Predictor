# Pattern Memory Store: Clusters pre-market setups into archetypes and dynamically updates confidence weights.
import json
from typing import Dict, Any, List, Optional
import numpy as np

class PatternMemory:
    def __init__(self):
        self.memory = {
            'midcap': {
                'total_gainer_cases': 0,
                'track_b_cases': 0,
                'archetypes': {
                    'CLEAN_AIR_VOLATILITY_SQUEEZE': {'hits': 0, 'attempts': 0, 'confidence_weight': 1.0, 'description': 'Clean air >= 2.5% + Vol ratio <= 0.70 + NR7/Inside'},
                    'RELATIVE_STRENGTH_LEADER': {'hits': 0, 'attempts': 0, 'confidence_weight': 1.0, 'description': 'RS Alpha >= +5.0% + Near 52w <= 5.0% + Trend > 50 SMA'},
                    'COILED_SPRING_50SMA_BOUNCE': {'hits': 0, 'attempts': 0, 'confidence_weight': 1.0, 'description': 'Price > 200 SMA + Pullback within 2% of 50 SMA + Inside day'},
                    'BASEMENT_MOMENTUM_REVERSAL': {'hits': 0, 'attempts': 0, 'confidence_weight': 0.5, 'description': 'Deep under 50 SMA + extreme dry-up (often fails)'},
                },
                'learned_insights': [],
            },
            'smallcap': {
                'total_gainer_cases': 0,
                'track_b_cases': 0,
                'archetypes': {
                    'EXPLOSIVE_VCP_BREAKOUT': {'hits': 0, 'attempts': 0, 'confidence_weight': 1.0, 'description': 'High ADR >= 4.0% + NR7 compression + Clean air >= 3.0%'},
                    'FLOAT_CONSTRAINED_MOMENTUM': {'hits': 0, 'attempts': 0, 'confidence_weight': 1.0, 'description': 'Turnover >= 10 Cr + RS Alpha >= +8.0% + 52w high proximity <= 6%'},
                    'HIGH_BETA_SECTOR_RUNNER': {'hits': 0, 'attempts': 0, 'confidence_weight': 1.0, 'description': 'Sector peer expansion + Price > 50 SMA + Volume dry-up'},
                    'ILLIQUID_PUMP_TRAP': {'hits': 0, 'attempts': 0, 'confidence_weight': 0.3, 'description': 'Turnover < 10 Cr + erratic wicks (penalized)'},
                },
                'learned_insights': [],
            }
        }

    def classify_setup(self, tier: str, feats: Dict[str, Any]) -> str:
        clean_air = feats.get('clean_air_margin', 0.0)
        vol_ratio = feats.get('vol_ratio_20d', 1.0)
        is_nr7 = feats.get('is_nr7', False)
        is_inside = feats.get('is_inside_day', False)
        rs_alpha = feats.get('composite_rs_alpha', 0.0)
        dist_52w = feats.get('dist_52w_pct', 15.0)
        above_50 = feats.get('above_50sma', False)
        above_200 = feats.get('above_200sma', False)
        dist_50 = abs(feats.get('dist_50sma_pct', 10.0))
        adr = feats.get('adr_pct', 3.0)

        if tier == 'midcap':
            if clean_air >= 2.5 and vol_ratio <= 0.75 and (is_nr7 or is_inside):
                return 'CLEAN_AIR_VOLATILITY_SQUEEZE'
            elif rs_alpha >= 4.0 and dist_52w <= 5.0 and above_50:
                return 'RELATIVE_STRENGTH_LEADER'
            elif above_200 and dist_50 <= 2.5 and is_inside:
                return 'COILED_SPRING_50SMA_BOUNCE'
            else:
                return 'BASEMENT_MOMENTUM_REVERSAL'
        else:
            if adr >= 3.5 and is_nr7 and clean_air >= 2.5:
                return 'EXPLOSIVE_VCP_BREAKOUT'
            elif rs_alpha >= 6.0 and dist_52w <= 6.0:
                return 'FLOAT_CONSTRAINED_MOMENTUM'
            elif above_50 and vol_ratio <= 0.75:
                return 'HIGH_BETA_SECTOR_RUNNER'
            else:
                return 'ILLIQUID_PUMP_TRAP'

    def score_candidate(self, tier: str, feats: Dict[str, Any]) -> float:
        archetype = self.classify_setup(tier, feats)
        weight = self.memory[tier]['archetypes'][archetype]['confidence_weight']

        ca_pts = min(feats.get('clean_air_margin', 0.0) * 7.0, 35.0)
        rs_pts = max(min(feats.get('composite_rs_alpha', 0.0) * 2.5 + 15.0, 35.0), 5.0)
        vdu_pts = max(min((1.0 - feats.get('vol_ratio_20d', 1.0)) * 20.0, 20.0), 2.0)
        proximity_bonus = 10.0 if feats.get('dist_52w_pct', 10.0) <= 5.0 else 0.0
        nr7_bonus = 5.0 if feats.get('is_nr7', False) else 0.0

        raw_score = (ca_pts + rs_pts + vdu_pts + proximity_bonus + nr7_bonus)
        return round(raw_score * weight, 1)

    def record_learning_event(
        self,
        tier: str,
        ticker: str,
        outcome: str,
        archetype: str,
        reason: str,
    ):
        arch_data = self.memory[tier]['archetypes'][archetype]
        arch_data['attempts'] += 1

        if outcome == 'HIT':
            arch_data['hits'] += 1
            # Reinforce confidence weight
            arch_data['confidence_weight'] = round(min(arch_data['confidence_weight'] * 1.05, 2.5), 2)
        elif outcome == 'FALSE_POSITIVE':
            # Penalize confidence weight
            arch_data['confidence_weight'] = round(max(arch_data['confidence_weight'] * 0.95, 0.2), 2)

    def save_memory(self, filepath: str):
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.memory, f, indent=2)

    def load_memory(self, filepath: str):
        with open(filepath, 'r', encoding='utf-8') as f:
            self.memory = json.load(f)
