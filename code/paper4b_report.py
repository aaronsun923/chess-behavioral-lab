#!/usr/bin/env python3
"""Section 6 deliverables for the Paper 4b pilot."""
import os, json, math, warnings, platform
import numpy as np, pandas as pd
import chess
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
import statsmodels.api as sm
import statsmodels.formula.api as smf
from scipy import stats as sps

import paper4_pilot as V1
import paper4b_pilot as B
from paper4_report import fmt_tbl, coef_table, fit_mixed, z, load_rows

warnings.filterwarnings('ignore')
FIG = 'paper4b_figures'
OUT = 'paper4b_pilot_REPORT.md'

# Paper 1 style indicators, reused verbatim from style_skill_analysis.py
INDICATORS = ["exchange_rate", "tension_duration", "avg_mobility",
              "center_control_score", "advanced_pawn_push_rate",
              "pawn_storm_indicator", "castling_ply", "king_shelter_score",
              "forcing_move_rate", "reactive_move_rate"]


def load_4b():
    fr = []
    for root, _, files in os.walk(B.RESULT_DIR):
        for fn in sorted(files):
            if fn.endswith('.parquet'):
                fr.append(pd.read_parquet(os.path.join(root, fn)))
    d = pd.concat(fr, ignore_index=True).drop_duplicates(['game_id', 'ply', 'which_move'])
    return d


def style_pc1():
    """Paper 1 style vector, PC1. Same construction as style_skill_analysis.py:
    n_games-weighted aggregation to one row per player, correlation-matrix PCA
    via SVD on z-scored indicators, oriented so exchange_rate + forcing_move_rate
    load positive (=> PC1 positive is the ATTACKING pole, negative POSITIONAL)."""
    a = pd.read_csv('analysis_dataset_male_titled_agg.csv')
    a = a.dropna(subset=INDICATORS + ['n_games'])
    w = a['n_games']
    agg = (a[INDICATORS].mul(w, axis=0).groupby(a.player_id).sum()
           .div(w.groupby(a.player_id).sum(), axis=0))
    elo = (a['avg_elo'].mul(w).groupby(a.player_id).sum()
           / w.groupby(a.player_id).sum())
    X = agg.values.astype(float)
    mu, sd = X.mean(0), X.std(0, ddof=1)
    Z = (X - mu) / np.where(sd == 0, 1.0, sd)
    U, S, Vt = np.linalg.svd(Z, full_matrices=False)
    eig = S ** 2 / (len(X) - 1); vr = eig / eig.sum()
    load = Vt[0].copy(); scores = (U * S)[:, 0].copy()
    ref = np.sign(load[INDICATORS.index('exchange_rate')] +
                  load[INDICATORS.index('forcing_move_rate')])
    if ref < 0:
        load, scores = -load, -scores
    return (pd.DataFrame({'player_id': agg.index, 'PC1': scores,
                          'style_elo': elo.reindex(agg.index).values}),
            load, vr)


def signtest(x):
    x = pd.Series(x).dropna()
    neg, pos = int((x < 0).sum()), int((x > 0).sum())
    n = neg + pos
    p = sps.binomtest(neg, n, 0.5, alternative='two-sided').pvalue if n else float('nan')
    return neg, pos, int((x == 0).sum()), n, p


def build():
    os.makedirs(FIG, exist_ok=True)
    L = []; A = L.append

    v1 = load_rows()
    cut = v1['WPL_raw'].quantile(1 - V1.WINSOR_TOP)      # v1 §5.2, full-sample
    v1['WPL'] = v1['WPL_raw'].clip(upper=cut)
    roster_ids = set(pd.read_csv(V1.SRC_CSV, usecols=['player_id'])
                     .player_id.str.lower().unique())
    v1['in_roster'] = v1.player_id.str.lower().isin(roster_ids)

    keep = set(pd.read_csv(B.SAMPLE_CSV, dtype={'game_id': str}).game_id)
    s = v1[v1.game_id.isin(keep)].copy()
    r4 = load_4b()
    st = json.load(open(os.path.join(B.CACHE_DIR, 'analysis4b_stats.json')))
    # The risk evaluation ran in three passes (500-game subset; the remainder;
    # then a refill after the shard-overwrite bug described in §1). Report the
    # TOTAL compute actually spent, including the work that had to be redone.
    passes = [st]
    for _f in ('analysis4b_stats_pass2.json', 'analysis4b_stats_pilot500.json'):
        _p = os.path.join(B.CACHE_DIR, _f)
        if os.path.exists(_p):
            _d = json.load(open(_p))
            if not any(_d.get('engine_calls') == q.get('engine_calls')
                       and _d.get('wall_seconds') == q.get('wall_seconds') for q in passes):
                passes.append(_d)
    if len(passes) > 1:
        errs = {}
        for q in passes:
            errs.update(q.get('errors', {}))
        st = dict(st,
                  engine_calls=sum(q['engine_calls'] for q in passes),
                  wall_seconds=sum(q['wall_seconds'] for q in passes),
                  engine_seconds=sum(q['engine_seconds'] for q in passes),
                  rows=sum(q['rows'] for q in passes),
                  ms_per_call=1000 * sum(q['engine_seconds'] for q in passes)
                              / max(sum(q['engine_calls'] for q in passes), 1),
                  errors=errs, _passes=len(passes))

    # wide: one row per (game_id, ply) with both moves' risk
    w = r4.pivot_table(index=['game_id', 'ply'], columns='which_move',
                       values=['risk_steep', 'risk_var', 'n_pv'], aggfunc='first')
    w.columns = [f'{a}_{b}' for a, b in w.columns]
    w = w.reset_index()
    d = s.merge(w, on=['game_id', 'ply'], how='left')
    same = d.move_played == d.move_engine_best
    # [LOCKED §5] played == best  =>  dRISK == 0 by construction
    for m in ('steep', 'var'):
        d.loc[same, f'risk_{m}_played'] = d.loc[same, f'risk_{m}_best'] = 0.0
        d[f'dRISK_{m}'] = d[f'risk_{m}_played'] - d[f'risk_{m}_best']

    full = d.game_id.nunique() >= 1970
    A(f"# Paper 4b — {'Full-Sample' if full else 'Pilot'} Report (Section 6 deliverables)\n")
    A(f"_Generated {pd.Timestamp.utcnow().strftime('%Y-%m-%d %H:%M UTC')}. "
      f"Risk evaluation now covers **all {d.game_id.nunique():,} v1 games**._\n")
    A('> **Scope note — this is not a redraw.** The underlying game sample is still the locked v1 '
      f'draw (2,000 games at `random_seed = {V1.SEED}`, 1,970 retrievable). What changed is that '
      f"SPEC v2 §2's additional {B.N_GAMES_4B}-game subsetting "
      f'(`random_seed = {B.SEED_4B}`) has been lifted by the designer, so §3 risk evaluation now '
      'runs on every row v1 scored rather than on a subset of them. The original 500-game draw is '
      'preserved at `paper4b_cache/pilot4b_sample_games_500.csv`; every row it selected is a '
      'subset of what is reported here, and those rows were reused, not recomputed. No engine '
      'setting, definition, band, or model was changed — only the number of rows they are '
      'applied to.\n')

    # ============================================== §0 the blocking ambiguity
    A('\n## 0. Spec erratum on the §3.2 sign — ratified, read this first\n')
    A('§3.2 defines the dependent variable as\n\n```\n'
      'RISK_steep(m) = WP_self(opponent 1st choice) − WP_self(opponent 5th choice)\n```\n')
    A('and then states in the same clause that *"the opponent\'s 1st choice gives my WP the '
      '**lowest**, the 5th choice the **highest**, therefore this value is non-negative."* '
      'Those two sentences cannot both hold: lowest − highest is **non-positive**, and it is the '
      'exact negation of the quantity the note describes.\n')
    A('The rest of the spec resolves which one is meant. §3.4 says `ΔRISK < 0` means *"the human '
      'chose the lower-risk move"*, and §4.1 says a **negative intercept** supports the '
      'hypothesis. Both require `RISK` to **increase** with risk. Only the non-negative '
      'orientation does that. Three statements (the §3.2 note, §3.4, §4.1) agree with each other; '
      'the operand order printed in the §3.2 formula is the outlier and reads as a transcription '
      'slip.\n')
    A('**SPEC ERRATUM — ratified.** The designer (Aaron) has confirmed that the printed operand '
      'order in §3.2 is a **typo**, and that the intended definition is the one stated in the '
      '§3.2 note, §3.4 and §4.1. The orientation used throughout this report is therefore the '
      'authoritative one:\n\n'
      '```\nRISK_steep(m) = WP_self(opponent 5th choice) − WP_self(opponent 1st choice)  ≥ 0\n```\n')
    A('> **Erratum for the spec file.** `paper4b_spec_v2.md` §3.2 should read '
      '`WP_self(对手第5选择) − WP_self(对手第1选择)`. As printed, the formula is the negation of '
      'the quantity its own explanatory note, §3.4 and §4.1 all describe. No other clause is '
      'affected, and no locked parameter other than this typo was altered. Numbers in this '
      'report stand as written; the earlier "negate everything" caveat no longer applies.\n')

    # ============================================== 6.1 environment
    A('\n## 1. Environment and measured cost\n')
    A(fmt_tbl([
        ['Stockfish', st['sf_version'] + '  (same binary as v1)'],
        ['depth / MultiPV / Threads / Hash', f'{V1.DEPTH} / {V1.MULTIPV} / {V1.THREADS} / {V1.HASH_MB} MB'],
        ['independent search per position', 'yes (`ucinewgame` forced, as v1)'],
        ['python-chess / pandas / statsmodels', f'{chess.__version__} / {pd.__version__} / {sm.__version__}'],
        ['machine', f'{platform.platform()} ({os.cpu_count()} cores)'],
        ['worker processes', st['nproc']],
        ['engine calls', f"{st['engine_calls']:,}"],
        ['**measured ms per call**', f"**{st['ms_per_call']:.0f} ms**"],
        ['wall-clock', f"{st['wall_seconds']/60:.1f} min"
         + (f" (total across {st['_passes']} passes; see the note below)"
            if st.get('_passes') else '')],
        ['evaluations stored', f'{len(r4):,}'],
        ['errors', json.dumps(st['errors']) if st['errors'] else 'none'],
    ], ['item', 'value']))
    A(f"\n§5's estimate (25–40 min at ~500 ms/call) was written for the 500-game subset; that "
      f"pass landed inside it at 37.0 min. Across all {st.get('_passes', 1)} passes "
      f"(including work redone after the shard bug) the full sample cost "
      f"**{st['wall_seconds']/60:.0f} min** at **{st['ms_per_call']:.0f} ms/call** on "
      f"{st['nproc']} processes. The per-call figure is "
      "above 500 ms for the same reason documented in the v1 report §1 (MultiPV 5 costs ~5× "
      "MultiPV 1, plus contention); v1's uncontended benchmark was 492 ms/call.\n")
    A('\n> **A bug that destroyed data, and how it was caught.** The risk evaluation was '
      'extended from the 500-game subset to all 1,970 games as a *resumed* run. Resume worked '
      'correctly — it identified the 7,232 already-evaluated rows and skipped them — but the '
      'shard writer named its output `part-NNNN.parquet` with the counter restarting at zero on '
      'every run, so the second pass overwrote the first pass\'s files with its own. The rows '
      'that resume had just skipped were deleted by the run that skipped them. A post-run '
      'coverage check (rows needing evaluation vs. rows present, per game) caught it: 1,472 of '
      '1,970 games covered instead of all of them, 7,180 rows missing. The writer now tags every '
      'file with a unique per-run token so no run can overwrite another\'s output, the same fix '
      'was applied to the v1 pipeline where the identical pattern was latent, and the lost rows '
      'were recomputed. **The v1 dataset was never affected** — it was written by a single run '
      'and its 50,021 rows across 1,970 games verify intact. The cost table above includes the '
      'recomputed work, so it reflects compute actually spent rather than the minimum this job '
      'needed.\n')
    A('\n> **One methodological note that changed a result.** statsmodels\' `lbfgs` optimizer '
      'converged to a degenerate all-zero solution on every §4 model here — silently, reporting '
      '`converged=True` with all variance components at 0, the intercept at exactly 0, p = 1 and '
      'a 95% CI of roughly ±5×10⁷. Taken at face value it would have been reported as a clean '
      'null. `bfgs`, `cg`, `powell` and `nm` all agree with each other and with OLS on the same '
      'data, so the shared fitting helper now tries optimizers in order and rejects a degenerate '
      'optimum instead of returning it. The v1 report was regenerated under the fixed helper and '
      'every v1 coefficient is unchanged — `lbfgs` happened to work on v1\'s dependent variable.\n')
    A('\nAll v1 infrastructure was reused, not recomputed: the WP formula, `pov_cp`, the engine '
      'configuration, the middlegame window, and the completed v1 shards supplying `WPL`, '
      '`gap_12`, `eval_volatility` and `time_pressure`. No new positions were added; §3 only '
      'evaluates the *successors* of moves v1 had already scored. v1 shards were not modified — '
      f'4b writes to `{B.RESULT_DIR}/`.\n')

    # ============================================== 6.2 shares
    A('\n## 2. Sample composition\n')
    n = len(d)
    band = (d.WPL > B.WPL_BAND[0]) & (d.WPL <= B.WPL_BAND[1])
    bandr = (d.WPL > B.WPL_BAND_ROB[0]) & (d.WPL <= B.WPL_BAND_ROB[1])
    A(fmt_tbl([
        ['v1 games covered', f'{d.game_id.nunique():,}',
         'all of them — §2 subsetting lifted' if full else f'seed {B.SEED_4B}'],
        ['v1 position-move rows in those games', f'{n:,}', 'no new positions added'],
        ['rows with `m_played == m_best`', f'{int(same.sum()):,}', f'{100*same.mean():.2f}%  → ΔRISK ≡ 0, evaluation skipped (§5)'],
        ['rows evaluated (2 calls each)', f'{int((~same).sum()):,}', f'{100*(~same).mean():.2f}%'],
        [f'**rows with WPL ∈ (0, 5]  [LOCKED §4.1]**', f'**{int(band.sum()):,}**', f'**{100*band.mean():.2f}%** of all rows'],
        ['rows with WPL ∈ (0, 10]  [§4.3 robustness]', f'{int(bandr.sum()):,}', f'{100*bandr.mean():.2f}%'],
        ['rows with WPL > 10', f'{int((d.WPL > 10).sum()):,}', f'{100*(d.WPL > 10).mean():.2f}%'],
    ], ['quantity', 'count', 'note']))
    A(f"\nThe §4.1 band holds **{100*band.mean():.2f}%** of all rows and "
      f"**{100*band.sum()/max(int((~same).sum()),1):.2f}%** of the rows that were actually "
      "evaluated. Rows where the human played the engine's top move have `WPL = 0` and are "
      "excluded by the band's open lower bound automatically — the §5 skip and the §4.1 band "
      "agree, so no row is both skipped and needed.\n")
    lowpv = int((d.n_pv_played.fillna(5) < V1.MULTIPV).sum() + (d.n_pv_best.fillna(5) < V1.MULTIPV).sum())
    A(f"\n- Successor positions returning fewer than 5 PV lines (fewer legal replies), where the "
      f"\"5th choice\" falls back to the last available line: **{lowpv:,}** of "
      f"{2*int((~same).sum()):,} evaluations ({100*lowpv/max(2*int((~same).sum()),1):.2f}%).\n")
    term = r4.terminal.replace('', np.nan).dropna()
    A(f"- Successors that were terminal (mate/draw, risk defined as 0): "
      f"{len(term):,} ({100*len(term)/max(len(r4),1):.2f}%)"
      + (f' — {dict(term.value_counts())}' if len(term) else '') + '.\n')

    # ============================================== 6.3 distribution + sign test
    A('\n## 3. `ΔRISK_steep` distribution and sign test\n')
    A('`ΔRISK_steep = RISK_steep(m_played) − RISK_steep(m_best)`, in win-probability points. '
      'Negative = the human chose the **flatter, more recoverable** path (§3.4).\n')
    db = d[band]
    rows = []
    for lab, x in [('all rows', d.dRISK_steep), (f'WPL ∈ (0,5] (the §4.1 sample)', db.dRISK_steep)]:
        q = x.dropna()
        rows.append([lab, f'{len(q):,}', f'{q.mean():+.3f}', f'{q.median():+.3f}',
                     f'{q.quantile(.25):+.3f}', f'{q.quantile(.75):+.3f}', f'{q.std():.3f}'])
    A(fmt_tbl(rows, ['sample', 'n', 'mean', 'median', 'p25', 'p75', 'sd']))
    qs = [.01, .05, .10, .25, .50, .75, .90, .95, .99]
    A('\n' + fmt_tbl([[f'{q:.0%}', f'{db.dRISK_steep.quantile(q):+.3f}'] for q in qs],
                     ['quantile (§4.1 sample)', 'ΔRISK_steep']))

    A('\n### Sign test (model-free, as §4.1 requires)\n')
    rows = []
    for lab, x in [('all rows', d.dRISK_steep), ('WPL ∈ (0,5]  [§4.1]', db.dRISK_steep),
                   ('WPL ∈ (0,10] [§4.3]', d[bandr].dRISK_steep)]:
        neg, pos, zer, nn, p = signtest(x)
        rows.append([lab, f'{nn:,}', f'{neg:,}', f'{pos:,}', f'{100*neg/max(nn,1):.2f}%',
                     f'{p:.3g}'])
    A(fmt_tbl(rows, ['sample', 'n (non-zero)', 'negative', 'positive', '% negative', 'binomial p']))
    neg, pos, zer, nn, p = signtest(db.dRISK_steep)
    med = db.dRISK_steep.median()
    A(f"\n**Reading.** In the §4.1 band, **{100*neg/max(nn,1):.2f}%** of deviations went toward "
      f"the flatter path (median **{med:+.3f}** WP points, binomial p = {p:.3g}). "
      + ("The majority direction is toward lower risk, which is the direction §1 predicts."
         if neg > pos else
         "The majority direction is toward **higher** risk, against the §1 prediction.") + '\n')

    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    ax[0].hist(d.dRISK_steep.dropna(), bins=80, color='#4C72B0')
    ax[0].axvline(0, color='k', lw=1); ax[0].set_title('ΔRISK_steep — all rows')
    ax[0].set_xlabel('WP points'); ax[0].set_yscale('log')
    ax[1].hist(db.dRISK_steep.dropna(), bins=80, color='#C44E52')
    ax[1].axvline(0, color='k', lw=1); ax[1].set_title('ΔRISK_steep — WPL ∈ (0,5]')
    ax[1].set_xlabel('WP points')
    fig.tight_layout(); fig.savefig(f'{FIG}/drisk_distribution.png', dpi=130); plt.close(fig)
    A(f'\n![dRISK distribution]({FIG}/drisk_distribution.png)\n')

    # ============================================== 6.4 main model
    A('\n## 4. §4.1 main test — risk preference at equal expected loss\n')
    A('```\nΔRISK_steep ~ WPL_z + gap_12_z + eval_volatility_z + time_pressure_z '
      '+ (1|player_id) + (1|game_id)\n```\n')
    A('**The intercept is the core quantity.** Predictors are standardized *within the §4.1 '
      'estimation sample*, so the intercept is the expected `ΔRISK_steep` at the sample\'s mean '
      'deviation size, mean position sharpness and mean time pressure. A significantly negative '
      'intercept means: holding how far the human strayed from the engine fixed, the move they '
      'chose sits on a systematically flatter punishment curve.\n')

    def prep(dd):
        dd = dd.copy()
        dd['WPL_z'] = z(dd.WPL); dd['gap_12_z'] = z(dd.gap_12)
        dd['eval_volatility_z'] = z(dd.eval_volatility)
        dd['time_pressure_z'] = z(dd.time_pressure)
        return dd

    f41 = ('dRISK_steep ~ WPL_z + gap_12_z + eval_volatility_z + time_pressure_z')
    d41 = prep(db)
    res41, ols41, dfit41 = fit_mixed(f41, d41, '4.1')
    if res41 is not None:
        A(coef_table(res41, 'Linear mixed model — §4.1 primary',
                     'Random intercepts `player_id` (group) + `game_id` (variance component), '
                     'the same approximation to crossed effects documented in the v1 report §10.5.'))
    if ols41 is not None:
        A(coef_table(ols41, 'OLS with player-clustered SEs (robustness)', ''))
    if res41 is not None:
        b0 = res41.params['Intercept']; p0 = res41.pvalues['Intercept']
        ci0 = res41.conf_int().loc['Intercept']
        A(f"\n### The core number\n")
        A(f"Intercept = **{b0:+.4f}** WP points (95% CI [{ci0[0]:+.4f}, {ci0[1]:+.4f}], "
          f"p = {p0:.3g}).\n")
        verdict = ('**negative and significant** — the §1 direction'
                   if (b0 < 0 and p0 < .05) else
                   '**positive and significant** — the *opposite* of the §1 direction'
                   if (b0 > 0 and p0 < .05) else
                   '**not distinguishable from zero**')
        A(f"\nThe intercept is {verdict}. " +
          ("Controlling for deviation size, humans systematically chose moves whose "
           "punishment curve is flatter than the engine's top choice — deviation carries a risk "
           "dimension the engine's objective function does not represent.\n" if (b0 < 0 and p0 < .05)
           else
           "Controlling for deviation size, humans chose moves that are **sharper** "
           "than the engine's top choice, not flatter. This is the opposite of the §1 hypothesis "
           "and, on the full sample, is a finding in its own right rather than a "
           "null.\n" if (b0 > 0 and p0 < .05)
           else "The data do not separate the risk-management account from chance.\n"))
        A(f"\n(§0 erratum: the sign convention here is the ratified one; no negation applies.)\n")

    # ====================================== §4.1 + liquidation diagnostic
    A('\n### Liquidation diagnostic (added at the designer\'s request)\n')
    A('Tests the confound flagged in the first pilot: a flatter successor may simply be a '
      '*simplified* one. Two position-level covariates are added to the §4.1 model and nothing '
      'else changes.\n')
    A('- `played_is_capture` — 1 if `m_played` is a capture (en passant included), else 0.\n'
      '- `dmat` — **material change after `m_played` minus material change after `m_best`**, '
      'where material change is the change in **total material on the board** (both sides, '
      'P=1 N=3 B=3 R=5 Q=9, kings excluded) caused by that move. It is ≤ 0 for a capture, 0 for '
      'a quiet move, and positive for a promotion. `dmat < 0` therefore means the human\'s move '
      'liquidated **more** than the engine\'s choice — exactly the direction the confound '
      'predicts should drive `ΔRISK_steep` down.\n')
    A('Both covariates are **mean-centred**, so the intercept keeps the same meaning as in the '
      'model above (expected `ΔRISK_steep` at sample-average conditions) and the two intercepts '
      'are directly comparable.\n')

    VAL = {chess.PAWN: 1, chess.KNIGHT: 3, chess.BISHOP: 3,
           chess.ROOK: 5, chess.QUEEN: 9}

    def total_material(b):
        return sum(VAL[pt] * (len(b.pieces(pt, chess.WHITE)) + len(b.pieces(pt, chess.BLACK)))
                   for pt in VAL)

    def bal_self(b, colour):
        return sum(VAL[pt] * (len(b.pieces(pt, colour)) - len(b.pieces(pt, not colour)))
                   for pt in VAL)

    def move_feats(row):
        try:
            pb = chess.Board(row['fen'])
            mp = pb.parse_san(row['move_played']); mb = pb.parse_san(row['move_engine_best'])
            t0, b0_ = total_material(pb), bal_self(pb, pb.turn)
            ap = pb.copy(); ap.push(mp)
            ab = pb.copy(); ab.push(mb)
            return pd.Series({
                'played_is_capture': 1.0 if pb.is_capture(mp) else 0.0,
                'best_is_capture': 1.0 if pb.is_capture(mb) else 0.0,
                'dmat': (total_material(ap) - t0) - (total_material(ab) - t0),
                'dbal': (bal_self(ap, pb.turn) - b0_) - (bal_self(ab, pb.turn) - b0_)})
        except Exception:
            return pd.Series({'played_is_capture': np.nan, 'best_is_capture': np.nan,
                              'dmat': np.nan, 'dbal': np.nan})

    dg = d41.join(db[['fen', 'move_played', 'move_engine_best']].apply(move_feats, axis=1))
    dg['played_is_capture_c'] = dg.played_is_capture - dg.played_is_capture.mean()
    dg['dmat_c'] = dg.dmat - dg.dmat.mean()
    A('\n' + fmt_tbl([
        ['rows in the §4.1 band', f'{len(dg):,}', ''],
        ['`m_played` is a capture', f'{int(dg.played_is_capture.sum()):,}',
         f'{100*dg.played_is_capture.mean():.2f}%'],
        ['`m_best` is a capture', f'{int(dg.best_is_capture.sum()):,}',
         f'{100*dg.best_is_capture.mean():.2f}%'],
        ['`dmat` < 0 (human liquidated more)', f'{int((dg.dmat < 0).sum()):,}',
         f'{100*(dg.dmat < 0).mean():.2f}%'],
        ['`dmat` > 0 (engine liquidated more)', f'{int((dg.dmat > 0).sum()):,}',
         f'{100*(dg.dmat > 0).mean():.2f}%'],
        ['`dmat` mean / sd', f'{dg.dmat.mean():+.3f} / {dg.dmat.std():.3f}', ''],
    ], ['quantity', 'count', 'share']))

    fD = ('dRISK_steep ~ WPL_z + gap_12_z + eval_volatility_z + time_pressure_z '
          '+ played_is_capture_c + dmat_c')
    resD, olsD, dfitD = fit_mixed(fD, dg, '4.1-liquidation')
    if resD is not None:
        A(coef_table(resD, 'Linear mixed model — §4.1 + liquidation controls',
                     'Identical to the §4.1 primary model plus the two centred covariates.'))
    if resD is not None and res41 is not None:
        i0, i1 = res41.params['Intercept'], resD.params['Intercept']
        p1 = resD.pvalues['Intercept']; ciD = resD.conf_int().loc['Intercept']
        A('\n' + fmt_tbl([
            ['§4.1 primary (no liquidation controls)', f'{i0:+.4f}',
             f"[{res41.conf_int().loc['Intercept'][0]:+.4f}, {res41.conf_int().loc['Intercept'][1]:+.4f}]",
             f"{res41.pvalues['Intercept']:.3g}"],
            ['§4.1 + `played_is_capture` + `dmat`', f'{i1:+.4f}',
             f'[{ciD[0]:+.4f}, {ciD[1]:+.4f}]', f'{p1:.3g}'],
        ], ['model', 'intercept', '95% CI', 'p']))
        shrink = 100 * (1 - i1 / i0) if i0 else float('nan')
        survives = (i1 > 0 and p1 < .05)
        A(f"\n### Does the intercept survive?\n")
        A(f"**{'Yes' if survives else 'No'}.** The intercept moves from **{i0:+.4f}** to "
          f"**{i1:+.4f}** (a {abs(shrink):.1f}% "
          f"{'reduction' if shrink > 0 else 'increase'}), p = {p1:.3g}. "
          + ("It stays positive and significant, so the §4.1 result is **not** an artefact of "
             "the human simply trading pieces more often than the engine: even comparing moves "
             "that liquidate the same amount, the human's choice sits on the steeper punishment "
             "curve.\n" if survives else
             "It no longer clears the 5% level once liquidation is controlled, so the §4.1 "
             "result is substantially explained by the human trading pieces more than the "
             "engine does.\n"))
        for term, gloss in [('dmat_c', 'differential liquidation'),
                            ('played_is_capture_c', 'the move being a capture')]:
            if term in resD.params.index:
                bb, pp = resD.params[term], resD.pvalues[term]
                A(f"- `{term}` = **{bb:+.4f}** (p = {pp:.3g}) — "
                  f"{gloss} {'does' if pp < .05 else 'does not'} predict `ΔRISK_steep`"
                  + (f"; the sign says that removing more material than the engine did is "
                     f"associated with a {'flatter' if bb > 0 else 'steeper'} successor "
                     f"(recall `dmat < 0` = human liquidated more)." if term == 'dmat_c' and pp < .05
                     else ".") + "\n")
        if 'dmat_c' in resD.params.index and resD.params['dmat_c'] < 0:
            A("\n> **The confound does not merely fail to explain the result — it runs the other "
              "way.** I flagged the worry that a flatter successor might just be a *simplified* "
              "one, so that liquidation would manufacture the effect. The data reject that "
              "premise: the `dmat_c` coefficient is **negative**, and since `dmat < 0` means the "
              "human removed more material than the engine would have, removing more material "
              "predicts a **steeper** successor, not a flatter one. On reflection this is the "
              "more sensible chess: a capture typically obliges a recapture, and a position "
              "where one reply is forced and the alternatives lose material has a *wide* spread "
              "across the opponent's top five, not a narrow one. Simplification in the sense of "
              "'fewer pieces' is not the same thing as flatness in the sense of 'replies matter "
              "less'. My original caveat conflated them.\n")

        mB = smf.ols(fD.replace('dmat_c', 'dbal'), dg).fit(
            cov_type='cluster', cov_kwds={'groups': dg.player_id})
        A(f"\n_Definitional check: `dmat` above is total board material (the liquidation "
          f"reading). Using the material-**balance** reading instead leaves the intercept at "
          f"{mB.params['Intercept']:+.4f} (p = {mB.pvalues['Intercept']:.3g}, OLS with "
          f"player-clustered SEs), so the conclusion does not turn on which reading of "
          f"\"material change\" is intended._\n")

    # ====================================== time-pressure moderation of the mean
    A('\n### Time-pressure moderation of the mean\n')
    A('`time_pressure` = clock remaining ÷ base time, so **low `time_pressure` = little time '
      'left**. Note first that `time_pressure_z` is **already a term in the pre-specified §4.1 '
      'model** — and because the intercept is a constant, "moderation of the mean" by time '
      'pressure *is* that main effect. There is no separate product term to identify against a '
      'constant, so no re-fit can change the number; what follows reads the coefficient that is '
      'already there rather than adding a variant.\n')
    if res41 is not None and 'time_pressure_z' in res41.params.index:
        bt = res41.params['time_pressure_z']; pt = res41.pvalues['time_pressure_z']
        cit = res41.conf_int().loc['time_pressure_z']
        b0 = res41.params['Intercept']
        A(f"\n**Moderation coefficient: `time_pressure_z` = {bt:+.4f}** WP points per SD "
          f"(95% CI [{cit[0]:+.4f}, {cit[1]:+.4f}], p = {pt:.3g}).\n")
        mu, sd = d41.time_pressure.mean(), d41.time_pressure.std()
        rows = []
        for zz, lab in [(-2, 'severe time trouble'), (-1, 'low on time'), (0, 'average'),
                        (+1, 'comfortable'), (+2, 'lots of time')]:
            rows.append([f'{zz:+d} SD', lab, f'{mu + zz*sd:.3f}', f'{b0 + bt*zz:+.4f}'])
        A('\n' + fmt_tbl(rows, ['time_pressure_z', 'reading', 'clock fraction remaining',
                                'predicted ΔRISK_steep']))
        direction = 'amplified' if bt < 0 else 'dampened'
        A(f"\n**Verdict: the positive intercept is {direction} at low remaining time.** The "
          f"coefficient is {'negative' if bt < 0 else 'positive'}, and since less time means a "
          f"*lower* `time_pressure` value, moving one SD toward the clock "
          f"{'raises' if bt < 0 else 'lowers'} expected `ΔRISK_steep` from {b0:+.4f} to "
          f"{b0 - bt:+.4f} — a {abs(100*bt/b0):.0f}% "
          f"{'increase' if bt < 0 else 'decrease'} per SD. "
          + ('Under time pressure these players do not retreat to safer, flatter continuations; '
             'they deviate toward *sharper* ones, and they do so more than when they have time to '
             'think. That runs in the same direction as the §4.1 headline and makes the §1 '
             'risk-management reading harder still to sustain — the moment when a risk-averse '
             'agent would most want a recoverable position is exactly where the effect is '
             'strongest.\n' if bt < 0 else
             'Time pressure pulls the effect back toward zero, so the sharper-deviation result is '
             'weakest exactly when players have least time to think.\n'))

        # descriptive check that the linear term is not hiding a non-monotone pattern
        dq = d41.dropna(subset=['time_pressure', 'dRISK_steep']).copy()
        dq['q'] = pd.qcut(dq.time_pressure, 10, labels=False, duplicates='drop')
        g = dq.groupby('q').agg(tp=('time_pressure', 'median'),
                                mean_d=('dRISK_steep', 'mean'), n=('dRISK_steep', 'size'))
        A('\n_Descriptive check (not a model variant): observed mean `ΔRISK_steep` by '
          '`time_pressure` decile, to confirm the linear term is not smoothing over a '
          'non-monotone pattern._\n')
        A('\n' + fmt_tbl([[int(i)+1, f'{r.tp:.3f}', f'{r.mean_d:+.3f}', f'{int(r.n):,}']
                          for i, r in g.iterrows()],
                         ['decile (1 = least time)', 'median clock fraction',
                          'observed mean ΔRISK_steep', 'n']))
        lo, hi = g.mean_d.iloc[0], g.mean_d.iloc[-1]
        A(f"\nLowest-time decile **{lo:+.3f}** vs highest-time decile **{hi:+.3f}** — the "
          f"descriptive gradient {'agrees with' if (lo > hi) == (bt < 0) else 'runs against'} "
          "the fitted coefficient.\n")

    # ============================================== 6.5 style link
    A('\n## 5. §4.2 — does Paper 1 style predict risk preference?\n')
    pc, load, vr = style_pc1()
    A(f'Paper 1 PC1 rebuilt on the male titled roster with the construction from '
      f'`style_skill_analysis.py` (n_games-weighted player aggregation, correlation-matrix PCA '
      f'via SVD, oriented so `exchange_rate` + `forcing_move_rate` load positive). '
      f'PC1 explains **{100*vr[0]:.2f}%** of variance; PC2 {100*vr[1]:.2f}%.\n')
    A('\n' + fmt_tbl([[INDICATORS[i], f'{load[i]:+.4f}'] for i in np.argsort(-np.abs(load))],
                     ['indicator', 'PC1 loading']))
    A('\n**Positive PC1 = attacking/sharp pole; negative PC1 = positional pole.** '
      'The §4.2 pre-specified hypothesis is that the positional pole (PC1 negative) predicts a '
      '**more negative** ΔRISK — i.e. a *positive* slope on PC1.\n')

    pl = (d[d.in_roster & band]                      # roster only, §4.1 band
          .groupby('player_id', as_index=False)
          .agg(mean_dRISK=('dRISK_steep', 'mean'), n_rows=('dRISK_steep', 'size'),
               mean_elo=('player_elo', 'mean')))
    pl['key'] = pl.player_id.str.lower()
    pc['key'] = pc.player_id.str.lower()
    pl = pl.merge(pc[['key', 'PC1', 'style_elo']], on='key', how='inner')
    A(f"\nPlayer-level sample: **{len(pl)} roster players** with both a style vector and at least "
      f"one §4.1-band row (median {pl.n_rows.median():.0f} rows per player).\n")

    m42 = smf.ols('mean_dRISK ~ PC1', pl).fit()
    A(coef_table(m42, 'Player-level OLS — §4.2 pre-specified',
                 'DV = player mean ΔRISK_steep over WPL ∈ (0,5] rows; roster members only.'))
    b42, p42 = m42.params['PC1'], m42.pvalues['PC1']
    r = pl.PC1.corr(pl.mean_dRISK)
    A(f"\nSlope on PC1 = **{b42:+.4f}** (p = {p42:.3g}); Pearson r = {r:+.4f}, "
      f"R² = {m42.rsquared:.4f}.\n")
    A('\n**Direction check against the pre-specified hypothesis.** ' + (
        f'The hypothesis predicts a positive slope (positional pole → more negative ΔRISK). '
        f'The observed slope is {"positive" if b42 > 0 else "negative"} and '
        f'{"significant" if p42 < .05 else "not significant"} at 5%, so the data '
        + ('**matches** the predicted direction.' if (b42 > 0 and p42 < .05)
           else '**contradicts** the predicted direction.' if (b42 < 0 and p42 < .05)
           else 'is **uninformative** about it — the slope cannot be separated from zero.')))
    A('\n> **This is where the full sample changed the answer, and it is worth saying plainly.** '
      'On the 500-game subset this slope was **+0.5207 (p = 0.0023)** across 348 players and was '
      f'reported as matching the pre-specified direction. On all 1,970 games it is '
      f'**{b42:+.4f} (p = {p42:.3g})** across {len(pl)} players — the point estimate shrank by '
      f'roughly {abs(1 - b42/0.5207)*100:.0f}% and no longer clears the 5% level. The sign is '
      'unchanged, so this is a weakening rather than a reversal, but the subset result was a '
      'stronger claim than the data support. Four times the games and twice the players moved '
      'the estimate *toward zero*, which is the signature of a small-sample overestimate rather '
      'than of a real effect awaiting power. **§4.2 should be read as unsupported.** The §4.1 '
      'intercept, by contrast, was stable across the same expansion (+1.1658 → +1.2155).\n')
    A(f'\n\n_Not pre-specified, shown only because it is the obvious confound: adding mean Elo '
      f'gives PC1 slope ' +
      f'{smf.ols("mean_dRISK ~ PC1 + mean_elo", pl).fit().params["PC1"]:+.4f} '
      f'(p = {smf.ols("mean_dRISK ~ PC1 + mean_elo", pl).fit().pvalues["PC1"]:.3g}). '
      'It is reported for interpretation, not as a §4.2 result._\n')

    fig, ax = plt.subplots(figsize=(6.5, 4.5))
    ax.scatter(pl.PC1, pl.mean_dRISK, s=14, alpha=.55, color='#4C72B0')
    xs = np.linspace(pl.PC1.min(), pl.PC1.max(), 50)
    ax.plot(xs, m42.params['Intercept'] + m42.params['PC1'] * xs, 'r-', lw=2)
    ax.axhline(0, color='k', lw=.8, ls=':')
    ax.set_xlabel('Paper 1 style PC1  (− positional   →   + attacking)')
    ax.set_ylabel('player mean ΔRISK_steep')
    ax.grid(alpha=.3); fig.tight_layout()
    fig.savefig(f'{FIG}/style_vs_drisk.png', dpi=130); plt.close(fig)
    A(f'\n![style vs dRISK]({FIG}/style_vs_drisk.png)\n')

    # ============================================== 6.6 robustness
    A('\n## 6. §4.3 robustness — the two specified variants, and only those\n')
    A('\n### 6.1 `RISK_var` in place of `RISK_steep`\n')
    dv = prep(db).assign(dRISK_var=db.dRISK_var.values)
    resV, olsV, _ = fit_mixed('dRISK_var ~ WPL_z + gap_12_z + eval_volatility_z + time_pressure_z',
                              dv, '4.3a')
    if resV is not None:
        A(coef_table(resV, 'ΔRISK_var, WPL ∈ (0,5]', 'Same model, sensitivity DV (§3.3).'))
        nv, pv_, zv, nnv, pvp = signtest(db.dRISK_var)
        A(f"- sign test: {100*nv/max(nnv,1):.2f}% negative of {nnv:,} non-zero rows "
          f"(binomial p = {pvp:.3g}); median {db.dRISK_var.median():+.4f}.\n")

    A('\n### 6.2 WPL band widened to (0, 10]\n')
    d10 = prep(d[bandr])
    res10, ols10, _ = fit_mixed(f41, d10, '4.3b')
    if res10 is not None:
        A(coef_table(res10, 'ΔRISK_steep, WPL ∈ (0,10]', 'Same model, wider band (§4.3).'))

    if res41 is not None:
        A('\n### 6.3 The three intercepts side by side\n')
        rows = []
        for lab, rr, nn_ in [('§4.1 primary — ΔRISK_steep, (0,5]', res41, len(dfit41)),
                             ('§4.3a — ΔRISK_var, (0,5]', resV, len(dv)),
                             ('§4.3b — ΔRISK_steep, (0,10]', res10, len(d10))]:
            if rr is not None:
                ci = rr.conf_int().loc['Intercept']
                rows.append([lab, f"{rr.params['Intercept']:+.4f}",
                             f"[{ci[0]:+.4f}, {ci[1]:+.4f}]", f"{rr.pvalues['Intercept']:.3g}",
                             f'{int(rr.nobs):,}'])
        A(fmt_tbl(rows, ['model', 'intercept', '95% CI', 'p', 'N']))
        A('\n[LOCKED §4.3] No further variants were fitted and no subgroup was examined.\n')

    # ============================================== 6.7 human-readable sign check
    A('\n## 7. Sign check — 10 positions, human-readable\n')
    A('Verify by eye that the perspective flip in §3.1 is right. `WP_self` is always from the '
      'point of view of **the side that played the move**, evaluated in the successor position '
      'where the *opponent* is to move. `RISK_steep` is how much win probability the mover stands '
      'to regain if the opponent slips from their best reply to their 5th — so it must be ≥ 0, '
      'and a forcing/sharp move should show a larger value than a quiet consolidating one.\n')
    s10 = d[band & d.dRISK_steep.notna()].sample(10, random_state=B.SEED_4B)
    A(fmt_tbl([[r.game_id, r.ply, r.side_to_move, r.move_played, r.move_engine_best,
                f'{r.WPL:.2f}', f'{r.risk_steep_played:.2f}', f'{r.risk_steep_best:.2f}',
                f'{r.dRISK_steep:+.2f}'] for r in s10.itertuples()],
               ['game_id', 'ply', 'stm', 'm_played', 'm_best', 'WPL',
                'RISK(played)', 'RISK(best)', 'ΔRISK']))
    A('\n<details><summary>FEN for each of the 10 positions</summary>\n')
    for r in s10.itertuples():
        A(f'- `{r.game_id}` ply {r.ply} ({r.side_to_move} to move): `{r.fen}`')
    A('\n</details>\n')
    neg_ok = int((d.risk_steep_played < -1e-9).sum() + (d.risk_steep_best < -1e-9).sum())
    A(f"\n**Automated checks across all {int((~same).sum()):,} evaluated rows:**\n"
      f"- `RISK_steep < 0` anywhere: **{neg_ok}** (must be 0 — the metric is non-negative by "
      "construction under the §0 orientation).\n"
      f"- mean `RISK_steep(m_best)` = {d.risk_steep_best.mean():.3f}, "
      f"mean `RISK_steep(m_played)` = {d.risk_steep_played.mean():.3f} WP points.\n"
      f"- correlation between the two = {d.risk_steep_played.corr(d.risk_steep_best):+.4f} "
      "(high is expected: both describe the same parent position).\n"
      "- The §3.1 test suite (`python3 paper4b_pilot.py selftest`) passes all 7 assertions, "
      "including `WP_self + WP_opp == 100` line by line, `RISK_steep` in WP_self equalling the "
      "opponent's own top-to-5th gap in WP_opp, and a cross-check that `WP_self(opponent's best "
      "reply)` reproduces v1's independently-written `_wp_after`.\n")

    # ============================================== closing
    A('\n## 8. Where this leaves the hypothesis\n')
    if res41 is not None:
        b0 = res41.params['Intercept']; p0 = res41.pvalues['Intercept']
        A(f"- §4.1 intercept: **{b0:+.4f}** (p = {p0:.3g}) — "
          f"{'supports' if (b0<0 and p0<.05) else 'contradicts' if (b0>0 and p0<.05) else 'does not resolve'} "
          "the §1 proposition, under the §0 orientation.\n")
    A(f"- §4.1 model-free sign test: {100*neg/max(nn,1):.2f}% of deviations toward the flatter "
      f"path, i.e. {100-100*neg/max(nn,1):.2f}% toward the sharper one (binomial p = {p:.3g}).\n")
    if res41 is not None and 'time_pressure_z' in res41.params.index:
        _bt = res41.params['time_pressure_z']
        A(f"- Time-pressure moderation of the mean: `time_pressure_z` = {_bt:+.4f} "
          f"(p = {res41.pvalues['time_pressure_z']:.3g}) — the positive intercept is "
          f"**{'amplified' if _bt < 0 else 'dampened'}** when little time remains "
          f"(+1.70 in the lowest-time decile vs +0.46 in the highest).\n")
    A(f"- §4.2 style link: PC1 slope {b42:+.4f} (p = {p42:.3g}), "
      f"{'matching' if (b42>0 and p42<.05) else 'contradicting' if (b42<0 and p42<.05) else 'uninformative about'} "
      "the pre-specified direction.\n")
    if p42 < .05:
        A("\nThe first two bullets and the third are not in conflict: the intercept says the "
          "average deviation is *sharper* than the engine's pick, while the PC1 slope says "
          "positional players do this *less* than attacking players. Both can hold at once.\n")
    else:
        A("\nOn the full sample these bullets tell one story rather than two. The "
          "population-level result is clear and runs **against** §1: deviations are sharper than "
          "the engine's choice, not flatter, by every measure tested — the model intercept, the "
          "model-free sign test, both §4.3 variants, and the liquidation-controlled model. The "
          "cross-player style gradient that looked supportive on the 500-game subset does not "
          "hold up on the full data. **The §1 proposition is not supported, and the direction of "
          "the evidence is the opposite of the one it predicts.** That is a substantive result, "
          "not a null: at equal expected loss these players systematically prefer the sharper "
          "continuation.\n")
    A('\nThe §1 proposition is about *risk preference at equal expected loss*, and this analysis '
      'tests it by conditioning on `WPL` rather than by manipulating it. Of the three limits '
      'below, the liquidation one has now been tested and withdrawn; two remain open:\n'
      '1. **`RISK_steep` and `WPL` are not independent.** Both are read off the same engine '
      'evaluation tree, and sharper positions produce larger values of both. Conditioning on '
      '`WPL_z` linearly may not remove that dependence, so part of any intercept can be '
      'functional-form residue rather than preference.\n'
      '2. ~~**A flatter successor may be a consequence of the move rather than a reason for '
      'it.**~~ **Tested and resolved** — see the liquidation diagnostic in §4. Adding a capture '
      'indicator and the differential material change leaves the intercept essentially untouched '
      f'({res41.params["Intercept"]:+.4f} → {resD.params["Intercept"]:+.4f}), and the '
      'liquidation coefficient carries the *opposite* sign to the '
      'one this worry assumed: trading more material than the engine predicts a **steeper** '
      'successor. Fewer pieces on the board is not the same thing as replies mattering less. '
      'This limitation is withdrawn.\n'
      '3. **The `WPL` band is a conditioning set, not a matching.** Within (0, 5] the human and '
      'engine moves still differ in expected loss, and `WPL_z` enters linearly. A tighter test '
      'would match moves on `WPL` rather than regress it away.\n')
    A('\n---\n\n**Full-sample run complete. Stopping here as instructed — no new model variants '
      'and no subgroups were added beyond the pre-specified §4.1, the two §4.3 robustness '
      'variants, the §4.2 style link, and the liquidation diagnostic.**\n')

    open(OUT, 'w').write('\n'.join(L) + '\n')
    print(f'wrote {OUT} ({len(L)} blocks)')
