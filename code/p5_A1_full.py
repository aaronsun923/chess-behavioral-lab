#!/usr/bin/env python3
"""
p5_A1_full.py — SPEC v5 Amendment A1: the remaining depth-20 evaluations, all rows
(data/spec_v5/A1_tasks.parquet, depth-20 part), resumable from the study store.

Batches, in the designer's order (2026-09-24): after h; after best_20; after best_2,
best_4, best_8; after best_12, best_15. Positions already in the store (pilot,
A1 check, or an earlier batch) are skipped.

    python3 code/p5_A1_full.py run [nproc]   # default nproc 6
    python3 code/p5_A1_full.py summary       # per-batch wall time, store counts, coverage
"""
import os, sys, json, logging

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p5_common as C
import p5_evals as EV

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s',
                    handlers=[logging.StreamHandler(),
                              logging.FileHandler(os.path.join(EV.EVAL_DIR, 'evals.log'))])

BATCHES = [('A1_d20_h', ['h']),
           ('A1_d20_best20', ['best_20']),
           ('A1_d20_best2_4_8', ['best_2', 'best_4', 'best_8']),
           ('A1_d20_best12_15', ['best_12', 'best_15'])]
BATCH_LOG = os.path.join(EV.EVAL_DIR, 'A1_batches.json')
# System sleep inside a batch (pmset -g log): processes paused, wall clock kept running.
# 2026-09-26 11:09:00 to 12:22:17 UTC, 'Low Power Sleep' on battery at 1%.
SLEEP_S = {'A1_d20_best2_4_8': 4397}


def tasks20():
    t = pd.read_parquet(os.path.join(C.OUT_DIR, 'A1_tasks.parquet'))
    return t[t.depth == 20].copy()


def record(tag, n_run, wall):
    b = json.load(open(BATCH_LOG)) if os.path.exists(BATCH_LOG) else {}
    prev = b.get(tag, {})
    b[tag] = {'evaluations_run': prev.get('evaluations_run', 0) + n_run,
              'wall_seconds': prev.get('wall_seconds', 0.0) + wall,
              'finished_utc': pd.Timestamp.utcnow().isoformat()}
    json.dump(b, open(BATCH_LOG, 'w'), indent=2)


def run(nproc):
    t = tasks20()
    for tag, items in BATCHES:
        x = t[t['item'].isin(items)].drop_duplicates(EV.KEY)
        st = EV.load_store()
        have = set(zip(st[st.depth == 20].row_id, st[st.depth == 20].move_uci))
        n_run = sum((a, b) not in have for a, b in zip(x.row_id, x.move_uci))
        wall = EV.run_tasks(x.assign(item=tag), tag, nproc)
        record(tag, n_run, wall)


def summary():
    t = tasks20()
    st = EV.load_store()
    s20 = st[st.depth == 20]
    have = set(zip(s20.row_id, s20.move_uci))
    missing = sum((a, b) not in have for a, b in zip(t.row_id, t.move_uci))
    b = json.load(open(BATCH_LOG))
    L = ['# SPEC v5 Amendment A1: depth-20 evaluations, all rows\n',
         'Spec: `specs/paper4_spec_v5.md`, Amendment A1 (880423e) and A1.4 outcome (b735062). nproc = 6, MultiPV 5, Threads 1, Hash 128, ucinewgame per search. '
         'Nothing from §6 or §7.\n',
         '## 1. Batches\n',
         '| Batch | Positions | Evaluations run (engine / terminal) | Wall (h), logged | System sleep in batch (h) | Wall (h), excluding sleep | Wall s per engine evaluation, excluding sleep |\n|---|---|---|---|---|---|---|']
    for tag, items in BATCHES:
        x = s20[s20.batch == tag]
        ne, nt = int((x.terminal == '').sum()), int((x.terminal != '').sum())
        w = b[tag]['wall_seconds']; sl = SLEEP_S.get(tag, 0)
        L.append(f"| {tag} | after {', '.join(items)} | {ne:,} / {nt:,} | {w / 3600:.2f} | {sl / 3600:.2f} | {(w - sl) / 3600:.2f} | {(w - sl) / max(ne, 1):.3f} |")
    tw = sum(b[t]['wall_seconds'] for t, _ in BATCHES); ts = sum(SLEEP_S.values())
    L.append(f"| Total | | | {tw / 3600:.2f} | {ts / 3600:.2f} | {(tw - ts) / 3600:.2f} | |")
    L.append('\nSleep source: `pmset -g log`, 2026-09-26 11:09:00 to 12:22:17 UTC (low-power sleep on battery at 1%); the run process was paused, not restarted, and no shard was lost. No other sleep in the run window.')
    L += ['\n## 2. Study store, depth 20\n', '| Batch | Evaluations |\n|---|---|']
    for tag, n in s20.batch.fillna('timing_d20').value_counts().sort_index().items():
        L.append(f'| {tag} | {n:,} |')
    L.append(f'| Total depth-20 | {len(s20):,} |')
    L.append(f'| of which terminal (by rule, no engine call) | {int((s20.terminal != "").sum()):,} |')
    L.append(f'| Depth-25 (A1.4 check) | {int((st.depth == 25).sum()):,} |')
    L.append(f'| Depth-15 (pilot) | {int((st.depth == 15).sum()):,} |')
    L.append(f'\nDepth-20 positions required by A1 (`A1_tasks.parquet`, {len(t.drop_duplicates(["row_id", "move_uci"])):,} distinct) missing from the store: {missing}.\n')
    p = os.path.join(C.REPO, 'reports', 'spec_v5_A1_d20_run.md')
    open(p, 'w').write('\n'.join(L))
    print('\n'.join(L))


if __name__ == '__main__':
    stage = sys.argv[1]
    if stage == 'run':
        run(int(sys.argv[2]) if len(sys.argv) > 2 else 6)
    else:
        summary()
