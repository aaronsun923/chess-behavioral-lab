# SPEC v5 Amendment A1.4: depth-25 truth check of the depth-20 ruler

Spec: `specs/paper4_spec_v5.md`, Amendment A1 at 880423e. Rows: the first 1,000 subsample rows in draw order (seed 20261001). V_D = depth-D win probability (0–100, mover's side) of the position after the move, MultiPV 5, Threads 1, Hash 128, ucinewgame per search; nproc = 6. e_d = V20(best_20) − V20(best_d); best_15 = best_15_singlepv. Bootstrap intervals: game-clustered percentile, 2,000 draws, seed 20261001. Nothing from §6 or §7. Rows with a missing V20: 0.

## 1. V25 − V20 by position type (terminal excluded)

| Position type | N | Mean | SD | p50 \|x\| | p99 \|x\| | max \|x\| | share \|x\| > 5 |
|---|---|---|---|---|---|---|---|
| after h | 998 | 0.0448 | 1.1245 | 0.5416 | 3.8489 | 8.4804 | 0.0050 |
| after best_20 | 998 | 0.0716 | 1.1236 | 0.5440 | 4.0605 | 7.8049 | 0.0050 |
| after best_2 | 998 | 0.0373 | 1.0893 | 0.5503 | 3.6446 | 7.8049 | 0.0060 |
| after best_4 | 998 | 0.0267 | 1.1567 | 0.5504 | 4.2354 | 8.4804 | 0.0070 |
| after best_8 | 998 | 0.0539 | 1.1116 | 0.5437 | 3.6415 | 8.4804 | 0.0050 |
| after best_12 | 998 | 0.0631 | 1.1369 | 0.5456 | 4.2226 | 7.8049 | 0.0050 |
| after best_15 | 998 | 0.0964 | 1.1082 | 0.5487 | 3.8490 | 7.8049 | 0.0040 |

## 2. SD rule

| Quantity | Value |
|---|---|
| SD(e_4) on these rows (N = 1,000) | 3.7232 |
| Bound 0.25 × SD(e_4) | 0.9308 |
| Largest SD of V25 − V20 (after best_4) | 1.1567 |
| Largest SD below bound | no |

## 3. HORIZON-group rule per depth (k = 6, depth-20 PV after best_d)

| d | Rows best_d ≠ best_20 | HORIZON = 1 / 0 (defined, V25 − V20 defined) | Flags (short PV / forcing to PV end / no PV) | Mean V25 − V20 at best_d, H = 1 | H = 0 | Difference (1 − 0) | 95% interval | Bound 0.25 × SD(e_d) | \|Difference\| below bound |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 527 | 191 / 336 | 2 / 0 / 0 | -0.1429 | -0.0013 | -0.1417 | [-0.3290, 0.0427] | 1.2243 | yes |
| 4 | 485 | 178 / 307 | 1 / 0 / 0 | -0.0643 | -0.1091 | 0.0448 | [-0.1725, 0.2720] | 0.9308 | yes |
| 8 | 358 | 128 / 230 | 0 / 0 / 0 | -0.0900 | -0.0795 | -0.0105 | [-0.2401, 0.2414] | 0.4764 | yes |
| 12 | 249 | 84 / 165 | 0 / 0 / 0 | -0.0470 | -0.1153 | 0.0682 | [-0.2045, 0.3700] | 0.2691 | yes |
| 15 | 185 | 57 / 128 | 0 / 0 / 0 | 0.0016 | 0.0117 | -0.0101 | [-0.3856, 0.3708] | 0.1773 | yes |

## 4. b_d and λ_d per depth (from V25 − V20)

| d | SD(e_d) | Var(e_d) | b_d = Var(n20) / Var(e_d) | N (b_d) | Var(n_d) | Var(u_d) | λ_d = 1 − Var(n_d) / Var(u_d) | N (λ_d) | λ_d ≥ 0.5 |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 4.8973 | 23.9837 | 0.0526 | 998 | 1.1840 | 22.4548 | 0.9473 | 995 | yes |
| 4 | 3.7232 | 13.8622 | 0.0909 | 998 | 1.3357 | 13.1333 | 0.8983 | 995 | yes |
| 8 | 1.9056 | 3.6315 | 0.3470 | 998 | 1.2333 | 3.5057 | 0.6482 | 995 | yes |
| 12 | 1.0763 | 1.1585 | 1.0878 | 998 | 1.2905 | 1.1329 | -0.1391 | 995 | no |
| 15 | 0.7091 | 0.5029 | 2.5059 | 998 | 1.2261 | 0.4899 | -1.5027 | 995 | no |

u_d = OLS residual of V20(best_d) on an intercept, V20(best_20) and the H1 primary covariates (as pilot §9: wp_level, wp_level², gap_12, spread_15, n_legal, n_reasonable, eval_volatility, time_pressure, player_elo); complete cases. n20, n_d = V25 − V20 at the best_20 and best_d positions; Var(n_d) on the same rows as u_d. Where best_d = best_20 the two positions are the same and n_d = n20.

## 5. Descriptives on these rows

| Quantity | Value |
|---|---|
| Mean L_h = V20(best_20) − V20(h) | 2.4668 |
| E_2 = mean e_2 | 2.0938 |
| E_4 = mean e_4 | 1.5183 |
| E_8 = mean e_8 | 0.6187 |
| E_12 = mean e_12 | 0.2685 |
| E_15 = mean e_15 | 0.1457 |

## 6. Depth-25 cost: measured against the 7.0× extrapolation

| Quantity | Value |
|---|---|
| Depth-25 engine evaluations (nproc = 6) | 2,430 |
| Depth-25 batch wall | 4.37 h |
| Depth-25 wall s per evaluation, measured | 6.477 |
| Depth-25 wall s per evaluation, extrapolated (A1 counts report §4, nproc = 8) | 10.742 |
| Measured / extrapolated | 0.603 |
| Depth-25 engine s per evaluation, mean / median | 38.834 / 36.316 |
| Engine-time ratio depth 25 / depth 20, same 2,430 positions (mean over mean) | 4.171 (extrapolation assumed 7.00) |
| Engine-time ratio depth 25 / depth 20, both at nproc = 6 (the 512 positions of the A1 depth-20 batch) | 6.521 |
| Positions in the all-positions ratio whose depth-20 time was measured in the pilot batch at nproc = 8 | 1,918 |
| Depth-20 batch for these positions: engine evaluations / wall h / wall s per evaluation | 512 / 0.15 / 1.036 |
