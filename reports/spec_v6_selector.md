# SPEC v6: pre-move selector test

Spec: `specs/paper4_spec_v6.md` at e721ee2 (LOCKED 2026-09-28). Ruler V20, anchor best_20 (SPEC v5 Amendment A1). No engine runs. This section is reported before any selector is fitted (§0).

## 0. The §2 row set

Rows: 50,021 (SPEC v5 row table) − 14 terminal rows − 100 rows missing gap_12 or spread_15 (overlap 0) = **49,907** rows in 1,970 games. Terminal row: the position after any of h, best_20, best_2, best_4, best_8 or best_15 is checkmate or a draw by rule; these are exactly the 14 rows whose best_20 successor is terminal, and they contain the 12 rows whose h successor is terminal.

| Quantity | Mean (WP points) | 95% interval |
|---|---|---|
| mean L_h = V20(best_20) − V20(h) | 2.5211 | [2.4505, 2.5882] |
| E_2 = mean L_2 | 2.0120 | [1.9590, 2.0660] |
| E_4 = mean L_4 | 1.5999 | [1.5576, 1.6417] |
| E_8 = mean L_8 | 0.7580 | [0.7350, 0.7812] |
| E_15 = mean L_15 (best_15 = best_15_singlepv) | 0.1333 | [0.1255, 0.1414] |

Intervals: game-clustered percentile bootstrap, 2,000 draws, seed 20261001; games resampled with replacement and the means recomputed on the drawn rows.

FEN features, computed from the v1 root FEN (the position before the move): material balance from the side to move's perspective (P = 1, N = B = 3, R = 5, Q = 9, kings not counted); number of pieces = all pieces on the board, kings and pawns included; in check = the side to move is in check. On the §2 rows: material mean -0.336 (SD 1.524); pieces mean 27.54 (range 15–32); in-check share 0.0218.

## Analysis note

- Rows: the §2 set, 49,907 rows, 1,970 games. Losses on the V20 ruler: L_h, L_d = e_d, L_15 with best_15 = best_15_singlepv. Targets g_d = L_d − L_h (human) and g^ref_d = L_d − L_15 (reference); rows with h = best_d keep g_d = 0.
- Folds: 5, by game; the 1,970 games are permuted with seed 20261001 and assigned to folds in rotation (fold sizes 9,865–10,064 rows). Every score is out-of-fold.
- Model: HistGradientBoostingRegressor (scikit-learn 1.6.1), max_depth 4, learning_rate 0.05, max_iter 500, squared error, random_state 20261001, one model per depth and selector. Early stopping on an explicit game-level validation set: 10% of the training fold's games (seed 20261001), excluded from fitting. scikit-learn 1.6.1 has no X_val argument, so the rule is reproduced: the model is fitted to 500 iterations without internal early stopping, the validation loss (half squared error; initial score at the training mean) is tracked per iteration with staged_predict, and the model stops at the first iteration where none of the last 10 scores improved on the score 11 positions back by more than 1e-7 (scikit-learn's n_iter_no_change and tol defaults). Scores come from the model truncated there; a refit with max_iter at that value reproduces the stored scores exactly (max abs difference 0.0e+00 over the permutation-importance refits). Stopping iterations per fold are in the table below.
- Coverage: in each test fold the top round(q × fold size) rows by predicted gain (ties by row_id). Random control: 200 selections of the same size per test fold (seed 20261001); G^rand is their mean, reported with the 2.5/97.5 percentiles across the 200 selections and with a bootstrap interval of the mean. Oracle: the top round(q × N) rows of all N rows by the true gain g_d.
- Intervals: game-clustered percentile bootstrap, 2,000 draws, seed 20261001, resampling games and recomputing every mean on the drawn rows with the out-of-fold scores and selections fixed; D and G^h − G^rand are computed within each draw. Spearman (primary only) is recomputed on the drawn rows (games repeated by their draw count). Precision is the share of selected rows with positive gain.
- Robustness 2 (ridge): scikit-learn Ridge, alpha 1.0 (default, no tuning), features standardized on the training fold, fitted on the whole training fold (no early stopping, so the validation games are not held out). Robustness 3: the v3 deviation rows within the §2 set, 28,645 rows (2 of the 28,647 v3 rows are among the 14 terminal rows); selectors refit on these rows with the same fold assignment by game.

Early-stopping iteration per fold (folds 1–5):

| Variant | Selector | d = 2 | d = 4 | d = 8 |
|---|---|---|---|---|
| primary | human | 33, 29, 73, 68, 45 | 32, 71, 78, 47, 50 | 39, 75, 102, 98, 50 |
| primary | reference | 49, 40, 56, 77, 31 | 48, 30, 27, 31, 54 | 38, 18, 49, 20, 26 |
| assisted | human | 90, 51, 33, 43, 43 | 61, 61, 65, 89, 60 | 49, 80, 99, 91, 64 |
| assisted | reference | 65, 59, 73, 56, 49 | 56, 46, 61, 51, 61 | 54, 25, 53, 50, 27 |
| deviation | human | 30, 53, 75, 74, 26 | 80, 69, 113, 127, 74 | 71, 93, 112, 118, 74 |
| deviation | reference | 55, 46, 29, 62, 51 | 37, 25, 63, 23, 40 | 36, 28, 34, 46, 72 |

## 1. Main table (primary selectors, assistant-free features)

WP points on the V20 ruler; each cell is estimate [95% interval]. G = mean over all N rows of the loss saved by the substitution on the selected rows.

### d = 2

| q | Baseline loss (mean L_d) | Human combination loss | G^h | G^ref | D = G^h − G^ref | G^rand (bootstrap) | G^rand 2.5/97.5% of 200 selections | G^h − G^rand | G^oracle | Precision (human) | Precision (reference) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.05 | 2.0120 [1.9590, 2.0660] | 2.0061 [1.9528, 2.0590] | 0.0059 [-0.0053, 0.0175] | 0.1346 [0.1168, 0.1532] | -0.1287 [-0.1480, -0.1101] | -0.0251 [-0.0286, -0.0214] | [-0.0360, -0.0140] | 0.0311 [0.0205, 0.0417] | 0.7124 [0.6744, 0.7535] | 0.2208 [0.2041, 0.2380] | 0.4321 [0.4120, 0.4517] |
| 0.10 | 2.0120 [1.9590, 2.0660] | 2.0070 [1.9524, 2.0599] | 0.0051 [-0.0121, 0.0223] | 0.2673 [0.2414, 0.2953] | -0.2623 [-0.2916, -0.2338] | -0.0507 [-0.0579, -0.0435] | [-0.0660, -0.0359] | 0.0557 [0.0397, 0.0720] | 0.9448 [0.9042, 0.9889] | 0.2367 [0.2245, 0.2490] | 0.4355 [0.4211, 0.4498] |
| 0.20 | 2.0120 [1.9590, 2.0660] | 1.9975 [1.9452, 2.0497] | 0.0145 [-0.0096, 0.0370] | 0.5230 [0.4876, 0.5599] | -0.5085 [-0.5470, -0.4704] | -0.1020 [-0.1161, -0.0876] | [-0.1259, -0.0841] | 0.1165 [0.0952, 0.1375] | 1.1287 [1.0878, 1.1724] | 0.2478 [0.2383, 0.2574] | 0.4384 [0.4284, 0.4491] |
| 0.30 | 2.0120 [1.9590, 2.0660] | 1.9995 [1.9484, 2.0532] | 0.0125 [-0.0180, 0.0416] | 0.7487 [0.7094, 0.7895] | -0.7362 [-0.7811, -0.6909] | -0.1541 [-0.1749, -0.1324] | [-0.1811, -0.1338] | 0.1666 [0.1404, 0.1917] | 1.1486 [1.1082, 1.1920] | 0.2511 [0.2432, 0.2592] | 0.4372 [0.4292, 0.4459] |

Spearman correlation of out-of-fold score with true gain, pooled over all N rows: human selector 0.0884 [0.0787, 0.0979]; reference selector 0.0821 [0.0728, 0.0912].

### d = 4

| q | Baseline loss (mean L_d) | Human combination loss | G^h | G^ref | D = G^h − G^ref | G^rand (bootstrap) | G^rand 2.5/97.5% of 200 selections | G^h − G^rand | G^oracle | Precision (human) | Precision (reference) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.05 | 1.5999 [1.5576, 1.6417] | 1.6077 [1.5653, 1.6509] | -0.0078 [-0.0164, 0.0000] | 0.1139 [0.0987, 0.1304] | -0.1217 [-0.1397, -0.1042] | -0.0453 [-0.0485, -0.0416] | [-0.0561, -0.0337] | 0.0374 [0.0291, 0.0455] | 0.5522 [0.5224, 0.5822] | 0.2188 [0.2017, 0.2364] | 0.4100 [0.3903, 0.4291] |
| 0.10 | 1.5999 [1.5576, 1.6417] | 1.6093 [1.5665, 1.6514] | -0.0095 [-0.0215, 0.0016] | 0.2144 [0.1935, 0.2367] | -0.2239 [-0.2480, -0.1995] | -0.0923 [-0.0987, -0.0852] | [-0.1061, -0.0757] | 0.0829 [0.0708, 0.0944] | 0.7383 [0.7081, 0.7694] | 0.2351 [0.2230, 0.2479] | 0.4098 [0.3956, 0.4237] |
| 0.20 | 1.5999 [1.5576, 1.6417] | 1.6380 [1.5937, 1.6805] | -0.0382 [-0.0584, -0.0199] | 0.3999 [0.3734, 0.4272] | -0.4381 [-0.4703, -0.4051] | -0.1834 [-0.1964, -0.1690] | [-0.2032, -0.1662] | 0.1452 [0.1269, 0.1636] | 0.8825 [0.8523, 0.9123] | 0.2328 [0.2240, 0.2418] | 0.4017 [0.3912, 0.4115] |
| 0.30 | 1.5999 [1.5576, 1.6417] | 1.6756 [1.6302, 1.7214] | -0.0758 [-0.1025, -0.0510] | 0.5711 [0.5404, 0.6025] | -0.6469 [-0.6864, -0.6065] | -0.2764 [-0.2955, -0.2550] | [-0.2999, -0.2547] | 0.2006 [0.1777, 0.2239] | 0.8939 [0.8637, 0.9234] | 0.2403 [0.2330, 0.2479] | 0.3957 [0.3873, 0.4038] |

Spearman correlation of out-of-fold score with true gain, pooled over all N rows: human selector 0.1033 [0.0936, 0.1135]; reference selector 0.0643 [0.0549, 0.0731].

### d = 8

| q | Baseline loss (mean L_d) | Human combination loss | G^h | G^ref | D = G^h − G^ref | G^rand (bootstrap) | G^rand 2.5/97.5% of 200 selections | G^h − G^rand | G^oracle | Precision (human) | Precision (reference) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.05 | 0.7580 [0.7350, 0.7812] | 0.7794 [0.7565, 0.8035] | -0.0214 [-0.0282, -0.0152] | 0.0498 [0.0419, 0.0584] | -0.0712 [-0.0820, -0.0613] | -0.0874 [-0.0907, -0.0839] | [-0.0977, -0.0771] | 0.0660 [0.0591, 0.0727] | 0.2817 [0.2670, 0.2971] | 0.1238 [0.1095, 0.1384] | 0.2834 [0.2649, 0.3026] |
| 0.10 | 0.7580 [0.7350, 0.7812] | 0.8103 [0.7852, 0.8353] | -0.0523 [-0.0632, -0.0424] | 0.0912 [0.0812, 0.1017] | -0.1435 [-0.1588, -0.1285] | -0.1766 [-0.1831, -0.1699] | [-0.1919, -0.1634] | 0.1243 [0.1134, 0.1353] | 0.3633 [0.3487, 0.3790] | 0.1409 [0.1291, 0.1521] | 0.2804 [0.2671, 0.2942] |
| 0.20 | 0.7580 [0.7350, 0.7812] | 0.8862 [0.8580, 0.9137] | -0.1282 [-0.1456, -0.1123] | 0.1726 [0.1584, 0.1866] | -0.3008 [-0.3234, -0.2795] | -0.3522 [-0.3648, -0.3387] | [-0.3720, -0.3368] | 0.2240 [0.2073, 0.2409] | 0.3939 [0.3791, 0.4098] | 0.1544 [0.1462, 0.1622] | 0.2725 [0.2634, 0.2822] |
| 0.30 | 0.7580 [0.7350, 0.7812] | 1.0074 [0.9776, 1.0383] | -0.2494 [-0.2732, -0.2282] | 0.2456 [0.2294, 0.2616] | -0.4951 [-0.5231, -0.4694] | -0.5293 [-0.5486, -0.5087] | [-0.5494, -0.5073] | 0.2798 [0.2564, 0.3025] | 0.3939 [0.3791, 0.4098] | 0.1624 [0.1559, 0.1685] | 0.2702 [0.2629, 0.2781] |

Spearman correlation of out-of-fold score with true gain, pooled over all N rows: human selector 0.1297 [0.1202, 0.1393]; reference selector 0.0396 [0.0306, 0.0483].

## 2. Recorded predictions (q = 0.10, primary)

| Hypothesis | Condition | Condition holds | Recorded prediction | Prediction correct |
|---|---|---|---|---|
| S1 | G^h_2(0.10) > 0, interval excluding zero | no | holds | **no** |
| S2 | G^h_4(0.10) > 0, interval excluding zero | no | does not hold | **yes** |
| S3 | G^h_8(0.10) ≤ 0 or interval including zero | yes | holds | **yes** |
| S4 | G^h_d(0.10) − G^rand_d(0.10) > 0, interval excluding zero, at every depth | yes (d = 2: yes, d = 4: yes, d = 8: yes) | holds at all depths | **yes** |
| S5 | D_d(0.10) < 0, interval excluding zero, at every depth | yes (d = 2: yes, d = 4: yes, d = 8: yes) | holds at all depths | **yes** |

S1 and S5 are the pre-registered results (§5); S2–S4 are the recorded shape of the curve.

## 3. Descriptives (§6)

Figure: `figures/spec_v6/fig_selector_curves.png` — G^h, G^ref, G^rand and G^oracle against q at each depth, primary selectors, 95% intervals.

### 3a. Permutation importance, primary human selector (increase in test-fold MSE of g_d when the feature is permuted; mean over 5 folds, 10 repeats each)

| Feature | d = 2 | d = 4 | d = 8 |
|---|---|---|---|
| player_elo | 0.4399 | 0.3296 | 0.2627 |
| opponent_elo | 0.0649 | 0.0341 | 0.0194 |
| time_pressure | 0.1086 | 0.1462 | 0.3346 |
| ply | 0.0864 | 0.1024 | 0.1109 |
| material | 0.0638 | 0.1267 | 0.3067 |
| pieces | 0.0469 | 0.0447 | 0.0414 |
| in_check | -0.0010 | 0.0008 | 0.0097 |

### 3b. Coincidence: share of human-selected rows with h = best_d

| q | d = 2 | d = 4 | d = 8 |
|---|---|---|---|
| 0.05 | 0.5671 | 0.5699 | 0.7018 |
| 0.10 | 0.5405 | 0.5383 | 0.6347 |
| 0.20 | 0.5074 | 0.5184 | 0.5753 |
| 0.30 | 0.4907 | 0.4922 | 0.5289 |

For reference, share of all §2 rows with h = best_d: d = 2: 0.4261, d = 4: 0.4104, d = 8: 0.4298.

## 4. Robustness (§7), q = 0.10

### Primary (for comparison)

| d | Baseline loss | G^h | G^ref | D | G^h − G^rand | G^oracle | Spearman (human) |
|---|---|---|---|---|---|---|---|
| 2 | 2.0120 [1.9590, 2.0660] | 0.0051 [-0.0121, 0.0223] | 0.2673 [0.2414, 0.2953] | -0.2623 [-0.2916, -0.2338] | 0.0557 [0.0397, 0.0720] | 0.9448 [0.9042, 0.9889] | 0.0884 |
| 4 | 1.5999 [1.5576, 1.6417] | -0.0095 [-0.0215, 0.0016] | 0.2144 [0.1935, 0.2367] | -0.2239 [-0.2480, -0.1995] | 0.0829 [0.0708, 0.0944] | 0.7383 [0.7081, 0.7694] | 0.1033 |
| 8 | 0.7580 [0.7350, 0.7812] | -0.0523 [-0.0632, -0.0424] | 0.0912 [0.0812, 0.1017] | -0.1435 [-0.1588, -0.1285] | 0.1243 [0.1134, 0.1353] | 0.3633 [0.3487, 0.3790] | 0.1297 |

| Hypothesis | Condition holds | Recorded prediction correct |
|---|---|---|
| S1 | no | no |
| S2 | no | yes |
| S3 | yes | yes |
| S4 | yes (d = 2: yes, d = 4: yes, d = 8: yes) | yes |
| S5 | yes (d = 2: yes, d = 4: yes, d = 8: yes) | yes |

### 1. Assisted: depth-15 root MultiPV features added (uses depth-15 information)

| d | Baseline loss | G^h | G^ref | D | G^h − G^rand | G^oracle | Spearman (human) |
|---|---|---|---|---|---|---|---|
| 2 | 2.0120 [1.9590, 2.0660] | 0.0097 [-0.0065, 0.0266] | 0.3783 [0.3498, 0.4083] | -0.3687 [-0.4024, -0.3355] | 0.0604 [0.0453, 0.0758] | 0.9448 [0.9042, 0.9889] | 0.0927 |
| 4 | 1.5999 [1.5576, 1.6417] | 0.0127 [0.0030, 0.0224] | 0.2642 [0.2447, 0.2860] | -0.2515 [-0.2752, -0.2304] | 0.1050 [0.0941, 0.1159] | 0.7383 [0.7081, 0.7694] | 0.1165 |
| 8 | 0.7580 [0.7350, 0.7812] | -0.0295 [-0.0382, -0.0209] | 0.1022 [0.0921, 0.1122] | -0.1317 [-0.1450, -0.1187] | 0.1471 [0.1372, 0.1567] | 0.3633 [0.3487, 0.3790] | 0.1664 |

| Hypothesis | Condition holds | Recorded prediction correct |
|---|---|---|
| S1 | no | no |
| S2 | yes | no |
| S3 | yes | yes |
| S4 | yes (d = 2: yes, d = 4: yes, d = 8: yes) | yes |
| S5 | yes (d = 2: yes, d = 4: yes, d = 8: yes) | yes |

### 2. Ridge regression in place of gradient boosting

| d | Baseline loss | G^h | G^ref | D | G^h − G^rand | G^oracle | Spearman (human) |
|---|---|---|---|---|---|---|---|
| 2 | 2.0120 [1.9590, 2.0660] | 0.0323 [0.0176, 0.0465] | 0.2795 [0.2537, 0.3092] | -0.2472 [-0.2779, -0.2184] | 0.0830 [0.0682, 0.0978] | 0.9448 [0.9042, 0.9889] | 0.0888 |
| 4 | 1.5999 [1.5576, 1.6417] | -0.0028 [-0.0145, 0.0089] | 0.2179 [0.1980, 0.2395] | -0.2207 [-0.2454, -0.1980] | 0.0895 [0.0771, 0.1014] | 0.7383 [0.7081, 0.7694] | 0.0968 |
| 8 | 0.7580 [0.7350, 0.7812] | -0.0580 [-0.0692, -0.0474] | 0.0965 [0.0856, 0.1075] | -0.1544 [-0.1702, -0.1393] | 0.1187 [0.1064, 0.1298] | 0.3633 [0.3487, 0.3790] | 0.1158 |

| Hypothesis | Condition holds | Recorded prediction correct |
|---|---|---|
| S1 | yes | yes |
| S2 | no | yes |
| S3 | yes | yes |
| S4 | yes (d = 2: yes, d = 4: yes, d = 8: yes) | yes |
| S5 | yes (d = 2: yes, d = 4: yes, d = 8: yes) | yes |

### 3. Deviation rows only (28,645 rows)

| d | Baseline loss | G^h | G^ref | D | G^h − G^rand | G^oracle | Spearman (human) |
|---|---|---|---|---|---|---|---|
| 2 | 2.3160 [2.2504, 2.3823] | -0.0894 [-0.1085, -0.0710] | 0.3118 [0.2796, 0.3429] | -0.4011 [-0.4382, -0.3640] | 0.1151 [0.0953, 0.1335] | 0.6893 [0.6547, 0.7283] | 0.1033 |
| 4 | 1.8512 [1.7969, 1.9073] | -0.0985 [-0.1154, -0.0817] | 0.2261 [0.2016, 0.2517] | -0.3247 [-0.3553, -0.2945] | 0.1534 [0.1356, 0.1712] | 0.5261 [0.4955, 0.5561] | 0.1200 |
| 8 | 0.9219 [0.8904, 0.9529] | -0.1568 [-0.1739, -0.1396] | 0.1049 [0.0923, 0.1182] | -0.2617 [-0.2824, -0.2415] | 0.1885 [0.1692, 0.2070] | 0.2536 [0.2398, 0.2684] | 0.1419 |

| Hypothesis | Condition holds | Recorded prediction correct |
|---|---|---|
| S1 | no | no |
| S2 | no | yes |
| S3 | yes | yes |
| S4 | yes (d = 2: yes, d = 4: yes, d = 8: yes) | yes |
| S5 | yes (d = 2: yes, d = 4: yes, d = 8: yes) | yes |

## 5. Limits (§8)

- One platform, fast time controls, titled players.
- Selectors are trained and tested on the same population (cross-fitted by game, not validated on new players or events).
- Scores and selections are fixed inside bootstrap draws; the intervals do not include selector refitting variance.
- The increment is on the V20 ruler, which has about 1 WP point of resolution per row and is reliable in means.
- The reference source is one engine (best_15_singlepv) at one depth.
- The oracle selects rows by the true gain, which contains the ruler's roughly 1 WP point of noise per row, so it is inflated by noise and is a loose upper bound.
