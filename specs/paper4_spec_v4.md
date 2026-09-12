# SPEC v4: Is the Return to Deviation a Stable Player Attribute?

Status: LOCKED 2026-09-11. The lock takes effect at the commit that adds this file to `chess-behavioral-lab/specs/`, which must precede any analysis run.

## 0. Note to the implementer

Rules of SPEC v1 through v3 apply. Reuse the v3 analysis table (`p4_v3_rows_analysis.parquet`, 28,603 rows) unchanged. No engine work. Work in `~/Desktop/chess-study/`; code and report go to the public repo.

## 1. Objective

The forecasting study found that a forecaster's gain over the model is a stable individual attribute (split-half r = 0.78 for superforecasters, 0.64 for the public; forecaster variance share 4.1%). This SPEC asks the same question of chess: is the opponent's excess error after a player's deviation (`RES`, the v3 §5 quantity) a property of the player, and separately, is the player's preference for sharpness (`ΔRISK_steep`) a property of the player.

The two quantities are reported side by side because they answer different questions. `ΔRISK_steep` is what the player chooses; `RES` is what the choice returns. A trait in the first without a trait in the second would say that players differ reliably in how they deviate but not in whether it pays.

## 2. Sample

- **[LOCKED]** Roster players only (the 630 `player_id`s in `analysis_dataset_male_titled_raw.csv`, matched case-insensitively, the rule `paper4_report.py` already uses). Non-roster opponents have too few rows (median 5) and are excluded.
- **[LOCKED]** All deviation rows of roster players with non-missing `RES`, without the (0, 5] band restriction. The band served the v3 hypothesis tests; a reliability question wants every row. Report the row count per player (min, quartiles, max) and the number of players with at least 20 rows.

## 3. Primary: variance share

For each of `RES` and `ΔRISK_steep` as the dependent variable:

```
y ~ WPL_self_z + gap_12_orig_z + eval_volatility_z + time_pressure_opp_z + elo_diff_opp_z
    + (1 | player_id) + (1 | game_id)
```

- Same covariates as v3 H2, so the player intercept captures what is left after position difficulty and the size of the deviation. Estimated with v1's `fit_mixed` (Amendment 2 of v3 applies; the nesting approximation is flagged in the table).
- **[LOCKED]** Core quantity: the player variance share, `var(player) / (var(player) + var(game) + residual)`, with a 95% interval from a cluster bootstrap over games (2,000 draws, seed 20260912). Also report a likelihood-ratio test of the player intercept against the model without it.
- Report the forecasting study's 4.1% next to the `RES` share, and say that the two are not on identical scales.

## 4. Secondary: split-half, descriptive

- Players with at least 20 rows. Split each player's rows into two halves by a fixed random assignment of games (seed 20260912, the same assignment for every player; a game's rows go to the same half so that the two halves share no game).
- Per player, mean residual `y` in each half, where the residual is from the §3 fixed-effects part only (no player intercept), so that position difficulty is removed before averaging.
- Report Pearson and Spearman correlations across players between the half-means, with bootstrap 95% intervals over players (2,000 draws), for `RES` and for `ΔRISK_steep`. Report the Spearman-Brown correction as a descriptive.
- **[LOCKED]** This is descriptive. The primary quantity is §3. With a median of about 15 rows per player and a per-row SD of about 4.5 WP for `RES`, the split-half will be attenuated, and the report says so.

## 5. Robustness (one item)

Restrict to the (0, 5] band and rerun §3. Purpose: does the variance share depend on the band the v3 tests used.

## 6. Deliverables

1. Row counts per §2.
2. §3 tables for both dependent variables: variance components, share with bootstrap interval, LR test, the Amendment 2 flag.
3. §4 correlations with intervals, both variables.
4. §5.
5. One figure: half-means scatter for `RES` and for `ΔRISK_steep`, side by side, same axes.
6. One paragraph: what the comparison of the two shares says, in the reading fixed in §1.

## 7. Stop rule

Stop after delivery. The result goes into the next version of Paper 4 as an exploratory section, or into the problem statement's open question 2, at the designer's decision.
