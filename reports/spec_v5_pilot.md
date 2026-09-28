# SPEC v5 pilot

Spec: `specs/paper4_spec_v5.md` at 6d25e7b (LOCKED). §5 pilot, run as instructed on 2026-09-24. best_15 = best_15_singlepv; V = depth-15 win probability (0–100, mover's side) of the position after the move, MultiPV 5, Threads 1, Hash 128, ucinewgame per search (pre-run count §1). WP points throughout. Bootstrap intervals: game-clustered percentile, 2,000 draws, seed 20261001. Nothing from §6 or §7.

## 1. Reproduction check (PV re-evaluations of v2/v3 positions)

| Item | Value |
|---|---|
| v2/v3 positions re-evaluated in the pilot | 3,633 |
| after best_12, rows with best_12 ≠ best_15 (pre-run count: 3,423) | 3,423 |
| after best_4, subsample rows with best_4 ≠ best_15 | 210 |
| Mismatches in wp_self_1 or mv_1 against the stored v2/v3 values (exact equality) | 0 |

## 2. Depth 12, all rows: E_12

| Quantity | Value |
|---|---|
| Rows | 50,021 |
| Rows with a missing V (h, best_15 or best_12) | 0 |
| E_12 = mean e_12 | 0.1808 |
| 95% interval | [0.1706, 0.1913] |

## 3. Depth 12: distributions of e_12 and I_12 (all rows; I_12 = e_12 − L_h by identity)

| Statistic | e_12 | I_12 |
|---|---|---|
| n | 50,021 | 50,021 |
| mean | 0.1808 | -2.1750 |
| sd | 1.1402 | 4.9389 |
| min | -19.9312 | -80.6116 |
| p10 | 0.0000 | -7.2450 |
| p20 | 0.0000 | -3.8509 |
| p30 | 0.0000 | -2.0235 |
| p40 | 0.0000 | -0.6444 |
| p50 | 0.0000 | 0.0000 |
| p60 | 0.0000 | 0.0000 |
| p70 | 0.0000 | 0.0000 |
| p80 | 0.0000 | 0.0000 |
| p90 | 0.5632 | 0.0910 |
| max | 33.1086 | 30.6311 |
| share e_12 ≤ 0 | 0.8664 | |
| share e_12 < 0 | 0.0653 | |
| share I_12 ≤ 0 | | 0.8976 |

## 4. Depth 12: disagreement rows and HORIZON (k = 6)

| Quantity | Value |
|---|---|
| Rows with best_12 ≠ best_15 | 10,196 / 50,021 = 0.2038 (§5 threshold 0.05) |
| HORIZON defined | 10,196 |
| HORIZON = 1 | 3,474 = 0.3407 of defined (§4 amendment band: below 0.20 or above 0.80) |
| Flag: Pq found within the PV | 10,135 |
| Flag: pv_shorter_than_k | 39 |
| Flag: forcing_to_pv_end | 22 |

HORIZON implementation: P0 = position after best_12; PV = line 1 of its depth-15 MultiPV-5 evaluation. A check counts if a PV move among plies 1..6 gives check (best_12 itself is not a PV move). Pq = the position after the first PV move at ply ≥ 6 that is neither a capture nor a check; if the PV ends first, Pq = the last PV position (flagged). Material: P=1, N=B=3, R=5, Q=9, White minus Black.

## 5. Depth-15 single-PV / MultiPV agreement and e_12 by agreement

| Rows | N | Mean e_12 |
|---|---|---|
| All | 50,021 | 0.1808 |
| best_15_singlepv = MultiPV best_15 (agree) | 37,871 (0.7571 of all rows) | 0.2206 |
| best_15_singlepv ≠ MultiPV best_15 (disagree) | 12,150 | 0.0565 |

## 6. Depth 4, subsample: V20 − V15 by position type

2,000 rows (seed 20261001). Terminal positions excluded.

| Position type | N | Mean V20 − V15 | SD V20 − V15 |
|---|---|---|---|
| after h | 1,998 | 0.0025 | 1.4578 |
| after best_15 | 1,998 | 0.0321 | 1.3542 |
| after best_4 | 1,998 | 0.0131 | 1.4042 |

## 7. Depth 4, subsample: SD rule

| Quantity | Value |
|---|---|
| SD(e_4) on the subsample (N = 2,000) | 3.2943 |
| Bound 0.25 × SD(e_4) | 0.8236 |
| Largest SD of V20 − V15 (h, best_15, best_4) | 1.4578 |
| Largest SD below bound | no |

## 8. Depth 4, subsample: HORIZON rule

| Quantity | Value |
|---|---|
| Subsample rows with best_4 ≠ best_15 | 960 |
| with HORIZON and V20 − V15 at best_4 defined | 960 (HORIZON = 1: 339; HORIZON = 0: 621) |
| HORIZON flag: Pq found within the PV | 955 |
| HORIZON flag: pv_shorter_than_k | 4 |
| HORIZON flag: forcing_to_pv_end | 1 |
| Mean V20 − V15 at best_4, HORIZON = 1 | -0.1680 |
| Mean V20 − V15 at best_4, HORIZON = 0 | -0.0536 |
| Difference (1 − 0) | -0.1144 |
| 95% interval | [-0.3301, 0.0881] |
| Bound 0.25 × SD(e_4) | 0.8236 |
| Absolute difference below bound | yes |

## 9. Depth 4, subsample: b_4 and λ_4

| Quantity | Value |
|---|---|
| b_4 = Var(n15) / Var(e_4) (N = 1,998) | 0.1688 |
| Var(n15) | 1.8339 |
| Var(e_4) | 10.8614 |
| λ_4 = 1 − Var(n4) / Var(u_4) (N = 1,992) | 0.8101 |
| Var(n4) | 1.9721 |
| Var(u_4) | 10.3855 |
| λ_4 ≥ 0.5 (§3 floor) | yes |

u_4 = OLS residual of V15(best_4) on an intercept, V15(best_15) and the H1 primary covariates: difficulty = the v3 difficulty features at the mover's root (wp_level = wp_best, wp_level², gap_12, spread_15, n_legal, n_reasonable, eval_volatility), clock = time_pressure, elo = player_elo; complete cases. Standardization does not change the residual. n15, n4 = V20 − V15 at the best_15 and best_4 positions; Var(n4) on the same rows as u_4.

## 10. Depth 4, subsample: I_4

| Quantity | Value |
|---|---|
| N | 2,000 |
| Mean I_4 | -0.9217 |
| SD I_4 | 5.4650 |

## 11. Cost

| Item | Evaluations | Hours (8 processes) |
|---|---|---|
| Pre-run estimate (pre-run count §5): depth 15 | 57,641 | 2.2 |
| Pre-run estimate: depth 20 | 4,296 | 1.2 |
| Pre-run estimate: PV re-evaluations (at most) | 14,579 | 0.5 |
| Pre-run estimate, total | | 3.9 |
| Pilot batch `pilot_pv12`: engine evaluations / terminal (no engine call), measured | 3,423 / 0 | 0.13 |
| Pilot batch `pilot_d15`: engine evaluations / terminal (no engine call), measured | 35,992 / 12 | 1.95 |
| Pilot batch `pilot_sub_d15`: engine evaluations / terminal (no engine call), measured | 794 / 0 | 0.04 |
| Pilot batch `pilot_sub_d20`: engine evaluations / terminal (no engine call), measured | 3,802 / 2 | 1.35 |

## 12. Additions before the truth amendment (2026-09-24, no engine)

### 12.1 Distribution of V20 − V15 per position type (subsample, terminal excluded)

| Position type | N | SD | p50 \|x\| | p90 \|x\| | p99 \|x\| | max \|x\| | share \|x\| > 5 | SD of rows with \|x\| ≤ 5 | 1.4826 × MAD |
|---|---|---|---|---|---|---|---|---|---|
| after h | 1,998 | 1.4578 | 0.6436 | 2.1315 | 5.9448 | 10.6059 | 0.0135 | 1.2264 | 0.9542 |
| after best_15 | 1,998 | 1.3542 | 0.6391 | 2.0876 | 4.8917 | 8.5252 | 0.0100 | 1.2045 | 0.9476 |
| after best_4 | 1,998 | 1.4042 | 0.6427 | 2.1904 | 5.1778 | 7.9114 | 0.0110 | 1.2433 | 0.9529 |

x = V20 − V15. The last two columns are the SD without the rows beyond 5 WP points and a tail-robust scale (normal-consistent MAD). 
Is the SD driven by a tail: no. Removing the rows with |x| > 5 (1.0% to 1.4% of rows) moves the SD from 1.35–1.46 to 1.20–1.24; the MAD scale is 0.95–0.95; all remain above the SD-rule bound 0.8236.

### 12.2 Var(V20 − V15) / Var(e_d) on the subsample

Var(e_4) = 10.8523 (N = 2,000); Var(e_12) = 1.1147 (pilot e_12 on the subsample rows, N = 2,000).

| Position type | Var(V20 − V15) | / Var(e_4) | / Var(e_12) |
|---|---|---|---|
| after h | 2.1251 | 0.1958 | 1.9063 |
| after best_15 | 1.8339 | 0.1690 | 1.6452 |
| after best_4 | 1.9718 | 0.1817 | 1.7688 |

best_12 positions were not evaluated at depth 20 in the pilot (§5(b) covers h, best_15, best_4), so there is no best_12 row; the depth-12 column divides the available position types by Var(e_12).

### 12.3 L_h under the depth-20 ruler (subsample)

Rows with V15 and V20 at both h and best_15: 1,998.

| Quantity | Mean | 95% interval |
|---|---|---|
| L_h, depth-20 ruler: V20(best_15) − V20(h) | 2.2872 | [2.0667, 2.5179] |
| L_h, depth-15 ruler: V15(best_15) − V15(h) | 2.2576 | [2.0422, 2.4795] |
| Difference (depth 20 − depth 15) | 0.0296 | [-0.0307, 0.0850] |
| Mean V20 − V15 at h positions | 0.0025 | |
| Mean V20 − V15 at best_15 positions | 0.0321 | |

Intervals: game-clustered percentile bootstrap, 2,000 draws, seed 20261001. The difference row equals the best_15 mean minus the h mean.
