#!/usr/bin/env python3
"""
p4_v3_consistency.py — SPEC v3 Amendment 1 item 2 [LOCKED].

Row-by-row comparison of the recomputed `risk_steep` against the value v2
stored. Same engine version and fixed depth should give exact equality. Any
mismatch is a stop condition: this script exits non-zero and nothing
downstream may run.

    python3 p4_v3_consistency.py
"""
import glob, os, sys
import numpy as np, pandas as pd

V2_DIR, SUCC_DIR = 'paper4b_results', 'p4_v3_successor_lines'


def _read(d):
    fs = sorted(glob.glob(os.path.join(d, '**', '*.parquet'), recursive=True))
    return pd.concat([pd.read_parquet(f) for f in fs], ignore_index=True)


def main():
    v2 = _read(V2_DIR).drop_duplicates(['game_id', 'ply', 'which_move'])
    sc = _read(SUCC_DIR).drop_duplicates(['game_id', 'ply', 'which_move'])
    print(f'v2 rows {len(v2)} | recomputed rows {len(sc)}')

    m = v2.merge(sc, on=['game_id', 'ply', 'which_move'], how='outer',
                 suffixes=('_v2', '_new'), indicator=True)
    missing = (m._merge != 'both').sum()
    print(f'coverage: matched {(m._merge == "both").sum()}, unmatched {missing}')
    if missing:
        print(m[m._merge != 'both'][['game_id', 'ply', 'which_move', '_merge']].head(20))

    b = m[m._merge == 'both'].copy()
    for col, new in [('risk_steep', 'risk_steep_recomp'),
                     ('wp_self_opp_best', 'wp_self_opp_best_recomp'),
                     ('wp_self_opp_worst', 'wp_self_opp_worst_recomp'),
                     ('n_pv', 'n_pv_new')]:
        old = col + '_v2' if col + '_v2' in b.columns else col
        if old not in b.columns or new not in b.columns:
            print(f'  [skip {col}: columns {old}/{new} not both present]'); continue
        o, n = b[old].to_numpy(float), b[new].to_numpy(float)
        both_nan = np.isnan(o) & np.isnan(n)
        d = np.where(both_nan, 0.0, np.abs(o - n))
        exact = int((~both_nan & (o != n)).sum())
        print(f'\n{col}:  max |diff| = {np.nanmax(d):.3e}   exact mismatches = {exact} / {len(b)}')
        for tol in (1e-12, 1e-9, 1e-6, 1e-3):
            print(f'    |diff| > {tol:>7.0e} : {int((d > tol).sum())}')
        if exact:
            bad = b[(~both_nan) & (o != n)]
            print('    worst rows:')
            print(bad.assign(diff=d[(~both_nan) & (o != n)])
                  .nlargest(10, 'diff')[['game_id', 'ply', 'which_move', old, new, 'diff']]
                  .to_string(index=False))

    o = b['risk_steep'].to_numpy(float) if 'risk_steep' in b.columns else b['risk_steep_v2'].to_numpy(float)
    n = b['risk_steep_recomp'].to_numpy(float)
    nan_ok = np.isnan(o) & np.isnan(n)
    n_mis = int((~nan_ok & (o != n)).sum())
    print(f'\n=== VERDICT: risk_steep mismatches = {n_mis}, '
          f'max |diff| = {np.nanmax(np.where(nan_ok, 0.0, np.abs(o - n))):.3e} ===')
    if n_mis or missing:
        print('STOP CONDITION MET (Amendment 1 item 2). Do not proceed.')
        sys.exit(1)
    print('PASS — recomputation reproduces v2 exactly. Proceeding is permitted.')


if __name__ == '__main__':
    main()
