#!/usr/bin/env python3
"""
p4_v3_depth_check.py — direct measurement of the §3.1 two-tier depth asymmetry.

§3.1 values an opponent reply from P(m_played)'s stored MultiPV-5 when the reply
is one of those lines, and otherwise from a fresh depth-15 search of the child
position. Those two valuations sit at different effective depths. This measures
the gap directly: draw 2,000 in-PV replies at random (seed 20260906), evaluate
the child position freshly at the same [LOCKED] configuration, and compare that
WP_self with the stored PV-line WP_self for the same move.

Changes no estimate. Writes p4_v3_depth_check.parquet.

    python3 p4_v3_depth_check.py [--n 2000] [--nproc 8]
"""
import os, glob, time, argparse, logging
import multiprocessing as mp
import numpy as np, pandas as pd
import chess, chess.engine

import paper4_pilot as P
from paper4_pilot import wp_from_cp, pov_cp, ENGINE, DEPTH, MULTIPV, THREADS, HASH_MB, MATE_CP

SEED = 20260906
OUT = 'p4_v3_depth_check.parquet'
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
log = logging.getLogger('depthchk')

_ENG = None
def _init():
    global _ENG
    _ENG = chess.engine.SimpleEngine.popen_uci(ENGINE)
    _ENG.configure({'Threads': THREADS, 'Hash': HASH_MB})


def _eval(task):
    """WP_self of the child position, exactly as p4_v3_build_rows._eval_reply
    computes it for off-PV replies: after the reply the deviating player is to
    move, so the engine score is already self-relative (no sign flip)."""
    gid, ply, succ_fen, uci = task
    b = chess.Board(succ_fen)
    b.push(chess.Move.from_uci(uci))
    if b.is_checkmate():
        return (gid, ply, wp_from_cp(-MATE_CP))
    if (b.is_stalemate() or b.is_insufficient_material() or
            b.is_seventyfive_moves() or b.is_fivefold_repetition()):
        return (gid, ply, wp_from_cp(0))
    i = _ENG.analyse(b, chess.engine.Limit(depth=DEPTH), multipv=MULTIPV, game=object())
    if not isinstance(i, list):
        i = [i]
    i = [x for x in i if 'score' in x]
    return (gid, ply, wp_from_cp(pov_cp(i[0]['score'])) if i else np.nan)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--n', type=int, default=2000)
    ap.add_argument('--nproc', type=int, default=8)
    a = ap.parse_args()

    rows = pd.read_parquet('p4_v3_rows/p4_v3_rows_analysis.parquet')
    sc = pd.concat([pd.read_parquet(f) for f in
                    sorted(glob.glob('p4_v3_successor_lines/*.parquet'))], ignore_index=True)
    sc = sc[sc.which_move == 'played'][['game_id', 'ply', 'succ_fen']]

    pool_rows = rows[(rows.reply_in_multipv == True) &
                     rows.wp_self_reply.notna() &
                     rows.delta_risk_steep.notna()].merge(sc, on=['game_id', 'ply'], how='left')
    pool_rows = pool_rows[pool_rows.succ_fen.notna()]
    log.info('in-PV replies available: %d; drawing %d with seed %d',
             len(pool_rows), a.n, SEED)

    samp = pool_rows.sample(n=min(a.n, len(pool_rows)), random_state=SEED).reset_index(drop=True)
    tasks = [(r.game_id, int(r.ply), r.succ_fen, r.reply_uci) for r in samp.itertuples()]

    t0 = time.time(); res = []
    with mp.Pool(a.nproc, initializer=_init) as pool:
        for n, r in enumerate(pool.imap_unordered(_eval, tasks, chunksize=4), 1):
            res.append(r)
            if n % 500 == 0:
                el = time.time() - t0
                log.info('%d/%d  %.1f pos/s  eta %.1f min', n, len(tasks),
                         n / el, (len(tasks) - n) / (n / el) / 60)
    log.info('done in %.1f min', (time.time() - t0) / 60)

    fr = pd.DataFrame(res, columns=['game_id', 'ply', 'wp_self_fresh'])
    out = samp[['game_id', 'ply', 'reply_uci', 'wp_self_reply', 'delta_risk_steep',
                'WPL_opp_actual_raw', 'wp_self_1_played']].merge(fr, on=['game_id', 'ply'])
    out['diff'] = out.wp_self_fresh - out.wp_self_reply     # fresh minus stored PV line
    out.to_parquet(OUT, index=False)
    log.info('wrote %s (%d rows) | mean diff %+.4f  sd %.4f',
             OUT, len(out), out['diff'].mean(), out['diff'].std())


if __name__ == '__main__':
    main()
