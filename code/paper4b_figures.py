#!/usr/bin/env python3
"""Figures A/B/C for the Paper 4b full-sample report. 300 DPI PNG + vector PDF."""
import os, json, warnings
import numpy as np, pandas as pd
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import statsmodels.formula.api as smf

import paper4_pilot as V1, paper4b_pilot as B, paper4b_report as R
from paper4_report import fit_mixed, z

warnings.filterwarnings('ignore')
FIG = 'paper4b_figures'

# validated palette (scripts/validate_palette.js, light surface: ALL CHECKS PASS)
BLUE, RED = '#4C72B0', '#C44E52'
INK, MUTED, GRID = '#22242A', '#5B6068', '#D8DBE0'

plt.rcParams.update({
    'font.size': 10, 'axes.labelcolor': INK, 'text.color': INK,
    'xtick.color': MUTED, 'ytick.color': MUTED,
    'axes.edgecolor': GRID, 'axes.linewidth': 0.8,
    'figure.facecolor': 'white', 'axes.facecolor': 'white',
    'savefig.facecolor': 'white', 'pdf.fonttype': 42, 'ps.fonttype': 42,
})


def save(fig, name):
    for ext in ('png', 'pdf'):
        fig.savefig(f'{FIG}/{name}.{ext}', dpi=300, bbox_inches='tight')
    plt.close(fig)
    print(f'  wrote {FIG}/{name}.png + .pdf')


def tidy(ax, xgrid=True):
    ax.spines['top'].set_visible(False); ax.spines['right'].set_visible(False)
    ax.grid(axis='x' if xgrid else 'y', color=GRID, lw=0.7, alpha=0.9)
    ax.set_axisbelow(True)


# ------------------------------------------------------------------ data
def assemble():
    v1 = R.load_rows()
    v1['WPL'] = v1['WPL_raw'].clip(upper=v1['WPL_raw'].quantile(1 - V1.WINSOR_TOP))
    roster = set(pd.read_csv(V1.SRC_CSV, usecols=['player_id']).player_id.str.lower().unique())
    v1['in_roster'] = v1.player_id.str.lower().isin(roster)
    r4 = R.load_4b()
    w = r4.pivot_table(index=['game_id', 'ply'], columns='which_move',
                       values=['risk_steep', 'risk_var'], aggfunc='first')
    w.columns = [f'{a}_{b}' for a, b in w.columns]; w = w.reset_index()
    d = v1.merge(w, on=['game_id', 'ply'], how='left')
    same = d.move_played == d.move_engine_best
    for m in ('steep', 'var'):
        d.loc[same, f'risk_{m}_played'] = d.loc[same, f'risk_{m}_best'] = 0.0
        d[f'dRISK_{m}'] = d[f'risk_{m}_played'] - d[f'risk_{m}_best']
    return d


def prep(dd):
    dd = dd.copy()
    for c in ('WPL', 'gap_12', 'eval_volatility', 'time_pressure'):
        dd[c + '_z'] = z(dd[c])
    return dd


F41 = 'dRISK_steep ~ WPL_z + gap_12_z + eval_volatility_z + time_pressure_z'


def intercept_of(res):
    ci = res.conf_int().loc['Intercept']
    return res.params['Intercept'], ci[0], ci[1]


def pc1_slope(d, games=None):
    pc, _, _ = R.style_pc1()
    dd = d if games is None else d[d.game_id.isin(games)]
    band = (dd.WPL > 0) & (dd.WPL <= 5)
    pl = (dd[dd.in_roster & band].groupby('player_id', as_index=False)
          .agg(mean_dRISK=('dRISK_steep', 'mean')))
    pl['key'] = pl.player_id.str.lower(); pc = pc.copy(); pc['key'] = pc.player_id.str.lower()
    pl = pl.merge(pc[['key', 'PC1']], on='key', how='inner')
    m = smf.ols('mean_dRISK ~ PC1', pl).fit()
    ci = m.conf_int().loc['PC1']
    return m.params['PC1'], ci[0], ci[1], len(pl)


# ------------------------------------------------------------------ Fig A
def fig_a(d):
    band = (d.WPL > 0) & (d.WPL <= 5)
    x = d.loc[band, 'dRISK_steep'].dropna()
    nz = x[x != 0]
    pct_pos = 100 * (nz > 0).mean(); pct_neg = 100 * (nz < 0).mean()
    med = x.median()
    LIM = 40
    beyond = int((x.abs() > LIM).sum())

    fig, ax = plt.subplots(figsize=(8.8, 4.8))
    bins = np.linspace(-LIM, LIM, 121)          # values outside are excluded, not piled up
    ax.hist(x[x < 0], bins=bins, color=BLUE, alpha=.92, label='flatter than engine  (lower risk)')
    ax.hist(x[x >= 0], bins=bins, color=RED, alpha=.92, label='sharper than engine  (higher risk)')
    ax.axvline(0, color=INK, lw=1.4, zorder=5)

    ymax = ax.get_ylim()[1]
    ax.set_ylim(0, ymax * 1.06)
    # median marked with a caret rather than a second vertical line: it sits only
    # 0.6 WP from zero and two near-coincident rules read as one thick line
    ax.plot([med], [ymax * 1.005], marker='v', ms=9, color=INK, clip_on=False, zorder=7)
    ax.annotate(f'median {med:+.3f}', xy=(med, ymax * 1.005), xytext=(9, 1),
                textcoords='offset points', ha='left', va='center',
                fontsize=10, fontweight='bold', color=INK)

    ax.text(-LIM * 0.96, ymax * 0.62, f'{pct_neg:.2f}%\nflatter', color=BLUE,
            fontsize=14, fontweight='bold', ha='left', va='top', linespacing=1.25)
    ax.text(LIM * 0.96, ymax * 0.62, f'{pct_pos:.2f}%\nsharper', color=RED,
            fontsize=14, fontweight='bold', ha='right', va='top', linespacing=1.25)

    ax.set_xlim(-LIM, LIM)
    ax.set_xlabel('ΔRISK_steep  =  RISK(move played) − RISK(engine best)   [WP points]')
    ax.set_ylabel('position-moves')
    ax.set_title('Human deviations land on sharper positions, not flatter ones',
                 fontsize=13.5, fontweight='bold', loc='left', pad=34)
    ax.text(0, 1.075, f'All 1,970 games · §4.1 sample (WPL ∈ (0,5]) · n = {len(x):,} · '
                      f'sign test p = 1.8e-170',
            transform=ax.transAxes, fontsize=9.5, color=MUTED, va='bottom')
    ax.text(0, 1.018, f'{beyond:,} moves ({100*beyond/len(x):.1f}%) fall beyond ±{LIM} WP and are '
                      f'outside the plotted range; they are included in every statistic shown.',
            transform=ax.transAxes, fontsize=8.6, color=MUTED, va='bottom')
    tidy(ax, xgrid=False)
    ax.legend(frameon=False, loc='upper left', bbox_to_anchor=(0.015, 0.93), fontsize=9.5)
    save(fig, 'figA_drisk_distribution')


# ------------------------------------------------------------------ Fig B
def fig_b(d):
    g500 = set(pd.read_csv('paper4b_cache/pilot4b_sample_games_500.csv',
                           dtype={'game_id': str}).game_id)
    band = (d.WPL > 0) & (d.WPL <= 5)
    r_full, _, _ = fit_mixed(F41, prep(d[band]), 'figB-full')
    r_500, _, _ = fit_mixed(F41, prep(d[band & d.game_id.isin(g500)]), 'figB-500')
    i500, i500lo, i500hi = intercept_of(r_500)
    ifull, ifulllo, ifullhi = intercept_of(r_full)
    s500, s500lo, s500hi, n500 = pc1_slope(d, g500)
    sfull, sfulllo, sfullhi, nfull = pc1_slope(d)

    fig, axes = plt.subplots(1, 2, figsize=(12.4, 3.9))
    fig.subplots_adjust(wspace=0.46)
    panels = [
        (axes[0], '§4.1 intercept — holds',
         'Deviations stay sharper than the engine; 4× more data barely moves it',
         [(i500, i500lo, i500hi, f'500 games'), (ifull, ifulllo, ifullhi, '1,970 games')],
         'ΔRISK_steep intercept  [WP points]'),
        (axes[1], '§4.2 style slope — collapses',
         f'Estimate shrinks ~69% and its CI crosses zero ({n500}→{nfull} players)',
         [(s500, s500lo, s500hi, '500 games'),
          (sfull, sfulllo, sfullhi, '1,970 games')],
         'PC1 slope on player mean ΔRISK_steep'),
    ]
    for ax, title, sub, pts, xlab in panels:
        ys = [1, 0]                                   # first row on top
        for y, (v, lo, hi, lab) in zip(ys, pts):
            crosses = lo < 0 < hi
            col = RED if crosses else BLUE
            ax.plot([lo, hi], [y, y], color=col, lw=2.8, solid_capstyle='round', zorder=3)
            ax.plot([v], [y], 'D' if crosses else 'o', ms=10, color=col,
                    mec='white', mew=1.6, zorder=4)
            ax.annotate(f'{v:+.3f}   [{lo:+.3f}, {hi:+.3f}]', xy=(v, y),
                        xytext=(0, 14), textcoords='offset points', ha='center',
                        fontsize=9.6, color=INK,
                        fontweight='normal' if crosses else 'bold')
        ax.axvline(0, color=INK, lw=1.3, zorder=2)
        ax.set_yticks(ys); ax.set_yticklabels([p[3] for p in pts], fontsize=10.5, color=INK)
        ax.set_ylim(-0.38, 1.55)
        ax.set_xlabel(xlab, fontsize=10)
        ax.set_title(title, fontsize=12.5, fontweight='bold', loc='left', pad=30)
        ax.text(0, 1.045, sub, transform=ax.transAxes, fontsize=9.3, color=MUTED, va='bottom')
        lo_all = min(p[1] for p in pts); hi_all = max(p[2] for p in pts)
        pad = (hi_all - lo_all) * .18
        ax.set_xlim(min(lo_all - pad, -pad * .5), hi_all + pad)
        tidy(ax)
    fig.legend(handles=[
        Line2D([], [], marker='o', ls='-', color=BLUE, ms=9, lw=2.8, label='95% CI excludes zero'),
        Line2D([], [], marker='D', ls='-', color=RED, ms=8, lw=2.8, label='95% CI includes zero')],
        frameon=False, fontsize=9.5, loc='lower center', bbox_to_anchor=(0.5, -0.22), ncol=2)
    fig.suptitle('One result survived the full sample; the other did not',
                 fontsize=14, fontweight='bold', x=0.062, ha='left', y=1.12)
    save(fig, 'figB_pilot_vs_full')
    return dict(i500=i500, ifull=ifull, s500=s500, sfull=sfull, nfull=nfull, n500=n500)


# ------------------------------------------------------------------ Fig C
def fig_c(d):
    import chess
    band = (d.WPL > 0) & (d.WPL <= 5)
    bandr = (d.WPL > 0) & (d.WPL <= 10)
    d41 = prep(d[band])

    r_pri, _, _ = fit_mixed(F41, d41, 'figC-primary')
    dv = d41.assign(dRISK_var=d[band].dRISK_var.values)
    r_var, _, _ = fit_mixed(F41.replace('dRISK_steep', 'dRISK_var'), dv, 'figC-var')
    r_10, _, _ = fit_mixed(F41, prep(d[bandr]), 'figC-band10')

    VAL = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9}
    def feats(row):
        pb = chess.Board(row['fen'])
        mp = pb.parse_san(row['move_played']); mb = pb.parse_san(row['move_engine_best'])
        tm = lambda b: sum(VAL[p]*(len(b.pieces(p, chess.WHITE))+len(b.pieces(p, chess.BLACK)))
                           for p in VAL)
        t0 = tm(pb)
        ap = pb.copy(); ap.push(mp); ab = pb.copy(); ab.push(mb)
        return pd.Series({'played_is_capture': float(pb.is_capture(mp)),
                          'dmat': (tm(ap)-t0) - (tm(ab)-t0)})
    ff = d[band][['fen', 'move_played', 'move_engine_best']].apply(feats, axis=1)
    dg = d41.join(ff)
    dg['played_is_capture_c'] = dg.played_is_capture - dg.played_is_capture.mean()
    dg['dmat_c'] = dg.dmat - dg.dmat.mean()
    r_liq, _, _ = fit_mixed(F41 + ' + played_is_capture_c + dmat_c', dg, 'figC-liq')

    # moderation: predicted mean at +/-2 SD time pressure (delta method)
    cov = r_pri.cov_params(); b0 = r_pri.params['Intercept']; bt = r_pri.params['time_pressure_z']
    def pred(zz):
        v = (cov.loc['Intercept', 'Intercept'] + zz**2*cov.loc['time_pressure_z', 'time_pressure_z']
             + 2*zz*cov.loc['Intercept', 'time_pressure_z'])
        se = np.sqrt(v); p = b0 + bt*zz
        return p, p - 1.96*se, p + 1.96*se

    rows = [
        ('§4.1 primary  ΔRISK_steep, WPL ∈ (0,5]', *intercept_of(r_pri), 'model'),
        ('§4.3a  ΔRISK_var  (different DV scale)', *intercept_of(r_var), 'model'),
        ('§4.3b  ΔRISK_steep, WPL ∈ (0,10]', *intercept_of(r_10), 'model'),
        ('liquidation-controlled  (+capture, +dmat)', *intercept_of(r_liq), 'model'),
        ('time pressure  −2 SD  (little time left)', *pred(-2), 'mod'),
        ('time pressure  +2 SD  (lots of time)', *pred(+2), 'mod'),
    ]

    fig, ax = plt.subplots(figsize=(9.6, 5.4))
    ys = list(range(len(rows)))[::-1]
    for y, (lab, v, lo, hi, kind) in zip(ys, rows):
        col = BLUE if kind == 'model' else RED
        mk = 'o' if kind == 'model' else 's'
        ax.plot([lo, hi], [y, y], color=col, lw=2.6, solid_capstyle='round', zorder=3)
        ax.plot([v], [y], mk, ms=10, color=col, mec='white', mew=1.6, zorder=4)
        ax.annotate(f'{v:+.3f}  [{lo:+.3f}, {hi:+.3f}]', xy=(v, y), xytext=(0, 13),
                    textcoords='offset points', ha='center', fontsize=9.3, color=INK)
    ax.axvline(0, color=INK, lw=1.3, zorder=2)
    div = (ys[3] + ys[4]) / 2
    ax.axhline(div, color=GRID, lw=1.2, ls=(0, (4, 3)), zorder=1)
    ax.set_yticks(ys); ax.set_yticklabels([r[0] for r in rows], fontsize=10, color=INK)
    ax.set_ylim(min(ys) - 0.7, max(ys) + 0.75)
    hi_max = max(r[3] for r in rows)
    ax.set_xlim(-0.16, hi_max * 1.30)
    ax.set_xlabel('predicted mean ΔRISK_steep  [WP points]   —   positive = sharper than engine')
    fig.suptitle('Every specification puts the effect on the same side of zero',
                 fontsize=13.5, fontweight='bold', x=0.012, ha='left', y=1.10)
    fig.text(0.012, 1.035, 'Full sample, all 1,970 games. Model rows are conditional means at '
                           'sample-average covariates; the two lower rows are predictions from '
                           'the §4.1 fit.',
             fontsize=9.4, color=MUTED, va='bottom', ha='left')
    ax.text(hi_max * 1.28, div - 0.12, 'moderation gradient', ha='right', va='top',
            fontsize=9.2, color=RED, style='italic')
    tidy(ax)
    save(fig, 'figC_robustness_ladder')
    return rows


if __name__ == '__main__':
    os.makedirs(FIG, exist_ok=True)
    print('assembling…')
    d = assemble()
    print(f'  {len(d):,} rows / {d.game_id.nunique():,} games')
    fig_a(d)
    chk = fig_b(d)
    rows = fig_c(d)
    # verify against the published report numbers
    print('\nconsistency check vs report:')
    for name, got, want in [('§4.1 intercept full', chk['ifull'], 1.2155),
                            ('§4.1 intercept 500', chk['i500'], 1.1658),
                            ('§4.2 PC1 slope full', chk['sfull'], 0.1605),
                            ('§4.2 PC1 slope 500', chk['s500'], 0.5207),
                            ('§4.3a RISK_var', rows[1][1], 0.4491),
                            ('§4.3b band(0,10]', rows[2][1], 1.4749),
                            ('liquidation-controlled', rows[3][1], 1.2146)]:
        ok = abs(got - want) < 0.002
        print(f'  [{"OK " if ok else "MISMATCH"}] {name:26s} got {got:+.4f}  want {want:+.4f}')
