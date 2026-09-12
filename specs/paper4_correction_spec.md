# Paper 4 correction: random-effects estimator

Date: 2026-09-11

Status: LOCKED 2026-09-11. The lock takes effect at the commit that adds this file to `chess-behavioral-lab/specs/`, which must precede any re-run.

Remark (2026-09-11): the paper input in §0, §4 and §5 changed from `docs/Sharper_Not_Safer_v6.docx` to `docs/Sharper_Not_Safer_v7.docx`, the version on Zenodo; input path only, no other change.

## 0. Note to the implementer

Rules of SPEC v1 through v3 apply. Every item marked **[LOCKED]** is a research-design decision. If you believe one is wrong, stop and state your reasoning in the report; do not change it and keep running. No engine work. No new models, no new samples, no new covariates: this correction changes the estimator and nothing else.

Context: the finding below arose in the feasibility audit for SPEC v4 (2026-09-11). SPEC v4 was not run.

Inputs: the code and reports in this repository, the v1/v2/v3 data in `~/Desktop/chess-study/`, and the paper as `docs/Sharper_Not_Safer_v7.docx`. If the paper file is absent at run time, stop and report.

## 1. The finding

Environment on record: Python 3.9.6, statsmodels 0.14.6 (the version listed in `docs/paper4_v3_REPORT.md` §1).

### 1.1 `fit_mixed` does not estimate a player intercept

`fit_mixed` (`code/paper4_report.py:74`) calls

```python
smf.mixedlm(formula, d, groups=d['player_id'], vc_formula={'game': '0 + C(game_id)'})
```

without `re_formula`. In statsmodels 0.14.6, `MixedLM.from_formula` sets no group-level random effect when `re_formula` is `None` (`exog_re = None`, `statsmodels/regression/mixed_linear_model.py`, around line 980). Every fit through `fit_mixed` observed in the audit has `k_re = 0` and an empty `cov_re` (five optimizers × two dependent variables, SPEC v4 §2 rows).

Therefore every model reported in the Paper 4 v1 pilot report, the Paper 4b (v2) report, and the v3 report as `(1 | player_id) + (1 | game_id)` was fitted with `(1 | game_id)` only. A game that contributes rows from two players receives two independent game intercepts, one per player group. No player variance was estimated in any of these models.

Consistent with this, every coefficient table produced through `fit_mixed` in the three reports prints a single `game Var` and no `Group Var`: v1 §8.1, §8.2, §9 (two tables); 4b §4 (two tables), §6.1, §6.2; v3 §6.1–§6.5, §7.1–§7.3. The v3 post-hoc §C table and the Paper 4b figures print no variance.

### 1.2 The optimizer guard accepted non-converged fits

`fit_mixed` tries `lbfgs`, `bfgs`, `powell`, `nm` in order and keeps the first fit that passes a degeneracy test (finite intercept CI of width ≤ 1e3, and not intercept ≈ 0 with p > 0.999). The guard does not read the `converged` flag.

Observed in the audit on SPEC v4 §2 rows, `RES` as the dependent variable: `lbfgs` returned the degenerate all-zero solution and was rejected. `bfgs` returned `converged = False` (gradient optimization failed, |grad| = 222.6) at log-likelihood −40,335.50, and `fit_mixed` returned that fit. `powell`, `nm` and `cg` each converged at −40,328.89 on the same rows.

In the reported analyses, the v3 log records the `bfgs` fallback for H1, H4-RES, H4-CF, R1-RES, R1-CF, R2-RES, R3-RES and R3-CF. Whether those fits, or any reported v1 or 4b fit, had converged was not recorded and has not been checked. The re-run in §3 records it.

A related observation, on the same SPEC v4 rows with `re_formula='1'` added: `lbfgs` reported `converged = True` at −40,344.84 while `nm` reached −40,327.77. The `converged` flag alone does not identify the optimum.

### 1.3 Reported variances were ratios to the residual variance

`coef_table` (`code/paper4_report.py:48`) prints the entries of `res.params` whose names contain `Var` as "random-effect variance". In statsmodels `MixedLMResults`, those entries are variance divided by the residual variance (`scale`). Audit example: `game Var` 0.01998 = `vcomp` 0.3831 / `scale` 19.172. Every "random-effect variance" line in the three reports is such a ratio. This includes v3 §4's `Group Var` = 0.0220, which comes from the expected-error model, also printed through `coef_table`. The residual variance was not printed.

### 1.4 v3 Amendment 2 mischaracterized the estimator

Amendment 2 item 1 states that `(1 | player_id) + (1 | game_id)` is estimated with `game_id` nested inside `player_id`. Item 2 states that what the approximation drops is the sharing of one game intercept across a game's two players. Both describe a model with a player intercept, and no player intercept was estimated (§1.1). Item 1 also describes the guard as rejecting degenerate optima without stating that it does not check convergence (§1.2). The same description is repeated in the random-effects flag printed under every v3 §6 and §7 table, and summarized in `README.md` line 34.

## 2. The corrected estimator [LOCKED]

1. A new module `code/paper4_mixed_v2.py` containing `fit_mixed_v2(formula, data, label)`. `code/paper4_report.py` is not modified; its hash before and after the correction run is recorded in the report.
2. Row handling is identical to `fit_mixed`: the same formula-token `dropna`, and the same rule of returning no fit below 50 rows.
3. Model:
   ```python
   smf.mixedlm(formula, d, groups=d['player_id'], re_formula='1',
               vc_formula={'game': '0 + C(game_id)'})
   ```
   REML (the statsmodels default, as in `fit_mixed`), `maxiter=2000`. `game_id` remains nested within `player_id`; the table flag says so.
4. Optimizer sweep: `lbfgs`, `bfgs`, `powell`, `nm`, `cg`, all five on every model, with no early exit. For each optimizer, record exception (if any), `converged`, log-likelihood and wall time.
5. **Degenerate fit.** A fit is degenerate when all its variance components are zero (player variance from `cov_re` = 0, game variance from `vcomp` = 0) and its intercept is exactly zero. A degenerate fit is never selected.
6. Selection: among fits with `converged = True` that are not degenerate, the one with the highest log-likelihood.
7. **No fit selected.** `fit_mixed_v2` returns no fit when either:
   - no optimizer converges; or
   - every converged fit is degenerate.

   The model's row reads "no converged fit" or "only degenerate converged fit". The implementer stops work on that model and reports it, with no fallback to a non-converged fit, to a degenerate fit, or to `fit_mixed`.
8. Variance components are reported on the natural scale: player variance from `cov_re`, game variance from `vcomp`, residual variance from `scale`. Never from `params`.
9. The per-optimizer record (item 4) is reported for every model, with each fit's degeneracy status.
10. The statsmodels version is recorded. If it is not 0.14.6, stop and report before fitting.

## 3. Re-run and verification [LOCKED]

Order: §3.4 first, then §3.1–§3.2. If §3.4 stops, nothing in §3.2 is fitted.

### 3.1 Procedure for the re-run list

1. **Rows.** Rebuild each model's rows with the original script's own data preparation on the original inputs. The model N must equal the published N. For post-hoc §C the published figure is the subgroup row count. B-5 has no published N; record it. If N differs from a published N, stop and report for that model.
2. **Old fit.** Re-execute the unchanged `fit_mixed` on those rows to record the optimizer it selected, its `converged` flag, and its game variance and residual variance on the natural scale. Its core coefficients must reproduce the published values to the printed precision: 4 decimals in the reports, 3 decimals in the figures. If they do not, stop and report for that model.
3. **Figure fits covered by report models.** `code/paper4b_figures.py` also fits `figB-full` and `figC-primary` (same model as B-1), `figC-var` (B-3), `figC-band10` (B-4) and `figC-liq` (B-2). For each, confirm that its N equals the corresponding report model's N and that its old fit reproduces the intercept and CI printed in the figure. If either check fails, stop and report; the figure fit is then not covered by the list.
4. **New fit.** `fit_mixed_v2` on the same rows.
5. **Side-by-side row,** one per core coefficient:
   - old coefficient and 95% CI (published);
   - new coefficient and 95% CI;
   - old convergence status (optimizer, `converged`) and new convergence status (selected optimizer, `converged`);
   - old variance components: player "not estimated", game, residual;
   - new variance components: player, game, residual;
   - for T-1 only, old and new TOST p-values and verdict (§4).

   Full old and new coefficient tables for every model go in an appendix.

### 3.2 The re-run list: 23 models

`docs/paper4_pilot_REPORT.md` (v1), fitted in `code/paper4_report.py`:

| ID | Report section | Model | Published N | Call site | Core coefficient(s) |
|---|---|---|---|---|---|
| V1-1 | §8.1 (spec §7.1, roster only) | `WPL ~ elo_z + gap_12_z + spread_15_z + n_legal_z + eval_volatility_z + time_pressure_z + elo_z:gap_12_z + elo_z:time_pressure_z` | 25,457 | `:392` | `elo_z`; `elo_z:gap_12_z`; `elo_z:time_pressure_z` |
| V1-2 | §8.2 (spec §7.1, all rows) | as V1-1 | 49,921 | `:401` | as V1-1 |
| V1-3 | §9 primary (spec §7.2) | `WPL_opponent_next ~ WPL_self_z * gap_12_z * elo_diff_z + n_legal_z + eval_volatility_z + time_pressure_z` | 47,959 | `:475` | `WPL_self_z` |
| V1-4 | §9 robustness, controls at t+1 | as V1-3, controls at the opponent's position | 47,959 | `:486` | `WPL_self_z` |

`docs/paper4b_pilot_REPORT.md` (4b, SPEC v2), fitted in `code/paper4b_report.py`, and figure B of the paper, fitted in `code/paper4b_figures.py`:

| ID | Source | Model | Published N | Call site | Core coefficient(s) |
|---|---|---|---|---|---|
| B-1 | report §4 primary (spec §4.1) | `dRISK_steep ~ WPL_z + gap_12_z + eval_volatility_z + time_pressure_z` | 19,842 | `paper4b_report.py:303` | `Intercept` |
| B-2 | report §4 liquidation diagnostic | B-1 `+ played_is_capture_c + dmat_c` | 19,842 | `paper4b_report.py:394` | `Intercept`; `dmat_c` |
| B-3 | report §6.1 (spec §4.3a) | B-1 with `dRISK_var` as DV | 19,842 | `paper4b_report.py:574` | `Intercept` |
| B-4 | report §6.2 (spec §4.3b) | B-1, WPL band (0, 10] | 25,012 | `paper4b_report.py:584` | `Intercept` |
| B-5 | figure B (`figures/paper4/figB_pilot_vs_full`), left panel, "500 games" | B-1, WPL band (0, 5], games in `paper4b_cache/pilot4b_sample_games_500.csv` | not published | `paper4b_figures.py:140` (`figB-500`) | `Intercept` |

`docs/paper4_v3_REPORT.md` (v3), fitted in `code/p4_v3_analysis.py` via `run()` (`:458`), except the post-hoc rows (`code/p4_v3_posthoc.py:159`). `H2` below stands for `delta_risk_steep_z + WPL_self_z + gap_12_orig_z + eval_volatility_orig_z + time_pressure_opp_z + elo_diff_opp_z`.

| ID | Report section | Model | Published N | Core coefficient(s) |
|---|---|---|---|---|
| T-1 | §6.1 H1 | `NET_realized ~ 1` | 18,903 | `Intercept`, plus the TOST verdict (§4) |
| T-2 | §6.2 H2 | `NET_realized ~ H2` | 18,903 | `delta_risk_steep_z` |
| T-3 | §6.3 H3 | H2 `+ delta_risk_steep_z:time_pressure_opp_z + delta_risk_steep_z:elo_diff_opp_z` | 18,903 | both interactions |
| T-4 | §6.4 H4a | `RES ~ H2` | 18,905 | `delta_risk_steep_z` |
| T-5 | §6.4 H4b | `CF ~ H2` | 18,885 | `delta_risk_steep_z` |
| T-6 | §6.5 control (v1 §7.2 form) | as V1-3 | 19,204 | `WPL_self_z` |
| T-7 | §7.1 H2, band (0, 10] | `NET_realized ~ H2` | 23,920 | `delta_risk_steep_z` |
| T-8 | §7.1 H4a, band (0, 10] | `RES ~ H2` | 23,928 | `delta_risk_steep_z` |
| T-9 | §7.1 H4b, band (0, 10] | `CF ~ H2` | 23,897 | `delta_risk_steep_z` |
| T-10 | §7.2 H4a, unrestricted training set | `RES ~ H2` | 18,905 | `delta_risk_steep_z` |
| T-11 | §7.3 H4a, LightGBM expected-error model | `RES ~ H2` | 19,812 | `delta_risk_steep_z` |
| T-12 | §7.3 H4b, LightGBM expected-error model | `CF ~ H2` | 19,812 | `delta_risk_steep_z` |
| T-13 | Post-hoc §C, reply inside MultiPV-5 | `RES ~ H2` | 14,894 (subgroup rows) | `delta_risk_steep_z` |
| T-14 | Post-hoc §C, reply freshly evaluated | `RES ~ H2` | 4,011 (subgroup rows) | `delta_risk_steep_z` |

Core coefficients are those each report, figure or spec names as the quantity a conclusion rests on:
- v1 §8.3 reads `elo_z` and both Elo interactions.
- v1 spec §7.2 names `WPL_self_z`.
- 4b §4 "The core number", "Does the intercept survive?" (`Intercept`, `dmat_c`), and §6.3.
- Figure B's left panel ("§4.1 intercept — holds").
- v3 spec §6.1 (intercept and TOST) and §6.2 core quantities, the §6.3 interactions, and v3 report §6.4.

### 3.3 Not in scope

These estimates contain no mixed model, so the finding does not apply to them:
- v1 §9 game-outcome model (`smf.logit`, player-clustered SEs, `paper4_report.py:530`);
- 4b §4 time-pressure moderation and 4b §5;
- the right panel of figure B (`pc1_slope`, OLS on player means, `paper4b_figures.py:74`);
- v3 post-hoc §B (two-way clustered mean) and §D.

The OLS fits with player-clustered SEs printed beside each mixed model do not depend on `re_formula` and are not re-run.

The v3 §4 expected-error model is out of scope for this correction. It was fitted with the player intercept its spec required (`(1 | player_id)`, `MixedLM` grouped on `player_id` with the default random intercept) and did not go through `fit_mixed`. It is subject only to the verification in §3.4.

### 3.4 Verification of the v3 expected-error model

1. **Fits covered.** `crossfit(kind='lmm')` (`p4_v3_analysis.py:92`) fits `WPL ~ wp_level_z + wp_level_z2 + gap_12_z + spread_15_z + n_legal_z + n_reasonable_z + eval_volatility_z + elo_z + time_pressure_z + (1 | player_id)` on five folds (fold seed 20260905) for two training sets, 10 fits in all:
   - the main training set (`p4_v3_analysis.py:262`);
   - the unrestricted training set of §7.2 (`p4_v3_analysis.py:559`).

   The post-hoc refit at `p4_v3_posthoc.py:58` uses the same training set, standardization and folds as `:262`, and is covered by those fits.
2. **Sweep.** For each of the 10 fold fits, fit the model exactly as `crossfit` does (`smf.mixedlm(f, tr, groups=tr['player_id'])`, `maxiter=2000`) with each of `lbfgs`, `bfgs`, `powell`, `nm`, `cg`. Report `converged` and log-likelihood for every optimizer.
3. **Test.** A fold fit "converged at the maximum" when both hold:
   - the `lbfgs` fit, which v3 used, has `converged = True`;
   - its log-likelihood is no more than 0.1 below the highest log-likelihood among converged fits in that fold's sweep.

   The 0.1 tolerance is above the difference seen between converged optimizers on identical rows in the audit (0.05), and corresponds to a likelihood-ratio statistic of 0.2.
4. **Reproduction.** The re-executed `lbfgs` fits on the main training set must reproduce the stored `E_played` and `E_best` in `p4_v3_rows_analysis.parquet`; report the maximum absolute difference. If it exceeds 1e-9, stop and report. The §7.2 predictions are not stored; their reproduction is checked through T-10 (§3.1 item 2).
5. **Outcome.**
   - If all 10 fold fits converged at the maximum, the expected-error model stands: `RES`, `CF` and `NET_realized` are unchanged, and §3.1–§3.2 proceed on the stored values.
   - If any fold fit did not, stop and report. That is a separate correction, and nothing in §3.2 is fitted under this spec.

## 4. The reading rule [LOCKED]

For each core coefficient, a published conclusion stands if both of the following are unchanged between the old and new fits:
- the sign of the coefficient;
- whether its 95% CI excludes zero.

For H1 (T-1), the conclusion also requires the TOST verdict to be unchanged. The verdict is recomputed from the new fit's intercept and standard error with v3's `tost` (`p4_v3_analysis.py:149`): ±0.5 WP points, df = N − 1, α = .05. The published verdict is overall p = 1, "NOT statistically equivalent to zero".

If any required element changes, the correction report names the sentence in the paper that must change, quoting it with its location in `docs/Sharper_Not_Safer_v7.docx`. If the affected conclusion is not stated in the paper, the correction report says so.

No other interpretation.

## 5. Deliverables

Report at `docs/paper4_correction_REPORT.md`:

1. **The §3.4 verification table:** 10 fold fits × 5 optimizers, with `converged`, log-likelihood, the at-the-maximum verdict, and the `E_played`/`E_best` reproduction difference.
2. **The side-by-side table** (§3.1 item 5) for all 23 models (V1-1 to V1-4, B-1 to B-5, T-1 to T-14), with:
   - the per-optimizer record and degeneracy status (§2 item 9);
   - the N, reproduction and figure-coverage checks (§3.1 items 1–3);
   - the full coefficient tables in an appendix.
3. **The list of sentences that must change,** each quoted from `docs/Sharper_Not_Safer_v7.docx` with its location, and with the model ID and core coefficient that triggers it under §4.
4. **The corrected text of v3 Amendment 2.**
5. **The corrected text of `README.md` line 34** (its description of Amendment 2), old and new quoted.

The implementer delivers items 4 and 5 as text in the report and does not edit `specs/` or `README.md`.

Stop after delivery. Do not commit.
