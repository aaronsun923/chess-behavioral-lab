# SPEC v4-A: effective depth

Pre-lock. No specification file exists yet for v4-A; this report holds descriptive counts requested before the lock.

## Step 0. Players as the mover (descriptive)

Rows: the SPEC v5 row table (`data/spec_v5/results/rows.parquet`, 50,021 rows) minus the 14 terminal rows (the position after best_20 is checkmate or a draw by rule; the same 14 rows as SPEC v6 §0, which contain the 12 rows with a terminal position after h) = **50,007 rows**, 1,970 games. The 100 rows missing gap_12 or spread_15 are kept.

Grouping: the mover's `player_id` (the side to move in the v1 row). A player's games as the mover = the number of distinct game_ids in which that player made at least one of these moves. Players: **2,317**.

| Games as the mover | Players |
|---|---|
| ≥ 1 | 2,317 |
| ≥ 2 | 670 |
| ≥ 4 | 253 |
| ≥ 8 | 13 |
| ≥ 12 | 1 |
| ≥ 16 | 0 |
| ≥ 24 | 0 |

Rows per player (moves as the mover, 2,317 players):

| Min | 25th percentile | Median | 75th percentile | Max |
|---|---|---|---|---|
| 2 | 13 | 13 | 26 | 156 |

No agreement rates or correlations are computed in this step.

## Decision, 2026-09-28

Insufficient sample: 13 players have at least 8 games as the mover and 0 have at least 16 (Step 0). The data were sampled by game, not by player, so per-player depth of play is thin. Under the threshold rule drafted for SPEC v4-A, the reliability study is not run on this data. No reliability coefficient is computed and no specification is locked. Per-player reliability of the effective-depth metric will be tested on profile-tool data (Lichess users with at least 100 games) under SPEC v4.
