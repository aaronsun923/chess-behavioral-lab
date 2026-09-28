#!/usr/bin/env python3
"""
p5_pilot.py — SPEC v5 §5 pilot, as instructed on 2026-09-24. Stages, run in order,
one engine job at a time:

    python3 code/p5_pilot.py pv12     # re-evaluate v2/v3 positions after best_12 (PV), reproduction check
    python3 code/p5_pilot.py evals12  # §4(a), §4(c), §4(b) at d = 12
    python3 code/p5_pilot.py sub4     # subsample: depth 15 after best_4 (incl. PV re-evaluations, check), depth 20 after h, best_15, best_4
    python3 code/p5_pilot.py report   # quantities and reports/spec_v5_pilot.md; no engine

best_15 := best_15_singlepv. V15(x) = wp_self_1 of the depth-15 MultiPV-5 evaluation
of the position after x (v2/v3 stored value where it exists; terminal positions by
rule: checkmate 100, draw 50). Nothing from §6 or §7.
"""
import os, sys, json, time, logging

import numpy as np
import pandas as pd
import chess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p5_common as C
import p5_evals as EV

K = 6                      # HORIZON k [LOCKED §4], initial value
PIECE = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9}
BATCH_LOG = os.path.join(EV.EVAL_DIR, 'pilot_batches.json')

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s',
                    handlers=[logging.StreamHandler(),
                              logging.FileHandler(os.path.join(EV.EVAL_DIR, 'evals.log'))])
log = logging.getLogger('p5pilot')


# ------------------------------------------------------------------ inputs
def san2uci(fen, san):
    return chess.Board(fen).parse_san(san).uci()


def load_rows():
    r = pd.read_parquet(os.path.join(C.OUT_DIR, 'root_choices.parquet'))
    r['h'] = [san2uci(f, s) for f, s in zip(r.fen, r.move_played)]
    r['b15_mpv'] = [san2uci(f, s) for f, s in zip(r.fen, r.move_engine_best)]
    r['b15'] = r['best_15_singlepv']
    r['b4'], r['b12'] = r['best_4'], r['best_12']
    v1 = C.load_v1()[['row_id', 'wp_best', 'gap_12', 'spread_15', 'n_legal', 'n_reasonable',
                      'eval_volatility', 'time_pressure', 'player_elo']]
    return r.merge(v1, on='row_id')


def load_existing(r):
    """v2/v3 depth-15 successor evaluations keyed by (row_id, move_uci)."""
    s = C.load_existing_successors()
    key = r.set_index(['game_id', 'ply'])[['row_id', 'fen']].rename(columns={'fen': 'fen_v1'})
    s = s.join(key, on=['game_id', 'ply'])
    assert (s.fen == s.fen_v1).all()
    s['move_uci'] = [san2uci(f, m) for f, m in zip(s.fen, s.move_san)]
    s['v15_old'] = s['wp_self_opp_best_recomp']       # = wp_self_1; terminal: 100 / 50
    return s[['row_id', 'game_id', 'ply', 'which_move', 'move_uci', 'v15_old', 'mv_1', 'terminal']] \
        .rename(columns={'mv_1': 'mv1_old', 'terminal': 'terminal_old'})


def task_df(rows, col, depth, item):
    return pd.DataFrame({'row_id': rows.row_id.values, 'game_id': rows.game_id.values,
                         'ply': rows.ply.values, 'fen': rows.fen.values,
                         'move_uci': rows[col].values, 'depth': depth, 'item': item})


def record_batch(tag, n, wall):
    b = json.load(open(BATCH_LOG)) if os.path.exists(BATCH_LOG) else {}
    b[tag] = {'tasks': n, 'wall_seconds': wall, 'finished_utc': pd.Timestamp.utcnow().isoformat()}
    json.dump(b, open(BATCH_LOG, 'w'), indent=2)


# ------------------------------------------------------------------ reproduction check
def repro_check(r, ex):
    """Store depth-15 evaluations of positions that v2/v3 also evaluated: wp_self_1 and
    mv_1 must equal the stored v2/v3 values exactly."""
    st = EV.load_store()
    st = st[st.depth == 15]
    m = st.merge(ex, on=['row_id', 'move_uci'], how='inner')
    ok_v = (m.wp_self_1 == m.v15_old) | (m.wp_self_1.isna() & m.v15_old.isna())
    ok_m = (m.mv_1 == m.mv1_old) | (m.mv_1.isna() & m.mv1_old.isna())
    bad = m[~(ok_v & ok_m)]
    return m, bad


def stop_if_mismatch(r, ex):
    m, bad = repro_check(r, ex)
    log.info('reproduction check: %d re-evaluated v2/v3 positions, %d mismatches', len(m), len(bad))
    if len(bad):
        cols = ['row_id', 'game_id', 'ply', 'move_uci', 'which_move', 'v15_old', 'wp_self_1', 'mv1_old', 'mv_1']
        p = os.path.join(C.OUT_DIR, 'repro_mismatches.csv')
        bad[cols].to_csv(p, index=False)
        print(bad[cols].to_string())
        raise SystemExit(f'STOP: {len(bad)} reproduction mismatches, listed in {p}')


# ------------------------------------------------------------------ stages
def stage_pv12(nproc):
    r = load_rows(); ex = load_existing(r)
    ek = set(zip(ex.row_id, ex.move_uci))
    sel = r[(r.b12 != r.b15) & np.array([(a, b) in ek for a, b in zip(r.row_id, r.b12)])]
    t = task_df(sel, 'b12', 15, 'pv_d12')
    t = t[~t.merge(ex, on=['row_id', 'move_uci'], how='left').terminal_old.fillna('').ne('').values]
    log.info('PV re-evaluations at d = 12: %d positions', len(t))
    wall = EV.run_tasks(t, 'pilot_pv12', nproc, 'SPEC v5 study evaluation; PV re-evaluation of a v2/v3 position')
    record_batch('pilot_pv12', len(t), wall)
    stop_if_mismatch(r, ex)


def stage_evals12(nproc):
    r = load_rows(); ex = load_existing(r)
    ek = set(zip(ex.row_id, ex.move_uci))
    parts = [task_df(r[r.h == r.b15_mpv], 'h', 15, 'a'),
             task_df(r[r.b15 != r.b15_mpv], 'b15', 15, 'c'),
             task_df(r[(r.b12 != r.h) & (r.b12 != r.b15)], 'b12', 15, 'b12')]
    t = pd.concat(parts, ignore_index=True)
    t = t[[(a, b) not in ek for a, b in zip(t.row_id, t.move_uci)]]
    wall = EV.run_tasks(t, 'pilot_d15', nproc)
    record_batch('pilot_d15', len(t.drop_duplicates(['row_id', 'move_uci'])), wall)
    stop_if_mismatch(r, ex)


def stage_sub4(nproc):
    r = load_rows(); ex = load_existing(r)
    ek = set(zip(ex.row_id, ex.move_uci))
    sub = pd.read_csv(os.path.join(C.OUT_DIR, 'subsample_ids.csv'))
    s = r[r.row_id.isin(sub.row_id)]
    # depth 15 after best_4: every subsample row with best_4 != best_15 needs a stored
    # evaluation with PV (HORIZON); positions v2/v3 evaluated are re-evaluated and checked.
    t = task_df(s[s.b4 != s.b15], 'b4', 15, 'b4_sub')
    t = t[~t.merge(ex, on=['row_id', 'move_uci'], how='left').terminal_old.fillna('').ne('').values]
    wall = EV.run_tasks(t, 'pilot_sub_d15', nproc)
    record_batch('pilot_sub_d15', len(t), wall)
    stop_if_mismatch(r, ex)
    # depth 20 after h, best_15, best_4, distinct per row
    t20 = pd.concat([task_df(s, 'h', 20, 'd'), task_df(s, 'b15', 20, 'd'), task_df(s, 'b4', 20, 'd')],
                    ignore_index=True).drop_duplicates(EV.KEY)
    wall = EV.run_tasks(t20, 'pilot_sub_d20', nproc)
    record_batch('pilot_sub_d20', len(t20), wall)


# ------------------------------------------------------------------ quantities
def material(b):
    return sum(v * (len(b.pieces(p, chess.WHITE)) - len(b.pieces(p, chess.BLACK))) for p, v in PIECE.items())


def horizon(succ_fen, pv, k=K):
    """§4 HORIZON on the depth-15 PV from P0 = position after best_d.
    Returns (HORIZON, flag): flag '' | 'pv_shorter_than_k' | 'forcing_to_pv_end' | 'no_pv'.
    Pq = first position at PV ply >= k reached by a move neither capture nor check; if the
    PV ends first, Pq = the last PV position (flagged)."""
    if not isinstance(pv, str) or not pv:
        return np.nan, 'no_pv'
    b = chess.Board(succ_fen); m0 = material(b)
    check_k = False; mq = None
    moves = pv.split()
    for i, u in enumerate(moves, 1):
        mv = chess.Move.from_uci(u)
        cap, chk = b.is_capture(mv), b.gives_check(mv)
        if i <= k and chk:
            check_k = True
        b.push(mv)
        if i >= k and not cap and not chk:
            mq = material(b); break
    flag = ''
    if mq is None:
        mq = material(b)
        flag = 'pv_shorter_than_k' if len(moves) < k else 'forcing_to_pv_end'
    return int(check_k or mq != m0), flag


def values(r):
    """Per (row_id, move_uci): V15, V20, PV-1 and successor FEN."""
    ex = load_existing(r)
    st = EV.load_store()
    s15 = st[st.depth == 15][['row_id', 'move_uci', 'wp_self_1', 'pv_1', 'succ_fen', 'terminal']]
    v15 = ex[['row_id', 'move_uci', 'v15_old']].merge(s15, on=['row_id', 'move_uci'], how='outer')
    v15['V15'] = v15.v15_old.where(v15.v15_old.notna(), v15.wp_self_1)
    s20 = st[st.depth == 20][['row_id', 'move_uci', 'wp_self_1', 'terminal']] \
        .rename(columns={'wp_self_1': 'V20', 'terminal': 'terminal20'})
    return v15, s20


def attach(r, v15, col, name):
    x = r[['row_id', col]].merge(v15[['row_id', 'move_uci', 'V15']], left_on=['row_id', col],
                                 right_on=['row_id', 'move_uci'], how='left')
    r[name] = x['V15'].values
    return r


def boot(games, cols_fn, n=2000, seed=C.SEED):
    """Game-clustered percentile bootstrap. games: array of game ids per row;
    cols_fn(w_rows) -> statistic given per-row weights (multiplicity of each row's game)."""
    g, gi = np.unique(games, return_inverse=True)
    rng = np.random.default_rng(seed)
    out = np.empty(n)
    for b in range(n):
        wg = np.bincount(rng.integers(0, len(g), len(g)), minlength=len(g))
        out[b] = cols_fn(wg[gi].astype(float))
    return np.percentile(out, [2.5, 97.5])


def wmean(x, w):
    return (x * w).sum() / w.sum()


def dist_row(x):
    q = np.percentile(x, np.arange(10, 100, 10))
    return {'n': len(x), 'mean': x.mean(), 'sd': x.std(ddof=1), 'min': x.min(), 'max': x.max(),
            **{f'p{10 * (i + 1)}': v for i, v in enumerate(q)}}


def stage_report():
    r = load_rows(); ex = load_existing(r)
    v15, s20 = values(r)
    for col, name in [('h', 'V_h'), ('b15', 'V_b15'), ('b12', 'V_b12'), ('b4', 'V_b4')]:
        r = attach(r, v15, col, name)
    N = len(r)
    sub_ids = pd.read_csv(os.path.join(C.OUT_DIR, 'subsample_ids.csv')).row_id
    pvlook = v15.set_index(['row_id', 'move_uci'])[['pv_1', 'succ_fen']]

    # ---------- (a) depth 12, all rows
    miss12 = int(r[['V_h', 'V_b15', 'V_b12']].isna().any(axis=1).sum())
    r['L_h'] = r.V_b15 - r.V_h
    r['e_12'] = r.V_b15 - r.V_b12
    r['I_12'] = r.V_h - r.V_b12
    ok = r.dropna(subset=['e_12', 'I_12'])
    E12 = ok.e_12.mean()
    E12_ci = boot(ok.game_id.values, lambda w: wmean(ok.e_12.values, w))
    dis = r[r.b12 != r.b15].copy()
    hz = [horizon(*pvlook.loc[(i, m)].values[::-1]) if (i, m) in pvlook.index else (np.nan, 'not_evaluated')
          for i, m in zip(dis.row_id, dis.b12)]
    dis['HORIZON'] = [h for h, _ in hz]; dis['hflag'] = [f for _, f in hz]
    agree = r.b15 == r.b15_mpv

    # ---------- reproduction check
    m, bad = repro_check(r, ex)

    # ---------- (b) depth 4, subsample
    s = r[r.row_id.isin(sub_ids)].copy()
    s['e_4'] = s.V_b15 - s.V_b4
    s['I_4'] = s.V_h - s.V_b4
    for col, name in [('h', 'V20_h'), ('b15', 'V20_b15'), ('b4', 'V20_b4')]:
        x = s[['row_id', col]].merge(s20, left_on=['row_id', col], right_on=['row_id', 'move_uci'], how='left')
        term = x.terminal20.fillna('').ne('').values
        s[name] = np.where(term, np.nan, x.V20.values)
    s['n_h'] = s.V20_h - s.V_h
    s['n15'] = s.V20_b15 - s.V_b15
    s['n4'] = s.V20_b4 - s.V_b4
    sd_e4 = s.e_4.std(ddof=1)
    bound = 0.25 * sd_e4
    sds = {t: s[c].dropna() for t, c in [('h', 'n_h'), ('best_15', 'n15'), ('best_4', 'n4')]}
    max_sd = max(v.std(ddof=1) for v in sds.values())
    d4 = s[s.b4 != s.b15].copy()
    hz4 = [horizon(*pvlook.loc[(i, mv)].values[::-1]) if (i, mv) in pvlook.index else (np.nan, 'not_evaluated')
           for i, mv in zip(d4.row_id, d4.b4)]
    d4['HORIZON'] = [h for h, _ in hz4]; d4['hflag'] = [f for _, f in hz4]
    hr = d4.dropna(subset=['HORIZON', 'n4'])
    h1, h0 = hr[hr.HORIZON == 1], hr[hr.HORIZON == 0]
    hdiff = h1.n4.mean() - h0.n4.mean()
    is1 = (hr.HORIZON == 1).values.astype(float); nv = hr.n4.values
    hdiff_ci = boot(hr.game_id.values, lambda w: wmean(nv, w * is1) - wmean(nv, w * (1 - is1)))
    bb = s.dropna(subset=['n15', 'e_4'])
    b_4 = bb.n15.var(ddof=1) / bb.e_4.var(ddof=1)
    X = s.assign(wp2=s.wp_best ** 2)
    xc = ['V_b15', 'wp_best', 'wp2', 'gap_12', 'spread_15', 'n_legal', 'n_reasonable',
          'eval_volatility', 'time_pressure', 'player_elo']
    lr = X.dropna(subset=xc + ['V_b4', 'n4'])
    A = np.column_stack([np.ones(len(lr))] + [lr[c].values for c in xc])
    beta, *_ = np.linalg.lstsq(A, lr.V_b4.values, rcond=None)
    u4 = lr.V_b4.values - A @ beta
    var_n4, var_u4 = lr.n4.var(ddof=1), np.var(u4, ddof=1)
    lam4 = 1 - var_n4 / var_u4

    # ---------- write
    L = []; P = L.append
    f = lambda x: f'{x:.4f}'
    P('# SPEC v5 pilot\n')
    P('Spec: `specs/paper4_spec_v5.md` at 6d25e7b (LOCKED). §5 pilot, run as instructed on 2026-09-24. '
      'best_15 = best_15_singlepv; V = depth-15 win probability (0–100, mover\'s side) of the position after the move, '
      'MultiPV 5, Threads 1, Hash 128, ucinewgame per search (pre-run count §1). WP points throughout. '
      'Bootstrap intervals: game-clustered percentile, 2,000 draws, seed 20261001. Nothing from §6 or §7.\n')

    P('## 1. Reproduction check (PV re-evaluations of v2/v3 positions)\n')
    P('| Item | Value |\n|---|---|')
    P(f'| v2/v3 positions re-evaluated in the pilot | {len(m):,} |')
    P(f'| after best_12, rows with best_12 ≠ best_15 (pre-run count: 3,423) | {int((m.item == "pv_d12").sum()):,} |')
    P(f'| after best_4, subsample rows with best_4 ≠ best_15 | {int((m.item == "b4_sub").sum()):,} |')
    P(f'| Mismatches in wp_self_1 or mv_1 against the stored v2/v3 values (exact equality) | {len(bad)} |\n')

    P('## 2. Depth 12, all rows: E_12\n')
    P('| Quantity | Value |\n|---|---|')
    P(f'| Rows | {N:,} |')
    P(f'| Rows with a missing V (h, best_15 or best_12) | {miss12:,} |')
    P(f'| E_12 = mean e_12 | {f(E12)} |')
    P(f'| 95% interval | [{f(E12_ci[0])}, {f(E12_ci[1])}] |\n')

    P('## 3. Depth 12: distributions of e_12 and I_12 (all rows; I_12 = e_12 − L_h by identity)\n')
    de, di = dist_row(ok.e_12.values), dist_row(ok.I_12.values)
    keys = ['n', 'mean', 'sd', 'min'] + [f'p{p}' for p in range(10, 100, 10)] + ['max']
    P('| Statistic | e_12 | I_12 |\n|---|---|---|')
    for k in keys:
        P(f"| {k} | {de[k]:,} | {di[k]:,} |" if k == 'n' else f'| {k} | {f(de[k])} | {f(di[k])} |')
    P(f'| share e_12 ≤ 0 | {(ok.e_12 <= 0).mean():.4f} | |')
    P(f'| share e_12 < 0 | {(ok.e_12 < 0).mean():.4f} | |')
    P(f'| share I_12 ≤ 0 | | {(ok.I_12 <= 0).mean():.4f} |\n')

    P('## 4. Depth 12: disagreement rows and HORIZON (k = 6)\n')
    nd = len(dis); hd = dis.dropna(subset=['HORIZON'])
    P('| Quantity | Value |\n|---|---|')
    P(f'| Rows with best_12 ≠ best_15 | {nd:,} / {N:,} = {nd / N:.4f} (§5 threshold 0.05) |')
    P(f'| HORIZON defined | {len(hd):,} |')
    P(f'| HORIZON = 1 | {int(hd.HORIZON.sum()):,} = {hd.HORIZON.mean():.4f} of defined (§4 amendment band: below 0.20 or above 0.80) |')
    for fl, c in dis.hflag.value_counts().items():
        P(f"| Flag: {fl or 'Pq found within the PV'} | {c:,} |")
    P('\nHORIZON implementation: P0 = position after best_12; PV = line 1 of its depth-15 MultiPV-5 evaluation. '
      'A check counts if a PV move among plies 1..6 gives check (best_12 itself is not a PV move). '
      'Pq = the position after the first PV move at ply ≥ 6 that is neither a capture nor a check; if the PV ends first, Pq = the last PV position (flagged). '
      'Material: P=1, N=B=3, R=5, Q=9, White minus Black.\n')

    P('## 5. Depth-15 single-PV / MultiPV agreement and e_12 by agreement\n')
    P('| Rows | N | Mean e_12 |\n|---|---|---|')
    P(f'| All | {len(ok):,} | {f(ok.e_12.mean())} |')
    ag = agree.loc[ok.index]
    P(f'| best_15_singlepv = MultiPV best_15 (agree) | {int(ag.sum()):,} ({agree.mean():.4f} of all rows) | {f(ok.e_12[ag].mean())} |')
    P(f'| best_15_singlepv ≠ MultiPV best_15 (disagree) | {int((~ag).sum()):,} | {f(ok.e_12[~ag].mean())} |\n')

    P('## 6. Depth 4, subsample: V20 − V15 by position type\n')
    P(f'2,000 rows (seed 20261001). Terminal positions excluded.\n')
    P('| Position type | N | Mean V20 − V15 | SD V20 − V15 |\n|---|---|---|---|')
    for t, v in sds.items():
        P(f'| after {t} | {len(v):,} | {f(v.mean())} | {f(v.std(ddof=1))} |')
    P('')

    P('## 7. Depth 4, subsample: SD rule\n')
    P('| Quantity | Value |\n|---|---|')
    P(f'| SD(e_4) on the subsample (N = {s.e_4.notna().sum():,}) | {f(sd_e4)} |')
    P(f'| Bound 0.25 × SD(e_4) | {f(bound)} |')
    P(f'| Largest SD of V20 − V15 (h, best_15, best_4) | {f(max_sd)} |')
    P(f'| Largest SD below bound | {"yes" if max_sd < bound else "no"} |\n')

    P('## 8. Depth 4, subsample: HORIZON rule\n')
    P('| Quantity | Value |\n|---|---|')
    P(f'| Subsample rows with best_4 ≠ best_15 | {len(d4):,} |')
    P(f'| with HORIZON and V20 − V15 at best_4 defined | {len(hr):,} (HORIZON = 1: {len(h1):,}; HORIZON = 0: {len(h0):,}) |')
    for fl, c in d4.hflag.value_counts().items():
        P(f"| HORIZON flag: {fl or 'Pq found within the PV'} | {c:,} |")
    P(f'| Mean V20 − V15 at best_4, HORIZON = 1 | {f(h1.n4.mean())} |')
    P(f'| Mean V20 − V15 at best_4, HORIZON = 0 | {f(h0.n4.mean())} |')
    P(f'| Difference (1 − 0) | {f(hdiff)} |')
    P(f'| 95% interval | [{f(hdiff_ci[0])}, {f(hdiff_ci[1])}] |')
    P(f'| Bound 0.25 × SD(e_4) | {f(bound)} |')
    P(f'| Absolute difference below bound | {"yes" if abs(hdiff) < bound else "no"} |\n')

    P('## 9. Depth 4, subsample: b_4 and λ_4\n')
    P('| Quantity | Value |\n|---|---|')
    P(f'| b_4 = Var(n15) / Var(e_4) (N = {len(bb):,}) | {f(b_4)} |')
    P(f'| Var(n15) | {f(bb.n15.var(ddof=1))} |')
    P(f'| Var(e_4) | {f(bb.e_4.var(ddof=1))} |')
    P(f'| λ_4 = 1 − Var(n4) / Var(u_4) (N = {len(lr):,}) | {f(lam4)} |')
    P(f'| Var(n4) | {f(var_n4)} |')
    P(f'| Var(u_4) | {f(var_u4)} |')
    P(f'| λ_4 ≥ 0.5 (§3 floor) | {"yes" if lam4 >= 0.5 else "no"} |')
    P('\nu_4 = OLS residual of V15(best_4) on an intercept, V15(best_15) and the H1 primary covariates: difficulty = the v3 difficulty features at the mover\'s root '
      '(wp_level = wp_best, wp_level², gap_12, spread_15, n_legal, n_reasonable, eval_volatility), clock = time_pressure, elo = player_elo; '
      'complete cases. Standardization does not change the residual. n15, n4 = V20 − V15 at the best_15 and best_4 positions; Var(n4) on the same rows as u_4.\n')

    P('## 10. Depth 4, subsample: I_4\n')
    i4 = s.I_4.dropna()
    P('| Quantity | Value |\n|---|---|')
    P(f'| N | {len(i4):,} |\n| Mean I_4 | {f(i4.mean())} |\n| SD I_4 | {f(i4.std(ddof=1))} |\n')

    P('## 11. Cost\n')
    bl = json.load(open(BATCH_LOG))
    st = EV.load_store()
    P('| Item | Evaluations | Hours (8 processes) |\n|---|---|---|')
    P('| Pre-run estimate (pre-run count §5): depth 15 | 57,641 | 2.2 |')
    P('| Pre-run estimate: depth 20 | 4,296 | 1.2 |')
    P('| Pre-run estimate: PV re-evaluations (at most) | 14,579 | 0.5 |')
    P('| Pre-run estimate, total | | 3.9 |')
    for tag, b in bl.items():
        x = st[st.batch == tag]
        P(f"| Pilot batch `{tag}`: engine evaluations / terminal (no engine call), measured | {int((x.terminal == '').sum()):,} / {int((x.terminal != '').sum()):,} | {b['wall_seconds'] / 3600:.2f} |")
    P('')
    os.makedirs(os.path.join(C.REPO, 'reports'), exist_ok=True)
    p = os.path.join(C.REPO, 'reports', 'spec_v5_pilot.md')
    open(p, 'w').write('\n'.join(L))
    dis[['row_id', 'b12', 'HORIZON', 'hflag']].to_parquet(os.path.join(C.OUT_DIR, 'pilot_horizon_d12.parquet'), index=False)
    s.to_parquet(os.path.join(C.OUT_DIR, 'pilot_subsample_d4.parquet'), index=False)
    r[['row_id', 'game_id', 'ply', 'h', 'b15', 'b15_mpv', 'b12', 'V_h', 'V_b15', 'V_b12', 'L_h', 'e_12', 'I_12']] \
        .to_parquet(os.path.join(C.OUT_DIR, 'pilot_d12_rows.parquet'), index=False)
    print(open(p).read())


if __name__ == '__main__':
    stage = sys.argv[1]
    nproc = int(sys.argv[2]) if len(sys.argv) > 2 else 8
    {'pv12': lambda: stage_pv12(nproc), 'evals12': lambda: stage_evals12(nproc),
     'sub4': lambda: stage_sub4(nproc), 'report': stage_report}[stage]()
