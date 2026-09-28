#!/usr/bin/env python3
"""
p5_fit.py — bootstrap execution order for fit_mixed_v2 (SPEC v5 analysis decision, 2026-09-27).

Kept in its own module on purpose: patsy evaluates `C(game_id)` in the calling module's
namespace, and p5_results.py binds `C` to p5_common. Nothing here may be named `C`.
"""
import contextlib, io, warnings

import numpy as np
import statsmodels.formula.api as smf

from paper4_mixed_v2 import fit_mixed_v2, rows_for, is_degenerate


def fit_selected(formula, data, method, label):
    """The full-data selected optimizer first; only if it raises, fails to converge or is
    degenerate, the full fit_mixed_v2 sweep. Same model, rows and selection rules as
    fit_mixed_v2. Returns (fe_params dict or None, 'selected' | 'fallback' | 'failed')."""
    d = rows_for(formula, data)
    try:
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            md = smf.mixedlm(formula, d, groups=d['player_id'], re_formula='1',
                             vc_formula={'game': '0 + C(game_id)'})
            res = md.fit(method=method, maxiter=2000)
        if res.converged and not is_degenerate(res) and np.isfinite(res.llf):
            return res.fe_params.to_dict(), 'selected'
    except Exception:
        pass
    with contextlib.redirect_stdout(io.StringIO()), warnings.catch_warnings():
        warnings.simplefilter('ignore')
        res, _, info = fit_mixed_v2(formula, data, label)
    if res is None:
        return None, 'failed'
    return res.fe_params.to_dict(), 'fallback'
