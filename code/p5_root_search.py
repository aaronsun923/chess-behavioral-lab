#!/usr/bin/env python3
"""
p5_root_search.py — SPEC v5 §3 root searches (pre-run count, step 2).

Single-PV root search on all 50,021 v1 positions at depths 4, 8, 12 and 15 (and,
under Amendment A1, 2 and 20 via --depths), one
full pass per depth on --nproc processes of one thread each. Root positions are
rebuilt from the PGN with the full move history, as v1 sent them, and checked
against the stored v1 FEN.

Writes data/spec_v5/root_choices.parquet (row keys + best_4, best_8, best_12,
best_15_singlepv in UCI), root_search_log.parquet (one row per search: move,
score, depth, seldepth, nodes, seconds, timestamp) and root_choices_engine_log.json.
Resumable per depth.

    python3 code/p5_root_search.py [--nproc 8]
"""
import os, sys, time, json, argparse, logging
import multiprocessing as mp

import pandas as pd
import chess, chess.engine

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p5_common as C

DEPTHS = [4, 8, 12, 15]                      # SPEC v5 §3
ALL_DEPTHS = [2, 4, 8, 12, 15, 20]           # + Amendment A1: depth 2 baseline, depth 20 anchor
COL = {d: f'best_{d}' for d in ALL_DEPTHS}
COL[15] = 'best_15_singlepv'

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s',
                    handlers=[logging.StreamHandler(),
                              logging.FileHandler(os.path.join(C.OUT_DIR, 'root_search.log'))])
log = logging.getLogger('p5root')

_ENG = None


def _init():
    global _ENG
    _ENG = chess.engine.SimpleEngine.popen_uci(C.ENGINE)
    _ENG.configure({'Threads': C.THREADS, 'Hash': C.HASH_MB})


def _search_game(task):
    """task = (depth, pgn, [(row_id, ply, fen), ...]) -> list of result dicts."""
    depth, pgn, rows = task
    board, moves = C.game_moves(pgn)
    want = {ply: (rid, fen) for rid, ply, fen in rows}
    out = []
    for i, mv in enumerate(moves):
        if i > max(want):
            break
        if i in want:
            rid, fen = want[i]
            if board.fen() != fen:
                raise RuntimeError(f'FEN mismatch row {rid}')
            t0 = time.perf_counter()
            info = _ENG.analyse(board, chess.engine.Limit(depth=depth),
                                game=object())            # ucinewgame before every search
            sec = time.perf_counter() - t0
            best = info['pv'][0]
            s = info['score'].relative
            out.append({'row_id': rid, 'depth': depth, 'move_uci': best.uci(),
                        'move_san': board.san(best),
                        'score_cp': s.score(mate_score=C.MATE_CP),
                        'depth_reached': info.get('depth'), 'seldepth': info.get('seldepth'),
                        'nodes': info.get('nodes'), 'seconds': sec,
                        'timestamp': pd.Timestamp.utcnow().isoformat()})
        board.push(mv)
    return out


def rerun_depth4(nproc):
    part = os.path.join(C.OUT_DIR, 'root_search_d04_rerun.parquet')
    if os.path.exists(part):
        raise SystemExit('depth-4 rerun already done')
    v1 = C.load_v1()
    pgns = C.load_pgns()
    tasks = [(4, pgns[g], list(zip(d.row_id, d.ply, d.fen))) for g, d in v1.groupby('game_id', sort=True)]
    log.info('depth-4 rerun: %d games on %d processes', len(tasks), nproc)
    res = []
    t0 = time.time(); started = pd.Timestamp.utcnow().isoformat()
    with mp.Pool(nproc, initializer=_init) as pool:
        for r in pool.imap_unordered(_search_game, tasks, chunksize=2):
            res.extend(r)
    wall = time.time() - t0
    df = pd.DataFrame(res).sort_values('row_id').reset_index(drop=True)
    assert len(df) == len(v1) and df.row_id.is_unique
    df.to_parquet(part, index=False)
    first = pd.read_parquet(os.path.join(C.OUT_DIR, 'root_search_d04.parquet'))
    m = first[['row_id', 'move_uci']].merge(df[['row_id', 'move_uci']], on='row_id',
                                             suffixes=('_first', '_rerun'))
    n_diff = int((m.move_uci_first != m.move_uci_rerun).sum())
    log_path = os.path.join(C.OUT_DIR, 'root_choices_engine_log.json')
    elog = json.load(open(log_path))
    elog['passes']['4']['note'] = 'overlapped a system sleep; wall time not usable'
    elog['passes']['4_rerun'] = {'started_utc': started, 'wall_seconds': wall, 'nproc': nproc,
                                 'searches': len(df), 'engine_seconds_sum': float(df.seconds.sum()),
                                 'nodes_sum': int(df.nodes.sum()),
                                 'rows_compared': len(m), 'best_4_rows_differing': n_diff}
    json.dump(elog, open(log_path, 'w'), indent=2)
    log.info('depth-4 rerun done: wall %.1f min, best_4 differing rows %d / %d', wall / 60, n_diff, len(m))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--nproc', type=int, default=8)
    ap.add_argument('--depths', type=int, nargs='+', default=DEPTHS)
    ap.add_argument('--rerun-depth4', action='store_true',
                    help='second depth-4 pass (first pass overlapped a system sleep): '
                         'separate files, row-by-row comparison, root_choices untouched')
    a = ap.parse_args()
    if a.rerun_depth4:
        return rerun_depth4(a.nproc)
    os.makedirs(C.OUT_DIR, exist_ok=True)

    v1 = C.load_v1()
    pgns = C.load_pgns()
    by_game = {g: list(zip(d.row_id, d.ply, d.fen)) for g, d in v1.groupby('game_id', sort=True)}
    einfo = C.engine_info()
    log.info('engine %s sha256 %s | rows %d games %d | nproc %d',
             einfo['engine_name'], einfo['engine_sha256'], len(v1), len(by_game), a.nproc)

    log_path = os.path.join(C.OUT_DIR, 'root_choices_engine_log.json')
    elog = json.load(open(log_path)) if os.path.exists(log_path) else {}
    elog.update({'spec': 'specs/paper4_spec_v5.md @ 6d25e7b; Amendment A1 @ 880423e', 'step': 'root searches (pre-run count step 2; A1.7)',
                 **einfo, 'MultiPV': 1, 'nproc': a.nproc,
                 'root_input': 'position startpos moves <full game history> (as v1)',
                 'rows': len(v1)})
    elog.setdefault('passes', {})

    for d in a.depths:
        part = os.path.join(C.OUT_DIR, f'root_search_d{d:02d}.parquet')
        if os.path.exists(part):
            log.info('depth %d already done', d); continue
        tasks = [(d, pgns[g], r) for g, r in by_game.items()]
        res = []
        t0 = time.time(); started = pd.Timestamp.utcnow().isoformat()
        with mp.Pool(a.nproc, initializer=_init) as pool:
            for n, r in enumerate(pool.imap_unordered(_search_game, tasks, chunksize=2), 1):
                res.extend(r)
                if n % 200 == 0:
                    el = time.time() - t0
                    log.info('depth %d: %d/%d games  %.0f pos/s  eta %.1f min', d, n, len(tasks),
                             len(res) / el, (len(tasks) - n) * el / n / 60)
        wall = time.time() - t0
        df = pd.DataFrame(res).sort_values('row_id').reset_index(drop=True)
        assert len(df) == len(v1) and df.row_id.is_unique
        df.to_parquet(part, index=False)
        elog['passes'][str(d)] = {'started_utc': started, 'wall_seconds': wall,
                                  'searches': len(df), 'engine_seconds_sum': float(df.seconds.sum()),
                                  'nodes_sum': int(df.nodes.sum())}
        json.dump(elog, open(log_path, 'w'), indent=2)
        log.info('depth %d done: %d searches, wall %.1f min', d, len(df), wall / 60)

    out = v1[['row_id', 'game_id', 'ply', 'fen', 'move_played', 'move_engine_best']].copy()
    done = [d for d in ALL_DEPTHS if os.path.exists(os.path.join(C.OUT_DIR, f'root_search_d{d:02d}.parquet'))]
    for d in done:
        p = pd.read_parquet(os.path.join(C.OUT_DIR, f'root_search_d{d:02d}.parquet'))
        out = out.merge(p[['row_id', 'move_uci']].rename(columns={'move_uci': COL[d]}), on='row_id')
    out.to_parquet(os.path.join(C.OUT_DIR, 'root_choices.parquet'), index=False)
    allp = pd.concat([pd.read_parquet(os.path.join(C.OUT_DIR, f'root_search_d{d:02d}.parquet'))
                      for d in done], ignore_index=True)
    allp.to_parquet(os.path.join(C.OUT_DIR, 'root_search_log.parquet'), index=False)
    log.info('wrote root_choices.parquet (%d rows) and root_search_log.parquet', len(out))


if __name__ == '__main__':
    main()
