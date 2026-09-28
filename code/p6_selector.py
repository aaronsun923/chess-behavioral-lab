#!/usr/bin/env python3
"""
p6_selector.py — SPEC v6 (specs/paper4_spec_v6.md, LOCKED at e721ee2): pre-move selector test.
No engine runs; inputs are data/spec_v5/results/rows.parquet (V20 values, best_d,
best_15_singlepv, covariates, v1 FENs).

    python3 code/p6_selector.py rows     # step 1: §2 row set, FEN features, §0 report section
    python3 code/p6_selector.py fit      # §3: out-of-fold scores, all selectors and variants
    python3 code/p6_selector.py report   # §4–§8: quantities, bootstrap, descriptives, robustness, S1–S5

Outputs: data/spec_v5/results/selector/ (not committed), reports/spec_v6_selector.md.
"""
import os, sys, json

import numpy as np
import pandas as pd
import chess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p5_common as C

RES5 = os.path.join(C.OUT_DIR, 'results')
OUT = os.path.join(RES5, 'selector'); os.makedirs(OUT, exist_ok=True)
REPORT = os.path.join(C.REPO, 'reports', 'spec_v6_selector.md')
SEED = 20261001
N_BOOT = 2000
PIECE = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3, chess.ROOK: 5, chess.QUEEN: 9}
TERM = ['h', 'b20', 'b2', 'b4', 'b8', 'b15']         # successors used by SPEC v6


def fen_features(fen):
    """material balance from the side to move (P 1, N 3, B 3, R 5, Q 9; kings not counted),
    number of pieces on the board (all pieces, kings and pawns included), side to move in check."""
    b = chess.Board(fen)
    us, them = b.turn, not b.turn
    mat = sum(v * (len(b.pieces(p, us)) - len(b.pieces(p, them))) for p, v in PIECE.items())
    return mat, len(b.piece_map()), int(b.is_check())


def build_rows():
    r = pd.read_parquet(os.path.join(RES5, 'rows.parquet'))
    n0 = len(r)
    term = r[[f'term_{x}' for x in TERM]].any(axis=1)
    miss = r.gap_12.isna() | r.spread_15.isna()
    info = {'rows_v5': n0, 'terminal_rows': int(term.sum()), 'missing_feature_rows': int(miss.sum()),
            'overlap': int((term & miss).sum())}
    r = r[~term & ~miss].reset_index(drop=True)
    info['N'] = len(r)
    assert len(r) == 49907, f'§2 row set has {len(r)} rows, spec says 49,907'
    f = [fen_features(x) for x in r.fen]
    r['material'] = [a for a, _, _ in f]
    r['pieces'] = [b for _, b, _ in f]
    r['in_check'] = [c for _, _, c in f]
    r['L_h'] = r.V20_b20 - r.V20_h
    for d in (2, 4, 8, 15):
        r[f'L_{d}'] = r[f'e_{d}']                          # L_d = V20(best_20) - V20(best_d) = e_d
    keep = ['row_id', 'game_id', 'ply', 'player_id', 'player_elo', 'opponent_elo', 'time_pressure',
            'material', 'pieces', 'in_check', 'wp_level', 'gap_12', 'spread_15', 'n_reasonable',
            'eval_volatility', 'move_played', 'move_engine_best', 'h', 'best_2', 'best_4', 'best_8',
            'best_15_singlepv', 'best_20', 'V20_h', 'V20_b20', 'V20_b2', 'V20_b4', 'V20_b8', 'V20_b15',
            'L_h', 'L_2', 'L_4', 'L_8', 'L_15']
    return r[keep], info


def boot_means(r, cols):
    """Game-clustered percentile bootstrap of column means: resample games with replacement,
    recompute the means on the drawn rows (seed 20261001, 2,000 draws)."""
    games = np.array(sorted(r.game_id.unique()))
    gi = np.searchsorted(games, r.game_id.values)
    n_g = np.bincount(gi, minlength=len(games)).astype(float)
    rng = np.random.default_rng(SEED)
    cnt = np.stack([np.bincount(rng.integers(0, len(games), len(games)), minlength=len(games))
                    for _ in range(N_BOOT)]).astype(float)
    out = {}
    for c in cols:
        s = np.bincount(gi, weights=r[c].values, minlength=len(games))
        v = (cnt @ s) / (cnt @ n_g)
        out[c] = (float(r[c].mean()), float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5)))
    return out, len(games)


def stage_rows():
    r, info = build_rows()
    r.to_parquet(os.path.join(OUT, 'rows_v6.parquet'), index=False)
    b, n_games = boot_means(r, ['L_h', 'L_2', 'L_4', 'L_8', 'L_15'])
    info.update(n_games=n_games, means={k: v for k, v in b.items()},
                features={'material_mean': float(r.material.mean()), 'material_sd': float(r.material.std(ddof=1)),
                          'pieces_mean': float(r.pieces.mean()), 'pieces_min': int(r.pieces.min()),
                          'pieces_max': int(r.pieces.max()), 'in_check_share': float(r.in_check.mean())})
    json.dump(info, open(os.path.join(OUT, 'section0.json'), 'w'), indent=2)

    f4 = lambda x: f'{x:.4f}'
    L = ['# SPEC v6: pre-move selector test\n',
         'Spec: `specs/paper4_spec_v6.md` at e721ee2 (LOCKED 2026-09-28). Ruler V20, anchor best_20 (SPEC v5 Amendment A1). '
         'No engine runs. This section is reported before any selector is fitted (§0).\n',
         '## 0. The §2 row set\n',
         f"Rows: {info['rows_v5']:,} (SPEC v5 row table) − {info['terminal_rows']} terminal rows − {info['missing_feature_rows']} rows missing gap_12 or spread_15 "
         f"(overlap {info['overlap']}) = **{info['N']:,}** rows in {n_games:,} games. "
         'Terminal row: the position after any of h, best_20, best_2, best_4, best_8 or best_15 is checkmate or a draw by rule; '
         'these are exactly the 14 rows whose best_20 successor is terminal, and they contain the 12 rows whose h successor is terminal.\n',
         '| Quantity | Mean (WP points) | 95% interval |\n|---|---|---|']
    lab = [('L_h', 'mean L_h = V20(best_20) − V20(h)'), ('L_2', 'E_2 = mean L_2'), ('L_4', 'E_4 = mean L_4'),
           ('L_8', 'E_8 = mean L_8'), ('L_15', 'E_15 = mean L_15 (best_15 = best_15_singlepv)')]
    for c, name in lab:
        m, lo, hi = b[c]
        L.append(f'| {name} | {f4(m)} | [{f4(lo)}, {f4(hi)}] |')
    ft = info['features']
    L.append(f"\nIntervals: game-clustered percentile bootstrap, {N_BOOT:,} draws, seed {SEED}; games resampled with replacement and the means recomputed on the drawn rows.\n")
    L.append('FEN features, computed from the v1 root FEN (the position before the move): material balance from the side to move\'s perspective '
             '(P = 1, N = B = 3, R = 5, Q = 9, kings not counted); number of pieces = all pieces on the board, kings and pawns included; '
             'in check = the side to move is in check. '
             f"On the §2 rows: material mean {ft['material_mean']:.3f} (SD {ft['material_sd']:.3f}); pieces mean {ft['pieces_mean']:.2f} "
             f"(range {ft['pieces_min']}–{ft['pieces_max']}); in-check share {ft['in_check_share']:.4f}.\n")
    L.append('No selector has been fitted.\n')
    open(REPORT, 'w').write('\n'.join(L))
    print('\n'.join(L))


# ================================================================== §3 selectors
FEAT = ['player_elo', 'opponent_elo', 'time_pressure', 'ply', 'material', 'pieces', 'in_check']
FEAT_ASSIST = FEAT + ['wp_level', 'wp_level2', 'gap_12', 'spread_15', 'n_reasonable', 'eval_volatility']
DEPTHS = [2, 4, 8]
QS = [0.05, 0.10, 0.20, 0.30]
N_FOLD = 5
GB = dict(max_depth=4, learning_rate=0.05, max_iter=500, loss='squared_error')
PATIENCE, TOL = 10, 1e-7                     # sklearn HistGradientBoosting early-stopping defaults
VARIANTS = {'primary': ('gb', FEAT, 'all'), 'assisted': ('gb', FEAT_ASSIST, 'all'),
            'ridge': ('ridge', FEAT, 'all'), 'deviation': ('gb', FEAT, 'dev')}


def load_v6():
    r = pd.read_parquet(os.path.join(OUT, 'rows_v6.parquet'))
    r['wp_level2'] = r.wp_level ** 2
    r['dev'] = r.move_played != r.move_engine_best
    for d in DEPTHS:
        r[f'g_{d}'] = r[f'L_{d}'] - r.L_h                 # human target: loss saved by h instead of best_d
        r[f'gref_{d}'] = r[f'L_{d}'] - r.L_15             # reference target: loss saved by best_15
    games = np.array(sorted(r.game_id.unique()))
    perm = np.random.default_rng(SEED).permutation(len(games))
    fold_of = {g: int(i % N_FOLD) for i, g in zip(range(len(games)), games[perm])}
    r['fold'] = r.game_id.map(fold_of).astype(int)
    return r


def fit_gb_early_stop(Xtr, ytr, Xva, yva):
    """HistGradientBoostingRegressor with early stopping on an explicit game-level validation
    set, reproducing sklearn's rule (scoring 'loss', n_iter_no_change 10, tol 1e-7): the
    validation score (negative half squared error, initial score = baseline) is tracked per
    iteration and fitting stops at the first iteration where none of the last 10 scores
    improved on the score 11 positions back by more than tol. sklearn 1.6.1 has no X_val in
    fit(); without subsampling the trees are deterministic, so the model truncated at the
    stopping iteration equals a refit with that many iterations."""
    from sklearn.ensemble import HistGradientBoostingRegressor
    m = HistGradientBoostingRegressor(**GB, early_stopping=False, random_state=SEED).fit(Xtr, ytr)
    base = ytr.mean()
    scores = [-0.5 * np.mean((yva - base) ** 2)]
    n_iter = m.n_iter_
    for i, pv in enumerate(m.staged_predict(Xva), 1):
        scores.append(-0.5 * np.mean((yva - pv) ** 2))
        ref = PATIENCE + 1
        if len(scores) >= ref and not any(sc > scores[-ref] + TOL for sc in scores[-ref + 1:]):
            n_iter = i
            break
    return m, n_iter


def predict_at(m, n_iter, X):
    for i, p in enumerate(m.staged_predict(X), 1):
        if i == n_iter:
            return p
    raise ValueError('n_iter beyond fitted iterations')


def oof_scores(r, feats, kind, target):
    """Out-of-fold predicted gain for every row of r; folds by game (column fold)."""
    from sklearn.linear_model import Ridge
    s = np.full(len(r), np.nan); log = []
    for k in range(N_FOLD):
        te = r.fold.values == k
        tr_games = np.array(sorted(r.loc[~te, 'game_id'].unique()))
        va_games = set(np.random.default_rng(SEED).choice(tr_games, int(round(0.1 * len(tr_games))), replace=False))
        va = (~te) & r.game_id.isin(va_games).values
        tr = (~te) & ~va
        X = r[feats].values.astype(float); y = r[target].values
        if kind == 'gb':
            m, n_iter = fit_gb_early_stop(X[tr], y[tr], X[va], y[va])
            s[te] = predict_at(m, n_iter, X[te])
            log.append({'fold': k, 'n_train': int(tr.sum()), 'n_val': int(va.sum()), 'n_test': int(te.sum()), 'n_iter': n_iter})
        else:                                     # ridge: standardized on the training rows, alpha 1.0
            fit_rows = ~te                        # no early stopping; training fold incl. its validation games
            mu, sd = X[fit_rows].mean(0), X[fit_rows].std(0); sd[sd == 0] = 1
            m = Ridge(alpha=1.0).fit((X[fit_rows] - mu) / sd, y[fit_rows])
            s[te] = m.predict((X[te] - mu) / sd)
            log.append({'fold': k, 'n_train': int(fit_rows.sum()), 'n_test': int(te.sum())})
    return s, log


def stage_fit():
    r = load_v6()
    meta = {}
    for v, (kind, feats, rows) in VARIANTS.items():
        rv = r if rows == 'all' else r[r.dev].reset_index(drop=True)
        out = rv[['row_id', 'game_id', 'fold']].copy()
        for d in DEPTHS:
            for sel, tgt in [('h', f'g_{d}'), ('ref', f'gref_{d}')]:
                out[f's_{sel}_{d}'], meta[f'{v}_{sel}_{d}'] = oof_scores(rv, feats, kind, tgt)
                print(v, sel, d, [x.get('n_iter') for x in meta[f'{v}_{sel}_{d}']], flush=True)
        out.to_parquet(os.path.join(OUT, f'scores_{v}.parquet'), index=False)
    json.dump(meta, open(os.path.join(OUT, 'fit_log.json'), 'w'), indent=2)


# ================================================================== §4 quantities
N_RAND = 200


def select_top(score, fold, q, row_id):
    """Coverage rule: in each test fold the top round(q × fold size) rows by score (ties by row_id)."""
    sel = np.zeros(len(score), bool)
    for k in np.unique(fold):
        idx = np.nonzero(fold == k)[0]
        n = int(round(q * len(idx)))
        order = idx[np.lexsort((row_id[idx], -score[idx]))]
        sel[order[:n]] = True
    return sel


class Boot:
    """Game-clustered bootstrap of means over rows, 2,000 draws, seed 20261001; row values fixed."""
    def __init__(self, r):
        games = np.array(sorted(r.game_id.unique()))
        self.gi = np.searchsorted(games, r.game_id.values)
        self.G = len(games)
        rng = np.random.default_rng(SEED)
        self.cnt = np.stack([np.bincount(rng.integers(0, self.G, self.G), minlength=self.G)
                             for _ in range(N_BOOT)]).astype(float)
        self.n = self.gsum(np.ones(len(r)))

    def gsum(self, x):
        return np.bincount(self.gi, weights=np.asarray(x, float), minlength=self.G)

    def mean(self, x):
        with np.errstate(all='ignore'):
            return (self.cnt @ self.gsum(x)) / (self.cnt @ self.n)

    def ratio(self, num, den):
        with np.errstate(all='ignore'):
            return (self.cnt @ self.gsum(num)) / (self.cnt @ self.gsum(den))


def pct(v):
    v = np.asarray(v, float); v = v[np.isfinite(v)]
    return float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))


def evaluate(r, sc, spearman_boot):
    """All §4 quantities for one variant. r and sc aligned on row order."""
    from scipy.stats import spearmanr
    B = Boot(r)
    fold, rid = sc.fold.values, r.row_id.values
    rng = np.random.default_rng(SEED)
    rand_sel = {}                                 # 200 random selections of q share per test fold
    for q in QS:
        m = np.zeros((N_RAND, len(r)), bool)
        for j in range(N_RAND):
            for k in np.unique(fold):
                idx = np.nonzero(fold == k)[0]
                m[j, rng.choice(idx, int(round(q * len(idx))), replace=False)] = True
        rand_sel[q] = m
    res = {}
    for d in DEPTHS:
        g, gref = r[f'g_{d}'].values, r[f'gref_{d}'].values
        Ld, Lh = r[f'L_{d}'].values, r.L_h.values
        sh, sr = sc[f's_h_{d}'].values, sc[f's_ref_{d}'].values
        sp = spearmanr(sh, g).correlation; spr = spearmanr(sr, gref).correlation
        sp_b = sp_rb = None
        if spearman_boot:
            sp_b, sp_rb = [], []
            for b in range(N_BOOT):
                idx = np.repeat(np.arange(len(r)), B.cnt[b][B.gi].astype(int))
                sp_b.append(spearmanr(sh[idx], g[idx]).correlation)
                sp_rb.append(spearmanr(sr[idx], gref[idx]).correlation)
        res[d] = {'spearman_h': (sp, *(pct(sp_b) if sp_b else (np.nan, np.nan))),
                  'spearman_ref': (spr, *(pct(sp_rb) if sp_rb else (np.nan, np.nan)))}
        for q in QS:
            selh = select_top(sh, fold, q, rid); selr = select_top(sr, fold, q, rid)
            n_or = int(round(q * len(r)))
            selo = np.zeros(len(r), bool); selo[np.lexsort((rid, -g))[:n_or]] = True     # oracle: top q of all rows by true g_d
            pbar = rand_sel[q].mean(0)
            rand_full = (rand_sel[q] * g).mean(1)                                   # G^rand of each of the 200 selections
            x = {'base': Ld, 'combo': np.where(selh, Lh, Ld), 'Gh': selh * g, 'Gref': selr * gref,
                 'D': selh * g - selr * gref, 'Grand': pbar * g, 'Gh_minus_rand': selh * g - pbar * g,
                 'Goracle': selo * g}
            o = {}
            for k, v in x.items():
                o[k] = (float(v.mean()), *pct(B.mean(v)))
            o['Grand_sel_pct'] = (float(np.percentile(rand_full, 2.5)), float(np.percentile(rand_full, 97.5)))
            o['prec_h'] = (float((g[selh] > 0).mean()), *pct(B.ratio(selh * (g > 0), selh)))
            o['prec_ref'] = (float((gref[selr] > 0).mean()), *pct(B.ratio(selr * (gref > 0), selr)))
            o['coinc_h'] = float((r.h.values[selh] == r[f'best_{d}'].values[selh]).mean())
            o['n_sel'] = int(selh.sum())
            res[d][q] = o
    return res


def s_lines(res):
    """S1–S5 at q = 0.10: whether each hypothesis' condition holds, and whether that matches the recorded prediction."""
    q = 0.10
    gh = {d: res[d][q]['Gh'] for d in DEPTHS}
    ghr = {d: res[d][q]['Gh_minus_rand'] for d in DEPTHS}
    dd = {d: res[d][q]['D'] for d in DEPTHS}
    pos = lambda t: t[0] > 0 and t[1] > 0
    neg = lambda t: t[0] < 0 and t[2] < 0
    out = []
    c1 = pos(gh[2]); out.append(('S1', 'G^h_2(0.10) > 0, interval excluding zero', c1, 'holds', c1))
    c2 = pos(gh[4]); out.append(('S2', 'G^h_4(0.10) > 0, interval excluding zero', c2, 'does not hold', not c2))
    c3 = not pos(gh[8]); out.append(('S3', 'G^h_8(0.10) ≤ 0 or interval including zero', c3, 'holds', c3))
    c4 = {d: pos(ghr[d]) for d in DEPTHS}
    out.append(('S4', 'G^h_d(0.10) − G^rand_d(0.10) > 0, interval excluding zero, at every depth', all(c4.values()), 'holds at all depths', all(c4.values()), c4))
    c5 = {d: neg(dd[d]) for d in DEPTHS}
    out.append(('S5', 'D_d(0.10) < 0, interval excluding zero, at every depth', all(c5.values()), 'holds at all depths', all(c5.values()), c5))
    return out


def perm_importance(r):
    """Primary human selector: permutation importance of the seven features on each test fold
    (increase in MSE, 10 repeats, seed 20261001), averaged over folds. Fold models are refit at
    their early-stopping iteration and must reproduce the stored out-of-fold scores."""
    from sklearn.ensemble import HistGradientBoostingRegressor
    from sklearn.inspection import permutation_importance
    log = json.load(open(os.path.join(OUT, 'fit_log.json')))
    sc = pd.read_parquet(os.path.join(OUT, 'scores_primary.parquet'))
    out = {}; maxdiff = 0.0
    for d in DEPTHS:
        imp = []
        for k in range(N_FOLD):
            te = r.fold.values == k
            tr_games = np.array(sorted(r.loc[~te, 'game_id'].unique()))
            va_games = set(np.random.default_rng(SEED).choice(tr_games, int(round(0.1 * len(tr_games))), replace=False))
            tr = (~te) & ~r.game_id.isin(va_games).values
            n_iter = log[f'primary_h_{d}'][k]['n_iter']
            m = HistGradientBoostingRegressor(**{**GB, 'max_iter': n_iter}, early_stopping=False,
                                              random_state=SEED).fit(r.loc[tr, FEAT].values.astype(float), r.loc[tr, f'g_{d}'].values)
            Xte = r.loc[te, FEAT].values.astype(float)
            maxdiff = max(maxdiff, float(np.abs(m.predict(Xte) - sc.loc[te, f's_h_{d}'].values).max()))
            pi = permutation_importance(m, Xte, r.loc[te, f'g_{d}'].values, scoring='neg_mean_squared_error',
                                        n_repeats=10, random_state=SEED)
            imp.append(pi.importances_mean)
        out[d] = np.mean(imp, axis=0)
    return out, maxdiff


def stage_report():
    r = load_v6()
    f4 = lambda x: 'NA' if x is None or not np.isfinite(x) else f'{x:.4f}'
    ci = lambda t: f'{f4(t[0])} [{f4(t[1])}, {f4(t[2])}]'
    results = {}
    for v, (kind, feats, rows) in VARIANTS.items():
        rv = r if rows == 'all' else r[r.dev].reset_index(drop=True)
        sc = pd.read_parquet(os.path.join(OUT, f'scores_{v}.parquet'))
        assert (sc.row_id.values == rv.row_id.values).all()
        results[v] = evaluate(rv, sc, spearman_boot=(v == 'primary'))
        print('evaluated', v, flush=True)
    pickle_path = os.path.join(OUT, 'results.json')
    json.dump({v: {str(d): {str(k): x for k, x in dv.items()} for d, dv in rv_.items()} for v, rv_ in results.items()},
              open(pickle_path, 'w'), indent=1, default=float)
    imp, maxdiff = perm_importance(r)
    log = json.load(open(os.path.join(OUT, 'fit_log.json')))
    P = results['primary']

    txt = open(REPORT).read().split('\n## Analysis note')[0].replace('No selector has been fitted.\n', '').rstrip('\n') + '\n'   # keep §0, rebuild the rest
    L = []; A = L.append
    A('\n## Analysis note\n')
    A('- Rows: the §2 set, 49,907 rows, 1,970 games. Losses on the V20 ruler: L_h, L_d = e_d, L_15 with best_15 = best_15_singlepv. Targets g_d = L_d − L_h (human) and g^ref_d = L_d − L_15 (reference); rows with h = best_d keep g_d = 0.')
    A('- Folds: 5, by game; the 1,970 games are permuted with seed 20261001 and assigned to folds in rotation (fold sizes 9,865–10,064 rows). Every score is out-of-fold.')
    A('- Model: HistGradientBoostingRegressor (scikit-learn 1.6.1), max_depth 4, learning_rate 0.05, max_iter 500, squared error, random_state 20261001, one model per depth and selector. '
      'Early stopping on an explicit game-level validation set: 10% of the training fold\'s games (seed 20261001), excluded from fitting. scikit-learn 1.6.1 has no X_val argument, so the rule is reproduced: '
      'the model is fitted to 500 iterations without internal early stopping, the validation loss (half squared error; initial score at the training mean) is tracked per iteration with staged_predict, '
      'and the model stops at the first iteration where none of the last 10 scores improved on the score 11 positions back by more than 1e-7 (scikit-learn\'s n_iter_no_change and tol defaults). '
      'Scores come from the model truncated there; a refit with max_iter at that value reproduces the stored scores exactly (max abs difference '
      f'{maxdiff:.1e} over the permutation-importance refits). Stopping iterations per fold are in the table below.')
    A('- Coverage: in each test fold the top round(q × fold size) rows by predicted gain (ties by row_id). Random control: 200 selections of the same size per test fold (seed 20261001); '
      'G^rand is their mean, reported with the 2.5/97.5 percentiles across the 200 selections and with a bootstrap interval of the mean. Oracle: the top round(q × N) rows of all N rows by the true gain g_d.')
    A('- Intervals: game-clustered percentile bootstrap, 2,000 draws, seed 20261001, resampling games and recomputing every mean on the drawn rows with the out-of-fold scores and selections fixed; '
      'D and G^h − G^rand are computed within each draw. Spearman (primary only) is recomputed on the drawn rows (games repeated by their draw count). Precision is the share of selected rows with positive gain.')
    A('- Robustness 2 (ridge): scikit-learn Ridge, alpha 1.0 (default, no tuning), features standardized on the training fold, fitted on the whole training fold (no early stopping, so the validation games are not held out). '
      'Robustness 3: the v3 deviation rows within the §2 set, 28,645 rows (2 of the 28,647 v3 rows are among the 14 terminal rows); selectors refit on these rows with the same fold assignment by game.')
    A('')
    A('Early-stopping iteration per fold (folds 1–5):\n')
    A('| Variant | Selector | d = 2 | d = 4 | d = 8 |\n|---|---|---|---|---|')
    for v in ('primary', 'assisted', 'deviation'):
        for sel in ('h', 'ref'):
            A(f"| {v} | {'human' if sel == 'h' else 'reference'} | " + ' | '.join(
                ', '.join(str(x['n_iter']) for x in log[f'{v}_{sel}_{d}']) for d in DEPTHS) + ' |')
    A('')

    A('## 1. Main table (primary selectors, assistant-free features)\n')
    A('WP points on the V20 ruler; each cell is estimate [95% interval]. G = mean over all N rows of the loss saved by the substitution on the selected rows.\n')
    for d in DEPTHS:
        A(f'### d = {d}\n')
        A('| q | Baseline loss (mean L_d) | Human combination loss | G^h | G^ref | D = G^h − G^ref | G^rand (bootstrap) | G^rand 2.5/97.5% of 200 selections | G^h − G^rand | G^oracle | Precision (human) | Precision (reference) |')
        A('|---|---|---|---|---|---|---|---|---|---|---|---|')
        for q in QS:
            o = P[d][q]
            A(f"| {q:.2f} | {ci(o['base'])} | {ci(o['combo'])} | {ci(o['Gh'])} | {ci(o['Gref'])} | {ci(o['D'])} | {ci(o['Grand'])} | "
              f"[{f4(o['Grand_sel_pct'][0])}, {f4(o['Grand_sel_pct'][1])}] | {ci(o['Gh_minus_rand'])} | {ci(o['Goracle'])} | {ci(o['prec_h'])} | {ci(o['prec_ref'])} |")
        A(f"\nSpearman correlation of out-of-fold score with true gain, pooled over all N rows: human selector {ci(P[d]['spearman_h'])}; reference selector {ci(P[d]['spearman_ref'])}.\n")

    A('## 2. Recorded predictions (q = 0.10, primary)\n')
    A('| Hypothesis | Condition | Condition holds | Recorded prediction | Prediction correct |\n|---|---|---|---|---|')
    for x in s_lines(P):
        extra = ''
        if len(x) > 5:
            extra = ' (' + ', '.join(f"d = {d}: {'yes' if v else 'no'}" for d, v in x[5].items()) + ')'
        A(f"| {x[0]} | {x[1]} | {'yes' if x[2] else 'no'}{extra} | {x[3]} | **{'yes' if x[4] else 'no'}** |")
    A('\nS1 and S5 are the pre-registered results (§5); S2–S4 are the recorded shape of the curve.\n')

    A('## 3. Descriptives (§6)\n')
    A('Figure: `figures/spec_v6/fig_selector_curves.png` — G^h, G^ref, G^rand and G^oracle against q at each depth, primary selectors, 95% intervals.\n')
    A('### 3a. Permutation importance, primary human selector (increase in test-fold MSE of g_d when the feature is permuted; mean over 5 folds, 10 repeats each)\n')
    A('| Feature | d = 2 | d = 4 | d = 8 |\n|---|---|---|---|')
    for i, fname in enumerate(FEAT):
        A(f"| {fname} | " + ' | '.join(f'{imp[d][i]:.4f}' for d in DEPTHS) + ' |')
    A('\n### 3b. Coincidence: share of human-selected rows with h = best_d\n')
    A('| q | d = 2 | d = 4 | d = 8 |\n|---|---|---|---|')
    for q in QS:
        A(f'| {q:.2f} | ' + ' | '.join(f"{P[d][q]['coinc_h']:.4f}" for d in DEPTHS) + ' |')
    A(f"\nFor reference, share of all §2 rows with h = best_d: " + ', '.join(f"d = {d}: {(r.h == r[f'best_{d}']).mean():.4f}" for d in DEPTHS) + '.\n')

    A('## 4. Robustness (§7), q = 0.10\n')
    labels = {'primary': 'Primary (for comparison)', 'assisted': '1. Assisted: depth-15 root MultiPV features added (uses depth-15 information)',
              'ridge': '2. Ridge regression in place of gradient boosting', 'deviation': '3. Deviation rows only (28,645 rows)'}
    for v in ('primary', 'assisted', 'ridge', 'deviation'):
        R_ = results[v]
        A(f'### {labels[v]}\n')
        A('| d | Baseline loss | G^h | G^ref | D | G^h − G^rand | G^oracle | Spearman (human) |\n|---|---|---|---|---|---|---|---|')
        for d in DEPTHS:
            o = R_[d][0.10]
            A(f"| {d} | {ci(o['base'])} | {ci(o['Gh'])} | {ci(o['Gref'])} | {ci(o['D'])} | {ci(o['Gh_minus_rand'])} | {ci(o['Goracle'])} | {f4(R_[d]['spearman_h'][0])} |")
        A('\n| Hypothesis | Condition holds | Recorded prediction correct |\n|---|---|---|')
        for x in s_lines(R_):
            extra = (' (' + ', '.join(f"d = {d}: {'yes' if vv else 'no'}" for d, vv in x[5].items()) + ')') if len(x) > 5 else ''
            A(f"| {x[0]} | {'yes' if x[2] else 'no'}{extra} | {'yes' if x[4] else 'no'} |")
        A('')

    A('## 5. Limits (§8)\n')
    for s_ in ['One platform, fast time controls, titled players.',
               'Selectors are trained and tested on the same population (cross-fitted by game, not validated on new players or events).',
               'Scores and selections are fixed inside bootstrap draws; the intervals do not include selector refitting variance.',
               'The increment is on the V20 ruler, which has about 1 WP point of resolution per row and is reliable in means.',
               'The reference source is one engine (best_15_singlepv) at one depth.',
               'The oracle selects rows by the true gain, which contains the ruler\'s roughly 1 WP point of noise per row, so it is inflated by noise and is a loose upper bound.']:
        A(f'- {s_}')
    open(REPORT, 'w').write(txt + '\n'.join(L) + '\n')
    json.dump({'perm_importance': {str(d): dict(zip(FEAT, map(float, imp[d]))) for d in DEPTHS}, 'refit_maxdiff': maxdiff},
              open(os.path.join(OUT, 'descriptives.json'), 'w'), indent=2)
    print('wrote', REPORT)


def stage_figure():
    """§6 figure: G^h, G^ref, G^rand, G^oracle against q, one panel per depth, primary selectors.
    Categorical slots 1–4 of the reference palette (validated: all checks pass; contrast WARN for
    slots 3–4, so identity also carries marker shape and a legend, and §1 of the report is the table view)."""
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    res = json.load(open(os.path.join(OUT, 'results.json')))['primary']
    SURF, INK, INK2, GRID, REF = '#fcfcfb', '#0b0b0b', '#52514e', '#e7e6e2', '#8f8e89'
    series = [('Goracle', 'Oracle (true gain; loose upper bound)', '#2a78d6', 's'),
              ('Gref', 'Reference: depth-15 engine, same selector', '#eb6834', 'D'),
              ('Gh', 'Human, pre-move selector', '#1baf7a', 'o'),
              ('Grand', 'Human, random rows (mean of 200)', '#eda100', '^')]
    plt.rcParams.update({'font.size': 9, 'axes.edgecolor': INK2, 'axes.labelcolor': INK, 'xtick.color': INK2,
                         'ytick.color': INK2, 'axes.spines.top': False, 'axes.spines.right': False})
    fig, axes = plt.subplots(1, 3, figsize=(10, 4.2), sharey=True, facecolor=SURF)
    for ax, d in zip(axes, DEPTHS):
        ax.set_facecolor(SURF)
        ax.axhline(0, color=REF, lw=1)
        for key, lab, col, mk in series:
            y = np.array([res[str(d)][str(q)][key][0] for q in QS])
            lo = np.array([res[str(d)][str(q)][key][1] for q in QS]); hi = np.array([res[str(d)][str(q)][key][2] for q in QS])
            ax.fill_between(QS, lo, hi, color=col, alpha=0.18, lw=0)
            ax.plot(QS, y, color=col, lw=2, marker=mk, ms=6, mec=SURF, mew=1.5, label=lab)
        ax.set_title(f'd = {d}', color=INK, loc='left')
        ax.set_xticks(QS); ax.set_xlabel('Coverage q (share of rows switched)')
        ax.grid(axis='y', color=GRID, lw=0.8); ax.set_axisbelow(True)
    axes[0].set_ylabel('Increment over the depth-d engine (WP points)')
    h, l = axes[0].get_legend_handles_labels()
    fig.legend(h, l, loc='lower center', ncol=2, frameon=False, fontsize=8, labelcolor=INK2)
    fig.suptitle('Selector increments by coverage, primary (assistant-free) selectors, 95% intervals', color=INK, x=0.01, ha='left')
    fig.tight_layout(rect=(0, 0.13, 1, 0.97))
    fd = os.path.join(C.REPO, 'figures', 'spec_v6'); os.makedirs(fd, exist_ok=True)
    fig.savefig(os.path.join(fd, 'fig_selector_curves.png'), dpi=200, facecolor=SURF); plt.close(fig)
    print('wrote figures/spec_v6/fig_selector_curves.png')


if __name__ == '__main__':
    {'rows': stage_rows, 'fit': stage_fit, 'report': stage_report, 'figure': stage_figure}[sys.argv[1]]()
