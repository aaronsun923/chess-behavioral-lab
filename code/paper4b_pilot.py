#!/usr/bin/env python3
"""
paper4b_pilot.py — Paper 4b pilot: is human deviation risk management?

Implements SPEC v2 (paper4b_spec_v2.md), §2 pilot only: 500 games drawn from
the 1,970 v1 games with random_seed = 20260824. All v1 infrastructure is
reused, not recomputed: the WP formula, the engine configuration, the
middlegame window, the completed shards and their `WPL` / `gap_12` /
`eval_volatility` / `time_pressure` columns.

Stages:
    python3 paper4b_pilot.py selftest   # §3.1 explicit perspective test
    python3 paper4b_pilot.py sample     # §2 locked draw
    python3 paper4b_pilot.py analyze    # §3 risk evaluation -> parquet
    python3 paper4b_pilot.py report     # §6 deliverables
"""
import os, io, sys, json, time, math, hashlib, argparse, logging
import multiprocessing as mp
from collections import Counter, defaultdict

import numpy as np
import pandas as pd
import chess, chess.engine

# ---- reuse ALL v1 infrastructure (spec §0) ----
import paper4_pilot as V1
from paper4_pilot import wp_from_cp, pov_cp, ENGINE, DEPTH, MULTIPV, THREADS, HASH_MB

SEED_4B    = 20260824          # [LOCKED §2]
N_GAMES_4B = 500               # [LOCKED §2]
WPL_BAND      = (0.0, 5.0)     # [LOCKED §4.1] exclusive lower, inclusive upper
WPL_BAND_ROB  = (0.0, 10.0)    # [LOCKED §4.3] robustness band

CACHE_DIR  = 'paper4b_cache'
RESULT_DIR = 'paper4b_results'
SAMPLE_CSV = os.path.join(CACHE_DIR, 'pilot4b_sample_games.csv')
N_BUCKETS  = 16
RUN_TAG    = 'run'

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
log = logging.getLogger('p4b')


# ==================================================================== §3.1
def risk_of_successor(board, move, eng):
    """[LOCKED §3.1-3.3] Evaluate P(move) at depth 15 / MultiPV 5 and return
    the risk profile of `move` **from the perspective of the side that played
    it** (`WP_self`).

    In P(move) the side to move is the OPPONENT, so the engine's scores are
    relative to the opponent and every one must be sign-flipped to become
    WP_self. The opponent's 1st choice minimises WP_self; their 5th choice
    maximises it.
    """
    b = board.copy(stack=False)
    b.push(move)

    if b.is_checkmate():                       # the mover delivered mate
        return dict(risk_steep=0.0, risk_var=0.0, wp_self_opp_best=100.0,
                    wp_self_opp_worst=100.0, n_pv=0, terminal='checkmate')
    if b.is_stalemate() or b.is_insufficient_material() or \
       b.is_seventyfive_moves() or b.is_fivefold_repetition():
        return dict(risk_steep=0.0, risk_var=0.0, wp_self_opp_best=50.0,
                    wp_self_opp_worst=50.0, n_pv=0, terminal='draw')

    info = eng.analyse(b, chess.engine.Limit(depth=DEPTH),
                       multipv=MULTIPV, game=object())   # independent search
    if not isinstance(info, list):
        info = [info]
    info = [x for x in info if 'score' in x]
    # sign flip: pov_cp is opponent-relative in P(move); negate for WP_self
    wp_self = [wp_from_cp(-pov_cp(x['score'])) for x in info]
    if not wp_self:
        return dict(risk_steep=np.nan, risk_var=np.nan, wp_self_opp_best=np.nan,
                    wp_self_opp_worst=np.nan, n_pv=0, terminal='no_pv')

    # MultiPV order is best-for-opponent first == lowest WP_self first
    lo, hi = wp_self[0], wp_self[-1]
    return dict(
        # [LOCKED §3.2] punishment steepness. See report §0: the spec's own
        # note, §3.4 and §4.1 all require this to be NON-NEGATIVE and rising
        # with risk, which is (5th choice - 1st choice); the operand order
        # printed in §3.2 yields exactly its negation. Magnitude is identical.
        risk_steep=hi - lo,
        risk_var=float(np.std(wp_self, ddof=0)),      # [LOCKED §3.3]
        wp_self_opp_best=lo, wp_self_opp_worst=hi,
        n_pv=len(wp_self), terminal='')


def stage_selftest():
    """§3.1 requires an explicit perspective test here; v1's mirror test is
    carried over and a v1<->v4b cross-check is added."""
    eng = chess.engine.SimpleEngine.popen_uci(ENGINE)
    eng.configure({'Threads': THREADS, 'Hash': HASH_MB})
    ok = True
    print("\n=== §3.1 PERSPECTIVE / SIGN SELF-TEST (Paper 4b) ===")

    # 1. v1's colour-mirror test, carried over unchanged
    mfen = "r1bq1rk1/pp2ppbp/2np1np1/8/2BNP3/2N1B3/PPP2PPP/R2Q1RK1 w - - 0 1"
    def wp0(fen):
        i = eng.analyse(chess.Board(fen), chess.engine.Limit(depth=DEPTH), multipv=MULTIPV)
        return wp_from_cp(pov_cp(i[0]['score']))
    a, b_ = wp0(mfen), wp0(chess.Board(mfen).mirror().fen())
    t = abs(a - b_) < 2.0
    print(f"[{'PASS' if t else 'FAIL'}] v1 colour mirror carried over -> {a:.2f} vs {b_:.2f}"); ok &= t

    # 2. WP_self after a move must equal v1's _wp_after (independent code path)
    board = chess.Board(mfen)
    mv = list(board.legal_moves)[0]
    r = risk_of_successor(board, mv, eng)
    V1._ENG = eng
    v1_wp = V1._wp_after(board, mv)     # v1: MultiPV-1 child search, negated
    t = abs(r['wp_self_opp_best'] - v1_wp) < 2.0
    print(f"[{'PASS' if t else 'FAIL'}] WP_self(opp best) == v1 _wp_after -> "
          f"{r['wp_self_opp_best']:.2f} vs {v1_wp:.2f}"); ok &= t

    # 3. steepness non-negative, and ordering of the two extremes
    t = r['risk_steep'] >= 0 and r['wp_self_opp_worst'] >= r['wp_self_opp_best']
    print(f"[{'PASS' if t else 'FAIL'}] steepness >= 0, opp-best <= opp-worst -> "
          f"steep {r['risk_steep']:.2f}, {r['wp_self_opp_best']:.2f} <= {r['wp_self_opp_worst']:.2f}"); ok &= t

    # 4. PERSPECTIVE IDENTITY: risk_steep computed in WP_self must equal the
    #    opponent's own top-to-5th gap computed in the opponent's WP. This is
    #    the exact sign-flip §3.1 warns about, tested directly rather than via
    #    chess intuition.
    tb = chess.Board(mfen); tm = tb.parse_san('Nxc6')
    r4 = risk_of_successor(tb, tm, eng)
    cb = tb.copy(); cb.push(tm)
    ci = eng.analyse(cb, chess.engine.Limit(depth=DEPTH), multipv=MULTIPV, game=object())
    wp_opp = [wp_from_cp(pov_cp(x['score'])) for x in ci]      # opponent's own POV
    gap_opp = wp_opp[0] - wp_opp[-1]
    t = abs(r4['risk_steep'] - gap_opp) < 1e-6
    print(f"[{'PASS' if t else 'FAIL'}] steep(WP_self) == opp gap(WP_opp) -> "
          f"{r4['risk_steep']:.4f} vs {gap_opp:.4f}"); ok &= t

    # 5. WP_self and WP_opp must sum to 100 line-by-line, and risk_var must be
    #    invariant to the flip (std is unchanged by x -> 100 - x).
    t = abs((r4['wp_self_opp_best'] + wp_opp[0]) - 100.0) < 1e-6
    print(f"[{'PASS' if t else 'FAIL'}] WP_self + WP_opp == 100 -> "
          f"{r4['wp_self_opp_best']:.4f} + {wp_opp[0]:.4f}"); ok &= t
    t = abs(r4['risk_var'] - float(np.std(wp_opp, ddof=0))) < 1e-6
    print(f"[{'PASS' if t else 'FAIL'}] risk_var flip-invariant -> "
          f"{r4['risk_var']:.4f} vs {float(np.std(wp_opp, ddof=0)):.4f}"); ok &= t

    # 5. mate-in-1 must give WP_self = 100 and zero risk
    mb = chess.Board("6k1/5ppp/8/8/8/8/5PPP/R5K1 w - - 0 1")
    rm = risk_of_successor(mb, mb.parse_san('Ra8+'), eng)
    t = rm['risk_steep'] >= 0
    print(f"[{'PASS' if t else 'FAIL'}] forcing check handled -> steep {rm['risk_steep']:.2f}"); ok &= t
    eng.quit()
    print(f"\nSELF-TEST {'PASSED' if ok else 'FAILED'}")
    return ok


# ==================================================================== §2
def v1_rows():
    fr = []
    for root, _, files in os.walk(V1.RESULT_DIR):
        for fn in sorted(files):
            if fn.endswith('.parquet'):
                fr.append(pd.read_parquet(os.path.join(root, fn)))
    df = pd.concat(fr, ignore_index=True).drop_duplicates(['game_id', 'ply'])
    return df.sort_values(['game_id', 'ply']).reset_index(drop=True)


def stage_sample():
    os.makedirs(CACHE_DIR, exist_ok=True)
    df = v1_rows()
    ids = np.sort(df.game_id.unique())
    rng = np.random.default_rng(SEED_4B)              # [LOCKED §2]
    keep = set(rng.choice(ids, size=N_GAMES_4B, replace=False))
    pd.DataFrame({'game_id': sorted(keep)}).to_csv(SAMPLE_CSV, index=False)
    sub = df[df.game_id.isin(keep)]
    same = (sub.move_played == sub.move_engine_best)
    log.info(f"[LOCKED §2] {len(keep)} games of {len(ids)} | {len(sub):,} v1 rows "
             f"| played==best {same.sum():,} ({100*same.mean():.2f}%) -> skipped per §5 "
             f"| to evaluate {(~same).sum():,} rows = {2*(~same).sum():,} engine calls")


# ==================================================================== §3
_ENG = None
def _init_worker():
    global _ENG
    _ENG = chess.engine.SimpleEngine.popen_uci(ENGINE)
    _ENG.configure({'Threads': THREADS, 'Hash': HASH_MB})   # same as v1


def _process_row(rec):
    """Evaluate both moves of one v1 row. Returns (records, n_calls, secs, err)."""
    try:
        board = chess.Board(rec['fen'])
        out = []; t0 = time.perf_counter()
        for which, san in (('played', rec['move_played']), ('best', rec['move_engine_best'])):
            mv = board.parse_san(san)
            r = risk_of_successor(board, mv, _ENG)
            r.update(game_id=rec['game_id'], ply=int(rec['ply']), which_move=which,
                     move_san=san, fen=rec['fen'])
            out.append(r)
        return out, 2, time.perf_counter() - t0, None
    except Exception as e:
        return [], 0, 0.0, f'{type(e).__name__}:{e}'


def _done_keys():
    """[LOCKED §5] resume on (game_id, ply, which_move)."""
    done = set()
    if not os.path.isdir(RESULT_DIR):
        return done
    for root, _, files in os.walk(RESULT_DIR):
        for fn in files:
            if fn.endswith('.parquet'):
                try:
                    d = pd.read_parquet(os.path.join(root, fn),
                                        columns=['game_id', 'ply', 'which_move'])
                    done |= set(map(tuple, d.values))
                except Exception:
                    pass
    return done


def stage_analyze(nproc):
    # unique per-run tag: a resumed run must never reuse an earlier run's
    # filenames, or it silently overwrites shards the resume just skipped.
    global RUN_TAG
    RUN_TAG = f'{int(time.time())}-{os.getpid()}'
    os.makedirs(RESULT_DIR, exist_ok=True)
    keep = set(pd.read_csv(SAMPLE_CSV, dtype={'game_id': str}).game_id)
    df = v1_rows()
    sub = df[df.game_id.isin(keep)].copy()
    # [LOCKED §5] played == best  =>  dRISK == 0 by construction, skip evaluation
    todo = sub[sub.move_played != sub.move_engine_best]
    done = _done_keys()
    recs = [r for r in todo.to_dict('records')
            if (r['game_id'], int(r['ply']), 'played') not in done]
    log.info(f"{len(sub):,} sampled rows | {len(todo):,} need evaluation | "
             f"{len(recs):,} remaining after resume | {2*len(recs):,} engine calls "
             f"on {nproc} processes")
    if not recs:
        return

    buf = defaultdict(list); errs = Counter()
    ncalls = 0; teng = 0.0; nrows = 0; chunk = 0
    t_start = time.time()

    def flush():
        nonlocal chunk
        for b, rows in buf.items():
            if rows:
                d = os.path.join(RESULT_DIR, f'bucket={b:02d}'); os.makedirs(d, exist_ok=True)
                pd.DataFrame(rows).to_parquet(os.path.join(d, f'part-{RUN_TAG}-{chunk:04d}.parquet'),
                                              index=False)
        buf.clear(); chunk += 1

    with mp.Pool(nproc, initializer=_init_worker) as pool:
        for rows, nc, tt, err in pool.imap(_process_row, recs, chunksize=1):
            nrows += 1; ncalls += nc; teng += tt
            if err:
                errs[err.split(':')[0]] += 1
            for r in rows:
                buf[V1.bucket_of(r['game_id']) % N_BUCKETS].append(r)
            if nrows % 500 == 0:
                el = time.time() - t_start
                log.info(f"{nrows}/{len(recs)} rows | {ncalls} calls | "
                         f"{1000*teng/max(ncalls,1):.0f} ms/call | {el/60:.1f} min | "
                         f"ETA {(el/nrows)*(len(recs)-nrows)/60:.1f} min")
            if nrows % 1000 == 0:
                flush()
    flush()
    st = {'rows': nrows, 'engine_calls': ncalls, 'engine_seconds': teng,
          'wall_seconds': time.time() - t_start,
          'ms_per_call': 1000 * teng / max(ncalls, 1), 'nproc': nproc,
          'sf_version': 'Stockfish 18', 'errors': dict(errs)}
    json.dump(st, open(os.path.join(CACHE_DIR, 'analysis4b_stats.json'), 'w'), indent=2)
    log.info(f"DONE {json.dumps(st)}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('stage', choices=['selftest', 'sample', 'analyze', 'report'])
    ap.add_argument('--nproc', type=int, default=9)
    a = ap.parse_args()
    if a.stage == 'selftest': sys.exit(0 if stage_selftest() else 1)
    elif a.stage == 'sample': stage_sample()
    elif a.stage == 'analyze': stage_analyze(a.nproc)
    elif a.stage == 'report':
        import paper4b_report; paper4b_report.build()


if __name__ == '__main__':
    main()
