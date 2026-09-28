#!/usr/bin/env python3
"""
p5_results_report.py — SPEC v5 §6–§8 report (reports/spec_v5_results.md) from the saved
outputs of p5_results.py: full-data fits (results/points/), bootstrap draws
(results/draws/<group>/), H3 fits (results/h3/), rows (results/rows*.parquet). No model is
fitted here. Per-row and per-draw summaries are written to data/spec_v5/results/summary/.
"""
import os, sys, json, glob, pickle

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p5_common as C
import p5_results as R

OUT = os.path.join(R.RES, 'summary'); os.makedirs(OUT, exist_ok=True)
FIG = os.path.join(C.REPO, 'figures', 'spec_v5'); os.makedirs(FIG, exist_ok=True)
D = R.D_ADM
f4 = lambda x: 'NA' if x is None or not np.isfinite(x) else f'{x:.4f}'
LAM15_4 = 0.810                                    # pilot λ_4 on the depth-15 ruler (pilot report §9)


def draws(group):
    return [json.load(open(f)) for f in sorted(glob.glob(os.path.join(R.DRAWS_DIR, group, 'draw_*.json')))]


def ci(a):
    a = np.asarray([x for x in a if x is not None and np.isfinite(x)], float)
    return (np.percentile(a, 2.5), np.percentile(a, 97.5), len(a)) if len(a) else (np.nan, np.nan, 0)


def coef(dr, model, term):
    f = dr['fits'].get(model)
    return None if f is None or f['params'] is None else f['params'].get(term)


def status_counts(dd, group):
    rows = []
    for name, _, _ in R.models(group):
        st = [x['fits'][name]['status'] for x in dd]
        rows.append((name, len(st), st.count('selected'), st.count('fallback'), st.count('failed')))
    return rows


def fmt_ci(lo, hi):
    return f'[{f4(lo)}, {f4(hi)}]'


def verdict(point, lo, hi, sign=-1):
    ok = (point < 0 if sign < 0 else point > 0) and ((hi < 0) if sign < 0 else (lo > 0))
    return 'PASS' if ok else 'FAIL'


def main():
    r = R.load_rows(); ck = R.load_check()
    P = R.point
    lam = {d: R.lam(ck, d)[0] for d in D}
    bd = {}
    for d in D:
        x = ck.dropna(subset=['n_best_20', f'e_{d}'])
        bd[d] = x.n_best_20.var(ddof=1) / x[f'e_{d}'].var(ddof=1)
    L = []; A = L.append
    notes = json.load(open(os.path.join(R.RES, 'nm_vs_sweep_57.json')))
    boot_log = json.load(open(os.path.join(R.RES, 'boot_log.json')))
    rob2 = json.load(open(os.path.join(R.RES, 'rob2_count.json')))
    prep = json.load(open(os.path.join(R.RES, 'prep.json')))

    A('# SPEC v5 results: engine depth as a knob on baseline fallibility\n')
    A('Spec: `specs/paper4_spec_v5.md` at b735062 (LOCKED 2026-09-22; Amendment A1, 880423e; A1.4 outcome). '
      'Ruler V20 (depth-20 win probability, 0–100, mover\'s side, of the position after the move); anchor best_20; '
      'admitted depths D = {2, 4, 8}; depths 12 and 15 descriptive only. Reading rule: sign and interval. No interpretation.\n')

    # ------------------------------------------------------------ analysis note
    h1p_d = draws('h1p'); h2_d = draws('h2'); h1s_d = draws('h1s'); rob_d = draws('rob'); rob2_d = draws('rob2')
    A('## Analysis note\n')
    A(f'- Estimator: `fit_mixed_v2` (`code/paper4_mixed_v2.py`), `(1 | player_id)` with `game_id` as a variance component nested in `player_id`, REML, five-optimizer sweep, '
      'converged non-degenerate fit with the highest log-likelihood; statsmodels 0.14.6. Full-data point estimates use the full sweep.')
    A('- Bootstrap: game-clustered percentile, seed 20261001; one sequence of game resamples shared by all groups (draw b uses the same games everywhere). '
      'A game drawn k times enters as k distinct game clusters; player ids are kept. '
      f'Draws: H1 primary {len(h1p_d):,}; H2 {len(h2_d):,}; H1 secondary {len(h1s_d):,}; robustness (1) and (3) {len(rob_d):,}; robustness (2) {len(rob2_d):,}. '
      'H3 and mixed-model descriptives: point estimates only; I_d and E_d means: 2,000 draws. '
      'Exploratory, post-results section (last): 500 draws.')
    A('- λ_d in every draw is recomputed on the A1.4 check rows (first 1,000 subsample rows) restricted to the drawn games, with multiplicity; β and λ are resampled jointly.')
    A('- Optimizer order in draws (designer decision 2026-09-27): nm first for every model; the full five-optimizer sweep only when nm fails to converge or is degenerate; '
      'draws where the sweep also fails are dropped from the interval and counted below. Reason: cg, selected on the full data for H1 at d = 2 and 8, converged in 0 of 57 resampled draws. '
      f"Check on those 57 draws, nm-first against the full sweep: max |Δβ| = {notes['2']['max']:.2e} (d = 2), {notes['4']['max']:.2e} (d = 4), {notes['8']['max']:.2e} (d = 8); nm fallbacks 0; tolerance 0.005. "
      'This changes execution order, not the estimator.')
    A('- Parallelism: 8 processes, one thread each. Measured gain over one process: 2.9× (83 s per H1 draw serial, 226 s per draw per process at 8 processes, full-sweep execution).')
    A('- Implementation record: the first H1 bootstrap attempt (56 draws) ran a wrapper that raised on every fit (patsy resolved `C(game_id)` to a module named `C`) and so always ran the full sweep; '
      'a worker of that run also wrote one draw after it was stopped. All 57 such draws were set aside (`results/draws_discarded/`); the 57 full-sweep draws of the second attempt are the reference set of the check above '
      '(`results/draws_reference/h1p/`). Every reported draw was produced by the nm-first procedure.')
    A('- Covariates: difficulty = v3 §4.2 features at the mover\'s root (wp_level, wp_level², gap_12, spread_15, n_legal, n_reasonable, eval_volatility), clock = time_pressure, elo = player_elo; '
      'z-scores on all 50,021 rows. 100 rows lack gap_12 and spread_15 (fewer than two root lines) and drop from every model. e_d_z is standardized on all rows.')
    A('- HORIZON(i, d): depth-20 PV (line 1 of the MultiPV-5 evaluation) after best_d, k = 6, as the pilot; defined on every best_d ≠ best_20 row with a non-terminal successor.')
    A(f"- Robustness (2): {rob2['to_evaluate']:,} depth-15 evaluations after best_4 run after all other bootstraps (nproc 6; {rob2['of_which_v2v3_reevaluated_for_PV']:,} of them re-evaluations of v2/v3 positions for the PV; wall {rob2['wall_seconds'] / 60:.1f} min). Reproduction check over all 8,303 v2/v3 positions re-evaluated in the study (pilot and this item): 0 mismatches in wp_self_1 or mv_1. λ_4 = 0.810 from the pilot, not resampled.")
    A('')
    A('Draw status per model (selected = nm converged; fallback = full sweep; failed = dropped):\n')
    A('| Group | Model | Draws | nm | Fallback | Failed |\n|---|---|---|---|---|---|')
    for g, dd in [('h1p', h1p_d), ('h2', h2_d), ('h1s', h1s_d), ('rob', rob_d), ('rob2', rob2_d)]:
        for name, n, s_, fb, fl in status_counts(dd, g):
            A(f'| {g} | {name} | {n:,} | {s_:,} | {fb:,} | {fl:,} |')
    A('')

    # ------------------------------------------------------------ item 0
    A('## 0. Inputs and checks\n')
    A('| Check | Value |\n|---|---|')
    A(f"| Rows | {len(r):,}; games {r.game_id.nunique():,}; players {r.player_id.nunique():,} |")
    A(f"| Missing values | none except gap_12 and spread_15: {prep['missing']['gap_12']} rows |")
    A(f"| Terminal successor positions (valued by rule) | h {prep['terminal_positions']['h']}, best_20 {prep['terminal_positions']['b20']}, each best_d 14 |")
    for d in R.D_ALL:
        h = prep['horizon'][str(d)]
        fl = {k: v for k, v in h['flags'].items() if k}
        A(f"| HORIZON (k = 6), d = {d} | rows best_d ≠ best_20 {h['rows_dis']:,}; HORIZON = 1 share {h['share_1']:.4f}; fallback-Pq flags {fl} |")
    A('| A1.5 (d = 12 share within 20–80%) | yes: k = 6 stands |')
    A('')

    # ------------------------------------------------------------ item 1: H1 primary
    beta = {d: P(f'H1_d{d}')['params'][f'V20_b{d}'] for d in D}
    bb = {d: [coef(x, f'H1_d{d}', f'V20_b{d}') for x in h1p_d] for d in D}
    lb = {d: [x['lam'][str(d)] for x in h1p_d] for d in D}
    dis = {d: [b / l if b is not None else None for b, l in zip(bb[d], lb[d])] for d in D}
    A('## 1. H1 primary: V20(h) ~ V20(best_d) + V20(best_20) + difficulty + clock + elo + (1 | player) + (1 | game)\n')
    A('| d | N | β_d | 95% interval | λ_d | 95% interval | β_d / λ_d | 95% interval | b_d | Selected optimizer (full data) |\n|---|---|---|---|---|---|---|---|---|---|')
    per = []
    for d in D:
        p = P(f'H1_d{d}'); c1, c2, _ = ci(bb[d]); l1, l2, _ = ci(lb[d]); q1, q2, _ = ci(dis[d])
        A(f"| {d} | {p['n']:,} | {f4(beta[d])} | {fmt_ci(c1, c2)} | {f4(lam[d])} | {fmt_ci(l1, l2)} | {f4(beta[d] / lam[d])} | {fmt_ci(q1, q2)} | {f4(bd[d])} | {p['selected']} |")
        per.append(dict(d=d, beta=beta[d], lam=lam[d], dis=beta[d] / lam[d], dis_lo=q1, dis_hi=q2, b=bd[d]))
    pd.DataFrame(per).to_csv(os.path.join(OUT, 'h1_primary.csv'), index=False)
    delta = beta[2] / lam[2] - beta[8] / lam[8]
    dd_ = [a - b if a is not None and b is not None else None for a, b in zip(dis[2], dis[8])]
    d24 = [a - b if a is not None and b is not None else None for a, b in zip(dis[2], dis[4])]
    d48 = [a - b if a is not None and b is not None else None for a, b in zip(dis[4], dis[8])]
    bstar = np.mean([beta[d] / lam[d] for d in D])
    nb_b = [np.mean([dis[d][i] for d in D]) * (lb[2][i] - lb[8][i]) if all(dis[d][i] is not None for d in D) else None
            for i in range(len(h1p_d))]
    raw_b = [a - b if a is not None and b is not None else None for a, b in zip(bb[2], bb[8])]
    A('')
    A('| Quantity | Estimate | 95% interval | Draws |\n|---|---|---|---|')
    c = ci(dd_); A(f'| Δ = β_2/λ_2 − β_8/λ_8 | {f4(delta)} | {fmt_ci(c[0], c[1])} | {c[2]:,} |')
    c = ci(d24); A(f'| β_2/λ_2 − β_4/λ_4 | {f4(beta[2] / lam[2] - beta[4] / lam[4])} | {fmt_ci(c[0], c[1])} | {c[2]:,} |')
    c = ci(d48); A(f'| β_4/λ_4 − β_8/λ_8 | {f4(beta[4] / lam[4] - beta[8] / lam[8])} | {fmt_ci(c[0], c[1])} | {c[2]:,} |')
    c = ci(raw_b); A(f'| Raw β_2 − β_8 (observed) | {f4(beta[2] - beta[8])} | {fmt_ci(c[0], c[1])} | {c[2]:,} |')
    c = ci(nb_b); A(f'| Noise benchmark: raw β_2 − β_8 implied by equal true coefficients, (λ_2 − λ_8) × β* | {f4((lam[2] - lam[8]) * bstar)} | {fmt_ci(c[0], c[1])} | {c[2]:,} |')
    A(f'\nβ* = mean of β_d/λ_d over d ∈ {{2, 4, 8}} = {f4(bstar)}: the common true coefficient under the null of equal true coefficients, under which the disattenuated coefficients are equal (Δ = 0) and the raw coefficients differ only by attenuation, β_d = λ_d β*.\n')
    c = ci(dd_)
    A(f'**Recorded prediction (A1.3): Δ < 0 with the interval excluding zero — {verdict(delta, c[0], c[1])}.**\n')
    A('Full-data convergence (five-optimizer sweep):\n')
    A('| Model | Optimizer | Converged | Log-likelihood | Degenerate | Seconds |\n|---|---|---|---|---|---|')
    for d in D:
        for x in P(f'H1_d{d}')['sweep']:
            llf = 'NA' if x['llf'] is None else f"{x['llf']:.3f}"
            A(f"| H1_d{d} | {x['method']} | {x['converged']} | {llf} | {x['degenerate']} | {x['seconds']} |")
    A('')
    A('| Model | Player variance | Game variance | Residual variance |\n|---|---|---|---|')
    for d in D:
        v = P(f'H1_d{d}')['vc']; A(f"| H1_d{d} | {f4(v['player'])} | {f4(v['game'])} | {f4(v['residual'])} |")
    A('')
    json.dump({'delta': delta, 'draws': dd_, 'd24': d24, 'd48': d48, 'noise_bench': nb_b}, open(os.path.join(OUT, 'h1_primary_draws.json'), 'w'))

    # ------------------------------------------------------------ item 2: H1 secondary
    A('## 2. H1 secondary\n')
    A('### 2a. Raw slope of L_h on e_d, all rows (OLS), next to b_d\n')
    A('| d | N | Raw slope | 95% interval | Draws | b_d (noise-implied raw slope) |\n|---|---|---|---|---|---|')
    for d in D:
        e, Lh = r[f'e_{d}'].values, r.L_h.values
        sl = np.cov(e, Lh, ddof=1)[0, 1] / np.var(e, ddof=1)
        c = ci([x['raw'][str(d)] for x in h1s_d])
        A(f'| {d} | {len(r):,} | {f4(sl)} | {fmt_ci(c[0], c[1])} | {c[2]:,} | {f4(bd[d])} |')
    A('\n### 2b. Binned E[L_h | e_d], deciles of e_d among rows with e_d > 0\n')
    cut = json.load(open(os.path.join(R.RES, 'bins.json')))
    A('| d | Decile | e_d range | N | Mean L_h | 95% interval |\n|---|---|---|---|---|---|')
    bins_out = []
    for d in D:
        pos = r[r[f'e_{d}'] > 0]
        q = np.digitize(pos[f'e_{d}'].values, cut[str(d)][1:-1])
        for i in range(10):
            m = pos.L_h.values[q == i]
            c = ci([x['bins'][str(d)][i] for x in h1s_d])
            A(f"| {d} | {i + 1} | {cut[str(d)][i]:.3f}–{cut[str(d)][i + 1]:.3f} | {len(m):,} | {f4(m.mean())} | {fmt_ci(c[0], c[1])} |")
            bins_out.append(dict(d=d, decile=i + 1, lo=cut[str(d)][i], hi=cut[str(d)][i + 1], n=len(m), mean_L=m.mean(), ci_lo=c[0], ci_hi=c[1]))
    pd.DataFrame(bins_out).to_csv(os.path.join(OUT, 'h1_bins.csv'), index=False)
    A('\n### 2c. Covariate-adjusted: L_h ~ e_d_z + difficulty + clock + elo + (1 | player) + (1 | game)\n')
    A('| d | N | e_d_z coefficient | 95% interval | Draws |\n|---|---|---|---|---|')
    for d in D:
        p = P(f'H1s_cov_d{d}'); c = ci([coef(x, f'H1s_cov_d{d}', f'e_{d}_z') for x in h1s_d])
        A(f"| {d} | {p['n']:,} | {f4(p['params'][f'e_{d}_z'])} | {fmt_ci(c[0], c[1])} | {c[2]:,} |")
    A('\n### 2d. Common row set {best_8 ≠ best_20}: H1 primary at d = 2, 4, 8\n')
    A('| d | N | β_d | 95% interval | β_d / λ_d | 95% interval |\n|---|---|---|---|---|---|')
    cb = {d: P(f'H1s_common_d{d}')['params'][f'V20_b{d}'] for d in D}
    cdis = {d: [coef(x, f'H1s_common_d{d}', f'V20_b{d}') / x['lam'][str(d)] if coef(x, f'H1s_common_d{d}', f'V20_b{d}') is not None else None for x in h1s_d] for d in D}
    for d in D:
        c = ci([coef(x, f'H1s_common_d{d}', f'V20_b{d}') for x in h1s_d]); q = ci(cdis[d])
        A(f"| {d} | {P(f'H1s_common_d{d}')['n']:,} | {f4(cb[d])} | {fmt_ci(c[0], c[1])} | {f4(cb[d] / lam[d])} | {fmt_ci(q[0], q[1])} |")
    cd = [a - b if a is not None and b is not None else None for a, b in zip(cdis[2], cdis[8])]
    c = ci(cd)
    A(f'\nΔ on the common row set = {f4(cb[2] / lam[2] - cb[8] / lam[8])}, 95% interval {fmt_ci(c[0], c[1])} ({c[2]:,} draws). λ_d from the full check rows, recomputed per draw.\n')

    # ------------------------------------------------------------ item 3: H2
    h2rows = []
    A('## 3. H2: L_h ~ HORIZON + e_d_z + difficulty + clock + elo + (1 | player) + (1 | game), rows best_d ≠ best_20\n')
    A('| d | Outcome | N | HORIZON coefficient | 95% interval | Draws | Recorded prediction (negative, interval excluding zero) |\n|---|---|---|---|---|---|---|')
    for d in D:
        for o, lab in [('L', 'L_h'), ('hb', '1[h = best_d] (linear probability)')]:
            p = P(f'H2_{o}_d{d}'); b = p['params'][f'HORIZON_{d}']
            c = ci([coef(x, f'H2_{o}_d{d}', f'HORIZON_{d}') for x in h2_d])
            v = verdict(b, c[0], c[1]) if o == 'L' else 'no recorded prediction'
            A(f"| {d} | {lab} | {p['n']:,} | {f4(b)} | {fmt_ci(c[0], c[1])} | {c[2]:,} | {v} |")
            h2rows.append(dict(d=d, outcome=o, n=p['n'], coef=b, lo=c[0], hi=c[1]))
    pd.DataFrame(h2rows).to_csv(os.path.join(OUT, 'h2.csv'), index=False)
    A('')

    # ------------------------------------------------------------ item 4: H3
    A('## 4. H3 (descriptive, point estimates, no test)\n')
    cuts = json.load(open(os.path.join(R.RES, 'h3', 'tercile_cuts.json')))
    A(f"Terciles on all rows: Elo cut points {[round(x) for x in cuts['elo']]}; clock (time_pressure) cut points {[round(x, 3) for x in cuts['clock']]}. β_d/λ_d uses the full-sample λ_d.\n")
    A('| Split | Tercile | d | N (H1) | H1 β_d / λ_d | N (H2) | H2 HORIZON coefficient |\n|---|---|---|---|---|---|---|')
    for sp in ['elo', 'clock']:
        for t in range(3):
            for d in D:
                a = pickle.load(open(os.path.join(R.RES, 'h3', f'{sp}{t}_H1_d{d}.pkl'), 'rb'))
                b = pickle.load(open(os.path.join(R.RES, 'h3', f'{sp}{t}_H2_L_d{d}.pkl'), 'rb'))
                h1v = f4(a['params'][f'V20_b{d}'] / lam[d]) if a.get('params') else a['status']
                h2v = f4(b['params'][f'HORIZON_{d}']) if b.get('params') else b['status']
                A(f"| {sp} | {t + 1} | {d} | {a['n']:,} | {h1v} | {b['n']:,} | {h2v} |")
    A('')

    # ------------------------------------------------------------ item 5: descriptives
    A('## 5. Descriptives: I_d against E_d\n')
    cnt = np.load(os.path.join(R.RES, 'draw_counts.npy'))
    games = np.array(sorted(r.game_id.unique())); gi = np.searchsorted(games, r.game_id.values)
    def gsum(x):
        return np.bincount(gi, weights=x, minlength=len(games))
    n_g = gsum(np.ones(len(r)))
    def bmean(x):
        s = gsum(x); v = (cnt @ s) / (cnt @ n_g)
        return x.mean(), np.percentile(v, 2.5), np.percentile(v, 97.5)
    Es = bmean(r.L_h.values)
    A('| d | E_d = mean e_d | 95% interval | Mean I_d | 95% interval | HORIZON = 1 share (best_d ≠ best_20) |\n|---|---|---|---|---|---|')
    desc = []
    for d in R.D_ALL:
        e = bmean(r[f'e_{d}'].values); i = bmean(r[f'I_{d}'].values)
        sh = r.loc[r[f'dis_{d}'], f'HORIZON_{d}'].mean()
        A(f'| {d} | {f4(e[0])} | {fmt_ci(e[1], e[2])} | {f4(i[0])} | {fmt_ci(i[1], i[2])} | {sh:.4f} |')
        desc.append(dict(d=d, E=e[0], E_lo=e[1], E_hi=e[2], I=i[0], I_lo=i[1], I_hi=i[2], horizon_share=sh))
    pd.DataFrame(desc).to_csv(os.path.join(OUT, 'descriptives.csv'), index=False)
    A(f'\nE* = mean L_h = {f4(Es[0])}, 95% interval {fmt_ci(Es[1], Es[2])}. By identity I_d = e_d − L_h row by row, so mean I_d = E_d − E*: the curve has slope one and crosses zero at E_d = E*. '
      'This is what the identity implies, not a finding. Figure: `figures/spec_v5/fig_Id_curve.png`. 2,000 draws.\n')

    # ------------------------------------------------------------ item 6: robustness
    A('## 6. Robustness\n')
    A('### 6.1 HORIZON with k = 4 and k = 8 (H2 refit)\n')
    A('| k | d | Outcome | N | HORIZON coefficient | 95% interval | Draws |\n|---|---|---|---|---|---|---|')
    for k in (4, 8):
        for d in D:
            for o in ('L', 'hb'):
                nm = f'R1_{o}_d{d}_k{k}'; p = P(nm)
                c = ci([coef(x, nm, f'HORIZON_{d}_k{k}') for x in rob_d])
                A(f"| {k} | {d} | {'L_h' if o == 'L' else '1[h = best_d]'} | {p['n']:,} | {f4(p['params'][f'HORIZON_{d}_k{k}'])} | {fmt_ci(c[0], c[1])} | {c[2]:,} |")
    A('\n### 6.2 Depth-15 ruler, anchor best_15_singlepv, all rows\n')
    A(f"Pilot λ values on the depth-15 ruler admit depth 4 only (λ_4 = 0.810; no pilot λ at depths 2 and 8; depth 12 had Var(V20 − V15)/Var(e_12) = 1.6–1.9). "
      f"Depth-15 evaluations after best_4 run for this item: {rob2['to_evaluate']:,}; missing after the run: {rob2['missing']}.\n")
    A('| Model | N | Coefficient | Estimate | 95% interval | Draws |\n|---|---|---|---|---|---|')
    p = P('R2_H1_d4'); b4 = p['params']['V15_b4']; c = ci([coef(x, 'R2_H1_d4', 'V15_b4') for x in rob2_d])
    A(f"| H1 primary, d = 4 | {p['n']:,} | β_4 on V15(best_4) | {f4(b4)} | {fmt_ci(c[0], c[1])} | {c[2]:,} |")
    A(f"| | | β_4 / 0.810 | {f4(b4 / LAM15_4)} | {fmt_ci(c[0] / LAM15_4, c[1] / LAM15_4)} | |")
    for o, lab in [('L', 'L15'), ('hb', '1[h = best_4]')]:
        p = P(f'R2_H2_{o}_d4'); c = ci([coef(x, f'R2_H2_{o}_d4', 'HORIZON15_4') for x in rob2_d])
        A(f"| H2 ({lab}), d = 4 | {p['n']:,} | HORIZON (depth-15 PV) | {f4(p['params']['HORIZON15_4'])} | {fmt_ci(c[0], c[1])} | {c[2]:,} |")
    A('\n### 6.3 Deviation rows only (28,647 v3 rows)\n')
    A('| Model | d | N | Coefficient | Estimate | 95% interval | Draws |\n|---|---|---|---|---|---|---|')
    rd = {}
    for d in D:
        p = P(f'R3_H1_d{d}'); b = p['params'][f'V20_b{d}']
        rd[d] = [coef(x, f'R3_H1_d{d}', f'V20_b{d}') / x['lam'][str(d)] if coef(x, f'R3_H1_d{d}', f'V20_b{d}') is not None else None for x in rob_d]
        c = ci([coef(x, f'R3_H1_d{d}', f'V20_b{d}') for x in rob_d]); q = ci(rd[d])
        A(f"| H1 primary | {d} | {p['n']:,} | β_d | {f4(b)} | {fmt_ci(c[0], c[1])} | {c[2]:,} |")
        A(f"| | | | β_d / λ_d | {f4(b / lam[d])} | {fmt_ci(q[0], q[1])} | |")
    c = ci([a - b if a is not None and b is not None else None for a, b in zip(rd[2], rd[8])])
    A(f"| H1 primary | Δ = β_2/λ_2 − β_8/λ_8 | | | {f4(P('R3_H1_d2')['params']['V20_b2'] / lam[2] - P('R3_H1_d8')['params']['V20_b8'] / lam[8])} | {fmt_ci(c[0], c[1])} | {c[2]:,} |")
    for d in D:
        for o, lab in [('L', 'H2 (L_h)'), ('hb', 'H2 (1[h = best_d])')]:
            p = P(f'R3_H2_{o}_d{d}'); c = ci([coef(x, f'R3_H2_{o}_d{d}', f'HORIZON_{d}') for x in rob_d])
            A(f"| {lab} | {d} | {p['n']:,} | HORIZON | {f4(p['params'][f'HORIZON_{d}'])} | {fmt_ci(c[0], c[1])} | {c[2]:,} |")
    A('')

    # ------------------------------------------------------------ pass/fail and limits
    A('## Recorded predictions\n')
    c = ci(dd_)
    A(f'- H1 (A1.3): Δ = β_2/λ_2 − β_8/λ_8 < 0 with the interval excluding zero: Δ = {f4(delta)}, {fmt_ci(c[0], c[1])} — **{verdict(delta, c[0], c[1])}**.')
    for x in h2rows:
        if x['outcome'] == 'L':
            A(f"- H2, d = {x['d']}: HORIZON coefficient on L_h negative with the interval excluding zero: {f4(x['coef'])}, {fmt_ci(x['lo'], x['hi'])} — **{verdict(x['coef'], x['lo'], x['hi'])}**.")
    A('')
    A('## Figures\n')
    A('- `figures/spec_v5/fig_H1_disattenuated.png`: β_d/λ_d against depth with 95% intervals; raw β_d; the noise benchmark (equal true coefficients: β* flat after disattenuation, λ_d β* before).')
    A('- `figures/spec_v5/fig_Id_curve.png`: mean I_d against E_d at d = 2, 4, 8, 12, 15 with 95% intervals; the line mean I_d = E_d − E* is the identity I_d = e_d − L_h.\n')
    A('## Limits (§8, plus the ruler resolution)\n')
    A('- One platform, fast time controls, titled players.')
    A('- The ruler is an engine (depth 20 by Amendment A1), not ground truth.')
    A('- HORIZON is a proxy for visibility, not a measure of what the player saw.')
    A('- The human\'s move is fixed, so nothing here measures what a human would do when shown a shallow engine.')
    A('- The v3 difficulty features were built for the opponent\'s error and are used for the mover\'s difficulty (§1).')
    A('- Ruler resolution: the engine disagrees with itself between adjacent depths by about one WP point in SD at both steps measured: SD(V20 − V15) = 1.35–1.46 on the 2,000-row subsample '
      '(pilot report §6, §12) and SD(V25 − V20) = 1.09–1.16 on 1,000 rows (`reports/spec_v5_A1_check.md` §1). Depths 12 and 15 are excluded from §6 because their Var(e_d) is of that order (λ_12 = −0.139, λ_15 = −1.503).')
    # ------------------------------------------------------------ exploratory, post-results
    ex_d = draws('expl')
    A('\n## Exploratory, post-results\n')
    A('Requested by the designer on 2026-09-28, after the results above were read. Not in the specification; no recorded prediction; '
      'same estimator, rows, covariates and bootstrap procedure (nm first, full sweep on non-convergence, λ_d recomputed per draw on the check rows of the drawn games).\n')
    A('### X.a H1 primary on rows with h ≠ best_d\n')
    A('| d | N | β_d | 95% interval | β_d / λ_d | 95% interval | Draws | nm / fallback / failed |\n|---|---|---|---|---|---|---|---|')
    xd = {}
    for d in D:
        nm = f'X_H1_d{d}'; p = P(nm); b = p['params'][f'V20_b{d}']
        bs = [coef(x, nm, f'V20_b{d}') for x in ex_d]
        xd[d] = [v / x['lam'][str(d)] if v is not None else None for v, x in zip(bs, ex_d)]
        c = ci(bs); q = ci(xd[d]); st = [x['fits'][nm]['status'] for x in ex_d]
        A(f"| {d} | {p['n']:,} | {f4(b)} | {fmt_ci(c[0], c[1])} | {f4(b / lam[d])} | {fmt_ci(q[0], q[1])} | {c[2]:,} | "
          f"{st.count('selected')} / {st.count('fallback')} / {st.count('failed')} |")
    xdelta = P('X_H1_d2')['params']['V20_b2'] / lam[2] - P('X_H1_d8')['params']['V20_b8'] / lam[8]
    c = ci([a - b if a is not None and b is not None else None for a, b in zip(xd[2], xd[8])])
    A(f'\nΔ = β_2/λ_2 − β_8/λ_8 on these rows = {f4(xdelta)}, 95% interval {fmt_ci(c[0], c[1])} ({c[2]:,} draws). Full-data optimizer: '
      + ', '.join(f"d = {d} {P(f'X_H1_d{d}')['selected']}" for d in D) + '.\n')
    A('### X.b P(h = best_d)\n')
    A('| d | All rows: N | P(h = best_d) | Rows best_d ≠ best_20: N | P(h = best_d) among them |\n|---|---|---|---|---|')
    xb = []
    for d in R.D_ALL:
        m = r[f'dis_{d}']
        A(f"| {d} | {len(r):,} | {r[f'hb_{d}'].mean():.4f} | {int(m.sum()):,} | {r.loc[m, f'hb_{d}'].mean():.4f} |")
        xb.append(dict(d=d, n=len(r), p_all=r[f'hb_{d}'].mean(), n_dis=int(m.sum()), p_dis=r.loc[m, f'hb_{d}'].mean()))
    pd.DataFrame(xb).to_csv(os.path.join(OUT, 'exploratory_p_h_eq_best_d.csv'), index=False)
    A(f"\nFor reference, P(h = best_20) = {(r.h == r.best_20).mean():.4f} on all {len(r):,} rows.\n")
    A('### X.c H2 second outcome 1[h = best_d] with HORIZON at k = 4\n')
    A('Already estimated as part of robustness (1) (§6.1, models R1_hb_d{2,4,8}_k4, 500 draws); repeated here next to the L_h outcome at k = 4. No new fit.\n')
    A('| d | Outcome | N | HORIZON (k = 4) coefficient | 95% interval | Draws |\n|---|---|---|---|---|---|')
    for d in D:
        for o, lab in [('L', 'L_h'), ('hb', '1[h = best_d]')]:
            nm = f'R1_{o}_d{d}_k4'; p = P(nm); c = ci([coef(x, nm, f'HORIZON_{d}_k4') for x in rob_d])
            A(f"| {d} | {lab} | {p['n']:,} | {f4(p['params'][f'HORIZON_{d}_k4'])} | {fmt_ci(c[0], c[1])} | {c[2]:,} |")
    A('')
    open(os.path.join(C.REPO, 'reports', 'spec_v5_results.md'), 'w').write('\n'.join(L))

    # ------------------------------------------------------------ figures
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    S1, INK, INK2, REF, SURF = '#2a78d6', '#0b0b0b', '#52514e', '#8f8e89', '#fcfcfb'
    plt.rcParams.update({'font.size': 10, 'axes.edgecolor': INK2, 'axes.labelcolor': INK, 'xtick.color': INK2,
                         'ytick.color': INK2, 'axes.spines.top': False, 'axes.spines.right': False})
    fig, ax = plt.subplots(figsize=(6.4, 4.2), facecolor=SURF); ax.set_facecolor(SURF)
    x = np.array(D, float)
    y = np.array([pp['dis'] for pp in per]); lo = np.array([pp['dis_lo'] for pp in per]); hi = np.array([pp['dis_hi'] for pp in per])
    ax.axhline(0, color=REF, lw=1)
    ax.axhline(bstar, color=REF, lw=1.5, ls='--', label='Null, disattenuated: β* (equal true coefficients)')
    ax.plot(x, [lam[d] * bstar for d in D], color=REF, lw=1.5, ls=':', marker='o', mfc=SURF, ms=6, label='Null, raw: λ_d β*')
    ax.plot(x, [beta[d] for d in D], ls='none', marker='o', mfc=SURF, mec=S1, mew=1.5, ms=8, label='Observed raw β_d')
    ax.errorbar(x, y, yerr=[y - lo, hi - y], fmt='o', color=S1, ms=8, lw=2, capsize=0, label='Observed β_d / λ_d, 95% interval')
    ax.set_xticks(D); ax.set_xlabel('Baseline search depth d'); ax.set_ylabel('Coefficient on V20(best_d)')
    ax.set_title('H1 primary: disattenuated coefficient by depth', color=INK, loc='left')
    ax.grid(axis='y', color='#e7e6e2', lw=0.8); ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=8, labelcolor=INK2)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, 'fig_H1_disattenuated.png'), dpi=200, facecolor=SURF); plt.close(fig)

    fig, ax = plt.subplots(figsize=(6.4, 4.2), facecolor=SURF); ax.set_facecolor(SURF)
    E = np.array([q['E'] for q in desc]); I = np.array([q['I'] for q in desc])
    xs = np.linspace(0, max(E.max(), Es[0]) * 1.1, 50)
    ax.axhline(0, color=REF, lw=1)
    ax.plot(xs, xs - Es[0], color=REF, lw=1.5, ls='--', label=f'Identity: mean I_d = E_d − E* (E* = {Es[0]:.2f})')
    ax.errorbar(E, I, xerr=[E - [q['E_lo'] for q in desc], [q['E_hi'] for q in desc] - E],
                yerr=[I - [q['I_lo'] for q in desc], [q['I_hi'] for q in desc] - I], fmt='o', color=S1, ms=8, lw=2, capsize=0,
                label='Mean I_d, 95% intervals')
    for q in desc:
        ax.annotate(f"d = {q['d']}", (q['E'], q['I']), textcoords='offset points', xytext=(8, -12), fontsize=8, color=INK2)
    ax.set_xlabel('E_d = mean e_d (WP points)'); ax.set_ylabel('Mean I_d (WP points)')
    ax.set_title('Substitution gain against baseline error (descriptive)', color=INK, loc='left')
    ax.grid(color='#e7e6e2', lw=0.8); ax.set_axisbelow(True)
    ax.legend(frameon=False, fontsize=8, labelcolor=INK2, loc='upper left')
    fig.tight_layout(); fig.savefig(os.path.join(FIG, 'fig_Id_curve.png'), dpi=200, facecolor=SURF); plt.close(fig)
    print('wrote reports/spec_v5_results.md and figures/spec_v5/')


if __name__ == '__main__':
    main()
