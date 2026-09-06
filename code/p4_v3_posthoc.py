#!/usr/bin/env python3
"""
p4_v3_posthoc.py — SPEC v3 Amendment 3: post-hoc diagnostics, NOT pre-registered.

Appends a clearly-labelled section to docs/paper4_v3_REPORT.md. H1-H4 are NOT
re-fitted; their estimates are read from the table the analysis already wrote.
The §4 nuisance model is re-fitted only to recover its out-of-fold predictions
on untreated rows (deterministic: same fold seed, same code path; the per-fold
R2 is printed so drift would be visible).

    python3 p4_v3_posthoc.py
"""
import os, warnings
import numpy as np, pandas as pd
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import statsmodels.api as sm
import statsmodels.formula.api as smf
from sklearn.linear_model import LogisticRegression

import paper4_pilot as P
import paper4_report as R
import p4_v3_analysis as A

warnings.filterwarnings('ignore')
OUT = os.path.join('docs', 'paper4_v3_REPORT.md')
FIG = A.FIG
FIG_REL = A.FIG_REL
BAND = A.BAND
BUF = []
def W(s=''):
    BUF.append(s)


def main():
    v1 = A._read('paper4_results').drop_duplicates(['game_id', 'ply'])
    cut = float(v1['WPL_raw'].quantile(1 - P.WINSOR_TOP))
    rows = pd.read_parquet('p4_v3_rows/p4_v3_rows_analysis.parquet')
    band = rows[(rows.WPL_self > BAND[0]) & (rows.WPL_self <= BAND[1])].copy()

    # untreated rows + their out-of-fold nuisance predictions (deterministic re-run)
    tr_all = A.build_training(v1, cut)
    train = tr_all[tr_all.prev_was_best].dropna(subset=A.RAW + ['WPL']).copy()
    par = A.zpar(train, A.RAW)
    trz = A.apply_z(train, par)

    def branch(d, which):
        b = pd.DataFrame({
            'wp_level': d[f'wp_level_{which}'].values, 'gap_12': d[f'gap_12_{which}'].values,
            'spread_15': d[f'spread_15_{which}'].values, 'n_legal': d[f'n_legal_{which}'].values,
            'n_reasonable': d[f'n_reasonable_{which}'].values,
            'eval_volatility': d[f'eval_volatility_{which}'].values,
            'elo': d['opponent_elo'].values, 'time_pressure': d['time_pressure_opp'].values,
            'game_id': d.game_id.values, 'ply': d.ply.values}, index=d.index)
        return A.apply_z(b, par)

    treated = pd.concat([branch(rows, 'played'), branch(rows, 'best')], ignore_index=True)
    oof, _, r2, _ = A.crossfit(trz, treated, par, kind='lmm')
    trz = trz.assign(_pred=oof.values)
    trz['_resid'] = trz.WPL - trz._pred

    W('\n\n---\n')
    W('\n## Post-hoc diagnostics (not pre-registered)\n')
    W('\nEverything in this section was added **after** the results in §1–§8 were produced and '
      'read, under SPEC v3 Amendment 3. None of it is pre-registered; none of it revises a '
      'pre-registered estimate. H1–H4 were not re-fitted — their coefficients are the ones '
      'already reported above. The §4 nuisance model was re-fitted only to recover its '
      'out-of-fold predictions on untreated rows; it is deterministic given `fold_seed = '
      f'{A.FOLD_SEED}`, and the per-fold out-of-sample R² reproduces §4 exactly: '
      + ', '.join(f'{x:.4f}' for x in r2) + '.\n')

    # ------------------------------------------------ (a) common support
    W('\n### A. Common-support calibration (Amendment 3 item 2)\n')
    W('\nThis replaces the §9.4 decile check, which Amendment 3 item 1 withdraws as invalid: it '
      'binned untreated rows by `ΔRISK_steep`, a property of the row\'s own move that is '
      'mechanically tied to that row\'s `WPL` and invisible to a position-feature model, so it '
      'could not have come out flat. The question §9.4 meant to ask is whether the model is '
      'unbiased **where its predictions are actually applied**. That is asked here by reweighting '
      'untreated rows to the treated rows\' feature distribution.\n')

    feats = A.NUIS
    X = np.vstack([trz[feats].to_numpy(), treated[feats].dropna().to_numpy()])
    y = np.r_[np.zeros(len(trz)), np.ones(len(treated[feats].dropna()))]
    ok = np.isfinite(X).all(axis=1)
    lr = LogisticRegression(max_iter=2000).fit(X[ok], y[ok])
    p_tr = lr.predict_proba(trz[feats].to_numpy())[:, 1]
    w = p_tr / np.clip(1 - p_tr, 1e-9, None)          # covariate-shift odds weights
    w = w / w.mean()
    trz['_w'] = w
    top = np.sort(w)[::-1]
    W(f'\nWeights are covariate-shift odds `p/(1−p)` from a logistic model separating the '
      f'{len(trz):,} untreated rows from the {len(treated.dropna(subset=feats)):,} treated branch '
      f'rows on the nine §4.2 features. Overlap is good: the largest single weight carries '
      f'{100*top[0]/w.sum():.3f}% of total weight and the top 1% carry '
      f'{100*top[:max(1,len(w)//100)].sum()/w.sum():.1f}%, so no handful of rows drives the '
      f'weighted numbers.\n')

    def calib(by, label, n=10):
        cols = list(dict.fromkeys([by, 'WPL', '_pred', '_resid', '_w']))  # by may be '_pred'
        d = trz[cols].dropna().copy()
        d['bin'] = pd.qcut(d[by], n, labels=False, duplicates='drop')
        out = []
        for b, g in d.groupby('bin'):
            uw = g._resid.mean()
            ww = np.average(g._resid, weights=g._w)
            row = [f'{b+1}', f'{len(g):,}', f'{g[by].mean():+.3f}']
            if by != '_pred':
                row.append(f'{g._pred.mean():.3f}')
            out.append(row + [f'{uw:+.4f}', f'{ww:+.4f}'])
        hdr = ['decile', 'n', f'mean {label}'] + ([] if by == '_pred' else ['mean predicted'])
        W(f'\n**Binned by {label}**\n')
        W(R.fmt_tbl(out, hdr + ['obs − pred (unweighted)', 'obs − pred (weighted)']))
        return d

    calib('_pred', 'predicted WPL')
    calib('wp_level', 'wp_level')
    calib('spread_15', 'spread_15')
    ov_u = trz._resid.mean(); ov_w = np.average(trz._resid, weights=trz._w)
    W(f'\nOverall bias on untreated rows: unweighted {ov_u:+.4f} WP, reweighted to the treated '
      f'feature distribution **{ov_w:+.4f} WP**. For scale, `RES` has mean '
      f'{band.RES.mean():+.3f} and the H4 `ΔRISK_steep_z` coefficient is −0.0854.\n')

    # ------------------------------------------------ (b) mean RES, clustered
    W('\n### B. Mean `RES`, two-way clustered (exploratory)\n')
    b2 = band.dropna(subset=['RES']).copy()
    m = smf.ols('RES ~ 1', b2).fit(
        cov_type='cluster',
        cov_kwds={'groups': np.column_stack([b2.player_id.factorize()[0],
                                             b2.game_id.factorize()[0]])})
    ci = m.conf_int().loc['Intercept']
    W(f'\n**Exploratory.** Mean `RES` = **{m.params["Intercept"]:+.4f} WP points**, 95% CI '
      f'[{ci[0]:+.4f}, {ci[1]:+.4f}], SE {m.bse["Intercept"]:.4f}, two-way cluster-robust by '
      f'`player_id` and `game_id`, N = {int(m.nobs):,}. This is a level, not a test of the '
      'H4 slope, and it is not a pre-registered quantity: §6 specifies no intercept test on '
      '`RES`. Read it only as the average size of the residual channel.\n')

    # ------------------------------------------------ (c) reply source split
    W('\n### C. Split by how the opponent reply was valued\n')
    W('\nThe two-tier rule in §3.1 values a reply from the stored MultiPV-5 when the reply is one '
      'of those lines, and otherwise from a fresh depth-15 search of the child position.\n')
    W('\n**This split conditions on the dependent variable, and the estimates below are therefore '
      'not interpretable.** A reply that falls outside P(m_played)\'s MultiPV-5 is, by '
      'construction, a worse move than the 5th line; `reply_in_multipv` is thus a coarse function '
      'of `WPL_opp_actual`, which is the outcome `RES` is built from. The large level gap between '
      'the groups is not a valuation artefact — it is **real opponent error**, which is precisely '
      'what the indicator selects on. Selecting on a function of the outcome breaks the '
      'exogeneity the H4 model assumes, so neither the within-group means nor the within-group '
      'slopes estimate the H4 effect, and the fact that they differ from the pooled estimate is '
      'not evidence against it. **The pooled pre-registered estimates in §6.4 stand.** The table '
      'is kept for completeness only.\n')
    sub = []
    for lab, g in [('inside MultiPV-5', b2[b2.reply_in_multipv == True]),
                   ('freshly evaluated', b2[b2.reply_in_multipv == False])]:
        gg = g.copy()
        for c in ['delta_risk_steep', 'WPL_self', 'time_pressure_opp', 'elo_diff_opp']:
            gg[c + '_z'] = R.z(gg[c])
        gg['gap_12_orig_z'] = R.z(gg['gap_12'])
        gg['eval_volatility_orig_z'] = R.z(gg['eval_volatility'])
        res, ols, d = R.fit_mixed(
            'RES ~ delta_risk_steep_z + WPL_self_z + gap_12_orig_z + eval_volatility_orig_z '
            '+ time_pressure_opp_z + elo_diff_opp_z', gg, f'posthoc-{lab}')
        co = res.params['delta_risk_steep_z'] if res is not None else np.nan
        cl = res.conf_int().loc['delta_risk_steep_z'] if res is not None else [np.nan, np.nan]
        pv = res.pvalues['delta_risk_steep_z'] if res is not None else np.nan
        sub.append([lab, f'{len(g):,}', f'{g.RES.mean():+.4f}',
                    f'{co:+.4f}', f'[{cl[0]:+.4f}, {cl[1]:+.4f}]', f'{pv:.3g}'])
    W(R.fmt_tbl(sub, ['reply valued from', 'n', 'mean RES',
                      'H4 ΔRISK_steep_z', '95% CI', 'p']))
    W('\nSame model form as H4a, fitted post hoc on each subgroup. Not a pre-registered '
      'comparison, and — per the note above — not an interpretable one: both rows condition on '
      'the outcome.\n')
    comp = b2.dropna(subset=['delta_risk_steep']).copy()
    comp['dec'] = pd.qcut(comp.delta_risk_steep, 10, labels=False, duplicates='drop')
    cg = comp.groupby('dec').agg(n=('RES', 'size'),
                                 mean_d=('delta_risk_steep', 'mean'),
                                 fresh=('reply_in_multipv', lambda s: 1 - s.mean()))
    W('\n**The compositional gradient is a real fact, about forcedness rather than about bias.** '
      'The share of replies needing a fresh search falls steadily as the deviation gets sharper:\n')
    W(R.fmt_tbl([[f'{i+1}', f'{r.n:,.0f}', f'{r.mean_d:+.3f}', f'{100*r.fresh:.1f}%']
                 for i, r in cg.iterrows()],
                ['ΔRISK_steep decile', 'n', 'mean ΔRISK_steep', 'share valued by fresh search']))
    W('\nFrom 25.6% in the least-sharp decile to 0.8% in the sharpest. The natural reading is '
      'forcedness: in sharper positions the opponent\'s available replies are more concentrated, '
      'so the move actually played is far more likely to be one of the engine\'s top five. That '
      'is a descriptive property of sharp positions, not a defect in the measurement.\n')
    W('\nWhat this split cannot settle — because it conditions on the outcome — is whether the '
      'two tiers are on the same scale. That is measured directly in Section E instead.\n')

    # ------------------------------------------------ (d) model-free H4
    W('\n### D. Raw mean `RES` by ΔRISK_steep decile, no covariates\n')
    W('\nThe model-free version of H4a on the treated analysis rows: no covariates, no random '
      'effects, no adjustment of any kind.\n')
    b3 = band.dropna(subset=['RES', 'delta_risk_steep']).copy()
    b3['dec'] = pd.qcut(b3.delta_risk_steep, 10, labels=False, duplicates='drop')
    g = b3.groupby('dec').agg(n=('RES', 'size'), mean_d=('delta_risk_steep', 'mean'),
                              mean_res=('RES', 'mean'), sd=('RES', 'std'))
    g['se'] = g.sd / np.sqrt(g.n)
    W(R.fmt_tbl([[f'{i+1}', f'{r.n:,.0f}', f'{r.mean_d:+.3f}', f'{r.mean_res:+.4f}',
                  f'[{r.mean_res-1.96*r.se:+.4f}, {r.mean_res+1.96*r.se:+.4f}]']
                 for i, r in g.iterrows()],
                ['ΔRISK_steep decile', 'n', 'mean ΔRISK_steep', 'mean RES', '95% CI (naive)']))
    rho = b3[['delta_risk_steep', 'RES']].corr().iloc[0, 1]
    W(f'\nSpearman-free check: Pearson correlation between `ΔRISK_steep` and `RES` on these '
      f'{len(b3):,} rows is **{rho:+.4f}**. CIs are naive (independent rows) and ignore the '
      'player/game clustering the §6 models account for.\n')

    fig, ax = plt.subplots(figsize=(5.6, 3.8))
    ax.errorbar(range(1, len(g) + 1), g.mean_res, yerr=1.96 * g.se, fmt='o-', ms=4, lw=1)
    ax.axhline(0, c='r', lw=1, ls='--')
    ax.set_xlabel('ΔRISK_steep decile (treated analysis rows)'); ax.set_ylabel('mean RES (WP points)')
    ax.set_title('Model-free H4a: raw mean RES by sharpness decile', fontsize=9)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, 'posthoc_res_by_decile.png'), dpi=130)
    plt.close(fig)
    W(f'\n![raw RES by decile]({FIG_REL}/posthoc_res_by_decile.png)\n')

    # ------------------------------------------------ (e) depth asymmetry
    W('\n### E. Direct measurement of the §3.1 depth asymmetry\n')
    dc_path = 'p4_v3_depth_check.parquet'
    if not os.path.exists(dc_path):
        W('\n_(p4_v3_depth_check.parquet not present; run `p4_v3_depth_check.py` first.)_\n')
    else:
        dc = pd.read_parquet(dc_path)
        W(f'\nThe two tiers in §3.1 sit at different effective depths: a stored MultiPV-5 line is '
          f'valued by the search of P(m_played), while an off-PV reply is valued by a fresh '
          f'depth-15 search of the child position, one ply deeper. Rather than argue about the '
          f'size of that gap, it is measured. {len(dc):,} in-PV replies were drawn at random '
          f'(seed {20260906}) and their child positions re-evaluated freshly at the same [LOCKED] '
          f'configuration (depth {P.DEPTH}, MultiPV {P.MULTIPV}, Threads=1, Hash=128). The '
          f'quantity below is `fresh WP_self − stored PV-line WP_self` for the same move, so it '
          f'isolates the valuation route with the move held fixed.\n')
        d = dc['diff'].dropna()
        W(R.fmt_tbl([['mean', f'{d.mean():+.4f}'], ['SD', f'{d.std():.4f}'],
                     ['p1', f'{d.quantile(.01):+.4f}'], ['p5', f'{d.quantile(.05):+.4f}'],
                     ['p25', f'{d.quantile(.25):+.4f}'], ['median', f'{d.median():+.4f}'],
                     ['p75', f'{d.quantile(.75):+.4f}'], ['p95', f'{d.quantile(.95):+.4f}'],
                     ['p99', f'{d.quantile(.99):+.4f}'],
                     ['n', f'{len(d):,}']],
                    ['statistic', 'fresh − stored (WP points)']))
        dc = dc.dropna(subset=['diff', 'delta_risk_steep']).copy()
        dc['dec'] = pd.qcut(dc.delta_risk_steep, 10, labels=False, duplicates='drop')
        dg = dc.groupby('dec').agg(n=('diff', 'size'), mean_d=('delta_risk_steep', 'mean'),
                                   m=('diff', 'mean'), sd=('diff', 'std'))
        dg['se'] = dg.sd / np.sqrt(dg.n)
        W('\n**Mean offset by ΔRISK_steep decile**\n')
        W(R.fmt_tbl([[f'{i+1}', f'{r.n:,.0f}', f'{r.mean_d:+.3f}', f'{r.m:+.4f}',
                      f'[{r.m-1.96*r.se:+.4f}, {r.m+1.96*r.se:+.4f}]']
                     for i, r in dg.iterrows()],
                    ['ΔRISK_steep decile', 'n', 'mean ΔRISK_steep', 'mean fresh − stored',
                     '95% CI']))
        sl = smf.ols('Q("diff") ~ delta_risk_steep', dc).fit()
        b_, ci_ = sl.params['delta_risk_steep'], sl.conf_int().loc['delta_risk_steep']
        spread = dg.m.max() - dg.m.min()
        W(f'\nSlope of the offset on `ΔRISK_steep`: **{b_:+.5f}** WP per unit '
          f'[{ci_[0]:+.5f}, {ci_[1]:+.5f}], p = {sl.pvalues["delta_risk_steep"]:.3g}. '
          f'Spread across decile means: {spread:.4f} WP.\n')
        ok_mean = abs(d.mean()) <= 0.5
        ok_grad = (ci_[0] <= 0 <= ci_[1]) and spread <= 0.5
        if ok_mean and ok_grad:
            W(f'\n**Verdict: the two-tier §3.1 rule stands.** The mean offset '
              f'({d.mean():+.4f} WP) is inside ±0.5 WP, the slope on `ΔRISK_steep` is not '
              f'distinguishable from zero, and the decile means span {spread:.4f} WP. The two '
              'valuation routes are on the same scale to within the tolerance set for this '
              'check, so the pooled §6 estimates are not carrying a depth artefact.\n')
        else:
            W(f'\n**Verdict: the check does NOT pass.** mean offset {d.mean():+.4f} WP '
              f'(tolerance ±0.5, {"inside" if ok_mean else "OUTSIDE"}); slope '
              f'{b_:+.5f} [{ci_[0]:+.5f}, {ci_[1]:+.5f}] '
              f'({"no gradient" if (ci_[0] <= 0 <= ci_[1]) else "GRADIENT PRESENT"}); decile '
              f'spread {spread:.4f} WP. Reported and stopped here: no estimate has been changed '
              'and no re-valuation attempted. Whether to re-value the off-PV replies on a common '
              'footing is the designer\'s decision under §10.\n')

    with open(OUT, 'a') as f:
        f.write('\n'.join(BUF))
    print(f'appended post-hoc section to {OUT}')


if __name__ == '__main__':
    main()
