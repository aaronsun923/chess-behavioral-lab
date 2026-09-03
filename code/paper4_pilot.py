#!/usr/bin/env python3
"""
paper4_pilot.py - Paper 4 pilot: human-engine deviation & complementarity.

Implements SPEC (Paper 4 groundwork), Section 8.1 PILOT ONLY (2000 games,
seed 20260823). All [LOCKED] parameters are taken verbatim from the spec.

Stages (run in order):
    python3 paper4_pilot.py sample     # draw + record the locked game sample
    python3 paper4_pilot.py fetch      # re-download PGNs from Chess.com
    python3 paper4_pilot.py clk        # %clk coverage  (REPORTED FIRST)
    python3 paper4_pilot.py selftest   # sign / perspective tests (Sec 5.1)
    python3 paper4_pilot.py analyze    # engine pass -> parquet shards
    python3 paper4_pilot.py report     # Section 9 deliverables
"""
import os, io, sys, csv, json, time, math, hashlib, argparse, logging
import multiprocessing as mp
from collections import Counter, defaultdict

import numpy as np
import pandas as pd
import chess, chess.pgn, chess.engine

# ---- Paper 1 reuse [LOCKED Sec 2]: middlegame boundary comes from Paper 1 ----
import chess_pipeline_v2 as P1
MIDDLEGAME_START = P1.MIDDLEGAME_START      # 14 (0-indexed ply)
MIDDLEGAME_END   = P1.MIDDLEGAME_END        # 40 (exclusive)
MIN_GAME_PLIES   = MIDDLEGAME_START + 5     # Paper 1 analyze_game() guard

# ---- LOCKED parameters (Sec 3, 5, 8) ----
SEED         = 20260823
N_GAMES      = 2000
DEPTH        = 15
MULTIPV      = 5
THREADS      = 1
HASH_MB      = 128
MATE_CP      = 10000
WINSOR_TOP   = 0.01        # top 1% of WPL, full-sample level
MAX_MG_MOVES = 30          # Sec 4 cap (never binds; see report)

# ---- paths ----
SRC_CSV     = 'analysis_dataset_male_titled_raw.csv'
ENGINE      = os.path.abspath('engine/stockfish')
CACHE_DIR   = 'paper4_cache'
PGN_DIR     = os.path.join(CACHE_DIR, 'pgn')
SAMPLE_CSV  = os.path.join(CACHE_DIR, 'pilot_sample_games.csv')
PGN_INDEX   = os.path.join(CACHE_DIR, 'pgn_index.jsonl')
RESULT_DIR  = 'paper4_results'
N_BUCKETS   = 16
RUN_TAG     = 'run'

UA = {'User-Agent': 'chess-research-paper4/1.0 (academic; contact aaronsun923@gmail.com)'}
REQUEST_DELAY = 0.45
MAX_MONTHS = 30

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
log = logging.getLogger('p4')


# ============================================================ Sec 5.1 WP
def wp_from_cp(cp):
    """[LOCKED Sec 5.1] Lichess win-probability conversion. cp is from the
    side-to-move's perspective; result is 0..100 for the side to move."""
    return 50.0 + 50.0 * (2.0 / (1.0 + math.exp(-0.00368208 * cp)) - 1.0)


def pov_cp(score, mate_cp=MATE_CP):
    """PovScore/Score -> centipawns from the side-to-move's perspective.
    [LOCKED Sec 5.1] mate maps to +/-10000."""
    s = score.relative if hasattr(score, 'relative') else score
    if s.is_mate():
        m = s.mate()
        return mate_cp if m > 0 else -mate_cp
    v = s.score()
    if v is None:
        return 0
    return max(-mate_cp, min(mate_cp, v))


def bucket_of(game_id):
    return int(hashlib.md5(str(game_id).encode()).hexdigest(), 16) % N_BUCKETS


# ============================================================ STAGE: sample
def stage_sample():
    os.makedirs(CACHE_DIR, exist_ok=True)
    df = pd.read_csv(SRC_CSV)
    df['game_id'] = df['url'].str.rsplit('/', n=1).str[-1]
    ids = np.sort(df['game_id'].unique())
    rng = np.random.default_rng(SEED)          # [LOCKED] seed 20260823
    samp = set(rng.choice(ids, size=N_GAMES, replace=False))
    sub = (df[df['game_id'].isin(samp)]
           .drop_duplicates('game_id')[['game_id', 'player_id', 'url',
                                        'time_category', 'eco', 'player_elo']])
    sub = sub.sort_values('game_id').reset_index(drop=True)
    sub.to_csv(SAMPLE_CSV, index=False)
    log.info(f"sampled {len(sub)} games from {len(ids)} unique games; "
             f"{sub.player_id.nunique()} players -> {SAMPLE_CSV}")


# ============================================================ STAGE: fetch
CURVE_JSON = os.path.join(CACHE_DIR, 'id_month_curve.json')

def _midx(m):                      # "YYYY/MM" -> month index
    y, mo = m.split('/'); return int(y) * 12 + int(mo)

def _load_curve():
    if os.path.exists(CURVE_JSON):
        return {int(k): tuple(v) for k, v in json.load(open(CURVE_JSON)).items()}
    return {}

def _predict(curve, gid):
    """Chess.com *live* game ids are globally monotonic in time (verified).
    Map a game id to the month index that most likely contains it."""
    if not curve:
        return None
    for idx, (lo, hi) in curve.items():
        if lo <= gid <= hi:
            return idx
    below = [(hi, idx) for idx, (lo, hi) in curve.items() if hi < gid]
    above = [(lo, idx) for idx, (lo, hi) in curve.items() if lo > gid]
    if below and above:
        (h, i0), (l, i1) = max(below), min(above)
        if l > h:
            frac = (gid - h) / (l - h)
            return int(round(i0 + frac * (i1 - i0)))
        return i0
    if below:  return max(below)[1]
    return min(above)[1]


def stage_fetch(nthread=4, max_tries=8):
    import requests
    from concurrent.futures import ThreadPoolExecutor
    import threading

    os.makedirs(PGN_DIR, exist_ok=True)
    samp = pd.read_csv(SAMPLE_CSV, dtype={'game_id': str})
    need = defaultdict(set)
    for r in samp.itertuples():
        need[r.player_id].add(r.game_id)

    have = set()
    if os.path.exists(PGN_INDEX):
        with open(PGN_INDEX) as f:
            for line in f:
                try: have.add(json.loads(line)['game_id'])
                except Exception: pass
    log.info(f"cache holds {len(have)} games; need {len(samp)}")

    curve = _load_curve()
    lock = threading.Lock()
    out = open(PGN_INDEX, 'a')
    local = threading.local()
    done_players = [0]; missing_total = []

    def sess():
        if not hasattr(local, 's'):
            local.s = requests.Session(); local.s.headers.update(UA)
        return local.s

    def get(url, tries=5):
        for a in range(tries):
            try:
                r = sess().get(url, timeout=180)
                if r.status_code == 429:
                    w = 20 * (a + 1); log.warning(f"429 backoff {w}s"); time.sleep(w); continue
                if r.status_code in (404, 410): return None
                r.raise_for_status()
                return r.json()
            except Exception as e:
                if a == tries - 1: return None
                time.sleep(3 * (a + 1))
        return None

    def do_player(player):
        want = {g for g in need[player] if g not in have}
        if not want:
            return
        arch = get(f"https://api.chess.com/pub/player/{player}/games/archives")
        if not arch:
            with lock: missing_total.extend((player, g, 'no_archives') for g in want)
            return
        avail = [a.rsplit('/games/', 1)[-1] for a in arch.get('archives', [])]
        base = arch['archives'][0].rsplit('/games/', 1)[0] if arch.get('archives') else None
        tried = set()
        while want and len(tried) < max_tries:
            gid = int(min(want, key=lambda x: int(x)))
            with lock:
                p = _predict(curve, gid)
            cands = [m for m in avail if m not in tried]
            if not cands: break
            cand = min(cands, key=lambda m: abs(_midx(m) - p)) if p is not None else cands[-1]
            tried.add(cand)
            data = get(f"{base}/games/{cand}")
            if data is None: continue
            games = data.get('games', [])
            ids = []
            for g in games:
                url = g.get('url') or ''
                if '/live/' not in url: continue
                gi = url.rsplit('/', 1)[-1]
                if gi.isdigit(): ids.append(int(gi))
                if gi in want:
                    rec = {'game_id': gi, 'player_id': player, 'url': url,
                           'pgn': g.get('pgn'), 'time_control': g.get('time_control'),
                           'time_class': g.get('time_class'), 'rated': g.get('rated'),
                           'rules': g.get('rules'),
                           'white': (g.get('white') or {}).get('username'),
                           'black': (g.get('black') or {}).get('username'),
                           'white_rating': (g.get('white') or {}).get('rating'),
                           'black_rating': (g.get('black') or {}).get('rating')}
                    with lock:
                        out.write(json.dumps(rec) + '\n'); out.flush(); have.add(gi)
                    want.discard(gi)
            if ids:
                with lock:
                    i = _midx(cand); lo, hi = min(ids), max(ids)
                    if i in curve:
                        curve[i] = (min(curve[i][0], lo), max(curve[i][1], hi))
                    else:
                        curve[i] = (lo, hi)
            time.sleep(0.15)
        with lock:
            done_players[0] += 1
            if want: missing_total.extend((player, g, 'not_found') for g in want)
            if done_players[0] % 25 == 0:
                log.info(f"[{done_players[0]}/{len(need)}] players | {len(have)} games cached "
                         f"| curve months={len(curve)} | missing={len(missing_total)}")

    players = sorted(need)
    # warm the curve serially on a few players so predictions start good
    for p in players[:3]:
        do_player(p)
    with ThreadPoolExecutor(nthread) as ex:
        list(ex.map(do_player, players[3:]))
    out.close()
    json.dump({str(k): list(v) for k, v in curve.items()}, open(CURVE_JSON, 'w'))
    with open(os.path.join(CACHE_DIR, 'fetch_missing.json'), 'w') as f:
        json.dump(missing_total, f, indent=2)
    log.info(f"fetch done: {len(have)}/{len(samp)} cached, {len(missing_total)} missing")


# ============================================================ STAGE: clk
def parse_tc(tc):
    """Chess.com TimeControl -> (base_seconds, increment_seconds)."""
    if not tc:
        return None, None
    tc = str(tc)
    if '/' in tc:                       # daily, e.g. '1/1209600'
        return None, None
    if '+' in tc:
        b, i = tc.split('+', 1)
        try: return float(b), float(i)
        except Exception: return None, None
    try: return float(tc), 0.0
    except Exception: return None, None


def load_games():
    """Yield (rec, pgn_game) for every cached PGN."""
    with open(PGN_INDEX) as f:
        seen = set()
        for line in f:
            try: d = json.loads(line)
            except Exception: continue
            if d['game_id'] in seen: continue
            seen.add(d['game_id'])
            g = chess.pgn.read_game(io.StringIO(d['pgn'] or ''))
            if g is None: continue
            yield d, g


def game_clk_status(g):
    """Return (n_plies, n_with_clk) over the WHOLE game."""
    n = w = 0
    node = g
    while node.variations:
        node = node.variation(0)
        n += 1
        if node.clock() is not None:
            w += 1
    return n, w


def stage_clk():
    samp = pd.read_csv(SAMPLE_CSV, dtype={'game_id': str})
    rows = []
    for d, g in load_games():
        n, w = game_clk_status(g)
        base, inc = parse_tc(d.get('time_control'))
        # middlegame-window plies present in this game
        mg = max(0, min(n, MIDDLEGAME_END) - MIDDLEGAME_START)
        rows.append({'game_id': d['game_id'], 'plies': n, 'plies_with_clk': w,
                     'full_clk': (n > 0 and w == n), 'any_clk': w > 0,
                     'base': base, 'inc': inc, 'time_class': d.get('time_class'),
                     'mg_plies': mg, 'usable': n >= MIN_GAME_PLIES})
    c = pd.DataFrame(rows)
    c.to_csv(os.path.join(CACHE_DIR, 'clk_coverage.csv'), index=False)
    n = len(c)
    print("\n=== %clk COVERAGE (pilot sample) ===")
    print(f"games sampled (locked seed {SEED}) : {len(samp)}")
    print(f"games retrieved & parsed          : {n}")
    if n:
        print(f"games with %clk on EVERY ply      : {c.full_clk.sum()}  ({100*c.full_clk.mean():.2f}%)")
        print(f"games with %clk on >=1 ply        : {c.any_clk.sum()}  ({100*c.any_clk.mean():.2f}%)")
        print(f"games with NO %clk (EXCLUDED from")
        print(f"  time-pressure analyses, Sec 5.4): {(~c.any_clk).sum()}  ({100*(~c.any_clk).mean():.2f}%)")
        print(f"games with parseable base time    : {c.base.notna().sum()}  ({100*c.base.notna().mean():.2f}%)")
        pl = c.plies.sum(); pw = c.plies_with_clk.sum()
        print(f"ply-level: {pw}/{pl} plies carry %clk ({100*pw/max(pl,1):.2f}%)")
        print(f"games too short for Paper1 window (<{MIN_GAME_PLIES} plies): {(~c.usable).sum()}")
    return c


# ============================================================ STAGE: selftest
def stage_selftest():
    """[Sec 5.1] Explicit perspective/sign tests. A sign error here inverts
    every conclusion in the paper, so these must pass before analysis."""
    eng = chess.engine.SimpleEngine.popen_uci(ENGINE)
    eng.configure({'Threads': THREADS, 'Hash': HASH_MB})
    ok = True

    def ev(fen):
        b = chess.Board(fen)
        info = eng.analyse(b, chess.engine.Limit(depth=DEPTH),
                           multipv=MULTIPV)
        return b, info, wp_from_cp(pov_cp(info[0]['score']))

    print("\n=== SIGN / PERSPECTIVE SELF-TEST ===")
    # 1) WP(0 cp) == 50
    t = abs(wp_from_cp(0) - 50.0) < 1e-9
    print(f"[{'PASS' if t else 'FAIL'}] WP(0cp) == 50            -> {wp_from_cp(0):.4f}"); ok &= t
    t = wp_from_cp(100) > 50 and wp_from_cp(-100) < 50
    print(f"[{'PASS' if t else 'FAIL'}] WP(+100)>50>WP(-100)     -> {wp_from_cp(100):.2f} / {wp_from_cp(-100):.2f}"); ok &= t
    t = abs(wp_from_cp(MATE_CP) - 100.0) < 1e-6 and abs(wp_from_cp(-MATE_CP)) < 1e-6
    print(f"[{'PASS' if t else 'FAIL'}] mate maps to 100/0       -> {wp_from_cp(MATE_CP):.6f} / {wp_from_cp(-MATE_CP):.6f}"); ok &= t

    # 2) same material-lopsided position, flipping only side to move
    # Same board, only the side to move differs: the winning side must be high,
    # the losing side low. (Values are WP for whoever is to move.)
    wtm = "4k3/8/8/8/8/8/8/3QK3 w - - 0 1"   # White up a queen, White to move
    btm = "4k3/8/8/8/8/8/8/3QK3 b - - 0 1"   # same board, Black to move
    _, _, wp_w = ev(wtm); _, _, wp_b = ev(btm)
    t = wp_w > 50 and wp_b < 50 and wp_w > wp_b
    print(f"[{'PASS' if t else 'FAIL'}] side-to-move POV flips   -> W-to-move {wp_w:.2f} vs B-to-move {wp_b:.2f}"); ok &= t

    bwtm = "3qk3/8/8/8/8/8/8/4K3 w - - 0 1"   # Black up a queen, White to move
    _, _, wp2 = ev(bwtm)
    t = wp2 < 50
    print(f"[{'PASS' if t else 'FAIL'}] losing side-to-move <50  -> {wp2:.2f}"); ok &= t

    # True colour mirror on a NON-mate middlegame position (mate scores make the
    # bare-king positions asymmetric at fixed depth). board.mirror() swaps
    # colours, flips ranks and flips the side to move, so WP for the side to
    # move must agree. This is the strongest guard against a sign flip.
    mfen = "r1bq1rk1/pp2ppbp/2np1np1/8/2BNP3/2N1B3/PPP2PPP/R2Q1RK1 w - - 0 1"
    _, _, wp_o = ev(mfen)
    _, _, wp_m = ev(chess.Board(mfen).mirror().fen())
    t = abs(wp_m - wp_o) < 2.0
    print(f"[{'PASS' if t else 'FAIL'}] colour mirror agrees     -> {wp_o:.2f} vs {wp_m:.2f}"); ok &= t

    # 3) WPL of the engine's own best move must be ~0, and a blunder must be > 0
    b = chess.Board("r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5Q2/PPPP1PPP/RNB1K1NR b KQkq - 0 1")
    info = eng.analyse(b, chess.engine.Limit(depth=DEPTH), multipv=MULTIPV)
    best = info[0]['pv'][0]
    wp_best = wp_from_cp(pov_cp(info[0]['score']))
    def wp_of(move):
        b2 = b.copy(); b2.push(move)
        i2 = eng.analyse(b2, chess.engine.Limit(depth=DEPTH))
        return wp_from_cp(-pov_cp(i2['score']))     # negate: child is opponent POV
    wpl_best = wp_best - wp_of(best)
    blunder = chess.Move.from_uci('a7a6')           # allows Qxf7#
    wpl_bad = wp_best - wp_of(blunder)
    t = abs(wpl_best) < 3.0
    print(f"[{'PASS' if t else 'FAIL'}] WPL(engine best) ~= 0    -> {wpl_best:.3f}"); ok &= t
    t = wpl_bad > 20.0
    print(f"[{'PASS' if t else 'FAIL'}] WPL(blunder a6) large    -> {wpl_bad:.2f}"); ok &= t
    t = wpl_bad > wpl_best
    print(f"[{'PASS' if t else 'FAIL'}] blunder WPL > best WPL"); ok &= t
    eng.quit()
    print(f"\nSELF-TEST {'PASSED' if ok else 'FAILED'}")
    return ok


# ============================================================ STAGE: analyze
_ENG = None

def _init_worker():
    global _ENG
    _ENG = chess.engine.SimpleEngine.popen_uci(ENGINE)
    # [LOCKED Sec 3] Threads=1, Hash=128 per worker; parallelism via processes
    _ENG.configure({'Threads': THREADS, 'Hash': HASH_MB})


def _analyse_root(board):
    """[LOCKED Sec 3] fixed depth 15, MultiPV 5, independent search."""
    return _ENG.analyse(board, chess.engine.Limit(depth=DEPTH),
                        multipv=MULTIPV, game=object())   # game=object() -> no tree reuse


def _wp_after(board, move):
    """WP of `move` from the mover's POV, via a depth-15 search of the child."""
    b2 = board.copy(stack=False); b2.push(move)
    if b2.is_checkmate():
        return wp_from_cp(MATE_CP)
    if b2.is_stalemate() or b2.is_insufficient_material():
        return wp_from_cp(0)
    i = _ENG.analyse(b2, chess.engine.Limit(depth=DEPTH), game=object())
    return wp_from_cp(-pov_cp(i['score']))


def _process_game(rec):
    """Return (rows, n_positions, engine_seconds, error_or_None)."""
    try:
        g = chess.pgn.read_game(io.StringIO(rec['pgn'] or ''))
        if g is None:
            return [], 0, 0.0, 'unparseable_pgn'
        moves, clocks = [], []
        node = g
        while node.variations:
            node = node.variation(0)
            moves.append(node.move); clocks.append(node.clock())
        n = len(moves)
        if n < MIN_GAME_PLIES:                      # Paper 1 guard
            return [], 0, 0.0, 'too_short'

        h = g.headers
        result = h.get('Result', '*')
        w_elo = pd.to_numeric(h.get('WhiteElo'), errors='coerce')
        b_elo = pd.to_numeric(h.get('BlackElo'), errors='coerce')
        w_id, b_id = h.get('White', ''), h.get('Black', '')
        base, inc = parse_tc(rec.get('time_control') or h.get('TimeControl'))
        game_has_clk = any(c is not None for c in clocks)

        # [LOCKED Sec 4] all middlegame moves, both sides. Two extra "context"
        # plies before the window are evaluated ONLY to define eval_volatility
        # at the window's first two plies; they are not emitted as rows.
        lo_ctx = max(0, MIDDLEGAME_START - 2)
        hi = min(n, MIDDLEGAME_END)
        eval_plies = list(range(lo_ctx, hi))
        window = [i for i in eval_plies if i >= MIDDLEGAME_START]
        # [LOCKED Sec 4] cap of 30, sampled at even intervals if exceeded
        if len(window) > MAX_MG_MOVES:
            idx = np.linspace(0, len(window) - 1, MAX_MG_MOVES).round().astype(int)
            keep = {window[k] for k in sorted(set(idx))}
            eval_plies = [i for i in eval_plies if i < MIDDLEGAME_START or i in keep]
            window = sorted(keep)

        board = g.board()
        wp_pos = {}          # ply -> WP of the position (side-to-move POV)
        rows = []
        t_eng = 0.0; npos = 0
        ts = pd.Timestamp.utcnow().isoformat()

        for i, mv in enumerate(moves):
            if i >= hi:
                break
            if i not in eval_plies:
                board.push(mv); continue

            stm = board.turn
            t0 = time.perf_counter()
            info = _analyse_root(board)
            t_eng += time.perf_counter() - t0; npos += 1
            if not isinstance(info, list):
                info = [info]
            info = [x for x in info if 'pv' in x and x['pv']]
            if not info:
                board.push(mv); continue

            wps = [wp_from_cp(pov_cp(x['score'])) for x in info]
            wp_best = wps[0]
            wp_pos[i] = wp_best

            if i in window:
                n_pv = len(wps)
                gap_12   = wp_best - wps[1] if n_pv >= 2 else np.nan
                spread_15 = wp_best - wps[-1] if n_pv >= 2 else np.nan
                # [Sec 5.3] right-censored at 5 -- flagged in the report
                n_reasonable = int(sum(1 for w in wps if wp_best - w <= 5.0))
                n_legal = board.legal_moves.count()

                pv_moves = [x['pv'][0] for x in info]
                if mv in pv_moves:
                    wp_played = wps[pv_moves.index(mv)]
                    played_in_pv = True
                else:
                    t1 = time.perf_counter()
                    wp_played = _wp_after(board, mv)
                    t_eng += time.perf_counter() - t1; npos += 1
                    played_in_pv = False

                vol = (abs(wp_best - wp_pos[i - 2])
                       if (i - 2) in wp_pos else np.nan)

                clk = clocks[i]
                tp = (clk / base) if (clk is not None and base) else np.nan

                if stm == chess.WHITE:
                    pid, oid, pelo, oelo = w_id, b_id, w_elo, b_elo
                    res = {'1-0': 1.0, '0-1': 0.0, '1/2-1/2': 0.5}.get(result, np.nan)
                else:
                    pid, oid, pelo, oelo = b_id, w_id, b_elo, w_elo
                    res = {'1-0': 0.0, '0-1': 1.0, '1/2-1/2': 0.5}.get(result, np.nan)

                rows.append({
                    'game_id': rec['game_id'], 'ply': i,
                    'side_to_move': 'white' if stm == chess.WHITE else 'black',
                    'player_id': pid, 'opponent_id': oid,
                    'player_elo': pelo, 'opponent_elo': oelo,
                    'elo_diff': (pelo - oelo) if pd.notna(pelo) and pd.notna(oelo) else np.nan,
                    'fen': board.fen(),
                    'fen_hash': hashlib.md5(board.epd().encode()).hexdigest()[:16],
                    'move_played': board.san(mv),
                    'move_engine_best': board.san(pv_moves[0]),
                    'wp_best': wp_best, 'wp_played': wp_played,
                    'WPL_raw': max(0.0, wp_best - wp_played),
                    'gap_12': gap_12, 'spread_15': spread_15,
                    'n_legal': n_legal, 'n_reasonable': n_reasonable,
                    'n_pv': n_pv, 'played_in_pv': played_in_pv,
                    'eval_volatility': vol,
                    'time_pressure': tp, 'has_clk': clk is not None,
                    'game_has_clk': game_has_clk,
                    'base_time': base, 'increment': inc,
                    'time_class': rec.get('time_class'),
                    'game_result': result, 'result_for_side_to_move': res,
                    'sf_version': SF_VERSION, 'depth': DEPTH, 'multipv': MULTIPV,
                    'analysis_timestamp': ts,
                })
            board.push(mv)
        return rows, npos, t_eng, None
    except Exception as e:
        return [], 0, 0.0, f'error:{type(e).__name__}:{e}'


SF_VERSION = 'Stockfish 18'

def _done_pairs():
    """[LOCKED Sec 6] resumability on (game_id, ply)."""
    done = set(); games = set()
    if not os.path.isdir(RESULT_DIR):
        return done, games
    for root, _, files in os.walk(RESULT_DIR):
        for fn in files:
            if fn.endswith('.parquet'):
                try:
                    d = pd.read_parquet(os.path.join(root, fn), columns=['game_id', 'ply'])
                    done |= set(map(tuple, d.values))
                    games |= set(d.game_id.unique())
                except Exception:
                    pass
    return done, games


def stage_analyze(nproc):
    # unique per-run tag: a resumed run must never reuse an earlier run's
    # filenames, or it silently overwrites shards the resume just skipped.
    global SF_VERSION, RUN_TAG
    RUN_TAG = f'{int(time.time())}-{os.getpid()}'
    e = chess.engine.SimpleEngine.popen_uci(ENGINE)
    SF_VERSION = e.id.get('name', 'Stockfish ?'); e.quit()
    os.makedirs(RESULT_DIR, exist_ok=True)

    recs = []
    seen = set()
    with open(PGN_INDEX) as f:
        for line in f:
            try: d = json.loads(line)
            except Exception: continue
            if d['game_id'] in seen: continue
            seen.add(d['game_id']); recs.append(d)

    _, done_games = _done_pairs()
    todo = [r for r in recs if r['game_id'] not in done_games]
    log.info(f"{len(recs)} cached games; {len(done_games)} already done; {len(todo)} to do "
             f"on {nproc} processes ({SF_VERSION}, depth {DEPTH}, MultiPV {MULTIPV})")
    if not todo:
        return

    buf = defaultdict(list); errs = Counter(); fails = []
    tot_pos = 0; tot_eng = 0.0; ngames = 0
    t_start = time.time()
    chunk = 0

    def flush():
        nonlocal chunk
        for b, rows in buf.items():
            if not rows: continue
            d = os.path.join(RESULT_DIR, f'bucket={b:02d}'); os.makedirs(d, exist_ok=True)
            pd.DataFrame(rows).to_parquet(os.path.join(d, f'part-{RUN_TAG}-{chunk:04d}.parquet'), index=False)
        buf.clear(); chunk += 1

    with mp.Pool(nproc, initializer=_init_worker) as pool:
        for rec, (rows, npos, teng, err) in zip(todo, pool.imap(_process_game, todo, chunksize=1)):
            ngames += 1; tot_pos += npos; tot_eng += teng
            if err:
                errs[err.split(':')[0] if err.startswith('error') else err] += 1
                fails.append({'game_id': rec['game_id'], 'reason': err})
            for r in rows:
                buf[bucket_of(r['game_id'])].append(r)
            if ngames % 100 == 0:
                el = time.time() - t_start
                log.info(f"{ngames}/{len(todo)} games | {tot_pos} pos | "
                         f"{1000*tot_eng/max(tot_pos,1):.1f} ms/pos (engine, 1 core) | "
                         f"{el/60:.1f} min elapsed | ETA {(el/ngames)*(len(todo)-ngames)/60:.1f} min")
            if ngames % 200 == 0:
                flush()
    flush()
    with open(os.path.join(CACHE_DIR, 'analysis_failures.json'), 'w') as f:
        json.dump({'counts': dict(errs), 'failures': fails}, f, indent=2)
    el = time.time() - t_start
    stats = {'games': ngames, 'positions': tot_pos,
             'engine_seconds': tot_eng, 'wall_seconds': el,
             'ms_per_position_single_core': 1000 * tot_eng / max(tot_pos, 1),
             'nproc': nproc, 'sf_version': SF_VERSION,
             'errors': dict(errs)}
    with open(os.path.join(CACHE_DIR, 'analysis_stats.json'), 'w') as f:
        json.dump(stats, f, indent=2)
    log.info(f"DONE {json.dumps(stats)}")


# ============================================================ CLI
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('stage', choices=['sample', 'fetch', 'clk', 'selftest',
                                      'analyze', 'report'])
    ap.add_argument('--nproc', type=int, default=8)
    ap.add_argument('--nthread', type=int, default=4)
    a = ap.parse_args()
    if a.stage == 'sample':   stage_sample()
    elif a.stage == 'fetch':  stage_fetch(a.nthread)
    elif a.stage == 'clk':    stage_clk()
    elif a.stage == 'selftest':
        sys.exit(0 if stage_selftest() else 1)
    elif a.stage == 'analyze': stage_analyze(a.nproc)
    elif a.stage == 'report':
        import paper4_report; paper4_report.build()


if __name__ == '__main__':
    main()
