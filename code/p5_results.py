#!/usr/bin/env python3
"""
p5_results.py — SPEC v5 §6–§8 analysis (instruction of 2026-09-27), spec at b735062
(LOCKED + Amendment A1 + A1.4 outcome). Ruler V20, anchor best_20, admitted depths
{2, 4, 8}; 12 and 15 descriptive only. fit_mixed_v2 is the only mixed-model estimator.

    python3 code/p5_results.py prep            # item 0: row table, missing counts, A1.5 shares, runtime gate
    python3 code/p5_results.py points GROUP    # full-data fit_mixed_v2 fits (five-optimizer sweep) of a group
    python3 code/p5_results.py boot GROUP N    # game-clustered bootstrap draws 0..N-1 on 8 processes, resumable
Groups: h1p (H1 primary), h2 (H2), h1s (H1 secondary), rob (robustness 1 and 3), rob2 (robustness 2),
expl (exploratory, post-results: H1 primary on rows with h != best_d).

Outputs under data/spec_v5/results/.
"""
import os
for _v in ('OPENBLAS_NUM_THREADS', 'OMP_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ.setdefault(_v, '1')                  # one thread per bootstrap process
import sys, json, time, pickle, glob, warnings, contextlib, io as _io
import multiprocessing as mp

import numpy as np
import pandas as pd
import chess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p5_common as C
import p5_evals as EV
from p5_pilot import horizon
from paper4_mixed_v2 import fit_mixed_v2, rows_for
from p5_fit import fit_selected

RES = os.path.join(C.OUT_DIR, 'results')
os.makedirs(RES, exist_ok=True)
D_ADM = [2, 4, 8]
D_ALL = [2, 4, 8, 12, 15]
MOVE = {'h': 'h', 'b20': 'best_20', 2: 'best_2', 4: 'best_4', 8: 'best_8', 12: 'best_12',
        15: 'best_15_singlepv'}
DIFF = ['wp_level_z', 'wp_level_z2', 'gap_12_z', 'spread_15_z', 'n_legal_z', 'n_reasonable_z',
        'eval_volatility_z']                     # v3 §4.2 difficulty features, mover's root
COV = DIFF + ['clock_z', 'elo_z']


def h1_formula(d, pre='V20'):
    return f'{pre}_h ~ {pre}_b{d} + {pre}_b20 + ' + ' + '.join(COV)


# ------------------------------------------------------------------ row table
def build_rows():
    r = pd.read_parquet(os.path.join(C.OUT_DIR, 'root_choices.parquet'))
    r['h'] = [chess.Board(fn).parse_san(s).uci() for fn, s in zip(r.fen, r.move_played)]
    v1 = C.load_v1()[['row_id', 'player_id', 'opponent_id', 'player_elo', 'opponent_elo', 'time_pressure',
                      'wp_best', 'gap_12', 'spread_15', 'n_legal', 'n_reasonable', 'eval_volatility']]
    r = r.merge(v1, on='row_id')
    st = EV.load_store()
    s20 = st[st.depth == 20].set_index(['row_id', 'move_uci'])
    for k, c in MOVE.items():
        key = pd.MultiIndex.from_arrays([r.row_id, r[c]])
        x = s20.reindex(key)
        tag = k if isinstance(k, str) else f'b{k}'
        r[f'V20_{tag}'] = x.wp_self_1.values
        r[f'term_{tag}'] = (x.terminal.fillna('').values != '')
        if tag not in ('h', 'b20'):
            r[f'pv_{tag}'] = x.pv_1.values
            r[f'succ_{tag}'] = x.succ_fen.values
    r['L_h'] = r.V20_b20 - r.V20_h
    for d in D_ALL:
        r[f'e_{d}'] = r.V20_b20 - r[f'V20_b{d}']
        r[f'I_{d}'] = r[f'e_{d}'] - r.L_h
        r[f'dis_{d}'] = r[MOVE[d]] != r.best_20
        r[f'hb_{d}'] = (r.h == r[MOVE[d]]).astype(float)       # H2 second outcome 1[h = best_d]
        for k in (4, 6, 8):
            hz = [horizon(sf, pv, k) if dis and not term else (np.nan, 'terminal' if dis else '')
                  for sf, pv, dis, term in zip(r[f'succ_b{d}'], r[f'pv_b{d}'], r[f'dis_{d}'], r[f'term_b{d}'])]
            sfx = '' if k == 6 else f'_k{k}'
            r[f'HORIZON_{d}{sfx}'] = [a for a, _ in hz]
            r[f'hflag_{d}{sfx}'] = [b for _, b in hz]
    # covariates, standardized on all rows
    r['wp_level'] = r.wp_best
    z = lambda x: (x - x.mean()) / x.std(ddof=1)
    for c in ['wp_level', 'gap_12', 'spread_15', 'n_legal', 'n_reasonable', 'eval_volatility']:
        r[f'{c}_z'] = z(r[c])
    r['wp_level_z2'] = r.wp_level_z ** 2
    r['clock_z'] = z(r.time_pressure)
    r['elo_z'] = z(r.player_elo.astype(float))
    r = r.drop(columns=[c for c in r.columns if c.startswith(('pv_', 'succ_'))])
    return r


def stage_prep():
    t0 = time.time()
    r = build_rows()
    r.to_parquet(os.path.join(RES, 'rows.parquet'), index=False)
    print(f'row table: {len(r):,} rows in {time.time() - t0:.0f} s')

    cols = (['V20_h', 'V20_b20'] + [f'V20_b{d}' for d in D_ALL] + ['L_h'] + [f'e_{d}' for d in D_ALL]
            + ['player_elo', 'opponent_elo', 'time_pressure', 'ply', 'wp_best', 'gap_12', 'spread_15',
               'n_legal', 'n_reasonable', 'eval_volatility', 'player_id', 'game_id'])
    miss = {c: int(r[c].isna().sum()) for c in cols}
    term = {t: int(r[f'term_{t}'].sum()) for t in ['h', 'b20'] + [f'b{d}' for d in D_ALL]}
    hz = {}
    for d in D_ALL:
        m = r[r[f'dis_{d}']]
        hz[d] = {'rows_dis': len(m), 'defined': int(m[f'HORIZON_{d}'].notna().sum()),
                 'share_1': float(m[f'HORIZON_{d}'].mean()),
                 'flags': m[f'hflag_{d}'].value_counts().to_dict()}
    a15 = 0.20 <= hz[12]['share_1'] <= 0.80

    # runtime gate: one H1 primary fit per admitted depth; coefficients are not displayed
    timing = {}
    fits = {}
    for d in D_ADM:
        t = time.time()
        res, rows, info = fit_mixed_v2(h1_formula(d), r, f'H1_d{d}_timing')
        timing[d] = {'seconds': time.time() - t, 'n': info['n'], 'status': info['status'],
                     'selected': info['selected'],
                     'sweep': [{k: x[k] for k in ('method', 'converged', 'llf', 'degenerate', 'seconds', 'error')}
                               for x in info['sweep']]}
        fits[d] = (res.fe_params.to_dict() if res is not None else None,
                   res.bse_fe.to_dict() if res is not None else None, info)
    proj_h = 2000 * sum(v['seconds'] for v in timing.values()) / 3600
    pickle.dump(fits, open(os.path.join(RES, 'H1_primary_point_fits.pkl'), 'wb'))   # not displayed
    out = {'missing': miss, 'terminal_positions': term, 'horizon': hz, 'A1.5_d12_within_20_80': a15,
           'timing': timing, 'bootstrap_projection_hours_2000x3': proj_h, 'gate_12h_pass': proj_h <= 12}
    json.dump(out, open(os.path.join(RES, 'prep.json'), 'w'), indent=2, default=str)
    print(json.dumps({k: v for k, v in out.items() if k != 'timing'}, indent=1, default=str))
    for d, v in timing.items():
        print(d, round(v['seconds'], 1), v['n'], v['status'], v['selected'],
              [(x['method'], x['converged'], x['seconds']) for x in v['sweep']])




# ================================================================== bootstrap machinery
XC = ['wp_best', 'wp2', 'gap_12', 'spread_15', 'n_legal', 'n_reasonable', 'eval_volatility',
      'time_pressure', 'player_elo']        # λ regressors, as reports/spec_v5_A1_check.md §4
NPROC = 8
FIRST_OPT = 'nm'
DRAWS_DIR = os.path.join(RES, 'draws')
POINTS_DIR = os.path.join(RES, 'points')
H2RHS = lambda d, hz: f'{hz} + e_{d}_z + ' + ' + '.join(COV)


def load_rows():
    r = pd.read_parquet(os.path.join(RES, 'rows.parquet'))
    z = lambda x: (x - x.mean()) / x.std(ddof=1)
    for d in D_ALL:
        r[f'e_{d}_z'] = z(r[f'e_{d}'])
    r['dev'] = r.move_played != r.move_engine_best
    assert int(r.dev.sum()) == 28647
    p15 = os.path.join(RES, 'rows15.parquet')
    if os.path.exists(p15):
        r = r.merge(pd.read_parquet(p15), on='row_id', how='left')
    return r


def load_check():
    return pd.read_parquet(os.path.join(C.OUT_DIR, 'A1_check_rows.parquet'))


def lam(ck, d):
    lr = ck.dropna(subset=XC + ['V20_best_20', f'V20_best_{d}', f'n_best_{d}'])
    A = np.column_stack([np.ones(len(lr)), lr.V20_best_20.values] + [lr[c].values for c in XC])
    with np.errstate(all='ignore'):
        beta, *_ = np.linalg.lstsq(A, lr[f'V20_best_{d}'].values, rcond=None)
        u = lr[f'V20_best_{d}'].values - A @ beta
    return float(1 - lr[f'n_best_{d}'].var(ddof=1) / np.var(u, ddof=1)), len(lr)


def subset(r, spec):
    m = np.ones(len(r), bool)
    for part in spec.split('&'):
        if part == 'all':
            continue
        if part == 'dev':
            m &= r.dev.values
        elif part.startswith('hne'):              # exploratory: rows with h != best_d
            m &= r[f'hb_{int(part[3:])}'].values == 0
        elif part == 'dis15':
            m &= r.dis15_4.values
        elif part.startswith('dis'):
            m &= r[f'dis_{int(part[3:])}'].values
    return r[m]


def models(group):
    """(name, formula, row spec) per group."""
    out = []
    if group == 'h1p':
        out = [(f'H1_d{d}', h1_formula(d), 'all') for d in D_ADM]
    elif group == 'h2':
        for d in D_ADM:
            out += [(f'H2_L_d{d}', f'L_h ~ ' + H2RHS(d, f'HORIZON_{d}'), f'dis{d}'),
                    (f'H2_hb_d{d}', f'hb_{d} ~ ' + H2RHS(d, f'HORIZON_{d}'), f'dis{d}')]
    elif group == 'h1s':
        for d in D_ADM:
            out += [(f'H1s_cov_d{d}', f'L_h ~ e_{d}_z + ' + ' + '.join(COV), 'all'),
                    (f'H1s_common_d{d}', h1_formula(d), 'dis8')]
    elif group == 'expl':                     # exploratory, post-results (2026-09-28): H1 primary on h != best_d
        out = [(f'X_H1_d{d}', h1_formula(d), f'hne{d}') for d in D_ADM]
    elif group == 'rob2':                     # robustness (2): depth-15 ruler, anchor best_15_singlepv, d = 4
        out = [('R2_H1_d4', 'V15_h ~ V15_b4 + V15_b15 + ' + ' + '.join(COV), 'all'),
               ('R2_H2_L_d4', 'L15 ~ HORIZON15_4 + e15_4_z + ' + ' + '.join(COV), 'dis15'),
               ('R2_H2_hb_d4', 'hb_4 ~ HORIZON15_4 + e15_4_z + ' + ' + '.join(COV), 'dis15')]
    elif group == 'rob':
        for k in (4, 8):
            for d in D_ADM:
                out += [(f'R1_L_d{d}_k{k}', f'L_h ~ ' + H2RHS(d, f'HORIZON_{d}_k{k}'), f'dis{d}'),
                        (f'R1_hb_d{d}_k{k}', f'hb_{d} ~ ' + H2RHS(d, f'HORIZON_{d}_k{k}'), f'dis{d}')]
        for d in D_ADM:
            out += [(f'R3_H1_d{d}', h1_formula(d), 'dev'),
                    (f'R3_H2_L_d{d}', f'L_h ~ ' + H2RHS(d, f'HORIZON_{d}'), f'dev&dis{d}'),
                    (f'R3_H2_hb_d{d}', f'hb_{d} ~ ' + H2RHS(d, f'HORIZON_{d}'), f'dev&dis{d}')]
    return out


def stage_points(group):
    """Full-data fit_mixed_v2 (five-optimizer sweep) for each model of a group."""
    os.makedirs(POINTS_DIR, exist_ok=True)
    r = load_rows()
    for name, formula, spec in models(group):
        p = os.path.join(POINTS_DIR, f'{name}.pkl')
        if os.path.exists(p):
            continue
        t = time.time()
        res, rows, info = fit_mixed_v2(formula, subset(r, spec), name)
        out = {'name': name, 'formula': formula, 'rows': spec, 'n': info['n'], 'status': info['status'],
               'selected': info['selected'], 'sweep': info['sweep'], 'seconds': time.time() - t}
        if res is not None:
            ci = res.conf_int()
            vc = {'player': float(res.cov_re.to_numpy().ravel()[0]),
                  'game': float(np.atleast_1d(res.vcomp)[0]), 'residual': float(res.scale)}
            out.update(params=res.fe_params.to_dict(), bse=res.bse_fe.to_dict(),
                       ci={k: (float(ci.loc[k, 0]), float(ci.loc[k, 1])) for k in res.fe_params.index},
                       vc=vc, llf=float(res.llf))
        pickle.dump(out, open(p, 'wb'))
        sel = next((x for x in info['sweep'] if x['method'] == info['selected']), {})
        print(f'{name}: n {info["n"]}, {info["status"]}, selected {info["selected"]} '
              f'({sel.get("seconds")} s), sweep {out["seconds"]:.0f} s', flush=True)


def point(name):
    return pickle.load(open(os.path.join(POINTS_DIR, f'{name}.pkl'), 'rb'))


# fit_selected lives in p5_fit.py: patsy would resolve C(game_id) to p5_common here.


# ---------------------------------------------------------------- draws
def draw_counts(n_draws, n_games):
    """Draw b resamples games with replacement; one sequence for all groups (seed 20261001)."""
    p = os.path.join(RES, 'draw_counts.npy')
    if os.path.exists(p):
        a = np.load(p)
        if a.shape[0] >= n_draws:
            return a
    rng = np.random.default_rng(C.SEED)
    a = np.stack([np.bincount(rng.integers(0, n_games, n_games), minlength=n_games) for _ in range(2000)])
    np.save(p, a)
    return a


_W = {}


def _winit(group):
    r = load_rows()
    ck = load_check()
    games = np.array(sorted(r.game_id.unique()))
    gpos = {g: i for i, g in enumerate(games)}
    rows_of = [[] for _ in games]
    for i, g in enumerate(r.game_id.values):
        rows_of[gpos[g]].append(i)
    ck_of = [[] for _ in games]
    for i, g in enumerate(ck.game_id.astype(str).values):
        ck_of[gpos[g]].append(i)
    # Optimizer order in draws (designer decision 2026-09-27, option 2): nm first for every
    # model, full fit_mixed_v2 sweep on non-convergence. cg, selected on the full data at
    # d = 2 and 8, converged in 0 of 57 resampled draws.
    sel = {name: FIRST_OPT for name, _, _ in models(group)}
    _W.update(r=r, ck=ck, games=games, rows_of=[np.array(x, int) for x in rows_of],
              ck_of=[np.array(x, int) for x in ck_of], sel=sel, group=group,
              counts=np.load(os.path.join(RES, 'draw_counts.npy')))


def resample(df, parts_of, cnt):
    idx, lab = [], []
    for gi in np.nonzero(cnt)[0]:
        rows = parts_of[gi]
        if not len(rows):
            continue
        for k in range(cnt[gi]):
            idx.append(rows); lab.append(np.full(len(rows), f'{gi}#{k}', dtype=object))
    out = df.iloc[np.concatenate(idx)].reset_index(drop=True)   # unique index: mixedlm aligns groups by label
    out['game_id'] = np.concatenate(lab)
    return out


def _draw(b):
    W = _W
    out_p = os.path.join(DRAWS_DIR, W['group'], f'draw_{b:04d}.json')
    if os.path.exists(out_p):
        return b, 0.0
    t = time.time()
    cnt = W['counts'][b]
    rb = resample(W['r'], W['rows_of'], cnt)
    ckb = resample(W['ck'], W['ck_of'], cnt)
    rec = {'draw': b, 'fits': {}, 'lam': {}}
    for d in D_ADM:
        rec['lam'][d] = lam(ckb, d)[0]
    for name, formula, spec in models(W['group']):
        params, status = fit_selected(formula, subset(rb, spec), W['sel'][name], name)
        rec['fits'][name] = {'status': status, 'params': params}
    if W['group'] == 'h1s':                                  # OLS raw slopes and binned means
        cut = json.load(open(os.path.join(RES, 'bins.json')))
        rec['raw'] = {}; rec['bins'] = {}
        for d in D_ADM:
            e, L = rb[f'e_{d}'].values, rb.L_h.values
            rec['raw'][d] = float(np.cov(e, L, ddof=1)[0, 1] / np.var(e, ddof=1))
            pos = rb[rb[f'e_{d}'] > 0]
            q = np.digitize(pos[f'e_{d}'].values, cut[str(d)][1:-1])
            rec['bins'][d] = [float(pos.L_h.values[q == i].mean()) if (q == i).any() else None for i in range(10)]
    rec['seconds'] = time.time() - t
    tmp = out_p + '.tmp'
    json.dump(rec, open(tmp, 'w'))
    os.replace(tmp, out_p)                                   # atomic: a partial file never exists
    return b, rec['seconds']


def stage_boot(group, n_draws, only=None):
    os.makedirs(os.path.join(DRAWS_DIR, group), exist_ok=True)
    r = load_rows()
    draw_counts(n_draws, r.game_id.nunique())
    if group == 'h1s' and not os.path.exists(os.path.join(RES, 'bins.json')):
        cut = {str(d): np.quantile(r.loc[r[f'e_{d}'] > 0, f'e_{d}'], np.linspace(0, 1, 11)).tolist() for d in D_ADM}
        json.dump(cut, open(os.path.join(RES, 'bins.json'), 'w'))
    todo = [b for b in (only if only is not None else range(n_draws))
            if not os.path.exists(os.path.join(DRAWS_DIR, group, f'draw_{b:04d}.json'))]
    print(f'[{group}] {n_draws} draws, {n_draws - len(todo)} done, {len(todo)} to run on {NPROC} processes', flush=True)
    t0 = time.time(); n = 0
    logp = os.path.join(RES, 'boot_log.json')
    with mp.Pool(NPROC, initializer=_winit, initargs=(group,)) as pool:
        for b, sec in pool.imap_unordered(_draw, todo, chunksize=1):
            n += 1
            if n % 50 == 0 or n == len(todo):
                el = time.time() - t0
                print(f'[{group}] {n}/{len(todo)}  {el / n:.1f} s/draw wall  eta {(len(todo) - n) * el / n / 3600:.2f} h', flush=True)
    wall = time.time() - t0
    lg = json.load(open(logp)) if os.path.exists(logp) else {}
    lg.setdefault(group, []).append({'draws_run': len(todo), 'wall_seconds': wall,
                                     'finished_utc': pd.Timestamp.utcnow().isoformat()})
    json.dump(lg, open(logp, 'w'), indent=2)


# ================================================================== H3 (descriptive, point estimates)
def stage_h3():
    """H1 primary and H2 (L_h) by Elo tercile and clock tercile, per admitted depth.
    Terciles on all 50,021 rows; fit_mixed_v2 full sweep; point estimates only."""
    r = load_rows()
    out_dir = os.path.join(RES, 'h3'); os.makedirs(out_dir, exist_ok=True)
    splits = {'elo': pd.qcut(r.player_elo, 3, labels=False), 'clock': pd.qcut(r.time_pressure, 3, labels=False)}
    cuts = {k: pd.qcut(r[c], 3, retbins=True)[1].tolist() for k, c in [('elo', 'player_elo'), ('clock', 'time_pressure')]}
    json.dump(cuts, open(os.path.join(out_dir, 'tercile_cuts.json'), 'w'), indent=2)
    for sp, lab in splits.items():
        for t in range(3):
            rt = r[lab.values == t]
            for d in D_ADM:
                for name, f, spec in [(f'H1_d{d}', h1_formula(d), 'all'),
                                      (f'H2_L_d{d}', f'L_h ~ ' + H2RHS(d, f'HORIZON_{d}'), f'dis{d}')]:
                    p = os.path.join(out_dir, f'{sp}{t}_{name}.pkl')
                    if os.path.exists(p):
                        continue
                    res, rows, info = fit_mixed_v2(f, subset(rt, spec), f'H3 {sp}{t} {name}')
                    o = {'n': info['n'], 'status': info['status'], 'selected': info['selected']}
                    if res is not None:
                        ci = res.conf_int()
                        o.update(params=res.fe_params.to_dict(),
                                 ci={k: (float(ci.loc[k, 0]), float(ci.loc[k, 1])) for k in res.fe_params.index})
                    pickle.dump(o, open(p, 'wb'))


# ================================================================== exploratory X.d: coincidence rows
def stage_coinc():
    """Exploratory, post-results (2026-09-28). Per admitted depth: (1) H1 primary by
    fit_mixed_v2 on coincidence rows (h = best_d), point estimate; (2) exact OLS
    (Frisch-Waugh) decomposition of the V20(best_d) slope into coincidence and
    non-coincidence rows: with u = residual of V20(best_d) on the other H1 regressors over
    all model rows, beta = sum_g w_g b_g, w_g = sum_g u^2 / sum u^2, b_g = sum_g u y / sum_g u^2.
    Weights are also given with u residualized on V20(best_20) alone."""
    r = load_rows()
    out = {}
    for d in D_ADM:
        p = os.path.join(RES, f'coinc_d{d}.pkl')
        if os.path.exists(p):
            o = pickle.load(open(p, 'rb'))                   # mixed fit cached; decomposition recomputed
        else:
            c = r[r[f'hb_{d}'] == 1]
            res, rows, info = fit_mixed_v2(h1_formula(d), c, f'X_coinc_d{d}')
            o = {'n_coinc': info['n'], 'status': info['status'], 'selected': info['selected'],
                 'sweep': [{k: x[k] for k in ('method', 'converged', 'llf', 'degenerate', 'seconds')} for x in info['sweep']],
                 'max_abs_Vh_minus_Vbd': float((c.V20_h - c[f'V20_b{d}']).abs().max())}
            if res is not None:
                o.update(beta=float(res.fe_params[f'V20_b{d}']), beta_b20=float(res.fe_params['V20_b20']),
                         residual_var=float(res.scale))
        m = rows_for(h1_formula(d), r)
        y = m.V20_h.values; x = m[f'V20_b{d}'].values; g = m[f'hb_{d}'].values == 1
        for tag, cols in [('cov', ['V20_b20'] + COV), ('b20', ['V20_b20'])]:
            Z = np.column_stack([np.ones(len(m))] + [m[k].values for k in cols])
            with np.errstate(all='ignore'):
                u = x - Z @ np.linalg.lstsq(Z, x, rcond=None)[0]
            ss = (u ** 2).sum()
            dec = {'n_model': len(m), 'row_share_coinc': float(g.mean()),
                   'w_coinc': float((u[g] ** 2).sum() / ss), 'w_non': float((u[~g] ** 2).sum() / ss),
                   'b_coinc': float((u[g] * y[g]).sum() / (u[g] ** 2).sum()),
                   'b_non': float((u[~g] * y[~g]).sum() / (u[~g] ** 2).sum()),
                   'beta_ols': float((u * y).sum() / ss)}
            dec['check'] = dec['w_coinc'] * dec['b_coinc'] + dec['w_non'] * dec['b_non'] - dec['beta_ols']
            # within-group view: each group's own OLS of y on V20(best_d) and the same regressors;
            # weights = each group's within-group residual variance of V20(best_d);
            # beta_ols - (w_c^w s_c + w_n^w s_n) = between-group term (coincidence correlates with u)
            wg = {}
            for gname, gm in [('coinc', g), ('non', ~g)]:
                Zg = Z[gm]; xg = x[gm]; yg = y[gm]
                with np.errstate(all='ignore'):
                    ug = xg - Zg @ np.linalg.lstsq(Zg, xg, rcond=None)[0]
                wg[gname] = ((ug ** 2).sum(), float((ug * yg).sum() / (ug ** 2).sum()))
            tot = wg['coinc'][0] + wg['non'][0]
            dec.update(ww_coinc=float(wg['coinc'][0] / tot), ww_non=float(wg['non'][0] / tot),
                       slope_within_coinc=wg['coinc'][1], slope_within_non=wg['non'][1])
            dec['within_mixture'] = dec['ww_coinc'] * dec['slope_within_coinc'] + dec['ww_non'] * dec['slope_within_non']
            dec['between_term'] = dec['beta_ols'] - dec['within_mixture']
            o[f'decomp_{tag}'] = dec
        pickle.dump(o, open(p, 'wb')); out[d] = o
        print(d, {k: v for k, v in o.items() if k != 'sweep'}, flush=True)


# ================================================================== robustness (2): depth-15 ruler
def rob2_tasks():
    """Depth-15 evaluations after best_4 needed on all rows with best_4 != best_15_singlepv:
    every such position must be in the study store (value and PV for HORIZON). v2/v3
    positions without a stored PV are re-evaluated and reproduction-checked."""
    import p5_pilot as P
    r = P.load_rows(); ex = P.load_existing(r)
    st = EV.load_store()
    have = set(zip(st[st.depth == 15].row_id, st[st.depth == 15].move_uci))
    exk = set(zip(ex.row_id, ex.move_uci))
    need = r[r.b4 != r.b15]
    t = P.task_df(need, 'b4', 15, 'rob2_b4')
    t['in_store'] = [(a, b) in have for a, b in zip(t.row_id, t.move_uci)]
    t['in_v2v3'] = [(a, b) in exk for a, b in zip(t.row_id, t.move_uci)]
    return r, ex, t


def stage_rob2count():
    r, ex, t = rob2_tasks()
    todo = t[~t.in_store]
    out = {'rows_best4_ne_best15': len(t), 'already_in_store': int(t.in_store.sum()),
           'to_evaluate': len(todo), 'of_which_v2v3_reevaluated_for_PV': int(todo.in_v2v3.sum())}
    json.dump(out, open(os.path.join(RES, 'rob2_count.json'), 'w'), indent=2)
    print(out, flush=True)


def stage_rob2eval(nproc=6):
    import p5_pilot as P
    r, ex, t = rob2_tasks()
    todo = t[~t.in_store].drop(columns=['in_store', 'in_v2v3'])
    wall = EV.run_tasks(todo, 'rob2_d15', nproc)
    lg = os.path.join(RES, 'rob2_count.json'); o = json.load(open(lg))
    o.update(wall_seconds=wall, nproc=nproc); json.dump(o, open(lg, 'w'), indent=2)
    P.stop_if_mismatch(r, ex)                                  # v2/v3 reproduction check


def stage_rob2rows():
    import p5_pilot as P
    r = P.load_rows()
    v15, _ = P.values(r)
    look = v15.set_index(['row_id', 'move_uci'])
    out = pd.DataFrame({'row_id': r.row_id})
    for c, n in [('h', 'V15_h'), ('b15', 'V15_b15'), ('b4', 'V15_b4')]:
        out[n] = look.reindex(pd.MultiIndex.from_arrays([r.row_id, r[c]])).V15.values
    out['L15'] = out.V15_b15 - out.V15_h
    out['e15_4'] = out.V15_b15 - out.V15_b4
    out['e15_4_z'] = (out.e15_4 - out.e15_4.mean()) / out.e15_4.std(ddof=1)
    out['dis15_4'] = (r.b4 != r.b15).values
    hz = []
    for dis, rid, u in zip(out.dis15_4, r.row_id, r.b4):
        if not dis:
            hz.append((np.nan, '')); continue
        x = look.loc[(rid, u)]
        hz.append(horizon(x.succ_fen, x.pv_1) if isinstance(x.pv_1, str) and x.pv_1 else (np.nan, 'no_pv'))
    out['HORIZON15_4'] = [a for a, _ in hz]; out['hflag15_4'] = [b for _, b in hz]
    out.to_parquet(os.path.join(RES, 'rows15.parquet'), index=False)
    miss = {c: int(out[c].isna().sum()) for c in ['V15_h', 'V15_b15', 'V15_b4']}
    miss['HORIZON15_4_on_dis_rows'] = int(out.loc[out.dis15_4, 'HORIZON15_4'].isna().sum())
    o = json.load(open(os.path.join(RES, 'rob2_count.json'))); o['missing'] = miss
    o['horizon15_share'] = float(out.loc[out.dis15_4, 'HORIZON15_4'].mean())
    json.dump(o, open(os.path.join(RES, 'rob2_count.json'), 'w'), indent=2)
    print(miss, flush=True)


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[0] in ('rob2count', 'rob2eval', 'rob2rows', 'h3', 'coinc'):
        {'rob2count': stage_rob2count, 'rob2eval': stage_rob2eval, 'rob2rows': stage_rob2rows,
         'h3': stage_h3, 'coinc': stage_coinc}[a[0]]()
    elif a[0] == 'prep':
        stage_prep()
    elif a[0] == 'points':
        stage_points(a[1])
    elif a[0] == 'boot':
        only = None
        if len(a) > 3 and a[3] == '--reference':            # rerun the draws kept in draws_reference/
            only = sorted(int(os.path.basename(f)[5:9]) for f in
                          glob.glob(os.path.join(RES, 'draws_reference', a[1], 'draw_*.json')))
        stage_boot(a[1], int(a[2]), only)
