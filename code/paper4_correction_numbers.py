#!/usr/bin/env python3
"""
paper4_correction_numbers.py — writes docs/paper4_correction_numbers.md: every number quoted in
docs/Sharper_Not_Safer_v7.docx that comes from a mixed model, old and new side by side, with its
location in the paper.

Old = the unchanged fit_mixed re-executed on the rebuilt rows, which reproduces the published
reports to printed precision (docs/paper4_correction_REPORT.md §4.1). New = fit_mixed_v2 on the
same rows. Every value is formatted from the runner's JSON, not retyped.

    python3 paper4_correction_run.py predict --work WORK
    python3 paper4_correction_run.py numbers --work WORK
"""
import os, json, time

CODE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(CODE)
SUP = str.maketrans('-0123456789', '⁻⁰¹²³⁴⁵⁶⁷⁸⁹')


# ---------------------------------------------------------------- formatting in the paper's style
def signed(x, k):
    return f'{x:+.{k}f}'.replace('-', '−')


def fmt(v, spec):
    kind, k = spec[0], spec[1]
    pre = spec[2] if len(spec) > 2 else ''
    if kind == 'f':                                   # signed fixed: +1.216, −0.235
        return pre + signed(v, k)
    if kind == 'u':                                   # magnitude: 1.722
        return pre + f'{v:.{k}f}'
    if kind == 'sci':                                 # p = 1.6 × 10⁻³⁵
        m, e = f'{v:.{k - 1}e}'.split('e')
        return pre + f'{m} × 10{str(int(e)).translate(SUP)}'
    if kind == 'pdec':                                # p = .0012
        return pre + f'{v:.{k}g}'.lstrip('0')
    if kind == 'pct':                                 # 27%
        return pre + f'{100 * v:.{k}f}%'
    if kind == 'ci':                                  # [−0.521, −0.146]
        return pre + f'[{signed(v[0], k)}, {signed(v[1], k)}]'
    if kind == 'eci':                                 # +1.166 [+0.787, +1.544]
        return pre + f'{signed(v[0], k)} [{signed(v[1], k)}, {signed(v[2], k)}]'
    if kind == 'excl':                                # both CIs exclude zero
        return 'both CIs exclude zero' if all(lo > 0 or hi < 0 for lo, hi in v) else 'not both exclude zero'
    raise ValueError(kind)


def full(v, spec):
    kind = spec[0]
    if kind in ('sci', 'pdec'):
        return f'{v:.4g}'
    if kind == 'pct':
        return f'{100 * v:.3f}%'
    if kind == 'ci':
        return f'[{v[0]:+.6f}, {v[1]:+.6f}]'
    if kind == 'eci':
        return f'{v[0]:+.6f} [{v[1]:+.6f}, {v[2]:+.6f}]'
    if kind == 'excl':
        return '; '.join(f'[{lo:+.4f}, {hi:+.4f}]' for lo, hi in v)
    return f'{v:+.6f}'


# ---------------------------------------------------------------- the paper's mixed-model numbers
def entries(M, P):
    """(location, as printed, source, value(which), format). which in {'old', 'new'}."""
    c = lambda mid, t: (lambda w: M[mid][w]['coef'][t])
    p = lambda mid, t: (lambda w: M[mid][w]['p'][t])
    ci = lambda mid, t: (lambda w: (M[mid][w]['lo'][t], M[mid][w]['hi'][t]))
    eci = lambda mid, t: (lambda w: (M[mid][w]['coef'][t], M[mid][w]['lo'][t], M[mid][w]['hi'][t]))
    loss = lambda w: -M['T-1'][w]['coef']['Intercept']
    pr = lambda z: (lambda w: P[w][z]['mean'])
    epr = lambda z: (lambda w: (P[w][z]['mean'], P[w][z]['lo'], P[w][z]['hi']))
    shift = lambda w: ((M['B-1'][w]['coef']['Intercept'] - M['B-2'][w]['coef']['Intercept'])
                       / M['B-1'][w]['coef']['Intercept'])
    tp_pct = lambda w: -M['B-1'][w]['coef']['time_pressure_z'] / M['B-1'][w]['coef']['Intercept']
    both = lambda w: [(M[m][w]['lo']['Intercept'], M[m][w]['hi']['Intercept']) for m in ('B-5', 'B-1')]
    I, TP, S, E, W = 'Intercept', 'time_pressure_z', 'delta_risk_steep_z', 'elo_z', 'WPL_self_z'
    return [
        ('Abstract', '+1.22', 'B-1 `Intercept` (4b §4.1 primary)', c('B-1', I), ('f', 2)),
        ('Abstract', 'p = 1.6 × 10⁻³⁵', 'B-1 `Intercept` p', p('B-1', I), ('sci', 2, 'p = ')),
        ('Abstract', '1.72', 'T-1 `Intercept` (v3 H1), stated as a loss (−coefficient)', loss, ('u', 2)),
        ('Abstract', '−0.48', 'T-2 `delta_risk_steep_z` (v3 H2)', c('T-2', S), ('f', 2)),
        ('Abstract', '−0.09', 'T-4 `delta_risk_steep_z` (v3 H4a)', c('T-4', S), ('f', 2)),
        ('§3', '−0.235', 'V1-1 `elo_z` (v1 §8.1)', c('V1-1', E), ('f', 3)),
        ('§3', 'p = 3 × 10⁻¹⁵', 'V1-1 `elo_z` p', p('V1-1', E), ('sci', 1, 'p = ')),
        ('§3', '+0.485', 'V1-1 `eval_volatility_z`', c('V1-1', 'eval_volatility_z'), ('f', 3)),
        ('§3', 'p = 1 × 10⁻⁶⁷', 'V1-1 `eval_volatility_z` p', p('V1-1', 'eval_volatility_z'), ('sci', 1, 'p = ')),
        ('§3', '+0.311', 'V1-1 `n_legal_z`', c('V1-1', 'n_legal_z'), ('f', 3)),
        ('§3', '−0.156', 'V1-1 `spread_15_z`', c('V1-1', 'spread_15_z'), ('f', 3)),
        ('§3', '−0.429', 'V1-1 `time_pressure_z`', c('V1-1', TP), ('f', 3)),
        ('§3', 'p = 3 × 10⁻⁵²', 'V1-1 `time_pressure_z` p', p('V1-1', TP), ('sci', 1, 'p = ')),
        ('§4.1, paragraph 2', '+1.216', 'B-1 `Intercept`', c('B-1', I), ('f', 3)),
        ('§4.1, paragraph 2', '[+1.02, +1.41]', 'B-1 `Intercept` 95% CI', ci('B-1', I), ('ci', 2)),
        ('§4.1, paragraph 2', 'p = 1.6 × 10⁻³⁵', 'B-1 `Intercept` p', p('B-1', I), ('sci', 2, 'p = ')),
        ('§4.1, paragraph 2', '+0.449', 'B-3 `Intercept` (4b §6.1, ΔRISK_var)', c('B-3', I), ('f', 3)),
        ('§4.1, paragraph 2', '+1.475', 'B-4 `Intercept` (4b §6.2, band (0, 10])', c('B-4', I), ('f', 3)),
        ('§4.2', '+1.215', 'B-2 `Intercept` (4b §4 liquidation control)', c('B-2', I), ('f', 3)),
        ('§4.2', 'p = 1.3 × 10⁻⁴⁵', 'B-2 `Intercept` p', p('B-2', I), ('sci', 2, 'p = ')),
        ('§4.2', '0.1%', 'intercept shift B-1 → B-2, (B-1 − B-2) / B-1', shift, ('pct', 1)),
        ('§4.3', '−0.334', 'B-1 `time_pressure_z`', c('B-1', TP), ('f', 3)),
        ('§4.3', '[−0.521, −0.146]', 'B-1 `time_pressure_z` 95% CI', ci('B-1', TP), ('ci', 3)),
        ('§4.3', 'p = 4.8 × 10⁻⁴', 'B-1 `time_pressure_z` p', p('B-1', TP), ('sci', 2, 'p = ')),
        ('§4.3', '+0.55', 'B-1 predicted mean ΔRISK_steep at `time_pressure_z` = +2', pr('2'), ('f', 2)),
        ('§4.3', '+1.88', 'B-1 predicted mean ΔRISK_steep at `time_pressure_z` = −2', pr('-2'), ('f', 2)),
        ('§4.3', '27%', 'B-1 increase per SD toward the clock, −`time_pressure_z` / `Intercept`', tp_pct, ('pct', 0)),
        ('Figure B caption', '+1.166', 'B-5 `Intercept` (500 games)', c('B-5', I), ('f', 3)),
        ('Figure B caption', '+1.216', 'B-1 `Intercept` (1,970 games; figB-full = B-1)', c('B-1', I), ('f', 3)),
        ('Figure B caption', 'both CIs exclude zero', 'B-5 and B-1 `Intercept` 95% CIs', both, ('excl', 0)),
        ('Figure B, left panel, "500 games"', '+1.166 [+0.787, +1.544]', 'B-5 `Intercept` and 95% CI', eci('B-5', I), ('eci', 3)),
        ('Figure B, left panel, "1,970 games"', '+1.216 [+1.024, +1.407]', 'B-1 `Intercept` and 95% CI (figB-full)', eci('B-1', I), ('eci', 3)),
        ('Figure C, "§4.1 primary"', '+1.216 [+1.024, +1.407]', 'B-1 `Intercept` and 95% CI (figC-primary)', eci('B-1', I), ('eci', 3)),
        ('Figure C, "§4.3a ΔRISK_var"', '+0.449 [+0.370, +0.528]', 'B-3 `Intercept` and 95% CI (figC-var)', eci('B-3', I), ('eci', 3)),
        ('Figure C, "§4.3b ΔRISK_steep, WPL ∈ (0,10]"', '+1.475 [+1.298, +1.652]', 'B-4 `Intercept` and 95% CI (figC-band10)', eci('B-4', I), ('eci', 3)),
        ('Figure C, "liquidation-controlled"', '+1.215 [+1.068, +1.361]', 'B-2 `Intercept` and 95% CI (figC-liq)', eci('B-2', I), ('eci', 3)),
        ('Figure C, "time pressure −2 SD"', '+1.883 [+1.462, +2.304]', 'B-1 predicted mean at `time_pressure_z` = −2, delta-method 95% CI', epr('-2'), ('eci', 3)),
        ('Figure C, "time pressure +2 SD"', '+0.548 [+0.127, +0.969]', 'B-1 predicted mean at `time_pressure_z` = +2, delta-method 95% CI', epr('2'), ('eci', 3)),
        ('§4.5, paragraph 3', '1.722', 'T-1 `Intercept` (H1), stated as a loss', loss, ('u', 3)),
        ('§4.5, paragraph 3', '[−1.789, −1.656]', 'T-1 `Intercept` 95% CI', ci('T-1', I), ('ci', 3)),
        ('§4.5, paragraph 3', '−0.475', 'T-2 `delta_risk_steep_z` (H2)', c('T-2', S), ('f', 3)),
        ('§4.5, paragraph 3', '[−0.527, −0.423]', 'T-2 95% CI', ci('T-2', S), ('ci', 3)),
        ('§4.5, paragraph 3', 'p = 2.9 × 10⁻⁷¹', 'T-2 p', p('T-2', S), ('sci', 2, 'p = ')),
        ('§4.5, paragraph 3', '−0.085', 'T-4 `delta_risk_steep_z` (H4a)', c('T-4', S), ('f', 3)),
        ('§4.5, paragraph 3', '[−0.137, −0.034]', 'T-4 95% CI', ci('T-4', S), ('ci', 3)),
        ('§4.5, paragraph 3', 'p = .0012', 'T-4 p', p('T-4', S), ('pdec', 2, 'p = ')),
        ('§4.5, paragraph 3', '−0.390', 'T-5 `delta_risk_steep_z` (H4b)', c('T-5', S), ('f', 3)),
        ('§4.5, paragraph 3', '[−0.397, −0.383]', 'T-5 95% CI', ci('T-5', S), ('ci', 3)),
        ('§4.5, paragraph 4', '+0.209', 'T-6 `WPL_self_z` (v3 §6.5 control)', c('T-6', W), ('f', 3)),
        ('§4.5, paragraph 4', '1.72', 'T-1 `Intercept`, as a loss ("the 1.72-point cost")', loss, ('u', 2)),
        ('§6, "A silent false null"', '+1.17', 'B-5 `Intercept` ("+1.17 at pilot scale")', c('B-5', I), ('f', 2)),
    ]


NOT_MIXED = [
    ('Abstract, §2', 'sample and evaluation counts (1,970 games; 50,021 position-moves; 126,449, 63,429, 57,294, 5,726 evaluations; 2,317 and 578 players; 51.0%; 30 of 2,000 games)', 'counts'),
    ('Abstract, §4.1, Figure A caption', '59.85%, sign-test p = 1.8 × 10⁻¹⁷⁰, median ΔRISK +0.63, 19,836 non-zero deviations, n = 19,842, 295 moves beyond ±40 WP', 'model-free sign test and descriptives'),
    ('§4.1', '39.7% and 42.7% of rows', 'counts'),
    ('§4.3', 'decile profile +0.46 and +1.70', 'observed decile means, no model'),
    ('§4.4, Figure B right panel and caption', 'PC1 slope +0.521 (p = .0023, n = 348; CI [+0.188, +0.854]), +0.161 (p = .065, n = 578), +0.160 [−0.010, +0.331], 69%', 'OLS on player means (`paper4b_figures.py:pc1_slope`, 4b §5)'),
    ('§4.5', '20,387 training moves; 44 rows, p = .98; one fifth of replies; +0.22 depth offset; 2,000 re-evaluated replies', 'counts, χ² test, depth check'),
    ('§4.5, paragraph 4', '+0.11 points', 'two-way cluster-robust mean of `RES` (v3 post-hoc §B), not a mixed model'),
    ('§4.5, paragraph 4', '99.2% and 74.4%', 'descriptive shares by decile'),
    ('§6', '7,232 rows, 25%', 'coverage counts'),
    ('§6', 'weighted overall −0.02 points', 'common-support calibration (v3 post-hoc §A)'),
    ('§6', '"an intercept of exactly zero, and p = 1"', 'the degenerate lbfgs output being described, not an estimate'),
]


def write(work, out):
    M = {}
    for b in ['v1', 'b4report', 'b4figs', 'v3']:
        for r in json.load(open(os.path.join(work, f'rerun_{b}.json'))):
            if r.get('id'):
                M[r['id']] = r
    P = json.load(open(os.path.join(work, 'predictions.json')))
    rows, n_change, mism = [], [], []
    for i, (loc, printed, src, val, spec) in enumerate(entries(M, P), 1):
        vo, vn = val('old'), val('new')
        fo, fn = fmt(vo, spec), fmt(vn, spec)
        paper_ok = fo == printed
        changed = fo != fn
        if changed:
            n_change.append((i, loc, printed, fn))
        if not paper_ok:
            mism.append((i, loc, printed, fo))
        rows.append([i, loc, f'`{printed}`', src, full(vo, spec), full(vn, spec), f'`{fn}`',
                     'yes' if paper_ok else f'**no** (old gives `{fo}`)',
                     '**yes**' if changed else 'no'])

    L = []
    A = L.append
    A('# Paper 4 correction: mixed-model numbers quoted in the paper\n')
    A(f'_Generated {time.strftime("%Y-%m-%d %H:%M")} by `code/paper4_correction_numbers.py`. Companion to '
      '`docs/paper4_correction_REPORT.md`. Paper: `docs/Sharper_Not_Safer_v7.docx`._\n')
    A('\n**Old** = the unchanged `fit_mixed` re-executed on the rebuilt rows; it reproduces the published '
      'reports to printed precision (correction report §4.1). **New** = `fit_mixed_v2` on the same rows. '
      '"New as printed" formats the new value at the precision and in the style the paper uses. The '
      '±2 SD predicted means use the delta method exactly as `paper4b_figures.py:fig_c` computes them, '
      f'applied to each fit (rows {P["rows"]:,}; new fit selected `{P["new_selected"]}`). '
      'A change at printed precision is not a §4 reading; the §4 outcome is in the correction report '
      '(no conclusion changes).\n')

    A('\n## Summary\n')
    A(f'- {len(rows)} mixed-model numbers located in the paper.')
    A(f'- {len(rows) - len(n_change)} are identical at the paper\'s printed precision under the new estimator; '
      f'**{len(n_change)}** differ:')
    for i, loc, printed, fn in n_change:
        A(f'  - #{i} {loc}: `{printed}` → `{fn}`')
    A(f'- Paper values that do not equal the old model output at their printed precision: {len(mism)}'
      + (':' if mism else '.'))
    for i, loc, printed, fo in mism:
        A(f'  - #{i} {loc}: paper `{printed}`, old model output `{fo}`')
    A('')

    A('\n## Values\n')
    A('| # | location in the paper | as printed | source (model ID, term) | old | new | new as printed | '
      'paper = old at printed precision | changes at printed precision |')
    A('|---|---|---|---|---|---|---|---|---|')
    for r in rows:
        A('| ' + ' | '.join(str(x) for x in r) + ' |')

    A('\n## Notes\n')
    A('- Model IDs are those of `specs/paper4_correction_spec.md` §3.2. Figure B "1,970 games" and the '
      'four model rows of Figure C come from figure fits that the correction report §4.2 confirms are the '
      'same fits as B-1, B-2, B-3 and B-4; their values are taken from those models.')
    A('- Figure values are the numbers printed in `figures/paper4/figB_pilot_vs_full.png` and '
      '`figC_robustness_ladder.png`.')
    A('- §6 "+1.17 at pilot scale" refers to the 500-game pilot estimate of the §4.1 model, which is B-5.')
    A('- "1.72" / "1.722" state the H1 intercept as a loss, so the value shown is the negated intercept.')

    A('\n## Numbers in the paper that are not from a mixed model (not listed above)\n')
    A('| location | values | source |')
    A('|---|---|---|')
    for loc, vals, srcn in NOT_MIXED:
        A(f'| {loc} | {vals} | {srcn} |')

    open(out, 'w').write('\n'.join(L) + '\n')
    print(f'wrote {out}: {len(rows)} values, {len(n_change)} change at printed precision, '
          f'{len(mism)} paper/old mismatches')
