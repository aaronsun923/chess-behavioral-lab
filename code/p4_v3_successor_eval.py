#!/usr/bin/env python3
"""
p4_v3_successor_eval.py — SPEC v3 Amendment 1 item 1.

Re-evaluates the 57,294 successor positions P(m_played) / P(m_best) that v2
already visited, at the identical configuration (depth 15, MultiPV 5,
Threads=1, Hash=128, independent search), and persists ALL FIVE MultiPV lines
(move + WP_self) instead of only the lo/hi summary v2 kept.

All v1 infrastructure is reused, not redefined: wp_from_cp, pov_cp, the engine
binary and the [LOCKED] engine configuration are imported from paper4_pilot.

Writes new table `p4_v3_successor_lines/`. v1 and v2 shards are never touched.
Resumable on key (game_id, ply, which_move).

    python3 p4_v3_successor_eval.py [--nproc 8]
"""
import os, sys, glob, time, argparse, logging
import multiprocessing as mp

import numpy as np
import pandas as pd
import chess, chess.engine

import paper4_pilot as V1
from paper4_pilot import wp_from_cp, pov_cp, ENGINE, DEPTH, MULTIPV, THREADS, HASH_MB

V2_RESULT_DIR = 'paper4b_results'
RESULT_DIR    = 'p4_v3_successor_lines'
RUN_TAG       = f'{int(time.time())}-{os.getpid()}'
CHUNK_ROWS    = 2000

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
log = logging.getLogger('p4v3')


def load_v2():
    fr = [pd.read_parquet(f) for f in
          sorted(glob.glob(os.path.join(V2_RESULT_DIR, '**', '*.parquet'), recursive=True))]
    if not fr:
        raise SystemExit('no v2 shards found')
    d = pd.concat(fr, ignore_index=True)
    return d.drop_duplicates(['game_id', 'ply', 'which_move'])


def _done_keys():
    done = set()
    for f in glob.glob(os.path.join(RESULT_DIR, '*.parquet')):
        try:
            d = pd.read_parquet(f, columns=['game_id', 'ply', 'which_move'])
        except Exception:
            continue
        done |= set(map(tuple, d.values))
    return done


_ENG = None


def _init_worker():
    global _ENG
    _ENG = chess.engine.SimpleEngine.popen_uci(ENGINE)
    # [LOCKED] identical to v1/v2: one thread per worker, 128 MB hash
    _ENG.configure({'Threads': THREADS, 'Hash': HASH_MB})


def _blank(gid, ply, which, fen, san, succ_fen, terminal, wp):
    """Terminal successor: v2 stored lo == hi == wp and risk_steep 0."""
    r = dict(game_id=gid, ply=ply, which_move=which, fen=fen, move_san=san,
             succ_fen=succ_fen, n_pv=0, terminal=terminal,
             risk_steep_recomp=0.0, wp_self_opp_best_recomp=wp,
             wp_self_opp_worst_recomp=wp)
    for k in range(1, MULTIPV + 1):
        r[f'mv_{k}'] = None
        r[f'wp_self_{k}'] = np.nan
    return r


def _eval_one(task):
    gid, ply, which, fen, san = task
    b = chess.Board(fen)
    mv = b.parse_san(san)
    b.push(mv)
    succ_fen = b.fen()

    # mirrors paper4b_pilot.risk_of_successor exactly
    if b.is_checkmate():
        return _blank(gid, ply, which, fen, san, succ_fen, 'checkmate', 100.0)
    if b.is_stalemate() or b.is_insufficient_material() or \
       b.is_seventyfive_moves() or b.is_fivefold_repetition():
        return _blank(gid, ply, which, fen, san, succ_fen, 'draw', 50.0)

    info = _ENG.analyse(b, chess.engine.Limit(depth=DEPTH),
                        multipv=MULTIPV, game=object())   # independent search
    if not isinstance(info, list):
        info = [info]
    info = [x for x in info if 'score' in x]
    # sign flip: pov_cp is opponent-relative in P(move); negate for WP_self
    wp_self = [wp_from_cp(-pov_cp(x['score'])) for x in info]
    if not wp_self:
        r = _blank(gid, ply, which, fen, san, succ_fen, 'no_pv', np.nan)
        r['risk_steep_recomp'] = np.nan
        return r

    moves = [(x['pv'][0].uci() if x.get('pv') else None) for x in info]
    lo, hi = wp_self[0], wp_self[-1]
    r = dict(game_id=gid, ply=ply, which_move=which, fen=fen, move_san=san,
             succ_fen=succ_fen, n_pv=len(wp_self), terminal='',
             risk_steep_recomp=hi - lo,
             wp_self_opp_best_recomp=lo, wp_self_opp_worst_recomp=hi)
    for k in range(1, MULTIPV + 1):
        r[f'mv_{k}'] = moves[k - 1] if k <= len(moves) else None
        r[f'wp_self_{k}'] = wp_self[k - 1] if k <= len(wp_self) else np.nan
    return r


def _flush(rows, chunk):
    os.makedirs(RESULT_DIR, exist_ok=True)
    p = os.path.join(RESULT_DIR, f'part-{RUN_TAG}-{chunk:04d}.parquet')
    pd.DataFrame(rows).to_parquet(p, index=False)
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--nproc', type=int, default=8)
    a = ap.parse_args()

    v2 = load_v2()
    tasks = [(r.game_id, int(r.ply), r.which_move, r.fen, r.move_san)
             for r in v2.itertuples()]
    done = _done_keys()
    if done:
        tasks = [t for t in tasks if (t[0], t[1], t[2]) not in done]
    log.info('successor positions: %d total, %d already done, %d to run',
             len(v2), len(done), len(tasks))
    if not tasks:
        log.info('nothing to do'); return

    t0 = time.time(); rows = []; chunk = 0; n = 0
    with mp.Pool(a.nproc, initializer=_init_worker) as pool:
        for r in pool.imap_unordered(_eval_one, tasks, chunksize=8):
            rows.append(r); n += 1
            if len(rows) >= CHUNK_ROWS:
                _flush(rows, chunk); chunk += 1; rows = []
                el = time.time() - t0
                log.info('%d/%d  %.0f pos/s  eta %.0f min',
                         n, len(tasks), n / el, (len(tasks) - n) / (n / el) / 60)
        if rows:
            _flush(rows, chunk)
    el = time.time() - t0
    log.info('done: %d positions in %.1f min (%.0f ms/pos wall, %d procs)',
             n, el / 60, el * 1000 * a.nproc / max(n, 1), a.nproc)


if __name__ == '__main__':
    main()
