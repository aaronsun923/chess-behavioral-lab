#!/usr/bin/env python3
"""
p5_evals.py — SPEC v5 successor-evaluation store and runner.

Every new depth-15/20 evaluation (C.eval_successor: MultiPV 5, Threads 1,
Hash 128, ucinewgame per search) is persisted once in data/spec_v5/evals/ with
engine name, SHA-256, settings, full PVs, nodes, seconds and timestamp, keyed by
(row_id, move_uci, depth). run_tasks() skips keys already in the store, so a
position is never evaluated twice and an interrupted batch resumes.
"""
import os, sys, glob, time, logging
import multiprocessing as mp

import pandas as pd
import chess, chess.engine

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p5_common as C

EVAL_DIR = os.path.join(C.OUT_DIR, 'evals')
CHUNK = 2000
KEY = ['row_id', 'move_uci', 'depth']

log = logging.getLogger('p5evals')

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


def load_store():
    """All study evaluations (timing sample + pilot batches); excludes the v3 reproduction check."""
    fs = [f for f in sorted(glob.glob(os.path.join(EVAL_DIR, '*.parquet')))
          if not os.path.basename(f).startswith('repro_check')]
    if not fs:
        return pd.DataFrame(columns=KEY)
    s = pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True)
    s['game_id'] = s['game_id'].astype(str)
    assert not s.duplicated(KEY).any(), 'duplicate evaluation in store'
    return s


def run_tasks(tasks, tag, nproc=8, purpose='SPEC v5 study evaluation'):
    """tasks: DataFrame with row_id, game_id, ply, fen, move_uci, depth, item."""
    tasks = tasks.drop_duplicates(KEY)
    have = load_store()
    done = set(map(tuple, have[KEY].values)) if len(have) else set()
    todo = [t for t in tasks.itertuples() if (t.row_id, t.move_uci, t.depth) not in done]
    log.info('[%s] %d tasks, %d already in store, %d to run', tag, len(tasks),
             len(tasks) - len(todo), len(todo))
    if not todo:
        return 0.0
    einfo = C.engine_info()
    jobs = [({'row_id': int(t.row_id), 'game_id': t.game_id, 'ply': int(t.ply), 'item': t.item},
             t.fen, t.move_uci, int(t.depth)) for t in todo]
    stamp = int(time.time())
    t0 = time.time(); buf = []; chunk = 0
    with mp.Pool(nproc, initializer=_init) as pool:
        for n, r in enumerate(pool.imap_unordered(_run, jobs, chunksize=1), 1):
            buf.append(r)
            if len(buf) >= CHUNK or n == len(jobs):
                df = pd.DataFrame(buf)
                for k in ['engine_name', 'engine_sha256', 'Threads', 'Hash_MB']:
                    df[k] = einfo[k]
                df['nproc'] = nproc; df['purpose'] = purpose; df['batch'] = tag
                df.to_parquet(os.path.join(EVAL_DIR, f'{tag}-{stamp}-{chunk:04d}.parquet'), index=False)
                chunk += 1; buf = []
                el = time.time() - t0
                log.info('[%s] %d/%d  %.1f eval/s  eta %.1f min', tag, n, len(jobs), n / el,
                         (len(jobs) - n) / (n / el) / 60)
    wall = time.time() - t0
    log.info('[%s] done: %d evaluations, wall %.1f min', tag, len(jobs), wall / 60)
    return wall
