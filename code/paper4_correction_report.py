#!/usr/bin/env python3
"""
paper4_correction_report.py — writes docs/paper4_correction_REPORT.md (correction spec §5)
from the JSON written by paper4_correction_run.py. Published values are parsed from the three
reports as committed; figure values are the numbers printed in figures/paper4/*.png.

    python3 paper4_correction_run.py report --work WORK
"""
import os, re, json, time, hashlib, platform, subprocess

CODE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(CODE)
DOCS = os.path.join(REPO, 'docs')

ORDER = ['V1-1', 'V1-2', 'V1-3', 'V1-4', 'B-1', 'B-2', 'B-3', 'B-4', 'B-5'] + \
        [f'T-{i}' for i in range(1, 15)]

SOURCE = {   # [§3.2] report / section, as listed in the spec
    'V1-1': 'v1 §8.1 (roster only)', 'V1-2': 'v1 §8.2 (all rows)', 'V1-3': 'v1 §9 primary',
    'V1-4': 'v1 §9 robustness, controls at t+1',
    'B-1': '4b §4 primary', 'B-2': '4b §4 liquidation', 'B-3': '4b §6.1 ΔRISK_var',
    'B-4': '4b §6.2 band (0, 10]', 'B-5': 'figure B, 500 games',
    'T-1': 'v3 §6.1 H1', 'T-2': 'v3 §6.2 H2', 'T-3': 'v3 §6.3 H3', 'T-4': 'v3 §6.4 H4a',
    'T-5': 'v3 §6.4 H4b', 'T-6': 'v3 §6.5 control', 'T-7': 'v3 §7.1 H2 (0, 10]',
    'T-8': 'v3 §7.1 H4a (0, 10]', 'T-9': 'v3 §7.1 H4b (0, 10]', 'T-10': 'v3 §7.2 H4a unrestricted',
    'T-11': 'v3 §7.3 H4a LightGBM', 'T-12': 'v3 §7.3 H4b LightGBM',
    'T-13': 'v3 post-hoc §C inside MultiPV-5', 'T-14': 'v3 post-hoc §C freshly evaluated'}

CORE = {'V1-1': ['elo_z', 'elo_z:gap_12_z', 'elo_z:time_pressure_z'],
        'V1-2': ['elo_z', 'elo_z:gap_12_z', 'elo_z:time_pressure_z'],
        'V1-3': ['WPL_self_z'], 'V1-4': ['WPL_self_z'],
        'B-1': ['Intercept'], 'B-2': ['Intercept', 'dmat_c'], 'B-3': ['Intercept'],
        'B-4': ['Intercept'], 'B-5': ['Intercept'],
        'T-1': ['Intercept'],
        'T-3': ['delta_risk_steep_z:time_pressure_opp_z', 'delta_risk_steep_z:elo_diff_opp_z'],
        'T-6': ['WPL_self_z']}
for _i in [2, 4, 5, 7, 8, 9, 10, 11, 12, 13, 14]:
    CORE[f'T-{_i}'] = ['delta_risk_steep_z']

V1, B4, V3 = 'paper4_pilot_REPORT.md', 'paper4b_pilot_REPORT.md', 'paper4_v3_REPORT.md'
PUB_TABLE = {   # first coefficient table after this title is the mixed model's
    'V1-1': (V1, 'Linear mixed model — roster members only (PRIMARY)'),
    'V1-2': (V1, 'Linear mixed model — all rows'),
    'V1-3': (V1, 'Linear mixed model (primary result of the paper)'),
    'V1-4': (V1, "Robustness: controls at the opponent's position"),
    'B-1': (B4, 'Linear mixed model — §4.1 primary'),
    'B-2': (B4, 'Linear mixed model — §4.1 + liquidation controls'),
    'B-3': (B4, '**ΔRISK_var, WPL ∈ (0,5]**'),
    'B-4': (B4, '**ΔRISK_steep, WPL ∈ (0,10]**'),
    'T-1': (V3, '**H1: intercept-only mixed model**'),
    'T-2': (V3, '**H2: net realised gain**'),
    'T-3': (V3, '**H3: two pre-specified interactions**'),
    'T-4': (V3, '**H4a: RES'), 'T-5': (V3, '**H4b: CF'),
    'T-6': (V3, 'for comparison only, not interpreted'),
    'T-7': (V3, '**H2 on (0, 10]**'), 'T-8': (V3, '**H4a on (0, 10]**'),
    'T-9': (V3, '**H4b on (0, 10]**'),
    'T-10': (V3, '**H4a with the unrestricted training set**'),
    'T-11': (V3, '**H4a with the LightGBM nuisance model**'),
    'T-12': (V3, '**H4b with the LightGBM nuisance model**')}
PUB_POSTHOC = {'T-13': 'inside MultiPV-5', 'T-14': 'freshly evaluated'}   # v3 post-hoc §C table
PUB_FIGURE = {'B-5': {'Intercept': ('+1.166', '+0.787', '+1.544')}}       # figB left panel
COVER_FIGURE = {   # [§3.1 item 3] intercept and CI printed in the figure
    'figB-full': ('+1.216', '+1.024', '+1.407'), 'figC-primary': ('+1.216', '+1.024', '+1.407'),
    'figC-var': ('+0.449', '+0.370', '+0.528'), 'figC-band10': ('+1.475', '+1.298', '+1.652'),
    'figC-liq': ('+1.215', '+1.068', '+1.361')}
PUB_TOST_T1 = dict(p='1', equivalent=False)   # v3 report §6.1: overall p = 1, NOT equivalent

PAPER = 'docs/Sharper_Not_Safer_v7.docx'
# [§4, §5 item 3] (model ID, core term) -> (location in the paper, quoted sentence).
# None means the conclusion is not stated in the paper. Prepared for every core coefficient
# before the results were read; the report prints only the entries §4 triggers.
_ABS_SHARP = ('Abstract', 'At equal expected loss, human moves sit on steeper curves than the engine\'s choice '
              '(intercept +1.22 win-probability points, p = 1.6 × 10⁻³⁵; 59.85% of deviations toward the '
              'sharper side, sign-test p = 1.8 × 10⁻¹⁷⁰).')
_ABS_ROBUST = ('Abstract', 'The effect survives a liquidation control and two pre-specified robustness variants, '
               'and it strengthens under time pressure.')
_ROBUST_41 = [('§4.1, paragraph 2', 'Both pre-specified robustness variants preserve the sign.'),
              ('§4.1, paragraph 2', 'The dispersion definition gives +0.449, and the widened band (0, 10] gives +1.475.'),
              _ABS_ROBUST,
              ('Figure C caption', 'Every specification places the effect on the sharper side of zero.'),
              ('§7', 'The preference survives liquidation and specification controls, and it intensifies under '
                     'time pressure, which is the opposite of risk management.')]
_ALLSIGNS = [('§4.5, paragraph 3', 'All signs hold when the band widens to (0, 10], when the training restriction '
                                   'is dropped, and when the expected-error model is replaced by gradient boosting.')]
_V1_INTER = [('§3', 'Elo-by-complexity and Elo-by-time-pressure interactions were not supported at this sample '
                    'size and are left for larger samples.')]
SENTENCES = {
    ('V1-1', 'elo_z'): [('Abstract', 'It falls with rating, rises with position volatility, and rises under time pressure.'),
                        ('§3', 'Deviation falls with rating (Elo −0.235, p = 3 × 10⁻¹⁵).'),
                        ('§3', 'Stronger titled players deviate less, and harder, sharper, more time-starved positions '
                               'produce more deviation.'),
                        ('§7', 'How much titled players deviate from a chess engine behaves like noise: more when '
                               'weaker, more when the position is volatile, more when time is short.')],
    ('V1-1', 'elo_z:gap_12_z'): _V1_INTER,
    ('V1-1', 'elo_z:time_pressure_z'): _V1_INTER,
    ('V1-2', 'elo_z'): None, ('V1-2', 'elo_z:gap_12_z'): None, ('V1-2', 'elo_z:time_pressure_z'): None,
    ('V1-3', 'WPL_self_z'): [('§1, paragraph 3', 'The mechanism coefficient came out positive and the outcome '
                              'coefficient came out negative, and the design could not separate genuine '
                              'opponent-directed play from a confound: sharp moments inflate both players\' errors at once.')],
    ('V1-4', 'WPL_self_z'): None,
    ('B-1', 'Intercept'): [_ABS_SHARP,
                           ('§4.1, paragraph 2', 'The intercept is +1.216 win-probability points (95% CI [+1.02, +1.41], '
                                                 'p = 1.6 × 10⁻³⁵).'),
                           ('§4.1, paragraph 2', 'This is the paper\'s central result.'),
                           ('§7', 'At equal expected loss, human moves sit on steeper punishment curves than the '
                                  'engine\'s choice.')],
    ('B-2', 'Intercept'): [('§4.2', 'The intercept barely moves (+1.215, p = 1.3 × 10⁻⁴⁵ on the full sample, a shift of 0.1%).'),
                           _ABS_ROBUST],
    ('B-2', 'dmat_c'): [('§4.2', 'Removing more material predicts a steeper successor, not a flatter one.')],
    ('B-3', 'Intercept'): _ROBUST_41,
    ('B-4', 'Intercept'): _ROBUST_41,
    ('B-5', 'Intercept'): [('Figure B caption', 'Left: the §4.1 intercept holds under a fourfold expansion '
                                                '(+1.166 → +1.216; both CIs exclude zero).')],
    ('T-1', 'Intercept'): [('Abstract', 'The average deviation loses 1.72 win-probability points net of everything it induces.'),
                           ('§4.5, paragraph 3', 'On the primary band the average deviation loses 1.722 win-probability '
                            'points net of everything it induces (95% CI [−1.789, −1.656]), and the pre-specified '
                            'equivalence test confirms the loss is not practically zero.')],
    ('T-1', 'TOST verdict'): [('§4.5, paragraph 3', 'On the primary band the average deviation loses 1.722 win-probability '
                               'points net of everything it induces (95% CI [−1.789, −1.656]), and the pre-specified '
                               'equivalence test confirms the loss is not practically zero.')],
    ('T-2', 'delta_risk_steep_z'): [('Abstract', 'Sharper deviations lose more, not less (−0.48 points per standard '
                                     'deviation of steepness), and the beyond-difficulty component does not rise with '
                                     'steepness (coefficient −0.09).'),
                                    ('§4.5, paragraph 3', 'Sharper deviations lose more: the steepness coefficient on net '
                                     'realized gain is −0.475 per standard deviation (95% CI [−0.527, −0.423], p = 2.9 × 10⁻⁷¹).'),
                                    ('§7', 'Sharper deviations lose more, and the opponent\'s error beyond what difficulty '
                                           'explains does not rise with sharpness.')],
    ('T-3', 'delta_risk_steep_z:time_pressure_opp_z'): [('§4.5, paragraph 3', 'Neither pre-registered moderator changes '
                                                         'this; the interactions with the opponent\'s clock and with the '
                                                         'rating gap are both null.')],
    ('T-3', 'delta_risk_steep_z:elo_diff_opp_z'): [('§4.5, paragraph 3', 'Neither pre-registered moderator changes this; '
                                                    'the interactions with the opponent\'s clock and with the rating gap '
                                                    'are both null.')],
    ('T-4', 'delta_risk_steep_z'): [('Abstract', 'Sharper deviations lose more, not less (−0.48 points per standard '
                                     'deviation of steepness), and the beyond-difficulty component does not rise with '
                                     'steepness (coefficient −0.09).'),
                                    ('§4.5, paragraph 3', 'In the beyond-difficulty model the steepness coefficient is '
                                     '−0.085 (95% CI [−0.137, −0.034], p = .0012).'),
                                    ('§4.5, paragraph 4', 'Opponents do err slightly more than difficulty predicts after a '
                                     'deviation, about +0.11 points on an exploratory two-way clustered estimate, an order '
                                     'of magnitude below the 1.72-point cost and, in the pre-registered model, slightly '
                                     'lower at higher steepness.'),
                                    ('§7', 'Sharper deviations lose more, and the opponent\'s error beyond what difficulty '
                                           'explains does not rise with sharpness.')],
    ('T-5', 'delta_risk_steep_z'): [('§4.5, paragraph 3', 'In the difficulty-explained model it is −0.390 (95% CI [−0.397, −0.383]).'),
                                    ('§4.5, paragraph 3', 'Sharper moves do not extract opponent error that difficulty fails '
                                     'to explain, and they reduce rather than raise the difficulty-explained component.'),
                                    ('§5.1, paragraph 2', 'The difficulty-explained component falls with steepness: a steep '
                                     'position raises the price of the opponent\'s fifth-best reply, but it also narrows the '
                                     'search, and in the sharpest positions the reply is nearly always among the engine\'s top lines.')],
    ('T-6', 'WPL_self_z'): [('Abstract', 'Rerunning the earlier confounded model on the same rows still gives a positive '
                             'coefficient, so the identification, not the data, reverses the conclusion.'),
                            ('§4.5, paragraph 4', 'Rerunning the original confounded model on the same rows still returns '
                             'a positive coefficient for the mover\'s error on the opponent\'s next error (+0.209).')],
    ('T-7', 'delta_risk_steep_z'): _ALLSIGNS, ('T-8', 'delta_risk_steep_z'): _ALLSIGNS,
    ('T-9', 'delta_risk_steep_z'): _ALLSIGNS, ('T-10', 'delta_risk_steep_z'): _ALLSIGNS,
    ('T-11', 'delta_risk_steep_z'): _ALLSIGNS, ('T-12', 'delta_risk_steep_z'): _ALLSIGNS,
    ('T-13', 'delta_risk_steep_z'): None, ('T-14', 'delta_risk_steep_z'): None,
}

AMENDMENT2_CORRECTED = '''\
> ## Amendment 2 (2026-09-05, after lock, during execution; corrected 2026-09-11)
>
> **Trigger**: implementation review of how the [LOCKED] random-effects structures are actually estimated, plus one feature-definition convention that belongs on the record. This amendment records existing practice. No estimate, parameter, or model specification changes under it.
>
> **Correction (2026-09-11, `specs/paper4_correction_spec.md`)**: items 1 to 3 as first written described an estimator that was not the one used. The text below is the corrected record. The effect on every reported estimate is in `docs/paper4_correction_REPORT.md`.
>
> **Decisions**:
>
> 1. **Random effects in §6.** The [LOCKED] structure `(1 | player_id) + (1 | game_id)` in §6.1 through §6.5, and in the §7 robustness refits that reuse those model forms, was fitted with v1's `fit_mixed` (`paper4_report.py:74`). That function calls `MixedLM` grouped on `player_id` with `game_id` as a variance component and without `re_formula`; in statsmodels 0.14.6 this estimates no player random intercept. Every §6 and §7 model as reported therefore carried a game random intercept only, with a game that contributes rows from two players receiving one independent intercept per player. The fit is retried across optimizers with a guard that rejects the degenerate all-zero optimum; the guard does not check convergence, so a non-converged fit could be returned. The "random-effect variance" printed under each table is the variance divided by the residual variance. An OLS fit with player-clustered standard errors is reported alongside on the same rows and does not depend on the random-effects structure. The same function fitted v1's §7.2 model, so §6.5's rerun of it is a like-for-like comparison of estimators, with the same omission on both sides. The corrected estimator is `fit_mixed_v2` (`code/paper4_mixed_v2.py`): a player random intercept, `game_id` as a variance component nested in `player_id`, a sweep of five optimizers, selection of the converged, non-degenerate fit with the highest log-likelihood, and variance components on the natural scale.
>
> 2. **The crossing is real, not incidental.** In the (0, 5] analysis band, 1,937 of 1,967 games (98.5%) contribute rows from both players, so `game_id` genuinely crosses `player_id` rather than nesting inside it. The reported fits did not approximate this crossing; they omitted the player intercept altogether (item 1). Under the corrected estimator, which nests `game_id` in `player_id`, what the approximation drops is the sharing of one game intercept across that game's two players, and it is flagged in every mixed-model coefficient table.
>
> 3. **§4.2 is not affected by item 1.** The nuisance model carries a single grouping factor, `(1 | player_id)`, fitted with `MixedLM` grouped on `player_id` and its default random intercept, which is estimated. No nesting approximation is involved there. It is fitted with `lbfgs` alone, without a convergence check; the correction's verification (correction spec §3.4) found all ten fold fits, on the main and the §7.2 training sets, converged at the maximum across five optimizers, and the stored predictions reproduce exactly. Its printed `Group Var` is likewise a ratio to the residual variance.
>
> 4. **`spread_15` convention.** §3.2 defines `spread_15` as `WP_opp(1st) − WP_opp(5th)`. It is computed against the last available MultiPV line, which is v1's own convention for the same feature (`wp_best - wps[-1]`). The two are identical wherever the engine returned five lines — 56,541 of 57,294 successor positions, 98.7% — and differ only where it returned fewer. Matching v1 keeps the nuisance model's training features and its prediction features on a single definition, which §4.2 requires.'''

README34_CORRECTED = (
    '- `specs/` — the locked specifications for the Paper 4 analyses: v1 (deviation structure and the '
    'complementarity test), v2 (the risk-direction analysis), and v3 (the §7.2 identification redesign; '
    '`paper4_spec_v3_en.md` is the governing English version, `paper4_spec_v3_zh_lock.md` the '
    'original-language lock record). v3 carries three amendments, all recorded in the English file: 1 permits '
    're-evaluating the successor positions to recover the MultiPV lines v2 did not persist, 2 records how the '
    'random effects are estimated (its original description was incorrect: the fitted models carried no player '
    'intercept; corrected under `paper4_correction_spec.md`, with the refitted estimates in '
    '`docs/paper4_correction_REPORT.md`), and 3 withdraws an invalid diagnostic and replaces it. Amendments 1 '
    'and 2 predate any results; 3, and the 2026-09-11 correction of 2, are dated and recorded after them.')


# ---------------------------------------------------------------- parsing
def _cells(line):
    return [c.strip() for c in line.strip().strip('|').split('|')]


def _ci(s):
    lo, hi = s.strip('[]').split(',')
    return lo.strip(), hi.strip()


def parse_table(fname, title):
    L = open(os.path.join(DOCS, fname)).read().splitlines()
    i = next(k for k, l in enumerate(L) if title in l)
    j = next(k for k in range(i + 1, len(L)) if L[k].startswith('|'))
    rows, k = {}, j + 2                          # skip header and separator
    while k < len(L) and L[k].startswith('|'):
        c = _cells(L[k])
        lo, hi = _ci(c[2])
        rows[c[0]] = (c[1], lo, hi)
        k += 1
    n = next(int(l.split('=')[1].replace(',', '').strip())
             for l in L[k:] if l.startswith('- N = '))
    return rows, n


def parse_posthoc(label):
    L = open(os.path.join(DOCS, V3)).read().splitlines()
    c = _cells(next(l for l in L if l.startswith(f'| {label}')))
    lo, hi = _ci(c[4])
    return {'delta_risk_steep_z': (c[3], lo, hi)}, int(c[1].replace(',', ''))


def published(mid):
    if mid in PUB_TABLE:
        rows, n = parse_table(*PUB_TABLE[mid])
        return rows, n, 4, f'{PUB_TABLE[mid][0]}, table "{PUB_TABLE[mid][1].strip("*")}"'
    if mid in PUB_POSTHOC:
        rows, n = parse_posthoc(PUB_POSTHOC[mid])
        return rows, n, 4, f'{V3}, post-hoc §C table (n = subgroup rows)'
    return PUB_FIGURE[mid], None, 3, 'figures/paper4/figB_pilot_vs_full.png (no N printed)'


# ---------------------------------------------------------------- formatting
def f4(x, dp=4):
    return '—' if x is None else f'{x:+.{dp}f}'


def fci(lo, hi, dp=4):
    return f'[{lo:+.{dp}f}, {hi:+.{dp}f}]'


def fvar(v):
    return 'not estimated' if v is None else f'{v:.4f}'


def comps(c):
    if not c:
        return '—'
    return f'{fvar(c["player"])} / {fvar(c["game"][0] if c["game"] else None)} / {c["residual"]:.4f}'


def sign(x):
    return (x > 0) - (x < 0)


def excl(lo, hi):
    return lo > 0 or hi < 0


def tbl(rows, hdr):
    out = ['| ' + ' | '.join(hdr) + ' |', '|' + '|'.join('---' for _ in hdr) + '|']
    out += ['| ' + ' | '.join(str(x) for x in r) + ' |' for r in rows]
    return '\n'.join(out)


def sha256(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


# ---------------------------------------------------------------- report
def write(work, out):
    J = lambda f: json.load(open(os.path.join(work, f)))
    setup, verify = J('setup.json'), J('verify.json')
    recs = []
    for b in ['v1', 'b4report', 'b4figs', 'v3']:
        p = os.path.join(work, f'rerun_{b}.json')
        recs += [dict(r, builder=b) for r in (json.load(open(p)) if os.path.exists(p) else [])]
    by_id = {r['id']: r for r in recs if r.get('id')}
    covers = [r for r in recs if r.get('covers')]
    unlisted = [r for r in recs if r.get('unlisted')]

    L = []
    A = L.append
    A('# Paper 4 correction: random-effects estimator — report\n')
    A(f'_Generated {time.strftime("%Y-%m-%d %H:%M")}. Executes `specs/paper4_correction_spec.md` '
      '(LOCKED 2026-09-11). Code: `code/paper4_mixed_v2.py` (the §2 estimator), '
      '`code/paper4_correction_run.py` (sandbox, §3.4, re-run), `code/paper4_correction_report.py` '
      '(this file)._\n')

    # ------------------------------------------------------------ evaluate every model
    results, trig = {}, []
    for mid in ORDER:
        r = by_id.get(mid)
        res = dict(id=mid, status='ok', notes=[], terms=[])
        results[mid] = res
        if r is None:
            res['status'] = 'STOP: model not reached by its script'
            continue
        pub, n_pub, dp, where = published(mid)
        res.update(where=where, dp=dp, n_pub=n_pub,
                   n_rebuilt=r['n_input'] if mid in PUB_POSTHOC else (r['old'] or {}).get('nobs', r['rows']))
        if n_pub is not None and res['n_rebuilt'] != n_pub:
            res['status'] = f'STOP [§3.1 item 1]: N {res["n_rebuilt"]:,} ≠ published {n_pub:,}'
        old = r['old']
        repro = []
        for t in CORE[mid]:
            if t not in pub:
                repro.append((t, False, 'term not in published table'))
                continue
            if old is None or t not in old['coef']:
                repro.append((t, False, 're-executed fit_mixed returned no fit'))
                continue
            got = (f4(old['coef'][t], dp), f4(old['lo'][t], dp), f4(old['hi'][t], dp))
            repro.append((t, got == tuple(pub[t]), f'published {pub[t][0]} [{pub[t][1]}, {pub[t][2]}], '
                                                  f're-executed {got[0]} [{got[1]}, {got[2]}]'))
        res['repro'] = repro
        if res['status'] == 'ok' and not all(ok for _, ok, _ in repro):
            res['status'] = 'STOP [§3.1 item 2]: re-executed fit_mixed does not reproduce the published core values'
        new, info = r.get('new'), r.get('new_info') or {}
        if res['status'] == 'ok' and new is None:
            res['status'] = f'STOP [§2 item 7]: {info.get("status")}'
        for t in CORE[mid]:
            p = pub.get(t)
            row = dict(term=t, pub=p)
            if p is not None:
                row.update(old_sign=sign(float(p[0])), old_excl=excl(float(p[1]), float(p[2])))
            if new is not None and t in new['coef']:
                row.update(new_coef=new['coef'][t], new_lo=new['lo'][t], new_hi=new['hi'][t],
                           new_sign=sign(new['coef'][t]), new_excl=excl(new['lo'][t], new['hi'][t]))
            if res['status'] == 'ok':
                ch = []
                if row['new_sign'] != row['old_sign']:
                    ch.append('sign')
                if row['new_excl'] != row['old_excl']:
                    ch.append('CI-excludes-zero')
                row['changes'] = ch
                if ch:
                    trig.append((mid, t, ch))
            res['terms'].append(row)
        if mid == 'T-1' and res['status'] == 'ok':
            tn = r.get('tost_new')
            res['tost'] = dict(old=r.get('tost_old'), new=tn)
            if tn is None or tn['equivalent'] != PUB_TOST_T1['equivalent']:
                trig.append((mid, 'TOST verdict', ['TOST verdict']))
                res['tost_changed'] = True

    n_ok = sum(1 for v in results.values() if v['status'] == 'ok')
    n_stop = len(ORDER) - n_ok
    n_terms = sum(len(v['terms']) for v in results.values() if v['status'] == 'ok')

    # ------------------------------------------------------------ 0. summary
    A('\n## 0. Summary\n')
    A(f'- §3.4 verification of the v3 expected-error model: **{"PASSED" if verify["passed"] else "FAILED"}** '
      f'({sum(f["at_maximum"] for f in verify["folds"])}/{len(verify["folds"])} fold fits converged at the maximum; '
      f'`E_played`/`E_best` reproduction {"passed" if verify["reproduction_passed"] else "failed"}).')
    A(f'- Re-run list: {len(ORDER)} models; {n_ok} completed every check; {n_stop} stopped'
      + (' (see §3 and §4.1).' if n_stop else '.'))
    A(f'- §4 reading on the {n_terms} core coefficients of the completed models: '
      f'**{len(trig)} change{"s" if len(trig) != 1 else ""}**.')
    for mid, t, ch in trig:
        A(f'  - {mid} ({SOURCE[mid]}), `{t}`: {", ".join(ch)} changed')
    A('')

    # ------------------------------------------------------------ 1. environment
    A('\n## 1. Environment and integrity\n')
    after = sha256(os.path.join(CODE, 'paper4_report.py'))
    since = setup['started']
    touched = []
    for root, dirs, files in os.walk(setup['data']):
        dirs[:] = [d for d in dirs if d not in ('.git', '__pycache__')]
        for fn in files:
            p = os.path.join(root, fn)
            try:
                if os.path.getmtime(p) > since:
                    touched.append(os.path.relpath(p, setup['data']))
            except OSError:
                pass
    git = subprocess.run(['git', 'status', '--porcelain'], cwd=REPO, capture_output=True, text=True).stdout
    try:
        import lightgbm
        lgbv = lightgbm.__version__
    except Exception:
        lgbv = 'not importable'
    A(tbl([
        ['python', setup['python']], ['statsmodels', f'{setup["statsmodels"]} (on record: 0.14.6)'],
        ['lightgbm', lgbv], ['platform', f'{setup["platform"]}, {setup["cores"]} cores'],
        ['`code/paper4_report.py` SHA-256 before', f'`{setup["paper4_report_sha256"]}`'],
        ['`code/paper4_report.py` SHA-256 after', f'`{after}` ({"unchanged" if after == setup["paper4_report_sha256"] else "CHANGED"})'],
        ['sandbox', 'scripts ran unmodified in a scratch directory with read-only links to the inputs and '
                    'private copies of every file they write; no engine binary was reachable'],
        ['files under the data root modified since setup', ', '.join(touched) if touched else 'none'],
    ], ['item', 'value']))
    A('\n`git status --porcelain` immediately before this report was written:\n\n```\n'
      + (git.strip() or '(clean)') + '\n```\n')

    # ------------------------------------------------------------ 2. §3.4
    A('\n## 2. Verification of the v3 expected-error model (§3.4)\n')
    A('Each fold fit of `crossfit(kind=\'lmm\')` was fitted with all five optimizers while '
      '`p4_v3_analysis.py` ran; the `lbfgs` fit, which v3 used, was handed back so the script '
      'proceeded exactly as in v3. No model on the re-run list was fitted in this stage. '
      f'"At the maximum" = `lbfgs` converged and its log-likelihood is no more than 0.1 below the '
      f'highest converged log-likelihood in the fold\'s sweep.\n')
    rows = []
    for f in verify['folds']:
        cells = []
        for s in f['sweep']:
            cells.append('error' if s['error'] else
                         f'{"conv" if s["converged"] else "NOT conv"} {s["llf"]:.3f}')
        rows.append([f['training_set'].split(' (')[0], f['fold'] + 1, f'{f["n"]:,}', f'{f["players"]:,}']
                    + cells + [f'{f["lbfgs_gap"]:.4f}' if f['lbfgs_gap'] is not None else '—',
                               'yes' if f['at_maximum'] else '**NO**'])
    A(tbl(rows, ['training set', 'fold', 'rows', 'players', 'lbfgs', 'bfgs', 'powell', 'nm', 'cg',
                 'lbfgs gap to max', 'at maximum']))
    rp = verify['reproduction']
    A(f'\n**Reproduction (§3.4 item 4).** The re-executed `lbfgs` fits regenerated '
      f'`p4_v3_rows_analysis.parquet` inside the sandbox; against the stored file '
      f'({rp["rows_stored"]:,} rows; {rp["unmatched"]} unmatched keys): '
      f'`E_played` max |difference| = {rp["E_played"]["max_abs_diff"]:.3g} over {rp["E_played"]["compared"]:,} rows '
      f'({rp["E_played"]["nan_mismatch"]} missing-value mismatches); '
      f'`E_best` max |difference| = {rp["E_best"]["max_abs_diff"]:.3g} over {rp["E_best"]["compared"]:,} rows '
      f'({rp["E_best"]["nan_mismatch"]} missing-value mismatches). Tolerance 1e-9. The §7.2 predictions are '
      'not stored; their reproduction is checked through T-10 (§3 below).\n')
    A(f'\n**Outcome (§3.4 item 5).** ' + (
        'All 10 fold fits converged at the maximum and the stored predictions reproduce. The expected-error '
        'model stands; `RES`, `CF` and `NET_realized` are unchanged, and the re-run proceeded on the stored values.'
        if verify['passed'] else 'STOP. See the table above; nothing in §3.2 was fitted.') + '\n')
    wn = sorted({w for f in verify['folds'] for s in f['sweep'] for w in s['warnings']})
    if wn:
        A('\nWarnings raised during the sweep (all optimizers, all folds): ' +
          '; '.join(f'"{w}"' for w in wn) + '.\n')

    # ------------------------------------------------------------ 3. side by side
    A('\n## 3. Side-by-side table (§3.1 item 5)\n')
    A('Old coefficient and CI: as published. Old fit: the optimizer the unchanged `fit_mixed` selected on '
      'the rebuilt rows and that fit\'s `converged` flag. Variance components on the natural scale, '
      'player / game / residual; the old fits estimated no player variance (spec §1.1). New fit: '
      '`fit_mixed_v2`. §4 reading: sign and whether the 95% CI excludes zero, old (published) vs new.\n')
    rows = []
    for mid in ORDER:
        v, r = results[mid], by_id.get(mid) or {}
        old, new, info = r.get('old'), r.get('new'), r.get('new_info') or {}
        ofit = f'{r.get("old_method") or "none"}, converged={old["converged"]}' if old else 'no fit'
        nfit = (f'{info.get("selected")}, converged={new["converged"]}' if new else (info.get('status') or '—'))
        for row in v['terms']:
            p = row['pub']
            oc = f'{p[0]} [{p[1]}, {p[2]}]' if p else '—'
            nc = f'{f4(row["new_coef"])} {fci(row["new_lo"], row["new_hi"])}' if 'new_coef' in row else '—'
            if v['status'] != 'ok':
                reading = v['status']
            elif row['changes']:
                reading = '**CHANGES: ' + ', '.join(row['changes']) + '**'
            else:
                reading = 'stands'
            rows.append([mid, f'`{row["term"]}`', oc, nc, ofit, nfit,
                         comps(old['components']) if old else '—',
                         comps(new['components']) if new else '—', reading])
    A(tbl(rows, ['ID', 'core coefficient', 'old coef [95% CI] (published)', 'new coef [95% CI]',
                 'old fit', 'new fit', 'old variance (player / game / residual)',
                 'new variance (player / game / residual)', '§4 reading']))
    t1 = results['T-1'].get('tost')
    if t1:
        o, n = t1['old'], t1['new']
        A(f'\n**T-1 TOST (§4).** Published: overall p = 1, not equivalent. Re-executed old fit: p = {o["p"]:.4g} '
          f'({"equivalent" if o["equivalent"] else "not equivalent"}). New fit: p = {n["p"]:.4g} '
          f'(p lower {n["p_lower"]:.4g}, p upper {n["p_upper"]:.4g}) → '
          f'**{"equivalent" if n["equivalent"] else "not equivalent"}** at α = .05 against ±0.5 WP points; '
          f'verdict {"CHANGES" if results["T-1"].get("tost_changed") else "unchanged"}.\n')

    # ------------------------------------------------------------ 4. checks
    A('\n## 4. Checks and per-optimizer record\n')
    A('\n### 4.1 N and reproduction (§3.1 items 1–2)\n')
    rows = []
    for mid in ORDER:
        v = results[mid]
        if 'repro' not in v:
            rows.append([mid, '—', '—', '—', v['status']])
            continue
        rows.append([mid, f'{v["n_pub"]:,}' if v['n_pub'] is not None else 'not published',
                     f'{v["n_rebuilt"]:,}',
                     '; '.join(f'`{t}` {"✓" if ok else "✗"} ({d})' for t, ok, d in v['repro']),
                     v['status']])
    A(tbl(rows, ['ID', 'published N', 'rebuilt N', 'core values: published vs re-executed fit_mixed '
                                                    '(printed precision)', 'status']))
    A('\nSources of published values: ' + '; '.join(
        f'{mid}: {results[mid]["where"]}' for mid in ORDER if 'where' in results[mid]) + '.\n')

    A('\n### 4.2 Figure fits covered by report models (§3.1 item 3)\n')
    rows = []
    for c in covers:
        tgt = by_id.get(c['covers'])
        n_c = (c['old'] or {}).get('nobs')
        n_t = ((tgt or {}).get('old') or {}).get('nobs')
        pub = COVER_FIGURE[c['label']]
        got = tuple(f4(c['old'][k]['Intercept'], 3) for k in ('coef', 'lo', 'hi')) if c['old'] else None
        ok = n_c == n_t and got == pub
        rows.append([f'`{c["label"]}`', c['covers'], f'{n_c:,}' if n_c else '—', f'{n_t:,}' if n_t else '—',
                     f'{pub[0]} [{pub[1]}, {pub[2]}]',
                     f'{got[0]} [{got[1]}, {got[2]}]' if got else '—',
                     'covered' if ok else '**STOP: not covered**'])
    A(tbl(rows, ['figure fit', 'report model', 'N', 'report model N', 'figure intercept [CI]',
                 're-executed intercept [CI]', 'result']))
    if unlisted:
        A('\n**Unlisted fit_mixed calls encountered:** ' + ', '.join(f'`{u["label"]}`' for u in unlisted) + '\n')
    else:
        A('\nEvery `fit_mixed` call made by the four scripts is either on the re-run list or a covered figure fit.\n')

    A('\n### 4.3 Per-optimizer record of `fit_mixed_v2` (§2 items 4, 9)\n')
    A('Each cell: converged flag and log-likelihood; **bold** = selected. "degenerate" per §2 item 5.\n')
    rows = []
    for mid in ORDER:
        r = by_id.get(mid) or {}
        info = r.get('new_info') or {}
        cells = []
        for s in info.get('sweep', []):
            if s['error']:
                c = 'error: ' + s['error'][:60]
            else:
                c = f'{"conv" if s["converged"] else "NOT conv"} {s["llf"]:.3f}' + (' degenerate' if s['degenerate'] else '')
            cells.append(f'**{c}**' if s['method'] == info.get('selected') else c)
        cells += ['—'] * (5 - len(cells))
        rows.append([mid, f'{info.get("n", "—"):,}' if isinstance(info.get('n'), int) else '—'] + cells
                    + [info.get('status') or '—'])
    A(tbl(rows, ['ID', 'rows', 'lbfgs', 'bfgs', 'powell', 'nm', 'cg', 'status']))
    ow = [(mid, by_id[mid]['old_log']) for mid in ORDER if by_id.get(mid) and by_id[mid].get('old_log')]
    if ow:
        A('\nMessages printed by the unchanged `fit_mixed` during re-execution: ' +
          '; '.join(f'{mid}: "{" | ".join(log.split(chr(10)))}"' for mid, log in ow) + '.\n')

    # ------------------------------------------------------------ 5. sentences
    A('\n## 5. Sentences that must change (§4, §5 item 3)\n')
    A(f'Source: `{PAPER}`.\n')
    if not trig:
        A('\nNo core coefficient changed sign or CI-excludes-zero status, and the T-1 TOST verdict is '
          'unchanged. Under §4 every published conclusion on the re-run list stands and no sentence '
          'must change.\n')
    for mid, t, ch in trig:
        m = SENTENCES.get((mid, t), 'UNMAPPED')
        if m == 'UNMAPPED':
            A(f'\n- **{mid}, `{t}`** ({", ".join(ch)}): NOT YET MAPPED')
        elif m is None:
            A(f'\n- **{mid}, `{t}`** ({", ".join(ch)}): the affected conclusion is not stated in the paper.')
        else:
            for loc, quote in m:
                A(f'\n- **{mid}, `{t}`** ({", ".join(ch)}) — {loc}: "{quote}"')
    A('')

    # ------------------------------------------------------------ 6-7. texts
    A('\n## 6. Corrected text of v3 Amendment 2 (§5 item 4)\n')
    A('Delivered as text; `specs/` is not edited.\n')
    A('\n' + (AMENDMENT2_CORRECTED or '_(not yet written)_') + '\n')
    A('\n## 7. Corrected text of `README.md` line 34 (§5 item 5)\n')
    A('Delivered as text; `README.md` is not edited.\n')
    old34 = open(os.path.join(REPO, 'README.md')).read().splitlines()[33]
    A('\n**Old:**\n\n> ' + old34 + '\n')
    A('\n**New:**\n\n> ' + (README34_CORRECTED or '_(not yet written)_') + '\n')

    # ------------------------------------------------------------ appendix
    A('\n## Appendix. Full coefficient tables, old and new, all 23 models\n')
    A('Old = the unchanged `fit_mixed` re-executed on the rebuilt rows; new = `fit_mixed_v2`. '
      'Wald 95% CIs.\n')
    for mid in ORDER:
        r = by_id.get(mid)
        A(f'\n### {mid} — {SOURCE[mid]}\n')
        if not r:
            A('\n_not reached_\n')
            continue
        A(f'\n`{r["formula"]}` — rows {r["rows"]:,}\n')
        old, new = r.get('old'), r.get('new')
        terms = list((old or new or {}).get('coef', {}).keys())
        rows = []
        for t in terms:
            rows.append([f'`{t}`',
                         f'{f4(old["coef"][t])} {fci(old["lo"][t], old["hi"][t])}' if old and t in old['coef'] else '—',
                         f'{old["p"][t]:.3g}' if old and t in old['p'] else '—',
                         f'{f4(new["coef"][t])} {fci(new["lo"][t], new["hi"][t])}' if new and t in new['coef'] else '—',
                         f'{new["p"][t]:.3g}' if new and t in new['p'] else '—'])
        A(tbl(rows, ['term', 'old coef [95% CI]', 'old p', 'new coef [95% CI]', 'new p']))
        A(f'\nVariance components (player / game / residual): old {comps(old["components"]) if old else "—"}; '
          f'new {comps(new["components"]) if new else "—"}.\n')

    open(out, 'w').write('\n'.join(L) + '\n')
    print(f'wrote {out}')
    return results, trig
