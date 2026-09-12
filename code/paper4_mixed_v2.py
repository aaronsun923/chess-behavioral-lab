#!/usr/bin/env python3
"""
paper4_mixed_v2.py — the corrected random-effects estimator (Paper 4 correction spec §2).

v1's fit_mixed (paper4_report.py:74) passes vc_formula without re_formula, so statsmodels
fits no player intercept, and its optimizer guard never reads `converged`. fit_mixed_v2 fits
(1 | player_id) with game_id as a variance component nested in player_id, sweeps five
optimizers on every model, and selects the converged, non-degenerate fit with the highest
log-likelihood. paper4_report.py is not modified.
"""
import time, warnings
import numpy as np
import statsmodels.formula.api as smf

METHODS = ('lbfgs', 'bfgs', 'powell', 'nm', 'cg')   # [LOCKED §2 item 4]
MAXITER = 2000


def rows_for(formula, data):
    """Row handling identical to fit_mixed (paper4_report.py:84-88)."""
    toks = {t.strip() for t in formula.replace('~', '+').replace('*', '+')
            .replace(':', '+').split('+')}
    return data.dropna(subset=[t for t in toks if t and t in data.columns]).copy()


def components(res):
    """[§2 item 8] variance components on the natural scale — never from res.params."""
    cov = res.cov_re.to_numpy().ravel()
    return dict(player=float(cov[0]) if cov.size else None,
                game=[float(v) for v in np.atleast_1d(res.vcomp)],
                residual=float(res.scale))


def is_degenerate(res):
    """[§2 item 5] all variance components zero and intercept exactly zero."""
    vc = components(res)
    zero_var = vc['player'] in (None, 0.0) and all(v == 0.0 for v in vc['game'])
    return bool(zero_var and 'Intercept' in res.fe_params.index
                and res.fe_params['Intercept'] == 0.0)


def fit_mixed_v2(formula, data, label):
    """Returns (result or None, rows, info). info carries the per-optimizer record."""
    d = rows_for(formula, data)
    info = dict(label=label, n=len(d), sweep=[], selected=None, status=None)
    if len(d) < 50:
        info['status'] = 'fewer than 50 rows'
        return None, d, info

    fits = {}
    for meth in METHODS:
        rec = dict(method=meth, converged=None, llf=None, degenerate=None,
                   error=None, seconds=None, warnings=[])
        t = time.time()
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            try:
                md = smf.mixedlm(formula, d, groups=d['player_id'], re_formula='1',
                                 vc_formula={'game': '0 + C(game_id)'})
                r = md.fit(method=meth, maxiter=MAXITER)
                rec.update(converged=bool(r.converged), llf=float(r.llf),
                           degenerate=is_degenerate(r))
                fits[meth] = r
            except Exception as e:
                rec['error'] = f'{type(e).__name__}: {e}'
        rec['seconds'] = round(time.time() - t, 2)
        rec['warnings'] = sorted({str(x.message)[:120] for x in w})
        info['sweep'].append(rec)

    conv = [x for x in info['sweep'] if x['converged']]
    ok = [x for x in conv if not x['degenerate'] and np.isfinite(x['llf'])]
    if not conv:
        info['status'] = 'no converged fit'
    elif not ok:
        info['status'] = 'only degenerate converged fit'
    if info['status']:
        print(f'  [{label}] fit_mixed_v2: {info["status"]} — stop and report')
        return None, d, info

    best = max(ok, key=lambda x: x['llf'])      # ties keep METHODS order
    info.update(selected=best['method'], status='ok')
    print(f'  [{label}] fit_mixed_v2: selected {best["method"]} (llf {best["llf"]:.3f})')
    return fits[best['method']], d, info
