# SPEC v5: Engine Depth as a Knob on Baseline Fallibility

Status: LOCKED 2026-09-22. All §10 parameters confirmed by the designer on 2026-09-22. Pushed to `chess-behavioral-lab` as `specs/paper4_spec_v5.md` before any engine run at depths other than 15; the push commit is the lock timestamp. Any change after this line is an amendment appended below §11, dated, marked pre- or post-results. Drafting history: the first draft's H1 was an identity and its H2 was confounded by engine error (see §1); draft 2 replaced them with the conditional-error design; drafts 3 and 4 added the noise benchmark, the common row set, the λ_d floor, and the difference-based comparison rule.

## 0. Note to the implementer

Rules of SPEC v3 and the correction spec apply. The v1 dataset (50,021 moves, 1,970 games) and the v2/v3 depth-15 evaluations are the fixed inputs; nothing at depth 15 is rerun except the single-PV root search of §3. New engine evaluations are logged with engine version, depth, and hash. `fit_mixed_v2` is the only mixed-model estimator allowed.

## 1. Objective

Paper 4 measured what a human adds to an engine that is strictly stronger and almost never wrong about the position, and found no return. The forecasting and image studies measured what a human adds to a model that is wrong about the outcome, and found a return. The problem statement's conjecture is that the human's increment is bounded by the kind of error the baseline makes.

This study varies the baseline's estimation error by design, inside one domain, by making the engine search less deeply. The question is not whether a human beats a shallow engine on average. That is an identity: with the human's move fixed and the ruler fixed at depth 15, the substitution gain I_d = V15(h) − V15(best_d) decomposes row by row as e_d − L_h, where e_d = V15(best_15) − V15(best_d) is the shallow engine's error and L_h = V15(best_15) − V15(h) is the human's loss, so mean I_d rises with mean e_d at slope exactly one and crosses zero at the human's mean loss against depth 15, a number already in hand. The first draft of this specification proposed that as H1; it is retained only as a descriptive with the identity stated.

The question with content is whether the human and the shallow engine err in the same places. Two hypotheses:

- H1. Is the human's loss against depth 15 smaller where the shallow engine's error is larger? Both err more in hard positions, so the raw slope of human loss on engine error is expected to be positive; the benchmark of independence is a zero slope after position difficulty is held fixed. A negative conditional slope is the strong prediction: the human does not fail where the engine fails. How that slope changes with depth is the test of the conjecture. The v3 difficulty features were built to predict the opponent's error; they are used here for the mover's difficulty on the assumption that the same position features drive both, and that assumption is stated as a limit.
- H2. Holding the engine's error fixed, is the human's loss smaller where the engine's error is a visible one, a move refuted by a forcing sequence, than where it is a quiet misjudgment?
- H3 (descriptive). How H1 and H2 vary with player rating and clock.

## 2. Data

- **[LOCKED]** All 50,021 moves of the v1 dataset, not the 28,647 deviation rows. Deviation was defined relative to depth 15; the row set must not depend on the knob.
- Fixed inputs from v2/v3: for every row, the depth-15 MultiPV-5 at the root; for deviation rows, the depth-15 evaluation of the position after the human's move and after `best_15`.
- Engine: the same Stockfish build as v2/v3, hash recorded. **[LOCKED]** Threads = 1, a fixed Hash size (the v2/v3 value), and `ucinewgame` before every search, so that `best_d` is reproducible and independent of search order.

## 3. The knob and the truth

- **[LOCKED]** Baseline depths: 4, 8, 12. At each depth d, `best_d` is the first choice of a single-PV root search. Depth 15 is the fourth point.
- **[LOCKED]** Baseline consistency: `best_15` from v2/v3 came from a MultiPV-5 search, which changes the search itself. A single-PV root search at depth 15 is run on all rows (short) and its first choice is compared with the MultiPV `best_15`; the agreement rate is reported. The single-PV choice is `best_15` for this study, so that all four points are produced the same way. Where it differs from the MultiPV choice and its successor was not evaluated in v2/v3, the successor is evaluated at depth 15.
- **[LOCKED]** Truth is the depth-15 evaluation throughout. V15(x) is the win probability, from the mover's side, after move x, from a separate depth-15 evaluation of the position after x. Root MultiPV scores are never substituted (a child inside a root search is searched one ply less, and the rows where `best_d` falls outside the root's top five are the rows with the largest engine error, so the substitution would bias exactly where it matters). This matches the v2/v3 treatment of deviation rows.
- **[LOCKED]** Truth check: a random 2,000 rows (seed 20261001) are also evaluated at depth 20 for the positions after the human's move, after `best_15`, and after `best_4`, `best_8` and `best_12` wherever those differ from moves already evaluated (at most a few thousand evaluations). Report V20 − V15 for each position type: its SD, and its mean by HORIZON group (§4) for each shallow depth's positions. Pass rules: the largest SD is below one quarter of SD(e_4) on the subsample; and at every depth the absolute difference of the two HORIZON-group means of V20 − V15 is below 0.25 × SD(e_d) on the subsample (an absolute bound, because at depth 12 the disagreement rows in the subsample are few and an interval rule would pass by lack of power). If the SD rule fails, depth 20 becomes the truth for the whole study by amendment; if the HORIZON rule fails at a depth, H2 is demoted to descriptive at that depth by amendment.
- **[LOCKED]** Noise benchmark, computed on the subsample for each shallow depth d, with `n15` = V20 − V15 at the `best_15` positions and `nd` = V20 − V15 at the `best_d` positions:
  - Shared-term bias, affecting the raw slope of L_h on e_d: `b_d = Var(n15) / Var(e_d)`. The noise-implied raw slope is `+b_d`; the observed raw slope is reported next to it.
  - Attenuation, affecting the primary H1 coefficient: `λ_d = 1 − Var(nd) / Var(u_d)`, where `u_d` is the residual of V15(best_d) regressed on V15(best_15) and the H1 covariates on the subsample. Measurement error in V15(best_d) multiplies the true coefficient by about λ_d.
  - Floor on λ_d: a depth with λ_d below 0.5 does not enter the disattenuated comparison. Its raw β_d is reported with that note, and the depth is excluded from the cross-depth H1 conclusion. Without this floor, a small Var(u_d) at the deepest baseline can make λ_d near zero or negative and β_d / λ_d meaningless.
  - Comparison rule: the observed primary coefficient at each admitted depth is divided by λ_d (`β_d / λ_d`). The conjecture is supported only if the difference of disattenuated coefficients between the shallowest and the deepest admitted depth, `β_4/λ_4 − β_D/λ_D`, has the predicted sign (negative) and a game-clustered joint bootstrap interval on that difference (β and λ resampled together) that excludes zero. This is the sign-and-interval reading of the correction spec applied to the difference, not to overlap of separate intervals.
  Both effects are largest where Var(e_d) is smallest, i.e. at the deepest baseline, so without this correction a coefficient that moves toward zero as depth increases is what noise alone produces.

## 4. Quantities

Per row i and depth d:

- `L_h(i) = V15(best_15) − V15(h)`. The human's loss against the depth-15 engine. Zero where the human played `best_15`. Fixed across d.
- `e_d(i) = V15(best_15) − V15(best_d)`. The depth-d engine's error on the fixed ruler. Zero where the shallow engine agrees with depth 15.
- `I_d(i) = V15(h) − V15(best_d) = e_d(i) − L_h(i)`. The substitution gain. Descriptive only, with the identity stated wherever it appears. It has no recalibration term and no combiner; it is not the I(h \| m) of the problem statement and does not enter the measurement package.
- `E_d = mean e_d`. The depth-d engine's error rate, the x axis for descriptives.
- `HORIZON(i, d)`, computed on the depth-15 principal variation from the position after `best_d`, for rows with `best_d ≠ best_15`. Let P0 be that position and let Pq be the first position on the PV, at or after ply k, that is reached by a move that is neither a capture nor a check (the end of the forcing sequence). HORIZON = 1 if a check occurs within the first k plies of the PV, or if the material balance at Pq differs from the balance at P0; else 0. An even exchange completed within the PV leaves the balance unchanged and does not count. The shallow engine's error is visible when its move is refuted by force. **[LOCKED]** k = 6 initially; the pilot reports the HORIZON = 1 share among `best_d ≠ best_15` rows at depth 12, and if it is above 80% or below 20%, k is changed by amendment before depths 8 and 4 run, to the value in {2, 4, 6, 8, 10} that brings the share closest to 50%.
- Existing covariates: Elo, opponent Elo, clock remaining, ply, difficulty features (v3).

New depth-15 evaluations needed: (a) the position after the human's move on the 21,374 non-deviation rows, once, shared across depths; (b) per depth, the position after `best_d` on every row where `best_d` differs from both the human's move and `best_15`; (c) any single-PV `best_15` successor not already evaluated (§3). The implementer counts (a), (b) per depth and (c) before running anything and reports them.

## 5. Pilot

**[LOCKED]** Two parts. (a) Depth 12 on all rows: E_12, the distributions of e_12 and I_12, the count of rows with `best_12 ≠ best_15`, the HORIZON = 1 share, and the single-PV/MultiPV agreement rate at depth 15. (b) The full depth-4 procedure on the 2,000-row truth-check subsample (seed 20261001): depth-4 root search, depth-15 evaluation after `best_4` where needed, and the depth-20 evaluations, the SD rule, the depth-4 HORIZON rule, and λ_4 of §3. Deliver both; stop. If fewer than 5% of rows have `best_12 ≠ best_15`, depth 12 is replaced by depth 10 by amendment before depths 8 and 4 run.

## 6. Hypotheses

- **H1.** Per depth d in {4, 8, 12}. **Primary specification:** the mixed model `V15(h) ~ V15(best_d) + V15(best_15) + difficulty_z + clock_z + elo_z + (1 \| player) + (1 \| game)`, `fit_mixed_v2`, one fit per depth. Entering V15(best_15) as its own regressor takes the shared term out of both sides, so the coefficient on V15(best_d) is the conditional relation between the human's outcome and the shallow engine's outcome with the shared measurement error controlled. The quantity is that coefficient; a positive coefficient means the human's move is worse exactly where the shallow engine's move is worse, holding the depth-15 value and difficulty fixed. Prediction, recorded in advance: the coefficient is smaller (closer to zero, or negative) at depth 4 than at depth 12, by more than the reliability ratio of §3 accounts for. **Secondary, reported alongside:** (i) the primary model refitted at all three shallow depths on the **common row set** `{best_12 ≠ best_15}`, the smallest of the three disagreement sets, so that the change across depths is estimated on one fixed set of positions and the composition effect (deeper baselines disagree only on the hardest positions) is separated from the depth effect; (ii) the raw slope of `L_h` on `e_d` across all rows, the binned E[L_h \| e_d] in deciles among rows with e_d > 0, and the covariate-adjusted `L_h ~ e_d_z + difficulty_z + clock_z + elo_z + (1 \| player) + (1 \| game)`; game-clustered bootstrap intervals (2,000 draws, seed 20261001) on all of them.
- **H2.** Per depth, on rows with `best_d ≠ best_15`: the mixed model `L_h ~ HORIZON + e_d_z + difficulty_z + clock_z + elo_z + (1 \| player) + (1 \| game)`, `fit_mixed_v2`. The HORIZON coefficient is the quantity; e_d is a covariate here because HORIZON = 1 rows have larger e_d by construction and the question is what the visibility of the error adds at a fixed size of error. Prediction, recorded: negative, the human's loss is smaller where the engine's error is a visible one. A second outcome, whether the human's move equals `best_d` (the human repeats the engine's mistake), is fitted with the same `fit_mixed_v2` as a linear probability model and reported alongside; no other estimator is introduced.
- **H3 (descriptive, no test).** The H1 slope and the H2 coefficient by Elo tercile and clock tercile at each depth.
- **Descriptives.** Mean I_d against E_d at the four depths with intervals, the identity I_d = e_d − L_h stated in the caption, and the crossing E* = mean L_h reported as what the identity implies rather than as a finding.

**[LOCKED]** No other tests. The reading rule of the correction spec applies: sign and interval.

## 7. Robustness (three items)

1. HORIZON with k − 2 and k + 2, where k is the value in force after the pilot.
2. H1 and H2 on the depth-20 truth for the 2,000-row subsample, at all three shallow depths (the truth check of §3 evaluates the `best_d` positions at every depth, so this is computable).
3. Deviation rows only (the 28,647), to show how the selection changes the answer.

## 8. Deliverables

1. Engine version, hash, per-depth evaluation counts and runtimes; the single-PV/MultiPV agreement rate at depth 15.
2. Truth check: V20 − V15 by position type and depth, SDs, the HORIZON-group mean differences against the absolute bound, b_d and λ_d per depth, pass/fail on both rules.
3. H1: the primary coefficient per depth, raw and disattenuated, with joint-bootstrap intervals; the common-row-set refit; the figure of disattenuated coefficient against depth; the secondary slopes and binned means with b_d next to the raw slope.
4. H2: HORIZON coefficients per depth for both outcomes, with intervals.
5. H3 tables.
6. The descriptive I_d curve with the identity stated.
7. The three robustness items.
8. Limits: one platform, fast time controls, titled players; depth 15 as truth; HORIZON is a proxy for visibility, not a measure of what the player saw; the human's move is fixed, so nothing here measures what a human would do when shown a shallow engine.

## 9. Stop rule

Stop after the pilot. Stop after the full run. The designer decides whether this becomes a section of Paper 4 or a separate short paper.

## 10. Parameters (confirmed 2026-09-22)

| Parameter | Proposed | Location |
|---|---|---|
| Baseline depths | 4, 8, 12; depth 10 replaces 12 by amendment if fewer than 5% of rows disagree at 12 | §3, §5 |
| best_15 for this study | single-PV depth-15 root choice, agreement with MultiPV reported | §3 |
| Truth | depth 15; depth 20 on 2,000 rows for h, best_15, best_4, best_8, best_12 | §3 |
| Truth-check rules | max SD(V20 − V15) < 0.25 × SD(e_4); HORIZON-group mean difference of V20 − V15 below 0.25 × SD(e_d) at every depth | §3 |
| Noise benchmark | b_d and λ_d as defined; λ_d < 0.5 excludes the depth; H1 compared on the difference β_4/λ_4 − β_D/λ_D with joint bootstrap | §3 |
| Common row set for H1 | {best_12 ≠ best_15} at all three depths, secondary | §6 |
| HORIZON | check within k plies, or material balance changed at the first non-forcing PV position at or after ply k; k = 6, pilot share rule | §4 |
| Row set | all 50,021 | §2 |
| Pilot | depth 12 on all rows; full depth-4 procedure on the 2,000-row subsample | §5 |
| H1 quantity | coefficient on V15(best_d) with V15(best_15) as regressor, per depth, disattenuated by λ_d, change across depths | §6 |
| H2 quantity | HORIZON coefficient with e_d as covariate; second outcome P(h = best_d) as a linear probability model | §6 |
| Bootstrap | game-clustered, 2,000 draws, seed 20261001 | §6 |
| Engine settings | Threads = 1, fixed Hash, ucinewgame per search | §2 |

## 11. Expected cost

Root searches at depths 4, 8, 12 on 50,021 positions: minutes each; single-PV depth-15 root search on 50,021 positions: under an hour. New depth-15 evaluations: 21,374 for the human's move on non-deviation rows, once; per depth, every row where `best_d` differs from both the human's move and `best_15`, largest at depth 4; plus any single-PV `best_15` successors not already evaluated. Depth-20 evaluations: 6,000 plus the best_8 and best_12 positions on the subsample where they differ, at most a few thousand more. Total engine time on 8 processes at 1 thread each: two to four days, to be revised after the count.
