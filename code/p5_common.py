#!/usr/bin/env python3
"""
p5_common.py — shared setup for SPEC v5 (specs/paper4_spec_v5.md, locked at 6d25e7b).

Inputs are the v1/v2/v3 data in ~/Desktop/chess-study (read only). Outputs go to
data/spec_v5/ in this repository.

Engine configuration [LOCKED §2]: the v2/v3 Stockfish build, Threads = 1,
Hash = 128 (the v2/v3 value), `ucinewgame` before every search (python-chess
sends it whenever `game` changes; a fresh `object()` per call forces it).

Root positions are sent exactly as v1 sent them: `position startpos moves ...`
with the full game history, rebuilt from the cached PGN. Successor positions are
sent exactly as v2/v3 sent them: `position fen <root fen> moves <move>`.
"""
import os, glob, json, hashlib, subprocess

import pandas as pd
import chess, chess.pgn, io

STUDY    = os.path.expanduser('~/Desktop/chess-study')
REPO     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT_DIR  = os.path.join(REPO, 'data', 'spec_v5')

ENGINE   = os.path.join(STUDY, 'engine', 'stockfish')
THREADS  = 1
HASH_MB  = 128
MATE_CP  = 10000          # v1 [LOCKED Sec 5.1]
SEED     = 20261001       # SPEC v5 §3, §5
N_SUB    = 2000


def engine_info():
    """Engine name, binary SHA-256 and compiler string, for every log."""
    sha = hashlib.sha256(open(ENGINE, 'rb').read()).hexdigest()
    out = subprocess.run([ENGINE], input='uci\ncompiler\nquit\n', capture_output=True,
                         text=True, timeout=30).stdout
    name = next((l[len('id name '):] for l in out.splitlines() if l.startswith('id name ')), '?')
    comp = [l.strip() for l in out.splitlines() if ':' in l and not l.startswith('option')]
    return {'engine_name': name, 'engine_path': ENGINE, 'engine_sha256': sha,
            'compiler': comp, 'Threads': THREADS, 'Hash_MB': HASH_MB,
            'ucinewgame': 'before every search (python-chess game=object())'}


def load_v1():
    """The 50,021 v1 rows, in a fixed order (game_id, ply) with row_id 0..N-1."""
    fs = sorted(glob.glob(os.path.join(STUDY, 'paper4_results', '**', '*.parquet'), recursive=True))
    v1 = pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True)
    v1['game_id'] = v1['game_id'].astype(str)
    v1 = v1.sort_values(['game_id', 'ply'], kind='mergesort').reset_index(drop=True)
    v1.insert(0, 'row_id', range(len(v1)))
    return v1


def load_pgns():
    """game_id -> PGN text, from the v1 cache."""
    out = {}
    with open(os.path.join(STUDY, 'paper4_cache', 'pgn_index.jsonl')) as f:
        for line in f:
            r = json.loads(line)
            out[str(r['game_id'])] = r['pgn']
    return out


def game_moves(pgn_text):
    g = chess.pgn.read_game(io.StringIO(pgn_text))
    return g.board(), list(g.mainline_moves())


SUCC_MULTIPV = 5          # v2/v3 successor configuration (v3 §3: depth 15, MultiPV 5)


def eval_successor(eng, root_fen, move_uci, depth):
    """Depth-`depth` evaluation of the position after `move_uci`, sent and scored
    exactly as v3's p4_v3_successor_eval._eval_one (terminal rules, sign flip,
    MultiPV 5), additionally persisting each line's full PV, score, nodes and time.
    wp_self_1 is V_depth(move) from the mover's side."""
    from paper4_pilot import wp_from_cp, pov_cp
    import time
    b = chess.Board(root_fen)
    mv = chess.Move.from_uci(move_uci)
    san = b.san(mv)
    b.push(mv)
    r = {'fen': root_fen, 'move_uci': move_uci, 'move_san': san, 'succ_fen': b.fen(),
         'depth': depth, 'multipv': SUCC_MULTIPV, 'terminal': '', 'n_pv': 0,
         'seconds': 0.0, 'nodes': None, 'seldepth': None, 'depth_reached': None}
    for k in range(1, SUCC_MULTIPV + 1):
        r[f'mv_{k}'] = None; r[f'wp_self_{k}'] = float('nan')
        r[f'score_cp_{k}'] = None; r[f'pv_{k}'] = None
    if b.is_checkmate():
        r.update(terminal='checkmate', wp_self_1=100.0); return r
    if b.is_stalemate() or b.is_insufficient_material() or \
       b.is_seventyfive_moves() or b.is_fivefold_repetition():
        r.update(terminal='draw', wp_self_1=50.0); return r
    t0 = time.perf_counter()
    info = eng.analyse(b, chess.engine.Limit(depth=depth), multipv=SUCC_MULTIPV,
                       game=object())                    # ucinewgame before every search
    r['seconds'] = time.perf_counter() - t0
    info = [x for x in (info if isinstance(info, list) else [info]) if 'score' in x]
    if not info:
        r['terminal'] = 'no_pv'; return r
    r.update(n_pv=len(info), nodes=info[0].get('nodes'), seldepth=info[0].get('seldepth'),
             depth_reached=info[0].get('depth'))
    for k, x in enumerate(info, 1):
        cp = pov_cp(x['score'])
        r[f'score_cp_{k}'] = cp                          # side to move in succ position
        r[f'wp_self_{k}'] = wp_from_cp(-cp)              # mover's side, as v3
        pv = x.get('pv') or []
        r[f'mv_{k}'] = pv[0].uci() if pv else None
        r[f'pv_{k}'] = ' '.join(m.uci() for m in pv)
    return r


def load_existing_successors():
    """v2/v3 depth-15 evaluations of successor positions (v3 table, identical
    configuration to v2). Keyed by (game_id, ply, move_san)."""
    fs = sorted(glob.glob(os.path.join(STUDY, 'p4_v3_successor_lines', '*.parquet')))
    s = pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True)
    s['game_id'] = s['game_id'].astype(str)
    return s
