# SPEC v5 Amendment A1: depth-20 evaluations, all rows

Spec: `specs/paper4_spec_v5.md`, Amendment A1 (880423e) and A1.4 outcome (b735062). nproc = 6, MultiPV 5, Threads 1, Hash 128, ucinewgame per search. Nothing from §6 or §7.

## 1. Batches

| Batch | Positions | Evaluations run (engine / terminal) | Wall (h), logged | System sleep in batch (h) | Wall (h), excluding sleep | Wall s per engine evaluation, excluding sleep |
|---|---|---|---|---|---|---|
| A1_d20_h | after h | 48,011 / 10 | 17.80 | 0.00 | 17.80 | 1.335 |
| A1_d20_best20 | after best_20 | 26,858 / 2 | 10.49 | 0.00 | 10.49 | 1.406 |
| A1_d20_best2_4_8 | after best_2, best_4, best_8 | 37,104 / 0 | 16.65 | 1.22 | 15.43 | 1.497 |
| A1_d20_best12_15 | after best_12, best_15 | 5,916 / 0 | 2.30 | 0.00 | 2.30 | 1.400 |
| Total | | | 47.24 | 1.22 | 46.02 | |

Sleep source: `pmset -g log`, 2026-09-26 11:09:00 to 12:22:17 UTC (low-power sleep on battery at 1%); the run process was paused, not restarted, and no shard was lost. No other sleep in the run window.

## 2. Study store, depth 20

| Batch | Evaluations |
|---|---|
| A1_check_d20 | 512 |
| A1_d20_best12_15 | 5,916 |
| A1_d20_best20 | 26,860 |
| A1_d20_best2_4_8 | 37,104 |
| A1_d20_h | 48,021 |
| pilot_sub_d20 | 3,804 |
| timing_d20 | 50 |
| Total depth-20 | 122,267 |
| of which terminal (by rule, no engine call) | 14 |
| Depth-25 (A1.4 check) | 2,432 |
| Depth-15 (pilot) | 40,421 |

Depth-20 positions required by A1 (`A1_tasks.parquet`, 122,267 distinct) missing from the store: 0.
