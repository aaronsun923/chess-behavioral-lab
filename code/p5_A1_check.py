#!/usr/bin/env python3
"""
p5_A1_check.py — SPEC v5 Amendment A1.4 truth check for the depth-20 ruler.

    python3 code/p5_A1_check.py run [nproc]   # depth 20, then depth 25, on the A1.4 positions
    python3 code/p5_A1_check.py report        # reports/spec_v5_A1_check.md; no engine

Positions: the first 1,000 subsample rows in draw order; after h, best_20 and each
best_d (d in 2, 4, 8, 12, 15), each distinct position once (data/spec_v5/A1_tasks.parquet,
depth-25 part). V_D = wp_self_1 of the depth-D MultiPV-5 successor evaluation.
e_d = V20(best_20) − V20(best_d); n_x = V25 − V20 at position type x. HORIZON(i, d) on
the depth-20 PV after best_d, k = 6. Nothing from §6 or §7.
"""
import os, sys, json

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p5_common as C
import p5_evals as EV
from p5_pilot import horizon, boot, wmean

SHALLOW = [2, 4, 8, 12, 15]
COL = {'h': 'h', 'best_20': 'best_20', 'best_2': 'best_2', 'best_4': 'best_4', 'best_8': 'best_8',
       'best_12': 'best_12', 'best_15': 'best_15_singlepv'}
BATCH_LOG = os.path.join(EV.EVAL_DIR, 'A1_batches.json')
f = lambda x: f'{x:.4f}'


def check_tasks():
    t = pd.read_parquet(os.path.join(C.OUT_DIR, 'A1_tasks.parquet'))
    return t[t.depth == 25].copy()


def record(tag, n_tasks, wall):
    b = json.load(open(BATCH_LOG)) if os.path.exists(BATCH_LOG) else {}
    b[tag] = {'tasks': n_tasks, 'wall_seconds': wall, 'finished_utc': pd.Timestamp.utcnow().isoformat()}
    json.dump(b, open(BATCH_LOG, 'w'), indent=2)


def stage_run(nproc):
    t25 = check_tasks()
    t20 = t25.assign(depth=20, item='A1_check_d20')
    wall = EV.run_tasks(t20, 'A1_check_d20', nproc)
    record('A1_check_d20', len(t20), wall)
    t25 = t25.assign(item='A1_check_d25')
    wall = EV.run_tasks(t25, 'A1_check_d25', nproc, 'SPEC v5 A1.4 depth-25 truth check')
    record('A1_check_d25', len(t25), wall)


def stage_report():
    r = pd.read_parquet(os.path.join(C.OUT_DIR, 'root_choices.parquet'))
    import chess
    r['h'] = [chess.Board(fn).parse_san(s).uci() for fn, s in zip(r.fen, r.move_played)]
    v1 = C.load_v1()[['row_id', 'wp_best', 'gap_12', 'spread_15', 'n_legal', 'n_reasonable',
                      'eval_volatility', 'time_pressure', 'player_elo']]
    r = r.merge(v1, on='row_id')
    rows = check_tasks().row_id.unique()
    s = r[r.row_id.isin(rows)].copy()
    st = EV.load_store()
    look = {D: st[st.depth == D].set_index(['row_id', 'move_uci']) for D in (20, 25)}

    def val(D, rid, u):
        x = look[D].loc[(rid, u)] if (rid, u) in look[D].index else None
        if x is None:
            return np.nan, True
        return x.wp_self_1, x.terminal != ''

    for name, c in COL.items():
        v20 = [val(20, a, u) for a, u in zip(s.row_id, s[c])]
        v25 = [val(25, a, u) for a, u in zip(s.row_id, s[c])]
        s[f'V20_{name}'] = [v for v, _ in v20]                    # terminal: 100 / 50 by rule
        s[f'n_{name}'] = [(b - a) if not ta and not tb else np.nan
                          for (a, ta), (b, tb) in zip(v20, v25)]  # terminal excluded
    for d in SHALLOW:
        s[f'e_{d}'] = s.V20_best_20 - s[f'V20_best_{d}']
    s['L_h'] = s.V20_best_20 - s.V20_h
    miss = int(s[[f'V20_{n}' for n in COL]].isna().any(axis=1).sum())

    L = []; P = L.append
    P('# SPEC v5 Amendment A1.4: depth-25 truth check of the depth-20 ruler\n')
    P(f'Spec: `specs/paper4_spec_v5.md`, Amendment A1 at 880423e. Rows: the first 1,000 subsample rows in draw order (seed 20261001). '
      'V_D = depth-D win probability (0–100, mover\'s side) of the position after the move, MultiPV 5, Threads 1, Hash 128, ucinewgame per search; '
      'nproc = 6. e_d = V20(best_20) − V20(best_d); best_15 = best_15_singlepv. Bootstrap intervals: game-clustered percentile, 2,000 draws, seed 20261001. '
      f'Nothing from §6 or §7. Rows with a missing V20: {miss}.\n')

    P('## 1. V25 − V20 by position type (terminal excluded)\n')
    P('| Position type | N | Mean | SD | p50 \\|x\\| | p99 \\|x\\| | max \\|x\\| | share \\|x\\| > 5 |\n|---|---|---|---|---|---|---|---|')
    sds = {}
    for name in COL:
        x = s[f'n_{name}'].dropna().values; a = np.abs(x)
        sds[name] = x.std(ddof=1)
        P(f'| after {name} | {len(x):,} | {f(x.mean())} | {f(sds[name])} | {f(np.percentile(a, 50))} | {f(np.percentile(a, 99))} | {f(a.max())} | {(a > 5).mean():.4f} |')
    P('')

    sd_e = {d: s[f'e_{d}'].std(ddof=1) for d in SHALLOW}
    bound4 = 0.25 * sd_e[4]
    mx = max(sds, key=sds.get)
    P('## 2. SD rule\n')
    P('| Quantity | Value |\n|---|---|')
    P(f'| SD(e_4) on these rows (N = {s.e_4.notna().sum():,}) | {f(sd_e[4])} |')
    P(f'| Bound 0.25 × SD(e_4) | {f(bound4)} |')
    P(f'| Largest SD of V25 − V20 (after {mx}) | {f(sds[mx])} |')
    P(f'| Largest SD below bound | {"yes" if sds[mx] < bound4 else "no"} |\n')

    P('## 3. HORIZON-group rule per depth (k = 6, depth-20 PV after best_d)\n')
    P('| d | Rows best_d ≠ best_20 | HORIZON = 1 / 0 (defined, V25 − V20 defined) | Flags (short PV / forcing to PV end / no PV) | Mean V25 − V20 at best_d, H = 1 | H = 0 | Difference (1 − 0) | 95% interval | Bound 0.25 × SD(e_d) | \\|Difference\\| below bound |\n|---|---|---|---|---|---|---|---|---|---|')
    for d in SHALLOW:
        c = COL[f'best_{d}']
        dd = s[s[c] != s.best_20].copy()
        hz = []
        for rid, u in zip(dd.row_id, dd[c]):
            x = look[20].loc[(rid, u)]
            hz.append(horizon(x.succ_fen, x.pv_1) if x.terminal == '' else (np.nan, 'no_pv'))
        dd['H'] = [a for a, _ in hz]; dd['flag'] = [b for _, b in hz]
        hr = dd.dropna(subset=['H', f'n_best_{d}'])
        g1, g0 = hr[hr.H == 1], hr[hr.H == 0]
        diff = g1[f'n_best_{d}'].mean() - g0[f'n_best_{d}'].mean()
        is1 = (hr.H == 1).values.astype(float); nv = hr[f'n_best_{d}'].values
        ci = boot(hr.game_id.values, lambda w: wmean(nv, w * is1) - wmean(nv, w * (1 - is1)))
        b = 0.25 * sd_e[d]
        fl = dd.flag.value_counts()
        P(f"| {d} | {len(dd):,} | {len(g1):,} / {len(g0):,} | {fl.get('pv_shorter_than_k', 0)} / {fl.get('forcing_to_pv_end', 0)} / {fl.get('no_pv', 0)} | "
          f"{f(g1[f'n_best_{d}'].mean())} | {f(g0[f'n_best_{d}'].mean())} | {f(diff)} | [{f(ci[0])}, {f(ci[1])}] | {f(b)} | {'yes' if abs(diff) < b else 'no'} |")
    P('')

    P('## 4. b_d and λ_d per depth (from V25 − V20)\n')
    P('| d | SD(e_d) | Var(e_d) | b_d = Var(n20) / Var(e_d) | N (b_d) | Var(n_d) | Var(u_d) | λ_d = 1 − Var(n_d) / Var(u_d) | N (λ_d) | λ_d ≥ 0.5 |\n|---|---|---|---|---|---|---|---|---|---|')
    s['wp2'] = s.wp_best ** 2
    xc = ['wp_best', 'wp2', 'gap_12', 'spread_15', 'n_legal', 'n_reasonable', 'eval_volatility', 'time_pressure', 'player_elo']
    for d in SHALLOW:
        bb = s.dropna(subset=['n_best_20', f'e_{d}'])
        b_d = bb.n_best_20.var(ddof=1) / bb[f'e_{d}'].var(ddof=1)
        lr = s.dropna(subset=xc + ['V20_best_20', f'V20_best_{d}', f'n_best_{d}'])
        A = np.column_stack([np.ones(len(lr)), lr.V20_best_20.values] + [lr[c].values for c in xc])
        beta, *_ = np.linalg.lstsq(A, lr[f'V20_best_{d}'].values, rcond=None)
        u = lr[f'V20_best_{d}'].values - A @ beta
        vn, vu = lr[f'n_best_{d}'].var(ddof=1), np.var(u, ddof=1)
        lam = 1 - vn / vu
        P(f"| {d} | {f(sd_e[d])} | {f(sd_e[d] ** 2)} | {f(b_d)} | {len(bb):,} | {f(vn)} | {f(vu)} | {f(lam)} | {len(lr):,} | {'yes' if lam >= 0.5 else 'no'} |")
    P('\nu_d = OLS residual of V20(best_d) on an intercept, V20(best_20) and the H1 primary covariates (as pilot §9: wp_level, wp_level², gap_12, spread_15, n_legal, n_reasonable, '
      'eval_volatility, time_pressure, player_elo); complete cases. n20, n_d = V25 − V20 at the best_20 and best_d positions; Var(n_d) on the same rows as u_d. '
      'Where best_d = best_20 the two positions are the same and n_d = n20.\n')

    P('## 5. Descriptives on these rows\n')
    P('| Quantity | Value |\n|---|---|')
    P(f'| Mean L_h = V20(best_20) − V20(h) | {f(s.L_h.mean())} |')
    for d in SHALLOW:
        P(f'| E_{d} = mean e_{d} | {f(s[f"e_{d}"].mean())} |')
    P('')

    P('## 6. Depth-25 cost: measured against the 7.0× extrapolation\n')
    bl = json.load(open(BATCH_LOG))
    x20 = st[(st.batch == 'A1_check_d20') & (st.terminal == '')]
    x25 = st[(st.batch == 'A1_check_d25') & (st.terminal == '')]
    pr = st[(st.depth == 20) & (st.terminal == '')][['row_id', 'move_uci', 'seconds']] \
        .merge(x25[['row_id', 'move_uci', 'seconds']], on=['row_id', 'move_uci'], suffixes=('_20', '_25'))
    w25 = bl['A1_check_d25']['wall_seconds'] / len(x25)
    w20 = bl['A1_check_d20']['wall_seconds'] / max(len(x20), 1)
    P('| Quantity | Value |\n|---|---|')
    P(f'| Depth-25 engine evaluations (nproc = 6) | {len(x25):,} |')
    P(f'| Depth-25 batch wall | {bl["A1_check_d25"]["wall_seconds"] / 3600:.2f} h |')
    P(f'| Depth-25 wall s per evaluation, measured | {w25:.3f} |')
    P(f'| Depth-25 wall s per evaluation, extrapolated (A1 counts report §4, nproc = 8) | 10.742 |')
    P(f'| Measured / extrapolated | {w25 / 10.742:.3f} |')
    P(f'| Depth-25 engine s per evaluation, mean / median | {x25.seconds.mean():.3f} / {x25.seconds.median():.3f} |')
    P(f'| Engine-time ratio depth 25 / depth 20, same {len(pr):,} positions (mean over mean) | {pr.seconds_25.mean() / pr.seconds_20.mean():.3f} (extrapolation assumed 7.00) |')
    same = x20[['row_id', 'move_uci', 'seconds']].merge(x25[['row_id', 'move_uci', 'seconds']],
                                                        on=['row_id', 'move_uci'], suffixes=('_20', '_25'))
    P(f'| Engine-time ratio depth 25 / depth 20, both at nproc = 6 (the {len(same):,} positions of the A1 depth-20 batch) | {same.seconds_25.mean() / same.seconds_20.mean():.3f} |')
    P(f'| Positions in the all-positions ratio whose depth-20 time was measured in the pilot batch at nproc = 8 | {len(pr) - len(same):,} |')
    P(f'| Depth-20 batch for these positions: engine evaluations / wall h / wall s per evaluation | {len(x20):,} / {bl["A1_check_d20"]["wall_seconds"] / 3600:.2f} / {w20:.3f} |')
    P('')

    p = os.path.join(C.REPO, 'reports', 'spec_v5_A1_check.md')
    open(p, 'w').write('\n'.join(L))
    s.to_parquet(os.path.join(C.OUT_DIR, 'A1_check_rows.parquet'), index=False)
    print(open(p).read())


if __name__ == '__main__':
    stage = sys.argv[1]
    nproc = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    {'run': lambda: stage_run(nproc), 'report': stage_report}[stage]()
