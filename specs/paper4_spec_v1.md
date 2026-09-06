# SPEC: Human–Engine Deviation and Complementarity Analysis (Paper 4 groundwork)

## 0. Note to the implementer

Every parameter marked **[LOCKED]** is a research-design decision, not an implementation detail.
Do not "optimize" it, substitute it, or change it because the job is slow. If you believe a
LOCKED parameter is wrong, **stop and state your reasoning in the report. Do not change it and
keep running.**

Everything else (code structure, parallelization strategy, storage details) is your call.

---

## 1. Objective

Quantify the structure of human middlegame deviation from an engine baseline, and test one
specific hypothesis:

> Do human moves the engine considers suboptimal, in some contexts, increase the opponent's
> subsequent error rate?

If yes, human judgment carries information absent from the engine's objective function
(opponent fallibility), which is direct evidence of human–AI complementarity. If no, that is a
valuable null result and should be reported as such.

---

## 2. Inputs

- The existing Paper 1 PGN dataset and python-chess pipeline.
- **[LOCKED]** The middlegame boundary definition **must reuse the existing Paper 1 function**.
  Do not redefine it. State the function name and file location in the report.
- Required fields: both players' Elo, game result, and PGN `%clk` where present.

---

## 3. Engine configuration

- Engine: Stockfish. **Report the exact version and build**; reproducibility depends on it.
- **[LOCKED]** Fixed `depth = 15`. **Do not use fixed time (movetime).** Wall-clock budgets
  vary with machine load and make results non-reproducible.
- **[LOCKED]** `MultiPV = 5`.
- Per worker: `Threads = 1`, `Hash = 128`. Parallelize with multiple processes, not one
  multi-threaded instance.
- **[LOCKED]** Evaluate each position independently. Do not reuse the previous search tree
  (no `go ponder`, no incremental analysis).

---

## 4. Position selection

- **[LOCKED]** Take **all middlegame moves by both sides**, not only the target player's.
  The core test in §7.2 requires the opponent's deviation; half the data makes it impossible.
- **[LOCKED]** If a game has more than 30 middlegame moves, sample 30 at even intervals;
  otherwise take all.
- Record the ply index for every move. Later analysis pairs each move with the opponent's
  next move by ply.

---

## 5. Quantities to compute per position

### 5.1 Win-probability conversion

- **[LOCKED]** Convert all centipawn values to win probability *before* differencing. Centipawns
  are strongly non-linear at evaluation extremes; differencing raw cp conflates a small error in
  a winning position with a large error in a balanced one.
- **[LOCKED]** Conversion (Lichess standard):

  ```
  WP(cp) = 50 + 50 * (2 / (1 + exp(-0.00368208 * cp)) - 1)
  ```

- All cp values are taken **from the side-to-move's perspective**. Write an explicit test for
  this: sign errors are the most common silent bug in this kind of pipeline and will invert
  every conclusion.
- Mate scores: **[LOCKED]** map to cp = ±10000, then convert.

### 5.2 Deviation measure (dependent variable)

- `WPL` = WP(engine's top choice) − WP(move actually played). Units are win-probability
  percentage points; non-negative.
- **[LOCKED]** Winsorize the top 1% of `WPL` at the full-sample level. A handful of blunders
  otherwise dominates the variance and every effect ends up hostage to the tail. Keep the
  untreated column `WPL_raw` for sensitivity analysis.

### 5.3 Position complexity (critical control)

**Why this section is mandatory:** `WPL` primarily measures *position difficulty*, not judgment
quality. The same player will show higher `WPL` in sharp positions. Without controlling for
complexity, an apparent "skill effect" is largely "style differences producing different
position distributions."

**[LOCKED]** Four proxies, all computed **at the position level** and entered as covariates.
Do **not** average them to the player level first and then compare.

| Variable | Definition |
|---|---|
| `gap_12` | WP(1st choice) − WP(2nd choice) |
| `spread_15` | WP(1st choice) − WP(5th choice) |
| `n_legal` | Number of legal moves |
| `n_reasonable` | Count of the MultiPV-5 lines within 5 WP points of the top choice (**right-censored at 5; this must be flagged in the report**) |

Plus:
- `eval_volatility` = |WP(current position) − WP(position two plies earlier)|, computed from
  the sequence.

### 5.4 Time pressure

- Where PGN has `%clk`: `time_pressure` = time remaining at that move / initial time. Record
  the increment.
- **[LOCKED]** Where `%clk` is absent, **exclude the whole game** from time-pressure analyses.
  Do not impute. Report the excluded proportion.

---

## 6. Output structure

Long format, **one row per position-move**. Minimum fields:

```
game_id, ply, side_to_move, player_id, opponent_id,
player_elo, opponent_elo, elo_diff,
fen_hash, move_played, move_engine_best,
wp_best, wp_played, WPL, WPL_raw,
gap_12, spread_15, n_legal, n_reasonable, eval_volatility,
time_pressure, has_clk,
game_result, result_for_side_to_move,
sf_version, depth, multipv, analysis_timestamp
```

- **[LOCKED]** Write Parquet shards (bucketed by a hash of `game_id`). Not one giant CSV.
- **[LOCKED]** Resumability: `(game_id, ply)` is the unique key; on restart, skip completed
  entries. The full job runs for hours and must survive interruption.

---

## 7. Analysis

### 7.1 Deviation-structure model

Linear mixed-effects model:

```
WPL ~ elo_z + gap_12_z + spread_15_z + n_legal_z + eval_volatility_z
      + time_pressure_z
      + elo_z:gap_12_z + elo_z:time_pressure_z
      + (1 | player_id) + (1 | game_id)
```

- Random intercepts are `player_id` and `game_id`. A position-level random intercept is not
  identifiable (one observation per position); complexity enters as fixed-effect covariates.
- Paper 1's style vector may be added as a player-level covariate to link the two papers.
- Standardize all continuous predictors; report standardized coefficients with 95% CIs.

### 7.2 Core complementarity test

**[LOCKED]** This section carries the paper. Do not let "humans deviate from the engine" stand
in as the finding. Deviation is suboptimality, not complementarity.

Test target: does a player's engine-suboptimal move raise the **opponent's `WPL` on the next
move**?

```
WPL_opponent_next ~ WPL_self_z * gap_12_z * elo_diff_z
                    + n_legal_z + eval_volatility_z + time_pressure_z
                    + (1 | player_id) + (1 | game_id)
```

- A positive coefficient on `WPL_self_z` is the complementarity evidence: deliberately entering
  positions the engine dislikes but where the opponent is more error-prone.
- **[LOCKED]** Also report a game-outcome version (logistic mixed model, DV
  `result_for_side_to_move`), but **state explicitly that its causal interpretation is limited**:
  the outcome is game-level while the move is ply-level, so no causal claim is licensed.
  Opponent next-move `WPL` is the cleaner mechanism variable and is the primary result.
- **[LOCKED]** Do not slice subgroups repeatedly looking for significance. The models above are
  pre-specified; report what they give.

---

## 8. Execution order and compute

### 8.1 Pilot first, do not go straight to full sample

- **[LOCKED]** Random sample of 2,000 games, `random_seed = 20260823`. Record the sampled
  `game_id` list.
- Once the pilot runs clean, **stop.** Return the §9 deliverables. Full-sample execution waits
  for confirmation that the pipeline is correct and the effect directions make sense.

### 8.2 Realistic compute estimate

- Full sample: ~59,425 games × ~30 moves ≈ 1.8M engine calls.
- At depth 15 with MultiPV 5, roughly 80–150ms per position.
- ~40–75 hours single-core; ~5–9 hours on 8 processes.
- Pilot (2,000 games) on 8 processes: ~10–20 minutes.
- If measured per-position time falls well outside that range, **stop and report**. It usually
  means the engine is misconfigured.

---

## 9. Pilot deliverables (return these before scaling up)

1. Environment and versions: Stockfish version, python-chess version, core count, measured
   per-position time.
2. Data integrity: games processed, positions analyzed, failures/skips with reasons, proportion
   of games lacking `%clk`.
3. `WPL` distribution: histogram plus quantile table, before and after winsorization.
4. Sign check: 20 randomly sampled positions listed human-readably (FEN, engine top choice,
   move played, both WP values, `WPL`) so the perspective and sign can be verified by eye.
5. Binned mean `WPL` against Elo (100-Elo bins), with and without complexity controls.
6. Correlation matrix among the four complexity proxies, to judge whether collinearity requires
   collapsing any of them.
7. Coefficient tables for the §7.1 and §7.2 models on the pilot sample.
8. Proportion of positions where `n_reasonable` hits the censoring value of 5.

---

## 10. Non-negotiables, summarized

- Do not change any [LOCKED] parameter; if you disagree, stop and say so.
- Fixed depth, never movetime.
- Convert cp to win probability before differencing.
- Control complexity at the position level.
- Reuse the existing Paper 1 middlegame definition.
- Pilot before full sample.
- Report null results as they come; no subgroup fishing.
