# SPEC v6: Can a Pre-Move Selector Turn Human Divergence into an Increment?

Status: LOCKED 2026-09-28. Post-results follow-up to SPEC v5 (b735062, results 882a929). All §9 parameters confirmed by the designer on 2026-09-28. Pushed to `chess-behavioral-lab` as `specs/paper4_spec_v6.md` before any selector is fitted; the push commit is the lock timestamp. Predictions in §5 are recorded before any selector output is seen. Any change after this line is an amendment appended below §10, dated, marked pre- or post-results.

## 0. Note to the implementer

Rules of SPEC v3 and the correction spec apply. No engine runs. All inputs are in `data/spec_v5/results/rows.parquet` (V20 values, best_d, best_15_singlepv, covariates) and the v1 FENs. Nothing in this spec refits a mixed model. Every quantity is a mean or a difference of means with a game-clustered bootstrap. Before any selector is fitted, report on the §2 row set: N, mean L_h, and E_d for d in {2, 4, 8, 15}; these numbers are cited by §5 and must be in the report before the first fit.

## 1. Objective

SPEC v5 found that the conditional coupling between the human's move value and the shallow engine's move value is dominated by whether the human played the same move, and that the sign of the coupling flips on rows where the moves differ (results report, Exploratory X.a). Neither quantity answers the problem statement's question, which is about I(h | m): whether a rule that uses the human's judgment in some positions and the baseline's in the rest beats the baseline, and D(h | m): whether the human is a better second opinion than a reference source.

Two questions. Using only information available before the move and without any engine, can a selector identify positions in which the human's move should replace the depth-d engine's move, such that the combination has a lower mean loss than the depth-d engine alone? And is the human's move, so selected, a better second opinion than a deeper engine's move selected the same way?

## 2. Data

- **[LOCKED]** All 50,021 rows of the v1 dataset with V20 values, minus the 14 terminal rows and the 100 rows missing gap_12 or spread_15: N = 49,907. The two missing-feature rows are dropped even though the primary selector does not use those features, so that every version of the selector runs on the same rows.
- Ruler V20, anchor best_20, as Amendment A1. Losses: L_h = V20(best_20) − V20(h); L_d = V20(best_20) − V20(best_d) = e_d; L_15 = e_15 with best_15 = best_15_singlepv.
- Depths d in {2, 4, 8}. Depth 15 is the reference source, not a baseline.

## 3. Selector

- **[LOCKED]** Primary features, assistant-free, all available before the move without any engine: player_elo, opponent Elo, time_pressure, ply, material balance, number of pieces, and whether the side to move is in check (the last three computed from the FEN). No engine evaluation of any kind enters the primary selector. Root MultiPV quantities from the depth-15 search (wp_level, wp_level², gap_12, spread_15, n_reasonable, eval_volatility) are excluded from the primary analysis because a selector that sees depth-15 information is stronger than the baselines it is paired with; they are used only in robustness item 1.
- **[LOCKED]** Target per depth: the gain g_d(i) = L_d(i) − L_h(i), the loss saved by replacing the depth-d engine's move with the human's. Rows where h = best_d have g_d = 0 and stay in the training set with that value. This is a regression target; there is no class weighting.
- **[LOCKED]** Model: gradient-boosted regression trees (scikit-learn HistGradientBoostingRegressor), max_depth 4, learning_rate 0.05, max_iter 500, squared error. Early stopping on a validation set that the implementer constructs by holding out 10% of the training fold's games (split by game_id, seed 20261001) and passing explicitly; sklearn's row-level validation_fraction is not used. One model per depth. No tuning beyond these fixed settings.
- **[LOCKED]** Splits: 5-fold cross-validation with folds assigned by game_id (seed 20261001), so no game appears in both training and test folds. Every row's selector score ŝ_d(i) is the out-of-fold predicted gain.
- **[LOCKED]** Coverage rule: the combination uses the human's move on the rows with the top q share of out-of-fold predicted gain, q in {0.05, 0.10, 0.20, 0.30}, thresholds set within each test fold. q = 0.10 is the primary; the others are reported.
- **[LOCKED]** Reference selector: the same features, folds, model and coverage rule, with target g^ref_d(i) = L_d(i) − L_15(i), the gain from replacing the depth-d engine's move with the depth-15 engine's move. Its combination uses best_15 on the selected rows and best_d elsewhere.

## 4. Quantities

Per depth d and coverage q, on all N rows:

- Baseline loss: mean L_d.
- Human combination loss: mean over rows of [L_h if selected by the human selector else L_d].
- **Human increment**: G^h_d(q) = mean L_d − human combination loss. Positive means the combination beats the depth-d engine.
- **Reference increment**: G^ref_d(q), the same with the reference selector and best_15 on the selected rows.
- **Difference**: D_d(q) = G^h_d(q) − G^ref_d(q), the human's value as a second opinion relative to a deeper engine used the same way.
- **Random control**: G^rand_d(q), the human used on a random share q of rows (seed 20261001, 200 random selections; mean and 2.5/97.5 percentiles).
- **Oracle bound**: G^oracle_d(q), the top q share of rows by the true gain g_d.
- Selector quality: Spearman correlation between ŝ_d and g_d, and precision at q (share of selected rows with g_d > 0), both computed on the pooled out-of-fold scores of all N rows, not as a per-fold average.
- **[LOCKED]** Intervals: game-clustered percentile bootstrap, 2,000 draws, seed 20261001, resampling games and recomputing the means on the drawn rows with the fixed out-of-fold scores (the selectors are not refit inside draws; this is the standard for cross-fitted quantities and is stated as a limit). D_d(q) is bootstrapped as a difference within each draw.

## 5. Hypotheses and recorded predictions

- **S1.** G^h_2(0.10) > 0 with the bootstrap interval excluding zero. Prediction, recorded: passes. Reason: on the §2 rows E_2 is close to the human's mean loss (both reported in §0), so a selector that avoids the depth-2 engine's largest errors should beat it.
- **S2.** G^h_4(0.10) > 0 with the interval excluding zero. Prediction, recorded: fails (interval includes zero or G^h_4 ≤ 0).
- **S3.** G^h_8(0.10) ≤ 0 or interval includes zero. Prediction, recorded: no increment at depth 8.
- **S4.** G^h_d(0.10) − G^rand_d(0.10) > 0 at every depth with the interval excluding zero. Prediction, recorded: passes at all depths (the selector is better than random even where it does not beat the engine).
- **S5.** D_d(0.10) < 0 at every depth with the interval excluding zero. Prediction, recorded: passes at all depths (a depth-15 engine is a better second opinion than the human wherever the selector sends it). A failure at any depth would mean the human adds something a deeper search does not, and would be the result of this study.

**[LOCKED]** No other tests. Reading rule: sign and interval. The pre-registered results are S1 and S5; S2 to S4 are the recorded shape of the curve.

## 6. Descriptives

- G^h_d(q), G^ref_d(q), G^rand_d(q) and G^oracle_d(q) for all four q at all three depths, one figure.
- Permutation importance of the seven primary features per depth on the test folds, as a table, no interpretation.
- Coincidence: the share of selected rows where h = best_d, per depth and q, for the human selector.

## 7. Robustness (three items)

1. Selector with the depth-15 root MultiPV features added (wp_level, wp_level², gap_12, spread_15, n_reasonable, eval_volatility): the assisted version. S1 to S5 recomputed and reported next to the primary, labelled as using depth-15 information.
2. Ridge regression in place of gradient boosting, same features, folds and target.
3. Deviation rows only (the 28,647 v3 rows): S1 to S5 recomputed.

## 8. Deliverables

1. Table: per depth and q, baseline loss, human combination loss, G^h, G^ref, D, G^rand, G^oracle, Spearman, precision, all with intervals.
2. The §6 figure and tables.
3. The three robustness items.
4. Pass/fail line for S1 to S5.
5. Limits: one platform, fast time controls, titled players; selectors trained and tested on the same population; scores fixed inside bootstrap draws; the increment is on the ruler, which has about 1 WP point of resolution per row and is reliable in means; the reference source is one engine at one depth; the oracle bound selects rows by the true gain, which contains the ruler's roughly 1 WP point of noise per row, so the oracle is inflated by noise and is a loose upper bound.
6. Report to `reports/spec_v6_selector.md`; per-row scores to `data/spec_v5/results/selector/` (not committed). Nothing committed until the designer has read the report.

## 9. Parameters (confirmed 2026-09-28)

| Parameter | Proposed | Location |
|---|---|---|
| Row set | 49,907 (all rows minus terminal and missing-feature rows) | §2 |
| Primary features | Elo, opponent Elo, time_pressure, ply, material, pieces, in-check; no engine information | §3 |
| Target | regression on g_d = L_d − L_h; reference on L_d − L_15 | §3 |
| Model | HistGradientBoostingRegressor, depth 4, lr 0.05, 500 iters, game-level early-stopping set | §3 |
| Folds | 5, by game, seed 20261001 | §3 |
| Coverage | q = 0.10 primary; 0.05, 0.20, 0.30 reported | §3 |
| Reference source | best_15_singlepv, same selector procedure | §3 |
| Bootstrap | game-clustered, 2,000 draws, seed 20261001, scores fixed | §4 |
| Predictions | S1 pass; S2 fail; S3 no increment; S4 pass at all depths; S5 pass at all depths | §5 |

## 10. Expected cost

Feature construction from FEN: minutes. Selector fits: 2 selectors × 3 depths × 5 folds × up to 500 iterations on 40,000 rows, a few minutes each on one core. Bootstrap on means: minutes. Total under two hours of compute; one day including implementation and the report.

## Outcome (post-results), 2026-09-28

Source: `reports/spec_v6_selector.md` (results commit 165e9ad). §2 row set, 49,907 rows; primary assistant-free selectors (HistGradientBoostingRegressor as §3); q = 0.10; game-clustered percentile bootstrap, 2,000 draws, seed 20261001, out-of-fold scores fixed. WP points on the V20 ruler.

| Hypothesis | Estimate [95% interval] | Condition holds | Recorded prediction correct |
|---|---|---|---|
| S1: G^h_2(0.10) > 0, interval excluding zero | 0.0051 [−0.0121, 0.0223] | no | no |
| S2: G^h_4(0.10) > 0, interval excluding zero | −0.0095 [−0.0215, 0.0016] | no | yes |
| S3: G^h_8(0.10) ≤ 0 or interval including zero | −0.0523 [−0.0632, −0.0424] | yes | yes |
| S4: G^h_d(0.10) − G^rand_d(0.10) > 0 at every depth | d = 2: 0.0557 [0.0397, 0.0720]; d = 4: 0.0829 [0.0708, 0.0944]; d = 8: 0.1243 [0.1134, 0.1353] | yes | yes |
| S5: D_d(0.10) < 0 at every depth | d = 2: −0.2623 [−0.2916, −0.2338]; d = 4: −0.2239 [−0.2480, −0.1995]; d = 8: −0.1435 [−0.1588, −0.1285] | yes | yes |

S1 by selector model: with ridge regression in place of gradient boosting (§7 item 2; same features, folds and target; alpha 1.0, no tuning), G^h_2(0.10) = 0.0323 [0.0176, 0.0465], and the S1 condition holds. The pre-registered S1 result is the gradient-boosting selector's: the condition does not hold. S2 to S5 are the same under ridge.
