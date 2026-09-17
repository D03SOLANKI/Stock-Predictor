import json
import sys
import pandas as pd
import numpy as np
from tradingagents.learning.self_learning_loop import SelfLearningLoop

sys.stdout.reconfigure(encoding='utf-8')

def main():
    print('================================================================================')
    print('HISTORICAL SELF-LEARNING AGENT: MID CAP & SMALL CAP DUAL TRACKS')
    print('================================================================================')

    df_all = pd.read_parquet('data_cache_2y.parquet')
    dates = df_all.index
    d_start = dates[0].strftime('%Y-%m-%d')
    d_end = dates[-1].strftime('%Y-%m-%d')
    print('Total Historical Trading Days: ' + str(len(dates)) + ' (' + d_start + ' to ' + d_end + ')')
    print('Running Walk-Forward Daily Learning Loop from Day 50 to 501...\n')

    learner = SelfLearningLoop(df_all)
    results = learner.run_simulation(start_idx=50, end_idx=len(dates))

    metrics = results['metrics']
    memory = results['memory']

    print('================================================================================')
    print('LEARNING SIMULATION COMPLETE: PERFORMANCE & ADAPTATION AUDIT')
    print('================================================================================')

    for tier in ['midcap', 'smallcap']:
        m = metrics[tier]
        total_p = m['predictions']
        tg_hits = m['top_gainer_hits']
        exp_hits = m['expanded_hits']
        fp = m['false_positives']
        missed = m['missed_gainers']

        print('\n--- ' + tier.upper() + ' LEARNING PERFORMANCE ---')
        print('  Total Predictions Made: ' + str(total_p))
        print('  Exact Top-Gainer Matches: ' + str(tg_hits) + ' (' + str(round(tg_hits / max(total_p, 1) * 100, 1)) + '%)')
        print('  Expanded Hits (>= +3.0% Expansion): ' + str(exp_hits) + ' (' + str(round(exp_hits / max(total_p, 1) * 100, 1)) + '%)')
        print('  False Positives (Failed/Stalled): ' + str(fp) + ' (' + str(round(fp / max(total_p, 1) * 100, 1)) + '%)')
        print('  Unpredicted Gainer Occurrences (Misses): ' + str(missed))

        print('\n  Learned Pattern Archetypes & Final Confidence Weights:')
        for arch_name, arch_info in memory[tier]['archetypes'].items():
            wr = round(arch_info['hits'] / max(arch_info['attempts'], 1) * 100, 1)
            w = str(round(arch_info['confidence_weight'], 2))
            h = str(arch_info['hits'])
            att = str(arch_info['attempts'])
            print('    * ' + arch_name + ': Weight=' + w + 'x | Hits=' + h + ' | Attempts=' + att + ' | Win Rate=' + str(wr) + '%')

    memory_file = 'learned_patterns_memory.json'
    learner.memory.save_memory(memory_file)
    print('\n[+] Persistent pattern memory saved to: ' + memory_file)

    audit_file = 'learning_daily_audit_log.json'
    with open(audit_file, 'w', encoding='utf-8') as f:
        json.dump(results['audit_log'], f, indent=2)
    print('[+] Daily audit log saved to: ' + audit_file)

if __name__ == '__main__':
    main()
