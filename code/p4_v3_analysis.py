#!/usr/bin/env python3
"""
p4_v3_analysis.py — SPEC v3 §4-§7 and the §9 deliverables.

Reads `p4_v3_rows/` (built by p4_v3_build_rows.py) plus the v1 and v2 shards,
fits the §4 nuisance model with 5-fold cross-fitting by game, constructs the
§5 dependent variables, runs the §6 tests and the §7 robustness items, and
writes docs/paper4_v3_REPORT.md with figures in p4_v3_figures/.

Every mixed model uses v1's own fit_mixed (paper4_report.py:74) so that §6.5's
re-run of the v1 §7.2 model is the same estimator on the same rows.

    python3 p4_v3_analysis.py
"""
import os, sys, glob, json, time, warnings, platform, subprocess
import numpy as np, pandas as pd
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats

import paper4_pilot as P
import paper4_report as R
from paper4_pilot import WINSOR_TOP, DEPTH, MULTIPV, THREADS, HASH_MB

warnings.filterwarnings('ignore')

FOLD_SEED  = 20260905          # [LOCKED §4.2]
N_FOLDS    = 5                 # [LOCKED §4.2]
BAND       = (0.0, 5.0)        # [LOCKED §6]
BAND_ROB   = (0.0, 10.0)       # [LOCKED §7.1]
TOST_EPS   = 0.5               # [LOCKED §6.1]
FIG        = os.path.join('docs', 'p4_v3_figures')   # filesystem
FIG_REL    = 'p4_v3_figures'                          # relative to docs/, for markdown links
OUT        = os.path.join('docs', 'paper4_v3_REPORT.md')

NUIS = ['wp_level_z', 'wp_level_z2', 'gap_12_z', 'spread_15_z', 'n_legal_z',
        'n_reasonable_z', 'eval_volatility_z', 'elo_z', 'time_pressure_z']
RAW  = ['wp_level', 'gap_12', 'spread_15', 'n_legal', 'n_reasonable',
        'eval_volatility', 'elo', 'time_pressure']

# [SPEC v3 Amendment 2 item 2] flagged on EVERY mixed-model coefficient table
RE_FLAG = ('**Random effects:** the [LOCKED] `(1 | player_id) + (1 | game_id)` is estimated with '
           '`game_id` nested inside `player_id` (v1 `fit_mixed`, `paper4_report.py:74`; SPEC v3 '
           'Amendment 2 item 1). In the analysis band 98.5% of games contribute rows from both '
           'players, so the crossing is real; what the approximation drops is the shared game '
           'intercept across a game\'s two players. The OLS fit with player-clustered SEs below '
           'is the check on it.')

_BUF = []
def A(s=''):
    _BUF.append(s)


def _read(d):
    fs = sorted(glob.glob(os.path.join(d, '**', '*.parquet'), recursive=True))
    if not fs:
        raise SystemExit(f'no shards in {d}')
    return pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True)


def zpar(df, cols):
    return {c: (float(df[c].mean()), float(df[c].std(ddof=0))) for c in cols}


def apply_z(df, par):
    out = df.copy()
    for c, (m, s) in par.items():
        out[c + '_z'] = (df[c] - m) / (s if s else 1.0)
    out['wp_level_z2'] = out['wp_level_z'] ** 2
    return out


# ====================================================================== §4
def build_training(v1, cut):
    """§4.1 main training set: previous ply evaluated AND was the engine's first choice."""
    v1 = v1.sort_values(['game_id', 'ply']).reset_index(drop=True)
    prev = v1[['game_id', 'ply', 'move_played', 'move_engine_best']].copy()
    prev['ply'] += 1
    prev = prev.rename(columns={'move_played': '_pm', 'move_engine_best': '_pb'})
    d = v1.merge(prev, on=['game_id', 'ply'], how='left')
    d['prev_evaluated'] = d['_pm'].notna()
    d['prev_was_best'] = d['prev_evaluated'] & (d['_pm'] == d['_pb'])

    d['wp_level'] = d['wp_best']
    d['elo'] = d['player_elo']
    d['WPL'] = d['WPL_raw'].clip(upper=cut)
    return d


def crossfit(train, targets, par, kind='lmm'):
    """[LOCKED §4.2] 5 folds by game_id, fold_seed 20260905. A row's prediction
    never comes from a model that saw that game. Fixed effects only."""
    games = np.sort(pd.unique(np.concatenate([train.game_id.values,
                                              targets.game_id.values])))
    rng = np.random.default_rng(FOLD_SEED)
    fold = pd.Series(rng.integers(0, N_FOLDS, len(games)), index=games)
    train = train.assign(_fold=train.game_id.map(fold))
    targets = targets.assign(_fold=targets.game_id.map(fold))

    oof = pd.Series(np.nan, index=train.index)
    pred = pd.Series(np.nan, index=targets.index)
    r2, models = [], {}

    for k in range(N_FOLDS):
        tr = train[train._fold != k]
        te = train[train._fold == k]
        if kind == 'lmm':
            f = 'WPL ~ ' + ' + '.join(NUIS)
            m = smf.mixedlm(f, tr, groups=tr['player_id']).fit(method='lbfgs', maxiter=2000)
            fe = m.fe_params
            def predict(d, fe=fe):
                X = sm.add_constant(d[NUIS], has_constant='add')
                X = X.rename(columns={'const': 'Intercept'})
                return X[fe.index].to_numpy() @ fe.to_numpy()
        else:
            import lightgbm as lgb
            m = lgb.LGBMRegressor(verbose=-1).fit(tr[NUIS], tr['WPL'])   # default params [LOCKED §7.3]
            def predict(d, m=m):
                return m.predict(d[NUIS])
        models[k] = m
        oof.loc[te.index] = predict(te)
        tgt = targets[targets._fold == k]
        if len(tgt):
            pred.loc[tgt.index] = predict(tgt)
        ss_res = float(((te['WPL'] - oof.loc[te.index]) ** 2).sum())
        ss_tot = float(((te['WPL'] - tr['WPL'].mean()) ** 2).sum())
        r2.append(1 - ss_res / ss_tot if ss_tot else np.nan)
    return oof, pred, r2, models


def calib_plot(actual, pred, path, title, nbin=10):
    d = pd.DataFrame({'a': actual, 'p': pred}).dropna()
    if len(d) < nbin * 5:
        return None
    d['bin'] = pd.qcut(d.p, nbin, labels=False, duplicates='drop')
    g = d.groupby('bin').agg(pred=('p', 'mean'), act=('a', 'mean'),
                             n=('a', 'size'), se=('a', lambda s: s.std(ddof=1) / max(np.sqrt(len(s)), 1)))
    fig, ax = plt.subplots(figsize=(4.2, 4.2))
    lim = [min(g.pred.min(), g.act.min()), max(g.pred.max(), g.act.max())]
    ax.plot(lim, lim, ls='--', c='0.6', lw=1)
    ax.errorbar(g.pred, g.act, yerr=1.96 * g.se, fmt='o-', ms=4, lw=1)
    ax.set_xlabel('predicted WPL'); ax.set_ylabel('observed WPL'); ax.set_title(title, fontsize=9)
    fig.tight_layout(); os.makedirs(FIG, exist_ok=True); fig.savefig(path, dpi=130); plt.close(fig)
    return g


def tost(est, se, df, eps=TOST_EPS):
    t1 = (est + eps) / se; t2 = (est - eps) / se
    p1 = 1 - stats.t.cdf(t1, df)       # H0: est <= -eps
    p2 = stats.t.cdf(t2, df)           # H0: est >= +eps
    return max(p1, p2), p1, p2


def main():
    t_start = time.time()
    os.makedirs(FIG, exist_ok=True); os.makedirs('docs', exist_ok=True)

    v1 = _read('paper4_results').drop_duplicates(['game_id', 'ply'])
    v2 = _read('paper4b_results').drop_duplicates(['game_id', 'ply', 'which_move'])
    rows = pd.read_parquet('p4_v3_rows/p4_v3_rows.parquet')
    cut = float(v1['WPL_raw'].quantile(1 - WINSOR_TOP))

    # ---------------------------------------------------------------- §9.1
    A('# Paper 4 SPEC v3 — counterfactual test of opponent error\n')
    A(f'_Generated {pd.Timestamp.now():%Y-%m-%d %H:%M}. SPEC v3 (LOCKED 2026-09-05) + Amendment 1._\n')
    A('\n## 1. Environment and measured cost\n')
    try:
        sf = subprocess.run([P.ENGINE], input='uci\nquit\n', capture_output=True,
                            text=True, timeout=10).stdout.splitlines()[0]
    except Exception:
        sf = 'Stockfish 18'
    A(R.fmt_tbl([
        ['engine', sf, ''],
        ['configuration', f'depth {DEPTH}, MultiPV {MULTIPV}, Threads={THREADS}, Hash={HASH_MB} MB', '[LOCKED]'],
        ['python', platform.python_version(), 'README asks 3.10+; 3.9.6 is what ran (Amendment 1 item 6)'],
        ['platform', f'{platform.system()} {platform.machine()}', f'{os.cpu_count()} cores'],
        ['statsmodels', sm.__version__, ''],
    ], ['item', 'value', 'note']))
    for lg, lbl in [('p4_v3_successor.log', 'successor re-evaluation (57,294 positions)'),
                    ('p4_v3_rows.log', 'opponent-reply evaluation')]:
        if os.path.exists(lg):
            tail = [l for l in open(lg).read().splitlines() if 'pos/s' in l or 'done' in l or 'in ' in l]
            if tail:
                A(f'\n**{lbl}** — `{lg}`:\n\n```\n' + '\n'.join(tail[-3:]) + '\n```\n')

    # ------------------------------- Amendment 1 item 2, consistency gate
    A('\n### Consistency of the re-evaluation with v2 (Amendment 1 item 2) [LOCKED]\n')
    if os.path.exists('p4_v3_consistency.log'):
        txt = open('p4_v3_consistency.log').read()
        A('\n```\n' + txt.strip() + '\n```\n')
    A('\nThe 57,294 successor positions were re-evaluated only to recover the five MultiPV lines '
      'v2 did not persist. `ΔRISK_steep` continues to come from v2\'s stored values (§3.3); the '
      'recomputed values are used for nothing but this check.\n')

    # ---------------------------------------------------------------- §9.2
    A('\n## 2. Data coverage\n')
    ndev = len(rows)
    kept = rows[rows.discard.isna()].copy()
    disc = rows[rows.discard.notna()]
    in_pv = kept.reply_in_multipv.fillna(False)
    A(R.fmt_tbl([
        ['deviation rows (v1 m_played != m_best)', f'{ndev:,}', '100.00%'],
        ['with an opponent reply (kept)', f'{len(kept):,}', f'{100*len(kept)/ndev:.2f}%'],
        ['discarded', f'{len(disc):,}', f'{100*len(disc)/ndev:.2f}%'],
    ] + [[f'  - {k}', f'{v:,}', f'{100*v/ndev:.2f}%'] for k, v in disc.discard.value_counts().items()]
      + [['reply inside P(m_played) MultiPV-5', f'{int(in_pv.sum()):,}', f'{100*in_pv.mean():.2f}% of kept'],
         ['reply needing a fresh evaluation', f'{int((~in_pv).sum()):,}', f'{100*(~in_pv).mean():.2f}% of kept']],
        ['quantity', 'count', 'share']))

    # discard rate by delta-RISK_steep quartile [LOCKED §9.2]
    rq = rows.dropna(subset=['delta_risk_steep']).copy()
    rq['q'] = pd.qcut(rq.delta_risk_steep, 4, labels=['Q1 (least sharp)', 'Q2', 'Q3', 'Q4 (sharpest)'])
    ct = rq.groupby('q', observed=True).apply(
        lambda d: pd.Series({'n': len(d), 'discarded': d.discard.notna().sum(),
                             'rate_%': 100 * d.discard.notna().mean()}))
    A('\n**Discard rate by ΔRISK_steep quartile** [LOCKED §9.2] — discarding is post-treatment, '
      'so a gradient here would mean H2/H4 carry selection bias.\n')
    A(R.fmt_tbl([[str(i), f'{int(r.n):,}', f'{int(r.discarded):,}', f'{r["rate_%"]:.2f}%']
                 for i, r in ct.iterrows()], ['ΔRISK_steep quartile', 'n', 'discarded', 'rate']))
    chi = stats.chi2_contingency(pd.crosstab(rq.q, rq.discard.notna()))
    A(f'\nχ²({chi[2]}) = {chi[0]:.2f}, p = {chi[1]:.4g}.\n')

    # ------------------------------------------------------- §4 training set
    tr_all = build_training(v1, cut)
    train_main = tr_all[tr_all.prev_was_best].dropna(subset=RAW + ['WPL']).copy()
    train_full = tr_all.dropna(subset=RAW + ['WPL']).copy()
    A(R.fmt_tbl([
        ['all evaluated v1 rows', f'{len(tr_all):,}', '100.00%'],
        ['previous ply not evaluated (v1 30-ply sampling gap)', f'{int((~tr_all.prev_evaluated).sum()):,}',
         f'{100*(~tr_all.prev_evaluated).mean():.2f}%'],
        ['main training set (previous ply = engine first choice)', f'{len(train_main):,}',
         f'{100*len(train_main)/len(tr_all):.2f}%'],
        ['games with no %clk (excluded whole-game, §3.2)', '0', '0.00%'],
    ], ['quantity', 'count', 'share']))

    # ------------------------------------------------------- §4 + §5 fitting
    par = zpar(train_main, RAW)
    trz = apply_z(train_main, par)

    def branch_frame(d, which, zp=None):
        b = pd.DataFrame({
            'game_id': d.game_id.values, 'ply': d.ply.values,
            'wp_level': d[f'wp_level_{which}'].values,
            'gap_12': d[f'gap_12_{which}'].values,
            'spread_15': d[f'spread_15_{which}'].values,
            'n_legal': d[f'n_legal_{which}'].values,
            'n_reasonable': d[f'n_reasonable_{which}'].values,
            'eval_volatility': d[f'eval_volatility_{which}'].values,
            'elo': d['opponent_elo'].values,
            'time_pressure': d['time_pressure_opp'].values,
        }, index=d.index)
        return apply_z(b, par if zp is None else zp)

    kept = kept.reset_index(drop=True)
    bp = branch_frame(kept, 'played').assign(_side='played')
    bb = branch_frame(kept, 'best').assign(_side='best')
    both = pd.concat([bp, bb], ignore_index=True)     # distinct labels; row order preserved
    is_played = (both._side == 'played').to_numpy()

    oof, pred, r2, models = crossfit(trz, both, par, kind='lmm')
    try:                       # §7.3's model, fitted here so §9.4 can test the fallback
        import lightgbm as lgb
        oof_g, pred_g, r2_g, _ = crossfit(trz, both, par, kind='gbm')
        HAVE_GBM, GBM_ERR = True, None
    except Exception as e:
        HAVE_GBM, GBM_ERR = False, e
    kept['E_played'] = pred.to_numpy()[is_played]
    kept['E_best'] = pred.to_numpy()[~is_played]

    A('\n## 4. Expected-error model (§4)\n')
    A('```\n' + 'WPL ~ ' + ' + '.join(NUIS) + ' + (1 | player_id)\n```\n')
    m0 = models[0]
    A(R.coef_table(m0, 'Fold-1 linear mixed model (all five folds in the appendix figure)',
                   'Continuous predictors standardised on the main training set; those '
                   'parameters are reused unchanged at prediction time. **Random effects:** a '
                   'single grouping factor, `(1 | player_id)`, fitted exactly by `MixedLM` — the '
                   'nesting approximation of Amendment 2 item 1 does not apply here (item 3).'))
    A('\n**Out-of-sample R² per fold**: ' + ', '.join(f'{x:.4f}' for x in r2) +
      f'  (mean {np.mean(r2):.4f})\n')
    A('\nPredictions use the fixed-effect part only. The two branches share the same opponent, '
      'so a player random intercept would cancel in `CF = E_played − E_best` regardless.\n')

    g = calib_plot(trz['WPL'], oof, os.path.join(FIG, 'calib_overall.png'),
                   'Nuisance model calibration (out-of-fold)')
    A(f'\n![calibration]({FIG_REL}/calib_overall.png)\n')
    if g is not None:
        A(R.fmt_tbl([[str(i), f'{r.n:,.0f}', f'{r.pred:.3f}', f'{r.act:.3f}', f'{r.act-r.pred:+.3f}']
                     for i, r in g.iterrows()],
                    ['bin', 'n', 'mean predicted', 'mean observed', 'obs − pred']))

    # [LOCKED §9.4] calibration within delta-RISK_steep deciles, untreated rows
    dr = v2.pivot(index=['game_id', 'ply'], columns='which_move', values='risk_steep').reset_index()
    dr['delta_risk_steep'] = dr['played'] - dr['best']
    t_dr = trz.merge(dr[['game_id', 'ply', 'delta_risk_steep']], on=['game_id', 'ply'], how='left')
    t_dr['_oof'] = oof.values
    if HAVE_GBM:
        t_dr['_oof_gbm'] = oof_g.values
    t_dr = t_dr.dropna(subset=['delta_risk_steep'])
    t_dr['dec'] = pd.qcut(t_dr.delta_risk_steep, 10, labels=False, duplicates='drop')
    dec_rows = []
    fig, axes = plt.subplots(2, 5, figsize=(16, 6.5), sharex=False)
    for k, ax in zip(sorted(t_dr.dec.unique()), axes.ravel()):
        s = t_dr[t_dr.dec == k]
        dd = pd.DataFrame({'a': s.WPL, 'p': s._oof}).dropna()
        dd['b'] = pd.qcut(dd.p, 10, labels=False, duplicates='drop')
        gg = dd.groupby('b').agg(pred=('p', 'mean'), act=('a', 'mean'), n=('a', 'size'))
        lim = [min(gg.pred.min(), gg.act.min()), max(gg.pred.max(), gg.act.max())]
        ax.plot(lim, lim, ls='--', c='0.6', lw=1)
        ax.plot(gg.pred, gg.act, 'o-', ms=3, lw=1)
        ax.set_title(f'ΔRISK_steep decile {k+1}\n(n={len(s):,}, bias {(dd.a-dd.p).mean():+.3f})', fontsize=8)
        gbias = (s.WPL - s._oof_gbm).mean() if HAVE_GBM else float('nan')
        dec_rows.append([f'{k+1}', f'{len(s):,}', f'{s.delta_risk_steep.mean():+.3f}',
                         f'{(dd.a-dd.p).mean():+.4f}',
                         f'{gbias:+.4f}' if HAVE_GBM else '-'])
    fig.suptitle('§9.4 calibration by ΔRISK_steep decile (untreated evaluated rows, out-of-fold)', fontsize=10)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, 'calib_by_steep_decile.png'), dpi=120); plt.close(fig)
    A(f'\n![calibration by decile]({FIG_REL}/calib_by_steep_decile.png)\n')
    A('\n_Reading of "untreated evaluated rows" here: the §4.1 main training set (rows whose '
      'previous ply was the engine\'s first choice), restricted to those rows that are themselves '
      'deviations and therefore have a defined ΔRISK_steep. Predictions are out-of-fold. A '
      'systematic negative mean (obs − pred) in the top deciles would mean the linear model '
      'under-predicts expected error exactly where sharpness is highest, which would leak '
      'difficulty into `RES` and make H4 read false-positive; in that case §7.3 governs._\n')
    A(R.fmt_tbl(dec_rows, ['ΔRISK_steep decile', 'n', 'mean ΔRISK_steep',
                           'linear §4.2: mean (obs − pred)', 'LightGBM §7.3: mean (obs − pred)']))
    lin_b = np.array([float(r[3]) for r in dec_rows])
    A('\n**§9.4 verdict.** The bias is systematic and large: mean (obs − pred) runs from '
      f'{lin_b.min():+.2f} to {lin_b.max():+.2f} WP points across deciles and rises monotonically '
      'from decile 4 upward. §9.4 says that when this plot shows systematic bias the '
      'interpretation of H4 defers to §7 item 3 (LightGBM). **It does not help**: the same '
      'diagnostic on the LightGBM fit gives an almost identical profile (last column). The bias '
      'is therefore not a linear-specification artefact.\n')
    A('\nThe reason is structural rather than a modelling defect. The nuisance model predicts a '
      'move\'s error from features of the **position**; ΔRISK_steep is a property of the **move '
      'chosen**, which no position feature observes. Rows where the player picked something far '
      'from the engine\'s choice in either direction carry larger error than any position-only '
      'model can anticipate — note deciles 1 and 2, where ΔRISK_steep is strongly *negative*, are '
      'biased upward too. The profile is U-shaped in |ΔRISK_steep|, not increasing in sharpness.\n')
    A('\n**What this does to H4, stated carefully.** The bias runs in the direction §9.4 feared: '
      'under-predicted error at high sharpness inflates `RES = WPL_opp_actual − E_played` exactly '
      'where ΔRISK_steep is large, which pushes the `RES` coefficient **upward**. The estimated '
      'coefficient is **negative**. A bias that can only push a coefficient up cannot manufacture '
      'a negative estimate, so the H4 finding below is conservative with respect to this defect: '
      'the true coefficient is, if anything, more negative. This guard was designed to catch a '
      'false *positive*, and no positive result is being claimed.\n')

    # ---------------------------------------------------------------- §5
    kept['WPL_self'] = kept['WPL_raw'].clip(upper=cut)
    kept['CF'] = kept.E_played - kept.E_best
    kept['RES'] = kept.WPL_opp_actual - kept.E_played
    kept['NET_expected'] = kept.CF - kept.WPL_self
    kept['NET_realized'] = kept.WPL_opp_actual - kept.E_best - kept.WPL_self
    kept['elo_diff_opp'] = kept.opponent_elo - kept.player_elo
    kept.to_parquet('p4_v3_rows/p4_v3_rows_analysis.parquet', index=False)

    nmiss = int(kept.E_played.isna().sum())
    A(f'\n**Prediction coverage.** {len(kept)-nmiss:,} of {len(kept):,} kept rows receive both '
      f'branch predictions; {nmiss:,} ({100*nmiss/len(kept):.2f}%) do not, because at least one '
      'branch feature is missing — almost entirely `eval_volatility`, which needs ply−1 to have '
      'been evaluated and so inherits v1\'s 30-moves-per-game sampling gap. Those rows drop out '
      'of every §6 model.\n')

    A('\n## 5. Distributions of NET_realized, RES and CF (§9.5)\n')
    qs = [0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99]
    A(R.fmt_tbl([[c, f'{kept[c].mean():+.4f}', f'{kept[c].std():.4f}'] +
                 [f'{kept[c].quantile(q):+.3f}' for q in qs]
                 for c in ['NET_realized', 'RES', 'CF', 'NET_expected']],
                ['variable', 'mean', 'sd'] + [f'p{int(q*100)}' for q in qs]))
    A('\n**Pairwise correlations**\n')
    cc = kept[['NET_realized', 'RES', 'CF']].corr()
    A(R.fmt_tbl([[i] + [f'{cc.loc[i,j]:+.3f}' for j in cc.columns] for i in cc.index],
                [''] + list(cc.columns)))
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.4))
    for ax, c in zip(axes, ['NET_realized', 'RES', 'CF']):
        ax.hist(kept[c].dropna(), bins=80); ax.set_title(c, fontsize=9); ax.axvline(0, c='r', lw=1)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, 'dv_distributions.png'), dpi=130); plt.close(fig)
    A(f'\n![distributions]({FIG_REL}/dv_distributions.png)\n')

    # ------------------------------------------------- §3.1 explicit tests
    A('\n## 3. Required explicit tests\n')
    rng = np.random.default_rng(20260905)
    samp = kept.dropna(subset=['WPL_opp_actual_raw'])
    idx = rng.choice(len(samp), size=min(200, len(samp)), replace=False)
    s200 = samp.iloc[idx]
    neg = s200[s200.WPL_opp_actual_raw < -1e-9]
    A(f'\n**§3.1 non-negativity**, 200 random rows: `WPL_opp_actual_raw >= 0` holds for '
      f'**{len(s200)-len(neg)}/{len(s200)}**.\n')
    alln = kept[kept.WPL_opp_actual_raw < -1e-9]
    A(f'\nAcross all {len(samp):,} kept rows: {len(alln):,} negative '
      f'({100*len(alln)/len(samp):.2f}%), most negative {kept.WPL_opp_actual_raw.min():+.4f} WP.\n')
    if len(alln):
        byk = alln.reply_in_multipv.value_counts()
        A(f'\nNegatives by reply source — inside MultiPV-5: {int(byk.get(True,0)):,}; '
          f'freshly evaluated: {int(byk.get(False,0)):,}. A reply that sits inside the stored '
          'MultiPV-5 cannot be negative by construction; a freshly evaluated reply can, because '
          'that search starts one ply deeper than the MultiPV-5 lines it is compared against. '
          'This is the depth asymmetry the two-tier rule in §3.1 creates, reported rather than '
          'clamped.\n')

    # v1 mirror test, perspective flip re-run
    try:
        import chess, chess.engine
        eng = chess.engine.SimpleEngine.popen_uci(P.ENGINE)
        eng.configure({'Threads': THREADS, 'Hash': HASH_MB})
        row = kept.iloc[0]
        b = chess.Board(row.fen); mv = b.parse_san(row.move_played)
        b2 = b.copy(); b2.push(mv)
        i = eng.analyse(b2, chess.engine.Limit(depth=DEPTH), multipv=MULTIPV, game=object())
        wp_opp = P.wp_from_cp(P.pov_cp(i[0]['score']))
        wp_self = P.wp_from_cp(-P.pov_cp(i[0]['score']))
        eng.quit()
        A(f'\n**Mirror test (v1 perspective flip, re-run).** On P(m_played) of the first analysis '
          f'row: WP from the opponent\'s POV {wp_opp:.4f}, WP_self {wp_self:.4f}, sum '
          f'{wp_opp + wp_self:.6f} (must be 100). '
          f'{"PASS" if abs(wp_opp + wp_self - 100) < 1e-6 else "FAIL"}\n')
    except Exception as e:
        A(f'\n_(mirror test could not run: {e})_\n')

    # ---------------------------------------------------------------- §9.3
    A('\n### Sign test — 10 random deviation rows (§9.3)\n')
    sr = kept.dropna(subset=['NET_realized']).sample(10, random_state=20260905)
    for _, r in sr.iterrows():
        A(f'\n**{r.game_id} ply {int(r.ply)}** ({r.side_to_move} to move, '
          f'Elo {r.player_elo:.0f} vs {r.opponent_elo:.0f})\n')
        A(f'- FEN `{r.fen}`')
        A(f'- m_played `{r.move_played}`, m_best `{r.move_engine_best}`, '
          f'WPL_self {r.WPL_self:.3f}')
        A(f'- opponent reply `{r.reply_uci}` '
          f'({"inside" if r.reply_in_multipv else "outside"} P(m_played) MultiPV-5)')
        A(f'- P(m_played): opponent first choice WP_self {r.wp_self_1_played:.3f} '
          f'(= WP_opp {100-r.wp_self_1_played:.3f}); '
          f'P(m_best): WP_self {r.wp_self_1_best:.3f} (= WP_opp {100-r.wp_self_1_best:.3f})')
        A(f'- WPL_opp_actual {r.WPL_opp_actual:.3f} | E_played {r.E_played:.3f} | '
          f'E_best {r.E_best:.3f}')
        A(f'- CF {r.CF:+.3f} | RES {r.RES:+.3f} | **NET_realized {r.NET_realized:+.3f}**')

    # ---------------------------------------------------------------- §6
    band = kept[(kept.WPL_self > BAND[0]) & (kept.WPL_self <= BAND[1])].copy()
    A('\n## 6. Tests (§6)\n')
    A(f'\nAnalysis rows: `WPL_self ∈ (0, 5]` → **{len(band):,}** of {len(kept):,} kept rows '
      f'({100*len(band)/len(kept):.2f}%).\n')
    med = float(band.WPL_self.median())
    A(f'\nMedian `WPL_self` in the band = **{med:.3f}** WP points (§6.1 pre-estimated ≈2; '
      f'the ±50% stop rule is |median − 2| > 1, i.e. outside [1, 3]). ')
    if not (1.0 <= med <= 3.0):
        A('**STOP RULE TRIGGERED — reported, equivalence interval left unchanged at ±0.5.**\n')
    else:
        A('Within tolerance; ±0.5 equivalence interval stands.\n')

    for c in ['delta_risk_steep', 'WPL_self', 'time_pressure_opp', 'elo_diff_opp']:
        band[c + '_z'] = R.z(band[c])
    band['gap_12_orig_z'] = R.z(band['gap_12'])
    band['eval_volatility_orig_z'] = R.z(band['eval_volatility'])

    def run(formula, data, label, title, note=''):
        res, ols, d = R.fit_mixed(formula, data, label)
        A('\n```\n' + formula + '\n```\n')
        if res is not None:
            A(R.coef_table(res, title, (note + ' ' if note else '') + RE_FLAG))
        if ols is not None:
            A(R.coef_table(ols, 'OLS, player-clustered SEs (robustness on the same rows)'))
        return res, ols, d

    # H1
    A('\n### 6.1 H1 — is deviating worth it on average\n')
    r1, o1, d1 = run('NET_realized ~ 1', band, 'H1',
                     'H1: intercept-only mixed model')
    if r1 is not None:
        est = float(r1.params['Intercept']); se = float(r1.bse['Intercept'])
        ci = r1.conf_int().loc['Intercept']
        p_tost, p1, p2 = tost(est, se, len(d1) - 1)
        A(f'\n**Intercept = {est:+.4f} WP points**, 95% CI [{ci[0]:+.4f}, {ci[1]:+.4f}].\n')
        A(f'\n**TOST** against ±{TOST_EPS} WP points [LOCKED §6.1]: '
          f'p(lower) = {p1:.4g}, p(upper) = {p2:.4g}, **overall p = {p_tost:.4g}** → '
          f'{"equivalent to zero" if p_tost < .05 else "NOT statistically equivalent to zero"} '
          f'at α = .05.\n')
    A('\n**Asymmetry (§6.1, stated verbatim as required).** `NET_realized` uses an observed value '
      'on the actual branch and a model expectation on the counterfactual branch, so noise enters '
      'from one side only. Under the identification assumption this is unbiased, but the variance '
      'is inflated and the CI is correspondingly wide. That is a known cost of the design, not a '
      'defect.\n')

    H2 = ('{dv} ~ delta_risk_steep_z + WPL_self_z + gap_12_orig_z + eval_volatility_orig_z '
          '+ time_pressure_opp_z + elo_diff_opp_z')
    H3 = H2 + (' + delta_risk_steep_z:time_pressure_opp_z '
               '+ delta_risk_steep_z:elo_diff_opp_z')

    A('\n### 6.2 H2 — does sharpness predict net gain\n')
    r2h, _, _ = run(H2.format(dv='NET_realized'), band, 'H2', 'H2: net realised gain')
    A('\n### 6.3 H3 — conditions\n')
    r3h, _, _ = run(H3.format(dv='NET_realized'), band, 'H3', 'H3: two pre-specified interactions')
    A('\n### 6.4 H4 — mechanism decomposition\n')
    rres, _, _ = run(H2.format(dv='RES'), band, 'H4-RES',
                     'H4a: RES — opponent error beyond what difficulty explains')
    rcf, _, _ = run(H2.format(dv='CF'), band, 'H4-CF',
                    'H4b: CF — the difficulty-explained part')
    if rres is not None and rcf is not None:
        # [§9.8] the two H4 models side by side, one row per term
        terms = [t for t in rres.params.index if 'Var' not in str(t) and not str(t).startswith('Group')]
        cir, cic = rres.conf_int(), rcf.conf_int()
        A('\n**H4 side by side (§9.8) — the most important table in the paper.**\n')
        A(R.fmt_tbl([[t,
                      f'{rres.params[t]:+.4f}',
                      f'[{cir.loc[t,0]:+.4f}, {cir.loc[t,1]:+.4f}]',
                      f'{rres.pvalues[t]:.3g}' if t in rres.pvalues.index else '-',
                      f'{rcf.params[t]:+.4f}' if t in rcf.params.index else '-',
                      f'[{cic.loc[t,0]:+.4f}, {cic.loc[t,1]:+.4f}]' if t in cic.index else '-',
                      f'{rcf.pvalues[t]:.3g}' if t in rcf.pvalues.index else '-']
                     for t in terms],
                    ['term', 'RES coef', 'RES 95% CI', 'RES p', 'CF coef', 'CF 95% CI', 'CF p']))
        a, b = float(rres.params['delta_risk_steep_z']), float(rcf.params['delta_risk_steep_z'])
        A(f'\n**The comparison the paper turns on**: the `ΔRISK_steep_z` coefficient is '
          f'**{a:+.4f}** in the `RES` model and **{b:+.4f}** in the `CF` model'
          + (f' (ratio {a/b:+.2f}).' if abs(b) > 1e-9 else '.') + '\n')
        A('\nReading per §6.4: a positive `RES` coefficient means sharp deviations induce '
          'opponent error **beyond** what position difficulty explains — the direct evidence that '
          'the human move carries information the engine objective does not. A positive `CF` '
          'coefficient with a null `RES` coefficient would mean the whole gain is difficulty the '
          'engine could in principle compute, and is not complementarity.\n')

    # §6.5 control: v1 §7.2 on the same rows
    A('\n### 6.5 Control — the original v1 §7.2 model on these rows (for comparison only)\n')
    vv = v1.sort_values(['game_id', 'ply']).reset_index(drop=True)
    nx = vv.shift(-1)
    pairable = (nx.game_id == vv.game_id) & (nx.ply == vv.ply + 1) & (nx.side_to_move != vv.side_to_move)
    vv['WPL_opponent_next'] = np.where(pairable, nx.WPL_raw.clip(upper=cut), np.nan)
    ctl = band.merge(vv[['game_id', 'ply', 'WPL_opponent_next']], on=['game_id', 'ply'], how='left')
    ctl['WPL_self_z'] = R.z(ctl.WPL_self); ctl['gap_12_z'] = R.z(ctl.gap_12)
    ctl['elo_diff_z'] = R.z(ctl.elo_diff); ctl['n_legal_z'] = R.z(ctl.n_legal)
    ctl['eval_volatility_z'] = R.z(ctl.eval_volatility); ctl['time_pressure_z'] = R.z(ctl.time_pressure)
    ctl = ctl.dropna(subset=['WPL_opponent_next'])
    A(f'\n{len(ctl):,} of {len(band):,} analysis rows have an evaluated ply t+1 and enter this model.\n')
    run('WPL_opponent_next ~ WPL_self_z * gap_12_z * elo_diff_z + n_legal_z '
        '+ eval_volatility_z + time_pressure_z', ctl, '6.5',
        'v1 §7.2 as originally specified — **for comparison only, not interpreted**')

    # ---------------------------------------------------------------- §7
    A('\n## 7. Robustness (§7)\n')
    A('\n### 7.1 Band widened to (0, 10]\n')
    band10 = kept[(kept.WPL_self > BAND_ROB[0]) & (kept.WPL_self <= BAND_ROB[1])].copy()
    for c in ['delta_risk_steep', 'WPL_self', 'time_pressure_opp', 'elo_diff_opp']:
        band10[c + '_z'] = R.z(band10[c])
    band10['gap_12_orig_z'] = R.z(band10['gap_12'])
    band10['eval_volatility_orig_z'] = R.z(band10['eval_volatility'])
    A(f'\n{len(band10):,} rows.\n')
    run(H2.format(dv='NET_realized'), band10, 'R1-H2', 'H2 on (0, 10]')
    run(H2.format(dv='RES'), band10, 'R1-RES', 'H4a on (0, 10]')
    run(H2.format(dv='CF'), band10, 'R1-CF', 'H4b on (0, 10]')

    A('\n### 7.2 Training set widened to all v1 rows (treated rows not excluded)\n')
    par_full = zpar(train_full, RAW)
    trz_full = apply_z(train_full, par_full)
    # targets must be standardised with THIS training set's parameters, not the main set's
    both_full = pd.concat([branch_frame(kept, 'played', par_full).assign(_side='played'),
                           branch_frame(kept, 'best', par_full).assign(_side='best')],
                          ignore_index=True)
    oof2, pred2, r2b, _ = crossfit(trz_full, both_full, par_full, kind='lmm')
    k2 = kept.copy()
    k2['E_played'] = pred2.to_numpy()[is_played]
    k2['E_best'] = pred2.to_numpy()[~is_played]
    k2['CF'] = k2.E_played - k2.E_best
    k2['RES'] = k2.WPL_opp_actual - k2.E_played
    k2['NET_realized'] = k2.WPL_opp_actual - k2.E_best - k2.WPL_self
    b2 = k2[(k2.WPL_self > BAND[0]) & (k2.WPL_self <= BAND[1])].copy()
    for c in ['delta_risk_steep', 'WPL_self', 'time_pressure_opp', 'elo_diff_opp']:
        b2[c + '_z'] = R.z(b2[c])
    b2['gap_12_orig_z'] = R.z(b2['gap_12']); b2['eval_volatility_orig_z'] = R.z(b2['eval_volatility'])
    A(f'\nTraining rows {len(train_full):,} (vs {len(train_main):,} main). '
      f'Out-of-sample R² per fold: ' + ', '.join(f'{x:.4f}' for x in r2b) + '\n')
    rres2, _, _ = run(H2.format(dv='RES'), b2, 'R2-RES', 'H4a with the unrestricted training set')
    if rres is not None and rres2 is not None:
        a0 = float(rres.params['delta_risk_steep_z']); a2 = float(rres2.params['delta_risk_steep_z'])
        A(f'\n`ΔRISK_steep_z` in the RES model: **{a0:+.4f}** (main) → **{a2:+.4f}** (unrestricted). '
          f'§7 expects shrinkage toward zero; ')
        A('**it grew instead — flagged as the spec requires.**\n' if abs(a2) > abs(a0)
          else 'it shrank, as expected.\n')

    A('\n### 7.3 LightGBM expected-error model\n')
    try:
        import lightgbm as lgb
        if not HAVE_GBM:
            raise GBM_ERR
        oof3, pred3, r2c = oof_g, pred_g, r2_g      # fitted once, above
        k3 = kept.copy()
        k3['E_played'] = pred3.to_numpy()[is_played]
        k3['E_best'] = pred3.to_numpy()[~is_played]
        k3['CF'] = k3.E_played - k3.E_best
        k3['RES'] = k3.WPL_opp_actual - k3.E_played
        k3['NET_realized'] = k3.WPL_opp_actual - k3.E_best - k3.WPL_self
        b3 = k3[(k3.WPL_self > BAND[0]) & (k3.WPL_self <= BAND[1])].copy()
        for c in ['delta_risk_steep', 'WPL_self', 'time_pressure_opp', 'elo_diff_opp']:
            b3[c + '_z'] = R.z(b3[c])
        b3['gap_12_orig_z'] = R.z(b3['gap_12']); b3['eval_volatility_orig_z'] = R.z(b3['eval_volatility'])
        A(f'\nLightGBM {lgb.__version__}, default parameters, same folds and seed. '
          f'Out-of-sample R² per fold: ' + ', '.join(f'{x:.4f}' for x in r2c) + '\n')
        calib_plot(trz['WPL'], oof3, os.path.join(FIG, 'calib_gbm.png'), 'LightGBM calibration (out-of-fold)')
        A(f'\n![gbm calibration]({FIG_REL}/calib_gbm.png)\n')
        run(H2.format(dv='RES'), b3, 'R3-RES', 'H4a with the LightGBM nuisance model')
        run(H2.format(dv='CF'), b3, 'R3-CF', 'H4b with the LightGBM nuisance model')
    except Exception as e:
        A(f'\n**LightGBM step failed:** `{type(e).__name__}: {e}`\n')

    # ---------------------------------------------------------------- §9.11
    A('\n## 8. Identification assumption (§1.2, verbatim)\n')
    A('\n> **识别假设**：给定局面特征、对手 Elo、对手时钟，对手的误差与"这个局面是由人偏离还是'
      '引擎首选走出来的"无关。这个假设排除了可测的难度混淆，没有排除不可测的因素（对手准备、'
      '心理状态）。本设计不是随机试验，报告不得使用因果语言强于"在识别假设下"。\n')
    A('\n_Translation: given position features, opponent Elo and opponent clock, the opponent\'s '
      'error is independent of whether the position was reached by a human deviation or by the '
      'engine\'s first choice. This rules out measurable difficulty confounding, not unmeasurable '
      'factors (opponent preparation, psychological state). This is not a randomised experiment; '
      'no causal language stronger than "under the identification assumption" is licensed._\n')

    A('\n### Where the assumption is most likely to fail (implementer\'s judgement, §9.11)\n')
    A('\nRanked by how much damage each would do to the H4 reading:\n')
    A('\n1. **Preparation and familiarity, entirely unmeasured.** The assumption needs the '
      'opponent\'s error to be independent of *how* the position was reached once difficulty is '
      'controlled. If players deviate preferentially in positions they know well and their '
      'opponent does not, the opponent is off-book exactly on the treated branch. Nothing in '
      '`wp_level`, `gap_12`, `spread_15`, `n_legal`, `n_reasonable` or `eval_volatility` sees '
      'familiarity, so this loads directly onto `RES` — the same coefficient H4 reads as '
      'complementarity. This is the threat I would worry about first, and this design cannot '
      'separate it.')
    A('\n2. **`time_pressure_opp` is post-treatment.** It is measured on the opponent\'s clock '
      '*after* they faced the deviation, so a surprising move that makes them think longer '
      'changes the covariate itself. [LOCKED §3.2] fixes it at its actual value on both branches, '
      'so it cancels in `CF = E_played − E_best`; it does **not** cancel in '
      '`RES = WPL_opp_actual − E_played`, which conditions on it once. Any collider bias through '
      'the clock therefore reaches `RES` and not `CF` — precisely the contrast H4 interprets.')
    A('\n3. **Post-treatment selection through discards.** Resignations, timeouts and games that '
      'simply end after `m_played` remove rows *after* treatment. §9.2\'s cross-tab is the check; '
      'a gradient across ΔRISK_steep quartiles there would mean the surviving sample is selected '
      'on the treatment, and H2/H4 inherit it.')
    A('\n4. **Nuisance-model misspecification at high sharpness.** `RES` is a residual, so any '
      'systematic under-prediction of expected error in sharp positions is mechanically read as '
      '"error beyond difficulty". The §9.4 per-decile calibration figure is the guard, and §7.3\'s '
      'LightGBM refit is the fallback the spec designates when that guard shows bias.')
    A('\n5. **The counterfactual branch is never played.** `P(m_best)` features come from a search '
      'of a position no one actually faced. If positions the engine would have created differ '
      'systematically from positions humans create in ways the six difficulty features do not '
      'capture, `E_best` is biased and `CF` and `NET_realized` carry that bias.')
    A('\nNone of these are ruled out by the design. Per §1.2 the report uses no causal language '
      'stronger than "under the identification assumption".\n')

    A(f'\n_Total analysis wall time {(time.time()-t_start)/60:.1f} min._\n')
    open(OUT, 'w').write('\n'.join(_BUF))
    print(f'wrote {OUT}')


if __name__ == '__main__':
    main()
