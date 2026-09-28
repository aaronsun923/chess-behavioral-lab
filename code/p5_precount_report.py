#!/usr/bin/env python3
"""
p5_precount_report.py — writes reports/spec_v5_precount.md from the logged outputs
of p5_root_search.py, p5_precount.py and p5_timing.py. No engine, no estimation.
"""
import os, sys, json

import pandas as pd
import chess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p5_common as C

D = C.OUT_DIR
E = os.path.join(D, 'evals')


def pct(a, b):
    return f'{100 * a / b:.2f}%'


def main():
    elog = json.load(open(os.path.join(D, 'root_choices_engine_log.json')))
    pc = json.load(open(os.path.join(D, 'precount.json')))
    tm = json.load(open(os.path.join(E, 'timing_summary.json')))
    rc = json.load(open(os.path.join(E, 'repro_check_v3.json')))
    t = pd.read_parquet(os.path.join(D, 'precount_tasks.parquet'))
    N = pc['N_rows']
    L = []
    A = L.append

    A('# SPEC v5 pre-run count\n')
    A(f'Spec: `specs/paper4_spec_v5.md` at 6d25e7b (LOCKED 2026-09-22). Rules of SPEC v3 and the '
      f'correction spec apply. Pilot not started. Outputs in `data/spec_v5/`; code in `code/p5_*.py`.\n')

    # 1
    A('## 1. Engine setup\n')
    A('| Item | Value |\n|---|---|')
    A(f"| Engine | {elog['engine_name']} (same binary as v2/v3: `~/Desktop/chess-study/engine/stockfish`) |")
    A(f"| Binary SHA-256 (build hash) | `{elog['engine_sha256']}` |")
    A(f"| Build | {'; '.join(elog['compiler'])} |")
    A(f"| Threads | {elog['Threads']} |")
    A(f"| Hash | {elog['Hash_MB']} MB (v2/v3 value) |")
    A(f"| ucinewgame | {elog['ucinewgame']} |")
    A('| Root searches | MultiPV 1; position sent as `startpos moves <full game history>`, as v1; each rebuilt root checked equal to the stored v1 FEN |')
    A(f'| Successor evaluations (depth 15 and 20) | MultiPV {C.SUCC_MULTIPV}, V = line-1 WP from the mover\'s side; position sent as `fen <root> moves <move>`; terminal rules as v3; the configuration of the 57,294 v2/v3 successor evaluations |')
    A(f"| Processes | {elog['nproc']} × 1 thread (machine: 10 cores, Apple silicon) |")
    A(f"| Evaluation function check against v3 | {rc['positions']} v2/v3 successor positions re-evaluated at depth 15: max abs WP difference {rc['max_abs_wp_diff']:.6g}, all five moves identical: {rc['moves_identical']} |\n")

    # 2
    A('## 2. Root searches (single-PV, all 50,021 positions)\n')
    agree = pc['agree_15_singlepv_multipv']
    A('| Depth | Searches | Wall time (min, 8 processes) | Engine time, mean per search (s) | Agreement of best_15_singlepv with MultiPV best_15 |\n|---|---|---|---|---|')
    for d in [4, 8, 12, 15]:
        p = elog['passes']['4_rerun' if d == 4 else str(d)]
        ag = f'{agree:,} / {N:,} = {pct(agree, N)}' if d == 15 else '—'
        A(f"| {d} | {p['searches']:,} | {p['wall_seconds'] / 60:.1f} | {p['engine_seconds_sum'] / p['searches']:.4f} | {ag} |")
    p1, p2 = elog['passes']['4'], elog['passes']['4_rerun']
    A(f"| 4, first pass | {p1['searches']:,} | not usable (overlapped a system sleep; logged {p1['wall_seconds'] / 60:.1f}) | {p1['engine_seconds_sum'] / p1['searches']:.4f} | — |")
    A(f"| 4, rerun vs first pass | best_4 differing rows: {p2['best_4_rows_differing']:,} / {p2['rows_compared']:,} | | | |")
    A('\nFile: `data/spec_v5/root_choices.parquet` (row_id, game_id, ply, fen, move_played, move_engine_best, best_4, best_8, best_12, best_15_singlepv; moves in UCI). '
      'Engine log beside it: `root_choices_engine_log.json`, `root_search_log.parquet` (per search: move, score, depth, seldepth, nodes, seconds, timestamp), `root_search.log`. '
      'best_4 in `root_choices.parquet` is from the first pass; both depth-4 runs are kept (`root_search_d04.parquet`, `root_search_d04_rerun.parquet`).\n')

    # 3
    A('## 3. Counts (§4, best_15 = best_15_singlepv)\n')
    A('"Already evaluated" = the same (game_id, ply, move) is among the 57,294 v2/v3 depth-15 successor evaluations. '
      '"Terminal" = checkmate or draw after the move; valued by rule, no engine call. '
      '"Engine evaluations" = rows − already evaluated − terminal.\n')
    A('| Item | Definition | Rows | Already evaluated | Terminal | Engine evaluations |\n|---|---|---|---|---|---|')
    lab = {'a': ('(a)', 'non-deviation rows, position after h (expected 21,374)'),
           'b4': ('(b) d = 4', 'best_4 ≠ h and best_4 ≠ best_15'),
           'b8': ('(b) d = 8', 'best_8 ≠ h and best_8 ≠ best_15'),
           'b12': ('(b) d = 12', 'best_12 ≠ h and best_12 ≠ best_15'),
           'c': ('(c)', 'best_15_singlepv ≠ MultiPV best_15, position after best_15_singlepv'),
           'd': ('(d)', 'depth 20, subsample: distinct positions after h, best_15, best_4, best_8, best_12')}
    for k in ['a', 'b4', 'b8', 'b12', 'c', 'd']:
        s = t[t['item'] == k]
        n_eng = int((~s.already_evaluated & ~s.terminal).sum())
        A(f"| {lab[k][0]} | {lab[k][1]} | {len(s):,} | {int(s.already_evaluated.sum()):,} | {int(s.terminal.sum()):,} | {n_eng:,} |")
    t15 = t[t.eval_depth == 15]
    new = t15[~t15.already_evaluated & ~t15.terminal]
    A(f"| (a)+(b)+(c) | distinct depth-15 engine evaluations (same row and move counted once) | | | | {new.drop_duplicates(['row_id', 'move_uci']).shape[0]:,} |")
    sd = t[t['item'] == 'd']
    for typ in ['h', 'best_15', 'best_4', 'best_8', 'best_12']:
        x = sd[sd.first_type == typ]
        A(f"| (d) by type | first counted as {typ} | {len(x):,} | | {int(x.terminal.sum()):,} | {int((~x.terminal).sum()):,} |")
    for d in [4, 8, 12]:
        A(f"| best_d = best_15 | d = {d} | {pc[f'eq_best15_{d}']:,} ({pct(pc[f'eq_best15_{d}'], N)}) | | | |")
    ne = pc['ne_best15_12']
    A(f"| §5 threshold | rows with best_12 ≠ best_15 | {ne:,} / {N:,} = {pct(ne, N)} (threshold 5%) | | | |")
    for d in [4, 8, 12]:
        A(f"| Not a §4 count | best_{d} ≠ best_15 and the position after best_{d} was evaluated in v2/v3, whose stored output has no PV (HORIZON's input) | {pc[f'pv_not_stored_{d}']:,} | | | |")
    A('\nSubsample: `data/spec_v5/subsample_ids.csv` (2,000 row ids, seed 20261001, `DataFrame.sample` on the v1 rows ordered by game_id, ply). Per-item evaluation list: `data/spec_v5/precount_tasks.parquet`.\n')

    # 4
    A('## 4. Timing sample (study evaluations, kept)\n')
    A('| Evaluation | Positions | Processes | Mean s / evaluation | Median s / evaluation | Batch wall time (s) | Mean nodes |\n|---|---|---|---|---|---|---|')
    for d in ['15', '20']:
        b = tm['batches'][d]
        A(f"| depth {d}, MultiPV {C.SUCC_MULTIPV}, after h | {b['n']} | {tm['nproc']} × 1 thread | {b['mean_s']:.3f} | {b['median_s']:.3f} | {b['wall_s']:.1f} | {b['nodes_mean']:,.0f} |")
    A('\nDepth 15: the first 200 subsample rows in draw order that are §4(a) rows (non-terminal). Depth 20: the first 50 subsample rows in draw order with a non-terminal post-h position. '
      'Stored with engine name, SHA-256, Threads, Hash, MultiPV, depth, full PVs, nodes, seconds and timestamp in `data/spec_v5/evals/timing_d15.parquet` and `timing_d20.parquet`; log `evals/evals.log`.\n')

    # 5
    A('## 5. Revised §11 estimate\n')
    n15 = new.drop_duplicates(['row_id', 'move_uci']).shape[0]
    n20 = int((~sd.terminal).sum())
    m15, m20 = tm['batches']['15']['mean_s'], tm['batches']['20']['mean_s']
    done15, done20 = tm['batches']['15']['n'], tm['batches']['20']['n']
    h15 = (n15 - done15) * m15 / 8 / 3600
    h20 = (n20 - done20) * m20 / 8 / 3600
    A('| Depth | Engine evaluations (step 3) | Done in step 4 | Remaining | Mean s / evaluation (step 4) | Hours on 8 processes |\n|---|---|---|---|---|---|')
    A(f'| 15 | {n15:,} | {done15} | {n15 - done15:,} | {m15:.3f} | {h15:.1f} |')
    A(f'| 20 | {n20:,} | {done20} | {n20 - done20:,} | {m20:.3f} | {h20:.1f} |')
    A(f'| Total | | | | | {h15 + h20:.1f} |')
    pvn = pc['pv_not_stored_4'] + pc['pv_not_stored_8'] + pc['pv_not_stored_12']
    A(f'\nRoot searches (step 2) are complete and not included. Not included either: the positions in the "not a §4 count" rows of section 3, which would add at most {pvn:,} depth-15 evaluations ({pvn * m15 / 8 / 3600:.1f} hours) if they were re-evaluated to obtain a PV.\n')

    os.makedirs(os.path.join(C.REPO, 'reports'), exist_ok=True)
    p = os.path.join(C.REPO, 'reports', 'spec_v5_precount.md')
    open(p, 'w').write('\n'.join(L))
    print(open(p).read())


if __name__ == '__main__':
    main()
