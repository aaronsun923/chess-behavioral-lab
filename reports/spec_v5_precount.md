# SPEC v5 pre-run count

Spec: `specs/paper4_spec_v5.md` at 6d25e7b (LOCKED 2026-09-22). Rules of SPEC v3 and the correction spec apply. Pilot not started. Outputs in `data/spec_v5/`; code in `code/p5_*.py`.

## 1. Engine setup

| Item | Value |
|---|---|
| Engine | Stockfish 18 (same binary as v2/v3: `~/Desktop/chess-study/engine/stockfish`) |
| Binary SHA-256 (build hash) | `bc0cac905ecdf2147fe22055c733bcd999b1e3f7c399fbaf7fb9055786563590` |
| Build | Compiled by                : clang++ 17.0.0 on Apple; Compilation architecture   : apple-silicon; Compilation settings       : 64bit NEON_DOTPROD POPCNT; Compiler __VERSION__ macro : Apple LLVM 17.0.0 (clang-1700.0.13.5) |
| Threads | 1 |
| Hash | 128 MB (v2/v3 value) |
| ucinewgame | before every search (python-chess game=object()) |
| Root searches | MultiPV 1; position sent as `startpos moves <full game history>`, as v1; each rebuilt root checked equal to the stored v1 FEN |
| Successor evaluations (depth 15 and 20) | MultiPV 5, V = line-1 WP from the mover's side; position sent as `fen <root> moves <move>`; terminal rules as v3; the configuration of the 57,294 v2/v3 successor evaluations |
| Processes | 8 × 1 thread (machine: 10 cores, Apple silicon) |
| Evaluation function check against v3 | 16 v2/v3 successor positions re-evaluated at depth 15: max abs WP difference 0, all five moves identical: True |

## 2. Root searches (single-PV, all 50,021 positions)

| Depth | Searches | Wall time (min, 8 processes) | Engine time, mean per search (s) | Agreement of best_15_singlepv with MultiPV best_15 |
|---|---|---|---|---|
| 4 | 50,021 | 1.4 | 0.0131 | — |
| 8 | 50,021 | 1.5 | 0.0136 | — |
| 12 | 50,021 | 14.3 | 0.0511 | — |
| 15 | 50,021 | 26.6 | 0.2541 | 37,871 / 50,021 = 75.71% |
| 4, first pass | 50,021 | not usable (overlapped a system sleep; logged 7.1) | 0.0118 | — |
| 4, rerun vs first pass | best_4 differing rows: 0 / 50,021 | | | |

File: `data/spec_v5/root_choices.parquet` (row_id, game_id, ply, fen, move_played, move_engine_best, best_4, best_8, best_12, best_15_singlepv; moves in UCI). Engine log beside it: `root_choices_engine_log.json`, `root_search_log.parquet` (per search: move, score, depth, seldepth, nodes, seconds, timestamp), `root_search.log`. best_4 in `root_choices.parquet` is from the first pass; both depth-4 runs are kept (`root_search_d04.parquet`, `root_search_d04_rerun.parquet`).

## 3. Counts (§4, best_15 = best_15_singlepv)

"Already evaluated" = the same (game_id, ply, move) is among the 57,294 v2/v3 depth-15 successor evaluations. "Terminal" = checkmate or draw after the move; valued by rule, no engine call. "Engine evaluations" = rows − already evaluated − terminal.

| Item | Definition | Rows | Already evaluated | Terminal | Engine evaluations |
|---|---|---|---|---|---|
| (a) | non-deviation rows, position after h (expected 21,374) | 21,374 | 0 | 12 | 21,362 |
| (b) d = 4 | best_4 ≠ h and best_4 ≠ best_15 | 18,345 | 1,841 | 0 | 16,504 |
| (b) d = 8 | best_8 ≠ h and best_8 ≠ best_15 | 13,220 | 1,930 | 0 | 11,290 |
| (b) d = 12 | best_12 ≠ h and best_12 ≠ best_15 | 7,803 | 1,770 | 0 | 6,033 |
| (c) | best_15_singlepv ≠ MultiPV best_15, position after best_15_singlepv | 12,150 | 3,353 | 0 | 8,797 |
| (d) | depth 20, subsample: distinct positions after h, best_15, best_4, best_8, best_12 | 4,348 | 0 | 2 | 4,346 |
| (a)+(b)+(c) | distinct depth-15 engine evaluations (same row and move counted once) | | | | 57,841 |
| (d) by type | first counted as h | 2,000 | | 2 | 1,998 |
| (d) by type | first counted as best_15 | 1,112 | | 0 | 1,112 |
| (d) by type | first counted as best_4 | 742 | | 0 | 742 |
| (d) by type | first counted as best_8 | 343 | | 0 | 343 |
| (d) by type | first counted as best_12 | 151 | | 0 | 151 |
| best_d = best_15 | d = 4 | 26,432 (52.84%) | | | |
| best_d = best_15 | d = 8 | 32,802 (65.58%) | | | |
| best_d = best_15 | d = 12 | 39,825 (79.62%) | | | |
| §5 threshold | rows with best_12 ≠ best_15 | 10,196 / 50,021 = 20.38% (threshold 5%) | | | |
| Not a §4 count | best_4 ≠ best_15 and the position after best_4 was evaluated in v2/v3, whose stored output has no PV (HORIZON's input) | 6,138 | | | |
| Not a §4 count | best_8 ≠ best_15 and the position after best_8 was evaluated in v2/v3, whose stored output has no PV (HORIZON's input) | 5,018 | | | |
| Not a §4 count | best_12 ≠ best_15 and the position after best_12 was evaluated in v2/v3, whose stored output has no PV (HORIZON's input) | 3,423 | | | |

Subsample: `data/spec_v5/subsample_ids.csv` (2,000 row ids, seed 20261001, `DataFrame.sample` on the v1 rows ordered by game_id, ply). Per-item evaluation list: `data/spec_v5/precount_tasks.parquet`.

## 4. Timing sample (study evaluations, kept)

| Evaluation | Positions | Processes | Mean s / evaluation | Median s / evaluation | Batch wall time (s) | Mean nodes |
|---|---|---|---|---|---|---|
| depth 15, MultiPV 5, after h | 200 | 8 × 1 thread | 1.083 | 1.052 | 28.2 | 657,643 |
| depth 20, MultiPV 5, after h | 50 | 8 × 1 thread | 8.231 | 8.262 | 56.8 | 4,852,311 |

Depth 15: the first 200 subsample rows in draw order that are §4(a) rows (non-terminal). Depth 20: the first 50 subsample rows in draw order with a non-terminal post-h position. Stored with engine name, SHA-256, Threads, Hash, MultiPV, depth, full PVs, nodes, seconds and timestamp in `data/spec_v5/evals/timing_d15.parquet` and `timing_d20.parquet`; log `evals/evals.log`.

## 5. Revised §11 estimate

| Depth | Engine evaluations (step 3) | Done in step 4 | Remaining | Mean s / evaluation (step 4) | Hours on 8 processes |
|---|---|---|---|---|---|
| 15 | 57,841 | 200 | 57,641 | 1.083 | 2.2 |
| 20 | 4,346 | 50 | 4,296 | 8.231 | 1.2 |
| Total | | | | | 3.4 |

Root searches (step 2) are complete and not included. Not included either: the positions in the "not a §4 count" rows of section 3, which would add at most 14,579 depth-15 evaluations (0.5 hours) if they were re-evaluated to obtain a PV.
