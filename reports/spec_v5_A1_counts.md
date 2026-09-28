# SPEC v5 Amendment A1: depth-20 and depth-25 counts and cost

Spec: `specs/paper4_spec_v5.md`, Amendment A1 at 880423e. A1.7 steps run: depth-2 root search, depth-20 root search, throttling check. Engine, settings and root input as the pre-run count §1 (Stockfish 18, SHA-256 `bc0cac905ecdf214…`, Threads 1, Hash 128, ucinewgame per search). The depth-25 check and the depth-20 evaluations have not been run.

## 1. Root searches (single-PV, all 50,021 positions)

| Depth | Searches | Wall time (min, 8 processes) | Engine time, mean per search (s) | Rows with best_d = best_20 |
|---|---|---|---|---|
| 2 | 50,021 | 1.2 | 0.0113 | 24,781 (0.4954) |
| 20 | 50,021 | 227.4 | 2.1754 | — |
| 4 (from the pre-run count) | | | | 26,065 (0.5211) |
| 8 (from the pre-run count) | | | | 31,744 (0.6346) |
| 12 (from the pre-run count) | | | | 37,607 (0.7518) |
| 15 (from the pre-run count) | | | | 41,249 (0.8246) |

Columns best_2 and best_20 added to `data/spec_v5/root_choices.parquet` (earlier columns unchanged; previous file kept as `root_choices_preA1.parquet`). best_15 here is best_15_singlepv. Rows with best_20 = h: 22,164.

## 2. Throttling check (A1.6)

200 depth-20 positions from the study store (study store, batch pilot_sub_d20, non-terminal, sample(seed 20261001)), re-run at nproc = 6 and then nproc = 8, back to back; results in `data/spec_v5/checks/`, not in the study store.

| nproc | Batch wall (s) | Wall s per evaluation | Evaluations per hour | Engine s per evaluation, mean | median | Positions differing from store (5 WP values, 5 moves, nodes) |
|---|---|---|---|---|---|---|
| 6 | 307.7 | 1.538 | 2,340 | 9.148 | 8.842 | 0 |
| 8 | 306.9 | 1.534 | 2,346 | 12.131 | 11.706 | 0 |

Faster: nproc = 8.

## 3. Evaluation counts

"In store" = already evaluated at depth 20 in the pilot (subsample: after h, best_15, best_4). Terminal = checkmate or draw after the move; no engine call.

| Item | Definition | Rows | In store | Terminal | Engine evaluations |
|---|---|---|---|---|---|
| depth 20: h | position after h, all rows | 50,021 | 2,000 | 12 | 48,011 |
| depth 20: best_20 | best_20 ≠ h | 27,857 | 893 | 2 | 26,962 |
| depth 20: best_2 | best_2 ≠ h and best_2 ≠ best_20 | 18,953 | 323 | 0 | 18,630 |
| depth 20: best_4 | best_4 ≠ h and best_4 ≠ best_20 | 18,620 | 756 | 0 | 17,864 |
| depth 20: best_8 | best_8 ≠ h and best_8 ≠ best_20 | 13,991 | 248 | 0 | 13,743 |
| depth 20: best_12 | best_12 ≠ h and best_12 ≠ best_20 | 9,446 | 198 | 0 | 9,248 |
| depth 20: best_15 | best_15 ≠ h and best_15 ≠ best_20 | 6,641 | 295 | 0 | 6,346 |
| depth 20: total | distinct (row, move), not in store, non-terminal | | | | 118,401 |
| depth 25: first counted as h | first 1,000 subsample rows in draw order, distinct positions | 1,000 | | 2 | 998 |
| depth 25: first counted as best_20 | first 1,000 subsample rows in draw order, distinct positions | 551 | | 0 | 551 |
| depth 25: first counted as best_2 | first 1,000 subsample rows in draw order, distinct positions | 386 | | 0 | 386 |
| depth 25: first counted as best_4 | first 1,000 subsample rows in draw order, distinct positions | 215 | | 0 | 215 |
| depth 25: first counted as best_8 | first 1,000 subsample rows in draw order, distinct positions | 162 | | 0 | 162 |
| depth 25: first counted as best_12 | first 1,000 subsample rows in draw order, distinct positions | 66 | | 0 | 66 |
| depth 25: first counted as best_15 | first 1,000 subsample rows in draw order, distinct positions | 52 | | 0 | 52 |
| depth 25: total | | 2,432 | | 2 | 2,430 |

Per-item list: `data/spec_v5/A1_tasks.parquet`.

## 4. Cost at the sustained rate

| Run | Engine evaluations | Wall s per evaluation (nproc = 8) | Hours |
|---|---|---|---|
| Depth-20 evaluations | 118,401 | 1.534 (throttling check) | 50.5 |
| Depth-25 check | 2,430 | 10.742 (extrapolated) | 7.3 |

Depth-25 rate: no depth-25 search has been run (A1.7). It is the throttled depth-20 rate × 7.00, the ratio of mean engine seconds at depth 20 to depth 15 on the 2,170 positions evaluated at both depths in the pilot (depth-15 mean 1.456 s, depth-20 mean 10.196 s), i.e. the same growth per five plies from 20 to 25 as from 15 to 20.
