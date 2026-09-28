#!/usr/bin/env python3
"""
p5_pilot_addenda.py — additions to reports/spec_v5_pilot.md requested 2026-09-24
before the truth amendment. No engine: reads data/spec_v5/pilot_subsample_d4.parquet
and pilot_d12_rows.parquet. Appends section 12 to the pilot report.
"""
import os, sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p5_common as C
from p5_pilot import boot, wmean

f = lambda x: f'{x:.4f}'


def main():
    s = pd.read_parquet(os.path.join(C.OUT_DIR, 'pilot_subsample_d4.parquet'))
    d12 = pd.read_parquet(os.path.join(C.OUT_DIR, 'pilot_d12_rows.parquet'))[['row_id', 'e_12']]
    chk = s[['row_id', 'e_12']].merge(d12, on='row_id', suffixes=('', '_pilot'))
    assert len(chk) == len(s) and (chk.e_12 == chk.e_12_pilot).all()
    types = [('h', 'n_h'), ('best_15', 'n15'), ('best_4', 'n4')]
    L = []; P = L.append
    P('\n## 12. Additions before the truth amendment (2026-09-24, no engine)\n')

    P('### 12.1 Distribution of V20 − V15 per position type (subsample, terminal excluded)\n')
    P('| Position type | N | SD | p50 \\|x\\| | p90 \\|x\\| | p99 \\|x\\| | max \\|x\\| | share \\|x\\| > 5 | SD of rows with \\|x\\| ≤ 5 | 1.4826 × MAD |\n|---|---|---|---|---|---|---|---|---|---|')
    for t, c in types:
        x = s[c].dropna().values; a = np.abs(x)
        core = x[a <= 5]
        mad = 1.4826 * np.median(np.abs(x - np.median(x)))
        P(f'| after {t} | {len(x):,} | {f(x.std(ddof=1))} | {f(np.percentile(a, 50))} | {f(np.percentile(a, 90))} | '
          f'{f(np.percentile(a, 99))} | {f(a.max())} | {(a > 5).mean():.4f} | {f(core.std(ddof=1))} | {f(mad)} |')
    P('\nx = V20 − V15. The last two columns are the SD without the rows beyond 5 WP points and a tail-robust scale (normal-consistent MAD). ')
    rows = []
    for t, c in types:
        x = s[c].dropna().values; a = np.abs(x)
        rows.append((x.std(ddof=1), x[a <= 5].std(ddof=1), 1.4826 * np.median(np.abs(x - np.median(x))), (a > 5).mean()))
    bound = 0.25 * s.e_4.std(ddof=1)
    tail = any(core < bound for _, core, _, _ in rows)
    P(f'Is the SD driven by a tail: {"yes" if tail else "no"}. Removing the rows with |x| > 5 '
      f'({min(r[3] for r in rows):.1%} to {max(r[3] for r in rows):.1%} of rows) moves the SD from '
      f'{min(r[0] for r in rows):.2f}–{max(r[0] for r in rows):.2f} to {min(r[1] for r in rows):.2f}–{max(r[1] for r in rows):.2f}; '
      f'the MAD scale is {min(r[2] for r in rows):.2f}–{max(r[2] for r in rows):.2f}; '
      f'{"all remain above" if not tail else "at least one falls below"} the SD-rule bound {bound:.4f}.\n')

    P('### 12.2 Var(V20 − V15) / Var(e_d) on the subsample\n')
    ve4 = s.e_4.var(ddof=1); ve12 = s.e_12.var(ddof=1)
    P(f'Var(e_4) = {f(ve4)} (N = {s.e_4.notna().sum():,}); Var(e_12) = {f(ve12)} (pilot e_12 on the subsample rows, N = {s.e_12.notna().sum():,}).\n')
    P('| Position type | Var(V20 − V15) | / Var(e_4) | / Var(e_12) |\n|---|---|---|---|')
    for t, c in types:
        v = s[c].var(ddof=1)
        P(f'| after {t} | {f(v)} | {f(v / ve4)} | {f(v / ve12)} |')
    P('\nbest_12 positions were not evaluated at depth 20 in the pilot (§5(b) covers h, best_15, best_4), so there is no best_12 row; '
      'the depth-12 column divides the available position types by Var(e_12).\n')

    P('### 12.3 L_h under the depth-20 ruler (subsample)\n')
    q = s.dropna(subset=['V20_h', 'V20_b15', 'V_h', 'V_b15']).copy()
    q['L20'] = q.V20_b15 - q.V20_h
    q['L15'] = q.V_b15 - q.V_h
    g = q.game_id.values
    ci20 = boot(g, lambda w: wmean(q.L20.values, w))
    ci15 = boot(g, lambda w: wmean(q.L15.values, w))
    cid = boot(g, lambda w: wmean((q.L20 - q.L15).values, w))
    P(f'Rows with V15 and V20 at both h and best_15: {len(q):,}.\n')
    P('| Quantity | Mean | 95% interval |\n|---|---|---|')
    P(f'| L_h, depth-20 ruler: V20(best_15) − V20(h) | {f(q.L20.mean())} | [{f(ci20[0])}, {f(ci20[1])}] |')
    P(f'| L_h, depth-15 ruler: V15(best_15) − V15(h) | {f(q.L15.mean())} | [{f(ci15[0])}, {f(ci15[1])}] |')
    P(f'| Difference (depth 20 − depth 15) | {f((q.L20 - q.L15).mean())} | [{f(cid[0])}, {f(cid[1])}] |')
    P(f'| Mean V20 − V15 at h positions | {f((q.V20_h - q.V_h).mean())} | |')
    P(f'| Mean V20 − V15 at best_15 positions | {f((q.V20_b15 - q.V_b15).mean())} | |')
    P('\nIntervals: game-clustered percentile bootstrap, 2,000 draws, seed 20261001. The difference row equals the best_15 mean minus the h mean.\n')

    p = os.path.join(C.REPO, 'reports', 'spec_v5_pilot.md')
    txt = open(p).read()
    txt = txt.split('\n## 12. Additions')[0].rstrip('\n') + '\n'
    open(p, 'w').write(txt + '\n'.join(L))
    print('\n'.join(L))


if __name__ == '__main__':
    main()
