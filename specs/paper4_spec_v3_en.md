# SPEC v3: A Counterfactual Test of Opponent Error (Identification Redesign of Paper 4 §7.2)

Status: LOCKED 2026-09-05. Handed to Claude Code for execution.

Language note: this English file is the governing version of SPEC v3. The Chinese file `paper4_spec_v3.md` is the original-language record of the lock (commits f084f80 and dc082ba, both pushed before any results existed); its content is identical to this file. Amendments after Amendment 1 are recorded in this English file only.

## 0. Note to the implementer

The rules of SPEC v1 and v2 apply. Every parameter marked **[LOCKED]** is a research-design decision, not an implementation detail. Do not change it. If you disagree, stop and state your reasoning in the report; do not change it and keep running. All of v1's infrastructure (data, pipeline, middlegame window, WPL, complexity proxies, Parquet shards) and v2's successor evaluations (MultiPV-5 on P(m_played) and P(m_best)) are reused as is and are not to be recomputed.

This SPEC adds no full-scale engine evaluation. All work is done on the 1,970 games already completed under v1 and v2.

---

## 1. Proposition and identification strategy

### 1.1 The problem with v1 §7.2

v1 §7.2 regressed `WPL_opponent_next` on `WPL_self`. That regression cannot separate two paths:

- Path A: the human's off-engine move led the opponent into a harder position, and the opponent erred because of it.
- Path B: the human was already in a hard position (which is why WPL_self is high), the difficulty carried over to the opponent, and the opponent erred because of that.

v1's complexity covariates control the difficulty of the position faced by the **mover**, not the difficulty of the position the **opponent** faces on the next move. So B was never ruled out. That is the shared-difficulty confound.

### 1.2 The strategy in this SPEC

v2 already evaluated two successor positions for every deviation row: the actual branch P(m_played) and the counterfactual branch P(m_best). So for both branches we have the difficulty features of the decision problem the opponent faces.

Identification proceeds in three steps:

1. Fit an **expected-error model** on all evaluated rows: given a position's difficulty features and the mover's rating and clock, predict the mover's WPL. This is a nuisance model.
2. Use that model to predict the opponent's expected error on P(m_played) and on P(m_best). The difference is the extra opponent error caused by the deviation that is explained purely by position difficulty, i.e. the part of Path A the engine could in principle see.
3. Subtract the model's expected error from the opponent's **actual** error on the actual branch. What remains is the extra opponent error that difficulty does not explain. That is the information absent from the engine's objective function (opponent fallibility), and it is the direct evidence of complementarity.

**Identifying assumption (must be stated verbatim in the report)**: conditional on the position features, the opponent's Elo, and the opponent's clock, the opponent's error is independent of whether the position was reached by a human deviation or by the engine's first choice. This assumption removes measurable difficulty confounding. It does not remove unmeasured factors (opponent preparation, psychological state). This design is not a randomized experiment, and the report must not use causal language stronger than "under the identifying assumption".

---

## 2. Sample and data

- **[LOCKED]** Sample = all 1,970 games completed under v1, the game_id list drawn with `random_seed = 20260823`. No subsampling, no new games.
- **[LOCKED]** Analysis rows = v1 rows with `m_played != m_best` (deviation rows) for which v2 completed the successor evaluations on both branches.
- Training rows (§4) = all evaluated v1 rows, both sides.

---

## 3. Quantities to be added

### 3.1 The opponent's actual reply error

For each deviation row i:

- P_i = P(m_played). v2 holds its MultiPV-5, stored as `WP_self` from the original mover's perspective.
- r_i = the opponent's actual reply on P_i, read from the PGN.
- If r_i is one of P_i's MultiPV-5 lines, take its WP directly. Otherwise evaluate the position after r_i on P_i once (**[LOCKED]** depth 15, MultiPV 5, Threads=1, Hash=128, independent evaluation, identical to v1).
- **[LOCKED]** The opponent's WP = 100 − WP_self. Therefore

  ```
  WPL_opp_actual_i = WP_self(r_i) − WP_self(opponent's 1st choice on P_i)
  ```

  This is non-negative (the opponent's 1st choice minimizes WP_self). **Write an explicit test**: on 200 random rows assert `WPL_opp_actual >= 0`, and rerun v1's mirror test for the perspective flip.

- **[LOCKED]** Winsorize at the same 1% threshold value v1 computed on its full sample; do not re-estimate it. Keep `WPL_opp_actual_raw`.
- If there is no opponent reply after m_played (resignation, timeout, game ends in a draw), drop the row and report the count. If the reply falls outside the middlegame window, **keep** it; the reply happened and counts.

### 3.2 Position features the opponent faces on each branch

Compute one set for P(m_played) and one for P(m_best), identical definitions, all from the perspective of **the side to move at P (the opponent)**:

| Variable | Definition | Source |
|---|---|---|
| `wp_level` | WP_opp(P) = 100 − WP_self(1st choice at P) | v2 |
| `gap_12` | WP_opp(1st) − WP_opp(2nd) | v2 |
| `spread_15` | WP_opp(1st) − WP_opp(5th) | v2 |
| `n_legal` | number of legal moves | python-chess, no engine needed |
| `n_reasonable` | number of MultiPV lines within 5 WP points of the top choice, right-censored at 5 | v2 |
| `eval_volatility` | \|WP(P) − WP(position two plies before P)\| | sequence; both branches share the same "two plies before" position |
| `opp_elo` | opponent's Elo | v1 |
| `elo_diff_opp` | opp_elo − player_elo | v1 |
| `time_pressure_opp` | opponent's remaining time at that ply / initial time | PGN %clk |

- **[LOCKED]** `wp_level` must enter the model. Error rates vary non-linearly with how good or bad the position is; v1 did not control this.
- **[LOCKED]** On the counterfactual branch, `time_pressure_opp` takes its actual value (the counterfactual changes the move, not the clock).
- **[LOCKED]** Games without %clk are excluded whole, not imputed; report the proportion. Same as v1.

### 3.3 Sharpness

`ΔRISK_steep` is taken from v2, definition and values, not recomputed. Positive = the human chose a sharper move than the engine's first choice.

---

## 4. Expected-error model (nuisance model)

### 4.1 Training set

- **[LOCKED]** Primary training set = v1 rows satisfying both: the previous ply was evaluated, and the move at the previous ply was the engine's first choice (`m_played == m_best`). Reason: rows that follow a deviation are "treated" rows. If the proposition is true, their error is inflated; letting them into the training set absorbs the treatment effect into the baseline and biases the test toward zero.
- Report the primary training set's row count and its share of all rows.
- Rows whose previous ply was not evaluated (gaps caused by v1's 30-moves-per-game sampling) do not enter the primary training set. Report the gap proportion.

### 4.2 Model

```
WPL ~ wp_level_z + wp_level_z^2 + gap_12_z + spread_15_z + n_legal_z
      + n_reasonable_z + eval_volatility_z + elo_z + time_pressure_z
      + (1 | player_id)
```

- Linear mixed model. All continuous predictors standardized; standardization parameters computed on the training set and reused at prediction time.
- **[LOCKED]** 5-fold cross-fitting, folds split by `game_id`, `fold_seed = 20260905`. The prediction for deviation row i must come from the fold model that did not see that game.
- Predictions use the fixed-effects part only. The difference between the two branches' predictions contains no player intercept (same opponent), so the random intercept cancels in the difference. State this in the report.
- Report: coefficient table, out-of-sample R² per fold, and a binned calibration plot of predicted against actual (10 bins).

---

## 5. Dependent variables

For each deviation row i, in WP percentage points, all from the **deviating player's** perspective, positive = the deviation paid off:

```
E_played_i = Ê(WPL | X_played,i)                 # opponent's expected error on the actual branch
E_best_i   = Ê(WPL | X_best,i)                   # opponent's expected error on the counterfactual branch

CF_i   = E_played_i − E_best_i                   # extra opponent error explained by difficulty (visible to the engine in principle)
RES_i  = WPL_opp_actual_i − E_played_i           # extra opponent error beyond difficulty (invisible to the engine)

NET_expected_i = CF_i − WPL_self_i               # whether the deviation pays on difficulty alone
NET_realized_i = WPL_opp_actual_i − E_best_i − WPL_self_i
               = CF_i + RES_i − WPL_self_i       # the net gain that actually occurred
```

`NET_realized` is the primary dependent variable. `RES` is the direct measure of the complementarity mechanism. `CF` is used for the decomposition.

---

## 6. Tests (all pre-specified)

**[LOCKED]** Analysis rows restricted to `WPL_self ∈ (0, 5]`, the same band as v2 §4.1; report the share.

### 6.1 H1: on average, does deviating pay?

```
NET_realized ~ 1 + (1 | player_id) + (1 | game_id)
```

Core quantity: the intercept with 95% CI. Also report an equivalence test (TOST).

- **[LOCKED]** Equivalence interval ±0.5 WP points, roughly one quarter of the median `WPL_self` in the analysis band; that is, a net gain smaller than one quarter of the typical cost of deviating is treated as practically equivalent to zero. At design time that median was estimated at about 2 WP points. The implementer reports the measured median; if it departs from 2 by more than 50%, stop and report, and do not adjust the interval.

Expectation: following the direction of the Vaccaro et al. 2024 meta-analysis, the intercept is likely negative or indistinguishable from zero. That is not a failure; it is the background for H2 through H4.

Asymmetry note (state verbatim in the report): `NET_realized` uses the observed value on the actual branch and the model's expected value on the counterfactual branch, so noise enters from one side only. Under the identifying assumption this is unbiased, but the variance is inflated and the CI will be wide. This is a known cost of the design, not a flaw.

### 6.2 H2: does sharpness predict net gain?

```
NET_realized ~ ΔRISK_steep_z + WPL_self_z + gap_12_orig_z + eval_volatility_orig_z
               + time_pressure_opp_z + elo_diff_opp_z
               + (1 | player_id) + (1 | game_id)
```

`gap_12_orig` and `eval_volatility_orig` are the difficulty of the **original position** (when the deviating player moved), from v1.

Core quantity: the coefficient on `ΔRISK_steep_z`. Positive = sharper deviations yield higher net gain, i.e. the pressure-seeking reported in Paper 4 is an effective strategy and not only a preference.

### 6.3 H3: conditions (two interactions only, no more)

Add to the H2 model:

```
+ ΔRISK_steep_z : time_pressure_opp_z
+ ΔRISK_steep_z : elo_diff_opp_z
```

- Expectation one: the shorter the opponent's clock (smaller `time_pressure_opp`), the larger the gain from a sharp deviation; the interaction coefficient is negative.
- Expectation two: the weaker the opponent relative to the player (more negative `elo_diff_opp`), the larger the gain from a sharp deviation; the interaction coefficient is negative.
- **[LOCKED]** Use the opponent's clock, not the deviating player's. v1 used the mover's clock, which was the wrong variable: what induces error is the opponent's time pressure.

### 6.4 H4: mechanism decomposition

Replace the dependent variable in H2 with `RES` and with `CF` in turn, same right-hand side, one fit each.

- A positive `ΔRISK_steep_z` coefficient in the `RES` model = sharp moves induce opponent error **beyond** what difficulty explains. That is direct evidence that the human carries information the engine does not have.
- A positive coefficient in the `CF` model with a zero coefficient in the `RES` model = the gain from sharp moves comes entirely from steering the opponent into hard positions, which the engine could in principle compute; that is not complementarity.
- Report the relative size of the two coefficients. This is the most important table in the paper.

### 6.5 Comparison: the original v1 §7.2 model

Rerun v1 §7.2's model verbatim on the same analysis rows. One table, labeled "for comparison" only, no interpretation. Purpose: let the reader see whether the conclusion changes when the identification changes.

**[LOCKED]** No model beyond these five is run.

---

## 7. Robustness (three items only)

1. Change the `WPL_self` band to (0, 10]; rerun H2 and H4.
2. Change the training set to all v1 rows (do not exclude treated rows); rerun §4 and H4. Expectation: the treatment effect is absorbed into the baseline and the `RES` coefficient shrinks toward zero. If it grows instead, stop and report.
3. Replace the expected-error model with gradient boosting (LightGBM, default parameters, the same 5 folds by game and the same seed); rerun H4. Purpose: rule out non-linearity missed by the linear specification in §4.2.

**[LOCKED]** No other versions.

---

## 8. Compute and execution

- §3.1 top-up: deviation rows whose opponent reply falls outside MultiPV-5 need one evaluation each, estimated at 10,000 to 25,000 calls, ~500 ms each, 15 to 30 minutes on 8 processes.
- `n_legal` and `eval_volatility` in §3.2 need no engine.
- Model fitting: minutes.
- Resumability key: `(game_id, ply, "opp_reply")`.
- Parquet: append as a new table `p4_v3_rows`; do not modify v1 or v2 shards.

## 9. Deliverables

1. Environment recap plus measured per-position time.
2. Data coverage: total deviation rows; rows with an opponent reply; rows dropped and why; share of opponent replies inside MultiPV-5; primary training set row count; gap proportion; share excluded for missing %clk.
   - **[LOCKED]** Add one cross-tabulation: the share of dropped rows (opponent resigned, timed out, no reply) by quartile of `ΔRISK_steep`. Dropping is a post-treatment event. If the drop rate varies with sharpness, H2 and H4 carry selection bias; discuss the direction in the report. If there is no association, dismiss it in one sentence.
3. **Sign test**: 10 random deviation rows, listed human-readably with FEN, m_played, m_best, the opponent's actual reply, the WP of the opponent's 1st choice on P(m_played) and on P(m_best) (both perspectives written out), `WPL_opp_actual`, `E_played`, `E_best`, `CF`, `RES`, `NET_realized`.
4. §4 model: coefficient table, out-of-sample R² per fold, overall calibration plot (10 bins).
   - **[LOCKED]** Also one calibration plot per decile of `ΔRISK_steep`, computed on untreated evaluated rows. This is the precondition for H4: the interpretation of the `RES` coefficient requires the model to have no systematic bias across sharpness levels. If the linear specification underestimates expected error at high sharpness, difficulty signal leaks into `RES` and H4 gives a false positive. If this plot shows systematic bias, the interpretation of H4 defers to §7 item 3 (LightGBM), and the report says so.
5. Distributions of `NET_realized`, `RES`, `CF` (histogram plus quantiles) and their pairwise correlations.
6. H1 intercept and TOST result.
7. H2 and H3 coefficient tables.
8. The two H4 tables side by side.
9. The §6.5 comparison table.
10. The three §7 robustness items.
11. The §1.2 identifying assumption verbatim, plus the implementer's own view of where it is most likely to fail.

## 10. Stop rule

Stop after delivery. The designer reads the direction and relative size of the two H4 coefficients before deciding whether to extend to a Lichess replication and a second domain.

## 11. Parameters confirmed by the designer (2026-09-05, all [LOCKED])

| Parameter | Value | Location |
|---|---|---|
| TOST equivalence interval | ±0.5 WP points | §6.1 |
| Cross-fitting folds and seed | 5 folds, 20260905 | §4.2 |
| Primary training set exclusion rule | previous ply was the engine's first choice | §4.1 |
| Sharpness measure | `RISK_steep` only, not `RISK_var` | §3.3 |
| Time-pressure variable | opponent's clock | §6.3 |
| Robustness item 3 model | LightGBM, default parameters | §7 |

---

## Amendment 1 (2026-09-05, after lock, before execution)

**Trigger**: the implementer's audit found that v2 did not persist the five MultiPV-5 lines. It stored only `wp_self_opp_best`, `wp_self_opp_worst`, `risk_var`, `n_pv`, and `risk_steep`. `gap_12` and `n_reasonable` in §3.2, and the §3.1 shortcut "if the reply is inside MultiPV-5, take its WP directly", cannot be obtained from v2.

**Decisions**:

1. §0's "v2 successor evaluations are not to be recomputed" is relaxed to: **the 57,294 successor positions may be re-evaluated once under the v1/v2 configuration (depth 15, MultiPV 5, Threads=1, Hash=128, independent evaluation), persisting the move and WP of all five lines**.
2. **[LOCKED]** The re-evaluation must be checked for consistency with v2: for every successor position, compare the recomputed `risk_steep` with the value v2 stored, row by row, and report the maximum absolute difference and the number of mismatching rows. With the same engine build and fixed depth they should match exactly. If any mismatch exists, stop and report; the recomputed values must not replace v2's `ΔRISK_steep` (§3.3 continues to use the v2 stored values).
3. The §3.1 opponent-reply evaluation is not band-restricted: all 28,647 deviation rows are evaluated, because §7 robustness item 1 needs the (0, 10] band.
4. §8 compute budget updated: measured 474 ms per position, 10 cores, 8 processes. Successor re-evaluation about 57 minutes, opponent replies about 28 minutes, about 1.5 hours in total.
5. The execution directory is `~/Desktop/chess-study/`, not the publication mirror `chess-behavioral-lab`. New output tables `p4_v3_rows` and `p4_v3_successor_lines`; v1 and v2 shards are not modified.
6. Environment: install `lightgbm`. Python 3.9.6 is acceptable; the README's 3.10+ requirement does not block this task; the report states the actual version.

All other clauses unchanged.

---

## Amendment 2 (2026-09-05, after lock, during execution)

**Trigger**: implementation review of how the [LOCKED] random-effects structures are actually estimated, plus one feature-definition convention that belongs on the record. This amendment records existing practice. No estimate, parameter, or model specification changes under it.

**Decisions**:

1. **Crossed random effects in §6.** The structure `(1 | player_id) + (1 | game_id)` in §6.1 through §6.5, and in the §7 robustness refits that reuse those model forms, is estimated with v1's `fit_mixed` (`paper4_report.py:74`): `game_id` enters as a variance component nested inside `player_id`; the fit is retried across optimizers with a guard that rejects degenerate optima (an all-zero variance solution reported as convergence); and an OLS fit with player-clustered standard errors is reported alongside it on the same rows. This is the same approximation v1 adopted and documented. Reusing it verbatim is also what makes §6.5's rerun of the v1 §7.2 model a like-for-like comparison — the same estimator on the same rows, so any difference in conclusion comes from the identification change and not from the fitting routine.

2. **The crossing is real, not incidental.** In the (0, 5] analysis band, 1,937 of 1,967 games (98.5%) contribute rows from both players, so `game_id` genuinely crosses `player_id` rather than nesting inside it. What the approximation drops is the sharing of one game intercept across that game's two players. Because the crossing is real, the approximation is flagged in **every** mixed-model coefficient table in the report, not only once in a methods note.

3. **§4.2 is not affected.** The nuisance model carries a single grouping factor, `(1 | player_id)`, and is fitted exactly (`MixedLM` grouped on `player_id`). No nesting approximation is involved there. Recorded so the distinction between §4.2 and §6 is explicit rather than assumed.

4. **`spread_15` convention.** §3.2 defines `spread_15` as `WP_opp(1st) − WP_opp(5th)`. It is computed against the last available MultiPV line, which is v1's own convention for the same feature (`wp_best - wps[-1]`). The two are identical wherever the engine returned five lines — 56,541 of 57,294 successor positions, 98.7% — and differ only where it returned fewer. Matching v1 keeps the nuisance model's training features and its prediction features on a single definition, which §4.2 requires.

All other clauses unchanged.
