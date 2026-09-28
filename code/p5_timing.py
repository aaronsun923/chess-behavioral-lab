#!/usr/bin/env python3
"""
p5_timing.py — SPEC v5 §11 timing sample (pre-run count, step 4).

On subsample rows (data/spec_v5/subsample_ids.csv, in draw order):
  - 200 depth-15 evaluations of the position after the human's move, taken from
    the first 200 rows that are §4(a) rows (non-deviation, no depth-15 evaluation,
    non-terminal);
  - 50 depth-20 evaluations of the position after the human's move, taken from the
    first 50 rows whose post-h position is non-terminal.
Each batch runs on --nproc processes of one thread each, as the full run will.
These are study evaluations: they are persisted with full engine metadata in
data/spec_v5/evals/ and must not be recomputed.

--check first re-evaluates 16 v2/v3 successor positions (drawn with the SPEC v5
seed) and compares wp_self_1..5 with the stored v3 values; not study evaluations.

    python3 code/p5_timing.py --check
    python3 code/p5_timing.py [--nproc 8]
"""
import os, sys, time, json, argparse, logging
import multiprocessing as mp

import numpy as np
import pandas as pd
import chess, chess.engine

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p5_common as C

EVAL_DIR = os.path.join(C.OUT_DIR, 'evals')
os.makedirs(EVAL_DIR, exist_ok=True)
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s',
                    handlers=[logging.StreamHandler(),
                              logging.FileHandler(os.path.join(EVAL_DIR, 'evals.log'))])
log = logging.getLogger('p5time')

_ENG = None


def _init():
    global _ENG
    _ENG = chess.engine.SimpleEngine.popen_uci(C.ENGINE)
    _ENG.configure({'Threads': C.THREADS, 'Hash': C.HASH_MB})


def _run(task):
    meta, fen, uci, depth = task
    r = C.eval_successor(_ENG, fen, uci, depth)
    r['timestamp'] = pd.Timestamp.utcnow().isoformat()
    return {**meta, **r}


def run_batch(tasks, nproc, einfo, purpose):
    t0 = time.time()
    with mp.Pool(nproc, initializer=_init) as pool:
        res = pool.map(_run, tasks, chunksize=1)
    wall = time.time() - t0
    df = pd.DataFrame(res)
    for k in ['engine_name', 'engine_sha256', 'Threads', 'Hash_MB']:
        df[k] = einfo[k]
    df['nproc'] = nproc; df['purpose'] = purpose
    return df, wall


def check(nproc, einfo):
    s = C.load_existing_successors()
    s = s[s.terminal == ''].sample(16, random_state=C.SEED)
    tasks = []
    for x in s.itertuples():
        b = chess.Board(x.fen)
        tasks.append(({'game_id': x.game_id, 'ply': x.ply, 'which_move': x.which_move},
                      x.fen, b.parse_san(x.move_san).uci(), 15))
    df, _ = run_batch(tasks, nproc, einfo, 'reproduction check vs v3 (not a study evaluation)')
    m = df.merge(s, on=['game_id', 'ply', 'which_move'], suffixes=('', '_v3'))
    diffs = np.abs(np.concatenate([m[f'wp_self_{k}'] - m[f'wp_self_{k}_v3'] for k in range(1, 6)]))
    mv_same = all((m[f'mv_{k}'] == m[f'mv_{k}_v3']).all() for k in range(1, 6))
    res = {'positions': len(m), 'max_abs_wp_diff': float(np.nanmax(diffs)), 'moves_identical': bool(mv_same)}
    df.to_parquet(os.path.join(EVAL_DIR, 'repro_check_v3.parquet'), index=False)
    json.dump(res, open(os.path.join(EVAL_DIR, 'repro_check_v3.json'), 'w'), indent=2)
    log.info('reproduction check: %s', res)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--nproc', type=int, default=8)
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args()
    einfo = C.engine_info()
    if a.check:
        return check(a.nproc, einfo)

    for f in ['timing_d15.parquet', 'timing_d20.parquet']:
        if os.path.exists(os.path.join(EVAL_DIR, f)):
            raise SystemExit(f'{f} exists: timing evaluations are never recomputed')

    t = pd.read_parquet(os.path.join(C.OUT_DIR, 'precount_tasks.parquet'))
    sub = pd.read_csv(os.path.join(C.OUT_DIR, 'subsample_ids.csv'))
    a_rows = t[(t['item'] == 'a') & ~t.already_evaluated & ~t.terminal].set_index('row_id')
    r = pd.read_parquet(os.path.join(C.OUT_DIR, 'root_choices.parquet')).set_index('row_id')

    def h_uci(rid):
        return chess.Board(r.at[rid, 'fen']).parse_san(r.at[rid, 'move_played']).uci()

    def h_terminal(rid):
        b = chess.Board(r.at[rid, 'fen']); b.push_uci(h_uci(rid))
        return b.is_checkmate() or b.is_stalemate() or b.is_insufficient_material() or \
            b.is_seventyfive_moves() or b.is_fivefold_repetition()

    pick15 = [rid for rid in sub.row_id if rid in a_rows.index][:200]
    pick20 = [rid for rid in sub.row_id if not h_terminal(rid)][:50]
    assert len(pick15) == 200 and len(pick20) == 50

    def mk(rid, depth):
        meta = {'row_id': int(rid), 'game_id': r.at[rid, 'game_id'], 'ply': int(r.at[rid, 'ply']),
                'which': 'h', 'item': 'a' if depth == 15 else 'd'}
        return (meta, r.at[rid, 'fen'], h_uci(rid), depth)

    summary = {}
    for depth, pick in [(15, pick15), (20, pick20)]:
        log.info('timing batch: %d evaluations at depth %d on %d processes', len(pick), depth, a.nproc)
        df, wall = run_batch([mk(rid, depth) for rid in pick], a.nproc, einfo,
                             'SPEC v5 study evaluation; §11 timing sample; do not recompute')
        df.to_parquet(os.path.join(EVAL_DIR, f'timing_d{depth}.parquet'), index=False)
        summary[depth] = {'n': len(df), 'mean_s': float(df.seconds.mean()),
                          'median_s': float(df.seconds.median()), 'wall_s': wall,
                          'nodes_mean': float(df.nodes.mean())}
        log.info('depth %d: %s', depth, summary[depth])
    json.dump({**einfo, 'MultiPV': C.SUCC_MULTIPV, 'nproc': a.nproc, 'batches': summary},
              open(os.path.join(EVAL_DIR, 'timing_summary.json'), 'w'), indent=2)


if __name__ == '__main__':
    main()
