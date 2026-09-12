#!/usr/bin/env python3
"""
paper4_correction_run.py — executes specs/paper4_correction_spec.md.

    python3 paper4_correction_run.py setup  --data ~/Desktop/chess-study --work WORK
    python3 paper4_correction_run.py verify --work WORK                   # §3.4, first
    python3 paper4_correction_run.py rerun  --work WORK --builder v1      # §3.1-§3.2
    python3 paper4_correction_run.py rerun  --work WORK --builder b4report
    python3 paper4_correction_run.py rerun  --work WORK --builder b4figs
    python3 paper4_correction_run.py rerun  --work WORK --builder v3
    python3 paper4_correction_run.py report --work WORK

The original report scripts run unmodified inside WORK, a sandbox holding read-only links to
the inputs and private copies of every file the scripts write, so no published report, figure
or data file is touched and no engine is reachable. Each script's own data preparation builds
the rows (§3.1 item 1). Its fit_mixed calls are intercepted: the unchanged fit_mixed runs and
its result is handed back to the script (§3.1 item 2), and fit_mixed_v2 is fitted on the same
rows (§3.1 item 4).
"""
import os, sys, io, json, time, runpy, hashlib, argparse, platform, contextlib, subprocess

CODE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(CODE)
sys.dont_write_bytecode = True
sys.path.insert(0, CODE)

LINKS = ['paper4_results', 'paper4b_results', 'paper4_cache', 'paper4b_cache',
         'analysis_dataset_male_titled_raw.csv', 'analysis_dataset_male_titled_agg.csv',
         'p4_v3_depth_check.parquet', 'p4_v3_successor.log', 'p4_v3_rows.log',
         'p4_v3_consistency.log']
COPIES = ['p4_v3_rows/p4_v3_rows.parquet']      # its directory is written by p4_v3_analysis.py:356

STATSMODELS_ON_RECORD = '0.14.6'                # [§2 item 10]
LLF_TOL = 0.1                                   # [§3.4 item 3]
REPRO_TOL = 1e-9                                # [§3.4 item 4]

# fit_mixed label -> model ID (§3.2), or the report model a figure fit must reproduce (§3.1 item 3)
MODELS = {'7.1-roster': 'V1-1', '7.1': 'V1-2', '7.2': 'V1-3', '7.2b': 'V1-4',
          '4.1': 'B-1', '4.1-liquidation': 'B-2', '4.3a': 'B-3', '4.3b': 'B-4',
          'figB-500': 'B-5',
          'H1': 'T-1', 'H2': 'T-2', 'H3': 'T-3', 'H4-RES': 'T-4', 'H4-CF': 'T-5',
          '6.5': 'T-6', 'R1-H2': 'T-7', 'R1-RES': 'T-8', 'R1-CF': 'T-9',
          'R2-RES': 'T-10', 'R3-RES': 'T-11', 'R3-CF': 'T-12',
          'posthoc-inside MultiPV-5': 'T-13', 'posthoc-freshly evaluated': 'T-14'}
COVER = {'figB-full': 'B-1', 'figC-primary': 'B-1', 'figC-var': 'B-3',
         'figC-band10': 'B-4', 'figC-liq': 'B-2'}


def sha256(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


def jdump(obj, path):
    json.dump(obj, open(path, 'w'), indent=1, default=float)


def jload(path):
    return json.load(open(path))


def summarize(res):
    """Fixed effects with Wald CIs, fit status, and variance components on the natural scale."""
    from paper4_mixed_v2 import components
    if res is None:
        return None
    fe, ci = res.fe_params, res.conf_int()
    return dict(nobs=int(res.nobs), converged=bool(res.converged), llf=float(res.llf),
                coef={t: float(fe[t]) for t in fe.index},
                lo={t: float(ci.loc[t, 0]) for t in fe.index},
                hi={t: float(ci.loc[t, 1]) for t in fe.index},
                se={t: float(res.bse[t]) for t in fe.index},
                p={t: float(res.pvalues[t]) for t in fe.index},
                components=components(res))


class Tee(io.StringIO):
    def write(self, s):
        sys.__stdout__.write(s)
        return super().write(s)


# ====================================================================== setup
def cmd_setup(a):
    import statsmodels
    if statsmodels.__version__ != STATSMODELS_ON_RECORD:
        raise SystemExit(f'STOP [§2 item 10]: statsmodels {statsmodels.__version__}, '
                         f'on record {STATSMODELS_ON_RECORD}')
    data = os.path.abspath(os.path.expanduser(a.data))
    work = os.path.abspath(a.work)
    if os.path.exists(work) and os.listdir(work):
        raise SystemExit(f'{work} is not empty')
    os.makedirs(os.path.join(work, 'p4_v3_rows'), exist_ok=True)
    for f in LINKS:
        if os.path.exists(os.path.join(data, f)):
            os.symlink(os.path.join(data, f), os.path.join(work, f))
    for f in COPIES:
        with open(os.path.join(data, f), 'rb') as src, open(os.path.join(work, f), 'wb') as dst:
            dst.write(src.read())
    jdump(dict(data=data, work=work, started=time.time(),
               paper4_report_sha256=sha256(os.path.join(CODE, 'paper4_report.py')),
               python=platform.python_version(), statsmodels=statsmodels.__version__,
               platform=f'{platform.system()} {platform.machine()}', cores=os.cpu_count()),
          os.path.join(work, 'setup.json'))
    print(f'sandbox ready: {work}')


# ===================================================================== §3.4
class SweepModel:
    """Stands in for smf.mixedlm(...) inside crossfit: sweeps all optimizers, returns the
    fit for the optimizer crossfit asked for, so the script proceeds exactly as in v3."""
    def __init__(self, real, calls, formula, data, groups, kw):
        self.real, self.calls, self.args = real, calls, (formula, data, groups, kw)

    def fit(self, method='lbfgs', **fit_kw):
        import warnings
        formula, data, groups, kw = self.args
        rec = dict(call=len(self.calls), n=len(data), players=int(groups.nunique()),
                   requested=method, sweep=[])
        chosen, chosen_err = None, None
        for meth in ('lbfgs', 'bfgs', 'powell', 'nm', 'cg'):
            r_ = dict(method=meth, converged=None, llf=None, error=None)
            t = time.time()
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter('always')
                try:
                    r = self.real.mixedlm(formula, data, groups=groups, **kw).fit(method=meth, **fit_kw)
                    r_.update(converged=bool(r.converged), llf=float(r.llf))
                    if meth == method:
                        chosen = r
                except Exception as e:
                    r_['error'] = f'{type(e).__name__}: {e}'
                    if meth == method:
                        chosen_err = e
            r_['seconds'] = round(time.time() - t, 2)
            r_['warnings'] = sorted({str(x.message)[:120] for x in w})
            rec['sweep'].append(r_)
        self.calls.append(rec)
        print(f'  [§3.4 call {rec["call"]}] n={rec["n"]:,} ' +
              ' '.join(f'{x["method"]}:{x["converged"]}/{x["llf"]}' for x in rec['sweep']))
        if chosen is None:
            raise chosen_err
        return chosen


class SweepSmf:
    def __init__(self, real, calls):
        self._real, self._calls = real, calls

    def __getattr__(self, name):
        return getattr(self._real, name)

    def mixedlm(self, formula, data, groups=None, **kw):
        return SweepModel(self._real, self._calls, formula, data, groups, kw)


def cmd_verify(a):
    import numpy as np, pandas as pd
    work = os.path.abspath(a.work)
    setup = jload(os.path.join(work, 'setup.json'))
    os.chdir(work)
    import statsmodels.formula.api as real_smf
    import paper4_report as R
    import p4_v3_analysis as A

    calls = []
    A.smf = SweepSmf(real_smf, calls)
    # §3.4 precedes §3.2: no model on the re-run list is fitted in this stage
    R.fit_mixed = lambda formula, data, label: (None, None, data)
    t0 = time.time()
    A.main()

    sets = ['main training set (p4_v3_analysis.py:262)', 'unrestricted training set, §7.2 (p4_v3_analysis.py:559)']
    folds, passed = [], len(calls) == 10
    for i, c in enumerate(calls):
        conv = [x['llf'] for x in c['sweep'] if x['converged'] and x['llf'] is not None and np.isfinite(x['llf'])]
        lb = c['sweep'][0]
        best = max(conv) if conv else None
        ok = bool(lb['converged'] and best is not None and lb['llf'] >= best - LLF_TOL)
        passed &= ok
        folds.append(dict(c, training_set=sets[i // 5] if i < 10 else 'unexpected', fold=i % 5,
                          best_converged_llf=best,
                          lbfgs_gap=(best - lb['llf']) if (best is not None and lb['llf'] is not None) else None,
                          at_maximum=ok))

    old = pd.read_parquet(os.path.join(setup['data'], 'p4_v3_rows', 'p4_v3_rows_analysis.parquet'))
    new = pd.read_parquet(os.path.join(work, 'p4_v3_rows', 'p4_v3_rows_analysis.parquet'))
    m = old[['game_id', 'ply', 'E_played', 'E_best']].merge(
        new[['game_id', 'ply', 'E_played', 'E_best']], on=['game_id', 'ply'],
        how='outer', suffixes=('_stored', '_rerun'), indicator=True)
    repro = dict(rows_stored=len(old), rows_rerun=len(new),
                 unmatched=int((m._merge != 'both').sum()))
    for c in ['E_played', 'E_best']:
        s, r = m[c + '_stored'], m[c + '_rerun']
        both = s.notna() & r.notna()
        repro[c] = dict(max_abs_diff=float((s[both] - r[both]).abs().max()) if both.any() else None,
                        nan_mismatch=int((s.isna() != r.isna()).sum()),
                        compared=int(both.sum()))
    repro_ok = (repro['unmatched'] == 0 and all(
        repro[c]['nan_mismatch'] == 0 and repro[c]['max_abs_diff'] is not None
        and repro[c]['max_abs_diff'] <= REPRO_TOL for c in ['E_played', 'E_best']))
    out = dict(n_calls=len(calls), folds=folds, reproduction=repro,
               sweep_passed=bool(passed), reproduction_passed=bool(repro_ok),
               passed=bool(passed and repro_ok), minutes=(time.time() - t0) / 60)
    jdump(out, os.path.join(work, 'verify.json'))
    print(f'§3.4: sweep {"PASS" if passed else "FAIL"} | reproduction '
          f'{"PASS" if repro_ok else "FAIL"} | {json.dumps(repro)}')
    if not out['passed']:
        raise SystemExit('STOP [§3.4 item 5]: the expected-error model did not verify; '
                         'nothing in §3.2 is fitted.')


# ================================================================ §3.1-§3.2
def cmd_rerun(a):
    work = os.path.abspath(a.work)
    v = jload(os.path.join(work, 'verify.json')) if os.path.exists(os.path.join(work, 'verify.json')) else None
    if not v or not v['passed']:
        raise SystemExit('STOP: §3.4 has not passed; nothing in §3.2 is fitted.')
    os.chdir(work)
    import paper4_report as R
    from paper4_mixed_v2 import fit_mixed_v2

    orig = R.fit_mixed
    recs = []
    out_path = os.path.join(work, f'rerun_{a.builder}.json')

    def intercept(formula, data, label):
        buf = Tee()
        t = time.time()
        with contextlib.redirect_stdout(buf):
            res, ols, d = orig(formula, data, label)
        log = buf.getvalue()
        method = 'lbfgs'
        for line in log.splitlines():
            if 'used method=' in line:
                method = line.split('used method=')[1].strip()
            if 'no optimizer produced a usable fit' in line:
                method = None
        if res is None:
            method = None
        rec = dict(label=label, formula=formula, n_input=len(data), rows=len(d),
                   id=MODELS.get(label), covers=COVER.get(label),
                   old=summarize(res), old_method=method, old_log=log.strip(),
                   old_seconds=round(time.time() - t, 1))
        if rec['id']:
            t = time.time()
            nres, nd, info = fit_mixed_v2(formula, data, label)
            assert len(nd) == len(d), f'{label}: row mismatch {len(nd)} vs {len(d)}'
            rec.update(new=summarize(nres), new_info=info, new_seconds=round(time.time() - t, 1))
            if label == 'H1':           # [§4] TOST recomputed from the new fit
                import p4_v3_analysis as A
                for k, r in (('old', res), ('new', nres)):
                    if r is not None:
                        pt, p1, p2 = A.tost(float(r.params['Intercept']), float(r.bse['Intercept']), len(d) - 1)
                        rec[f'tost_{k}'] = dict(p=float(pt), p_lower=float(p1), p_upper=float(p2),
                                                equivalent=bool(pt < .05))
        elif not rec['covers']:
            rec['unlisted'] = True
        recs.append(rec)
        jdump(recs, out_path)
        return res, ols, d

    R.fit_mixed = intercept
    t0 = time.time()
    if a.builder == 'v1':
        R.build()
    elif a.builder == 'b4report':
        import paper4b_report as B4
        B4.fit_mixed = intercept
        B4.build()
    elif a.builder == 'b4figs':
        runpy.run_path(os.path.join(CODE, 'paper4b_figures.py'), run_name='__main__')
    elif a.builder == 'v3':
        import p4_v3_analysis as A
        A.main()
        import p4_v3_posthoc as PH
        PH.main()
    jdump(recs, out_path)
    print(f'rerun {a.builder}: {len(recs)} fit_mixed calls in {(time.time()-t0)/60:.1f} min')


# ======================================================= paper §4.3 / Figure C
def delta_pred(res, zz):
    """Predicted mean at time_pressure_z = zz with its delta-method 95% CI — the formula of
    paper4b_figures.py:fig_c."""
    import numpy as np
    cov = res.cov_params(); b0 = res.params['Intercept']; bt = res.params['time_pressure_z']
    v = (cov.loc['Intercept', 'Intercept'] + zz**2 * cov.loc['time_pressure_z', 'time_pressure_z']
         + 2 * zz * cov.loc['Intercept', 'time_pressure_z'])
    se = float(np.sqrt(v)); p = float(b0 + bt * zz)
    return dict(mean=p, lo=p - 1.96 * se, hi=p + 1.96 * se)


def cmd_predict(a):
    """Predicted mean ΔRISK_steep at time_pressure_z = ±2, by the delta method exactly as
    paper4b_figures.py:fig_c computes it, from the unchanged fit_mixed and from fit_mixed_v2
    on the same rows (the figC-primary fit, covered by B-1)."""
    work = os.path.abspath(a.work)
    os.chdir(work)
    import paper4_report as R
    from paper4_mixed_v2 import fit_mixed_v2

    orig, out = R.fit_mixed, {}

    def intercept(formula, data, label):
        res, ols, d = orig(formula, data, label)
        if label == 'figC-primary':
            nres, nd, info = fit_mixed_v2(formula, data, label)
            assert len(nd) == len(d), f'{label}: row mismatch'
            out.update(rows=len(d), new_selected=info['selected'], new_status=info['status'],
                       old={str(z): delta_pred(res, z) for z in (-2, 2)},
                       new={str(z): delta_pred(nres, z) for z in (-2, 2)} if nres is not None else None)
        return res, ols, d

    R.fit_mixed = intercept
    runpy.run_path(os.path.join(CODE, 'paper4b_figures.py'), run_name='__main__')
    jdump(out, os.path.join(work, 'predictions.json'))
    print(f'predictions: {json.dumps(out)}')


# ======================================================= figures B and C, corrected
FIGS = ['figB_pilot_vs_full', 'figC_robustness_ladder']
FIG_ROWS = {31: ('figB-500', None), 32: ('figB-full', None), 33: ('figC-primary', None),   # rows of
            34: ('figC-var', None), 35: ('figC-band10', None), 36: ('figC-liq', None),     # docs/paper4_
            37: ('figC-primary', -2), 38: ('figC-primary', 2)}                             # correction_numbers.md


def cmd_figures(a):
    """Figures B and C redrawn from fit_mixed_v2. Same interception point as cmd_rerun: each
    fit_mixed call in paper4b_figures.py runs the unchanged fit_mixed and fit_mixed_v2 on the same
    rows, but the fit handed back to the script is fit_mixed_v2's. The values the new figures print
    must equal docs/paper4_correction_numbers.md before any published file is replaced; the
    committed versions are kept as *_v1.png and *_v1.pdf."""
    work = os.path.abspath(a.work)
    fig_repo = os.path.join(REPO, 'figures', 'paper4')
    os.chdir(work)
    import paper4_report as R
    from paper4_mixed_v2 import fit_mixed_v2

    orig, got = R.fit_mixed, {}

    def intercept(formula, data, label):
        res, ols, d = orig(formula, data, label)
        nres, nd, info = fit_mixed_v2(formula, data, label)
        if nres is None:
            raise SystemExit(f'STOP [§2 item 7]: {label}: {info["status"]}; figures left unchanged')
        assert len(nd) == len(d), f'{label}: row mismatch'
        ci = nres.conf_int().loc['Intercept']
        got[label] = dict(est=[float(nres.params['Intercept']), float(ci[0]), float(ci[1])],
                          selected=info['selected'], rows=len(d))
        if label == 'figC-primary':
            for z in (-2, 2):
                q = delta_pred(nres, z)
                got[f'{label}@{z}'] = dict(est=[q['mean'], q['lo'], q['hi']])
        return nres, ols, d

    R.fit_mixed = intercept
    runpy.run_path(os.path.join(CODE, 'paper4b_figures.py'), run_name='__main__')

    want = {}
    for line in open(os.path.join(REPO, 'docs', 'paper4_correction_numbers.md')):
        c = [x.strip() for x in line.strip().strip('|').split('|')]
        if len(c) > 6 and c[0].isdigit() and int(c[0]) in FIG_ROWS:
            want[int(c[0])] = c[6].strip('`')
    check = []
    for n, (label, z) in FIG_ROWS.items():
        e = got[label if z is None else f'{label}@{z}']['est']
        s = f'{e[0]:+.3f} [{e[1]:+.3f}, {e[2]:+.3f}]'.replace('-', '−')
        check.append(dict(row=n, fit=label, z=z, printed=s, numbers_doc=want.get(n), match=s == want.get(n)))
        print(f'  [{"OK " if s == want.get(n) else "MISMATCH"}] #{n} {label}{"" if z is None else f" z={z}"}: '
              f'figure {s} | numbers doc {want.get(n)}')
    out = dict(fits=got, check=check, files=[])
    if not all(x['match'] for x in check):
        jdump(out, os.path.join(work, 'figures.json'))
        raise SystemExit('STOP: printed values differ from the numbers table; published figures left unchanged')

    for name in FIGS:
        for ext in ('png', 'pdf'):
            rel = f'figures/paper4/{name}.{ext}'
            v1 = os.path.join(fig_repo, f'{name}_v1.{ext}')
            committed = subprocess.run(['git', 'show', f'HEAD:{rel}'], cwd=REPO, capture_output=True).stdout
            if not committed:
                raise SystemExit(f'STOP: {rel} not found at HEAD')
            if not os.path.exists(v1):
                open(v1, 'wb').write(committed)          # the published version, from git
            with open(os.path.join(work, 'paper4b_figures', f'{name}.{ext}'), 'rb') as src:
                open(os.path.join(REPO, rel), 'wb').write(src.read())
            out['files'].append(dict(file=rel, v1=os.path.relpath(v1, REPO),
                                     v1_sha256=hashlib.sha256(open(v1, 'rb').read()).hexdigest(),
                                     new_sha256=sha256(os.path.join(REPO, rel))))
    jdump(out, os.path.join(work, 'figures.json'))
    print('figures replaced; published versions kept as *_v1')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('stage', choices=['setup', 'verify', 'rerun', 'predict', 'figures', 'report', 'numbers'])
    ap.add_argument('--data', default='~/Desktop/chess-study')
    ap.add_argument('--work', required=True)
    ap.add_argument('--builder', choices=['v1', 'b4report', 'b4figs', 'v3'])
    ap.add_argument('--out', default=os.path.join(REPO, 'docs', 'paper4_correction_REPORT.md'))
    ap.add_argument('--numbers-out', default=os.path.join(REPO, 'docs', 'paper4_correction_numbers.md'))
    a = ap.parse_args()
    if a.stage == 'report':
        import paper4_correction_report as CR
        CR.write(a.work, a.out)
    elif a.stage == 'numbers':
        import paper4_correction_numbers as CN
        CN.write(a.work, a.numbers_out)
    else:
        {'setup': cmd_setup, 'verify': cmd_verify, 'rerun': cmd_rerun, 'predict': cmd_predict,
         'figures': cmd_figures}[a.stage](a)
