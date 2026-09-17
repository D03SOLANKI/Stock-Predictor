# Unit Tests for Historical Self-Learning Agent
import pytest
import pandas as pd
import numpy as np

from tradingagents.learning.feature_extractor import extract_premarket_features, calculate_clean_air_margin
from tradingagents.learning.retrospection_agent import RetrospectionAgent
from tradingagents.learning.pattern_memory import PatternMemory

def test_feature_extractor_clean_air():
    highs = pd.Series([100, 102, 101, 105, 103, 104, 108])
    margin = calculate_clean_air_margin(highs, lookback=5)
    assert margin == 10.0  # Blue sky breakout

    # 108 sits right within the last 5 lookback sessions (index -3)
    highs_trapped = pd.Series([100, 102, 108, 101, 103, 104, 106])
    margin_trapped = calculate_clean_air_margin(highs_trapped, lookback=5)
    assert margin_trapped < 5.0  # (108 - 106) / 106 * 100 = 1.89%

def test_feature_extractor_nr7_inside():
    dates = pd.date_range('2024-01-01', periods=30)
    close = pd.Series(np.linspace(100, 150, 30), index=dates)
    high = close + 2.0
    low = close - 2.0
    open_s = close - 0.5
    vol = pd.Series([1000000] * 30, index=dates)

    feats = extract_premarket_features(close, high, low, open_s, vol)
    assert feats is not None
    assert 'curr_close' in feats
    assert 'trigger' in feats
    assert feats['trigger'] > feats['curr_close']

def test_pattern_memory_reinforcement():
    pm = PatternMemory()
    w_initial = pm.memory['midcap']['archetypes']['CLEAN_AIR_VOLATILITY_SQUEEZE']['confidence_weight']
    pm.record_learning_event('midcap', 'TEST.NS', 'HIT', 'CLEAN_AIR_VOLATILITY_SQUEEZE', 'hit')
    w_after_hit = pm.memory['midcap']['archetypes']['CLEAN_AIR_VOLATILITY_SQUEEZE']['confidence_weight']
    assert w_after_hit > w_initial

    pm.record_learning_event('midcap', 'TEST.NS', 'FALSE_POSITIVE', 'CLEAN_AIR_VOLATILITY_SQUEEZE', 'miss')
    w_after_miss = pm.memory['midcap']['archetypes']['CLEAN_AIR_VOLATILITY_SQUEEZE']['confidence_weight']
    assert w_after_miss < w_after_hit
