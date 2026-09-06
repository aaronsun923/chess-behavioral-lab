#!/usr/bin/env python3
"""
p4_v3_build_rows.py — SPEC v3 §3.1 + §3.2.

Builds the analysis table `p4_v3_rows/` : one row per v1 deviation row, with
  - the opponent's ACTUAL reply and its WPL          (§3.1)
  - the difficulty features the opponent faced on BOTH branches   (§3.2)

Engine work is only for replies that fall outside P(m_played)'s MultiPV-5;
those are evaluated at the [LOCKED] v1 configuration (depth 15, MultiPV 5,
Threads=1, Hash=128, independent search). Resumable on (game_id, ply,
"opp_reply") per §8.

    python3 p4_v3_build_rows.py [--nproc 8]
"""
import os, io, sys, glob, json, time, argparse, logging
import multiprocessing as mp

import numpy as np
import pandas as pd
import chess, chess.pgn, chess.engine

import paper4_pilot as V1
from paper4_pilot import (wp_from_cp, pov_cp, ENGINE, DEPTH, MULTIPV,
                          THREADS, HASH_MB, MATE_CP, WINSOR_TOP)

V1_DIR   = 'paper4_results'
V2_DIR   = 'paper4b_results'
SUCC_DIR = 'p4_v3_successor_lines'
OUT_DIR  = 'p4_v3_rows'
PGN_INDEX = os.path.join('paper4_cache', 'pgn_index.jsonl')

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
log = logging.getLogger('p4v3rows')


def _read(d):
    fs = sorted(glob.glob(os.path.join(d, '**', '*.parquet'), recursive=True))
    if not fs:
        raise SystemExit(f'no shards in {d}')
    return pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True)


def load_all():
    v1 = _read(V1_DIR).drop_duplicates(['game_id', 'ply'])
    v2 = _read(V2_DIR).drop_duplicates(['game_id', 'ply', 'which_move'])
    sc = _read(SUCC_DIR).drop_duplicates(['game_id', 'ply', 'which_move'])
    return v1, v2, sc


# ------------------------------------------------------------------ §3.1
def build_tasks(v1, sc):
    """Parse every PGN once; locate the opponent's actual reply."""
    dev = v1[v1.move_played != v1.move_engine_best].copy()
    played = sc[sc.which_move == 'played'].set_index(['game_id', 'ply'])

    pgns = {}
    for line in open(PGN_INDEX):
        d = json.loads(line)
        pgns[d['game_id']] = d['pgn']

    tasks, meta = [], []
    for gid, sub in dev.groupby('game_id', sort=False):
        g = chess.pgn.read_game(io.StringIO(pgns.get(gid) or ''))
        if g is None:
            for r in sub.itertuples():
                meta.append(dict(game_id=gid, ply=int(r.ply), discard='unparseable_pgn'))
            continue
        moves, clocks = [], []
        node = g
        while node.variations:
            node = node.variation(0)
            moves.append(node.move); clocks.append(node.clock())
        base = float(sub.base_time.iloc[0]) if pd.notna(sub.base_time.iloc[0]) else None

        for r in sub.itertuples():
            i = int(r.ply)
            rec = dict(game_id=gid, ply=i)
            if i + 1 >= len(moves):
                b = chess.Board(r.fen); b.push_san(r.move_played)
                if b.is_checkmate():
                    rec['discard'] = 'checkmate'
                elif (b.is_stalemate() or b.is_insufficient_material() or
                      b.is_seventyfive_moves() or b.is_fivefold_repetition()):
                    rec['discard'] = 'draw_terminal'
                else:
                    rec['discard'] = 'game_ended_no_reply'
                meta.append(rec); continue

            reply = moves[i + 1]
            clk = clocks[i + 1]
            rec['reply_uci'] = reply.uci()
            rec['time_pressure_opp'] = (clk / base) if (clk is not None and base) else np.nan
            rec['has_clk_opp'] = clk is not None

            key = (gid, i)
            if key not in played.index:
                rec['discard'] = 'no_successor_lines'; meta.append(rec); continue
            row = played.loc[key]
            lines = [row[f'mv_{k}'] for k in range(1, MULTIPV + 1)]
            if reply.uci() in [m for m in lines if m]:
                k = [m for m in lines].index(reply.uci()) + 1
                rec['reply_in_multipv'] = True
                rec['wp_self_reply'] = float(row[f'wp_self_{k}'])
            else:
                rec['reply_in_multipv'] = False
                rec['wp_self_reply'] = np.nan
                b = chess.Board(row['succ_fen']); b.push(reply)
                tasks.append((gid, i, b.fen()))
            meta.append(rec)
    return dev, pd.DataFrame(meta), tasks


_ENG = None


def _init_worker():
    global _ENG
    _ENG = chess.engine.SimpleEngine.popen_uci(ENGINE)
    _ENG.configure({'Threads': THREADS, 'Hash': HASH_MB})


def _eval_reply(task):
    """WP_self of the position AFTER the opponent's reply.

    In that position the side to move is the deviating player, so the engine's
    score is already self-relative: no sign flip (contrast with §3.2, where the
    successor has the OPPONENT to move)."""
    gid, ply, q_fen = task
    b = chess.Board(q_fen)
    if b.is_checkmate():                       # the opponent mated us
        return (gid, ply, wp_from_cp(-MATE_CP))
    if (b.is_stalemate() or b.is_insufficient_material() or
            b.is_seventyfive_moves() or b.is_fivefold_repetition()):
        return (gid, ply, wp_from_cp(0))
    info = _ENG.analyse(b, chess.engine.Limit(depth=DEPTH),
                        multipv=MULTIPV, game=object())
    if not isinstance(info, list):
        info = [info]
    info = [x for x in info if 'score' in x]
    if not info:
        return (gid, ply, np.nan)
    return (gid, ply, wp_from_cp(pov_cp(info[0]['score'])))


# ------------------------------------------------------------------ §3.2
def branch_features(sc, v1, which):
    """Opponent-perspective difficulty features on one branch."""
    b = sc[sc.which_move == which].copy()
    w1 = b['wp_self_1'].to_numpy()
    cols = [b[f'wp_self_{k}'].to_numpy() for k in range(1, MULTIPV + 1)]
    # WP of the LAST available line (v1 spread_15 uses wps[-1], not wps[4])
    lastvals = np.full(len(b), np.nan)
    for col in cols:
        m = ~np.isnan(col)
        lastvals[m] = col[m]
    with np.errstate(invalid='ignore'):
        n_reas = np.nansum(np.stack([(c - w1) <= 5.0 for c in cols]), axis=0)
    out = pd.DataFrame({
        'game_id': b.game_id.values, 'ply': b.ply.values,
        f'wp_level_{which}': 100.0 - w1,
        f'gap_12_{which}': cols[1] - w1,
        f'spread_15_{which}': lastvals - w1,
        f'n_reasonable_{which}': n_reas,
        f'n_legal_{which}': [chess.Board(f).legal_moves.count() for f in b.succ_fen],
        f'wp_self_1_{which}': w1,
        f'n_pv_{which}': b.n_pv.values,
    })
    # eval_volatility: |WP_opp(P) - WP(position two plies earlier, i.e. ply-1)|
    prev = v1[['game_id', 'ply', 'wp_best']].copy()
    prev['ply'] = prev['ply'] + 1                     # ply-1 -> joins onto ply
    out = out.merge(prev.rename(columns={'wp_best': '_wp_prev'}),
                    on=['game_id', 'ply'], how='left')
    out[f'eval_volatility_{which}'] = (out[f'wp_level_{which}'] - out['_wp_prev']).abs()
    return out.drop(columns=['_wp_prev'])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--nproc', type=int, default=8)
    a = ap.parse_args()

    v1, v2, sc = load_all()
    log.info('v1 %d rows | v2 %d rows | successor lines %d rows', len(v1), len(v2), len(sc))

    dev, meta, tasks = build_tasks(v1, sc)
    log.info('deviation rows %d | need engine eval for reply: %d', len(dev), len(tasks))

    if tasks:
        t0 = time.time(); res = []
        with mp.Pool(a.nproc, initializer=_init_worker) as pool:
            for n, r in enumerate(pool.imap_unordered(_eval_reply, tasks, chunksize=8), 1):
                res.append(r)
                if n % 2000 == 0:
                    el = time.time() - t0
                    log.info('%d/%d  %.0f pos/s  eta %.0f min', n, len(tasks),
                             n / el, (len(tasks) - n) / (n / el) / 60)
        el = time.time() - t0
        log.info('reply evals: %d in %.1f min', len(res), el / 60)
        rr = pd.DataFrame(res, columns=['game_id', 'ply', 'wp_self_reply_eval'])
        meta = meta.merge(rr, on=['game_id', 'ply'], how='left')
        meta['wp_self_reply'] = meta['wp_self_reply'].fillna(meta['wp_self_reply_eval'])
        meta = meta.drop(columns=['wp_self_reply_eval'])

    df = dev.merge(meta, on=['game_id', 'ply'], how='left')
    for which in ('played', 'best'):
        df = df.merge(branch_features(sc, v1, which), on=['game_id', 'ply'], how='left')

    # ΔRISK_steep [LOCKED §3.3]: v2 stored values, never the recomputed ones
    rs = v2.pivot(index=['game_id', 'ply'], columns='which_move',
                  values='risk_steep').reset_index()
    rs['delta_risk_steep'] = rs['played'] - rs['best']
    df = df.merge(rs[['game_id', 'ply', 'delta_risk_steep']], on=['game_id', 'ply'], how='left')

    # §3.1 dependent quantity, opponent's realised error
    df['WPL_opp_actual_raw'] = df['wp_self_reply'] - df['wp_self_1_played']
    cut = v1['WPL_raw'].quantile(1 - WINSOR_TOP)      # [LOCKED] v1 full-sample 1% level
    df['WPL_opp_actual'] = df['WPL_opp_actual_raw'].clip(upper=cut)
    df['winsor_cut'] = cut

    os.makedirs(OUT_DIR, exist_ok=True)
    df.to_parquet(os.path.join(OUT_DIR, 'p4_v3_rows.parquet'), index=False)
    log.info('wrote %s  (%d rows, %d cols)', OUT_DIR, len(df), df.shape[1])
    log.info('kept %d | discarded %d', df.discard.isna().sum(), df.discard.notna().sum())


if __name__ == '__main__':
    main()
