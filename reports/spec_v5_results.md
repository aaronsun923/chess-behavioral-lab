# SPEC v5 results: engine depth as a knob on baseline fallibility

Spec: `specs/paper4_spec_v5.md` at b735062 (LOCKED 2026-09-22; Amendment A1, 880423e; A1.4 outcome). Ruler V20 (depth-20 win probability, 0–100, mover's side, of the position after the move); anchor best_20; admitted depths D = {2, 4, 8}; depths 12 and 15 descriptive only. Reading rule: sign and interval. No interpretation.

## Analysis note

- Estimator: `fit_mixed_v2` (`code/paper4_mixed_v2.py`), `(1 | player_id)` with `game_id` as a variance component nested in `player_id`, REML, five-optimizer sweep, converged non-degenerate fit with the highest log-likelihood; statsmodels 0.14.6. Full-data point estimates use the full sweep.
- Bootstrap: game-clustered percentile, seed 20261001; one sequence of game resamples shared by all groups (draw b uses the same games everywhere). A game drawn k times enters as k distinct game clusters; player ids are kept. Draws: H1 primary 2,000; H2 2,000; H1 secondary 500; robustness (1) and (3) 500; robustness (2) 500. H3 and mixed-model descriptives: point estimates only; I_d and E_d means: 2,000 draws. Exploratory, post-results section (last): 500 draws.
- λ_d in every draw is recomputed on the A1.4 check rows (first 1,000 subsample rows) restricted to the drawn games, with multiplicity; β and λ are resampled jointly.
- Optimizer order in draws (designer decision 2026-09-27): nm first for every model; the full five-optimizer sweep only when nm fails to converge or is degenerate; draws where the sweep also fails are dropped from the interval and counted below. Reason: cg, selected on the full data for H1 at d = 2 and 8, converged in 0 of 57 resampled draws. Check on those 57 draws, nm-first against the full sweep: max |Δβ| = 7.49e-07 (d = 2), 0.00e+00 (d = 4), 3.94e-06 (d = 8); nm fallbacks 0; tolerance 0.005. This changes execution order, not the estimator.
- Parallelism: 8 processes, one thread each. Measured gain over one process: 2.9× (83 s per H1 draw serial, 226 s per draw per process at 8 processes, full-sweep execution).
- Implementation record: the first H1 bootstrap attempt (56 draws) ran a wrapper that raised on every fit (patsy resolved `C(game_id)` to a module named `C`) and so always ran the full sweep; a worker of that run also wrote one draw after it was stopped. All 57 such draws were set aside (`results/draws_discarded/`); the 57 full-sweep draws of the second attempt are the reference set of the check above (`results/draws_reference/h1p/`). Every reported draw was produced by the nm-first procedure.
- Covariates: difficulty = v3 §4.2 features at the mover's root (wp_level, wp_level², gap_12, spread_15, n_legal, n_reasonable, eval_volatility), clock = time_pressure, elo = player_elo; z-scores on all 50,021 rows. 100 rows lack gap_12 and spread_15 (fewer than two root lines) and drop from every model. e_d_z is standardized on all rows.
- HORIZON(i, d): depth-20 PV (line 1 of the MultiPV-5 evaluation) after best_d, k = 6, as the pilot; defined on every best_d ≠ best_20 row with a non-terminal successor.
- Robustness (2): 19,056 depth-15 evaluations after best_4 run after all other bootstraps (nproc 6; 4,670 of them re-evaluations of v2/v3 positions for the PV; wall 62.7 min). Reproduction check over all 8,303 v2/v3 positions re-evaluated in the study (pilot and this item): 0 mismatches in wp_self_1 or mv_1. λ_4 = 0.810 from the pilot, not resampled.

Draw status per model (selected = nm converged; fallback = full sweep; failed = dropped):

| Group | Model | Draws | nm | Fallback | Failed |
|---|---|---|---|---|---|
| h1p | H1_d2 | 2,000 | 2,000 | 0 | 0 |
| h1p | H1_d4 | 2,000 | 2,000 | 0 | 0 |
| h1p | H1_d8 | 2,000 | 2,000 | 0 | 0 |
| h2 | H2_L_d2 | 2,000 | 2,000 | 0 | 0 |
| h2 | H2_hb_d2 | 2,000 | 2,000 | 0 | 0 |
| h2 | H2_L_d4 | 2,000 | 2,000 | 0 | 0 |
| h2 | H2_hb_d4 | 2,000 | 2,000 | 0 | 0 |
| h2 | H2_L_d8 | 2,000 | 2,000 | 0 | 0 |
| h2 | H2_hb_d8 | 2,000 | 2,000 | 0 | 0 |
| h1s | H1s_cov_d2 | 500 | 500 | 0 | 0 |
| h1s | H1s_common_d2 | 500 | 500 | 0 | 0 |
| h1s | H1s_cov_d4 | 500 | 500 | 0 | 0 |
| h1s | H1s_common_d4 | 500 | 500 | 0 | 0 |
| h1s | H1s_cov_d8 | 500 | 500 | 0 | 0 |
| h1s | H1s_common_d8 | 500 | 500 | 0 | 0 |
| rob | R1_L_d2_k4 | 500 | 500 | 0 | 0 |
| rob | R1_hb_d2_k4 | 500 | 500 | 0 | 0 |
| rob | R1_L_d4_k4 | 500 | 500 | 0 | 0 |
| rob | R1_hb_d4_k4 | 500 | 500 | 0 | 0 |
| rob | R1_L_d8_k4 | 500 | 500 | 0 | 0 |
| rob | R1_hb_d8_k4 | 500 | 500 | 0 | 0 |
| rob | R1_L_d2_k8 | 500 | 500 | 0 | 0 |
| rob | R1_hb_d2_k8 | 500 | 500 | 0 | 0 |
| rob | R1_L_d4_k8 | 500 | 500 | 0 | 0 |
| rob | R1_hb_d4_k8 | 500 | 500 | 0 | 0 |
| rob | R1_L_d8_k8 | 500 | 500 | 0 | 0 |
| rob | R1_hb_d8_k8 | 500 | 500 | 0 | 0 |
| rob | R3_H1_d2 | 500 | 500 | 0 | 0 |
| rob | R3_H2_L_d2 | 500 | 500 | 0 | 0 |
| rob | R3_H2_hb_d2 | 500 | 500 | 0 | 0 |
| rob | R3_H1_d4 | 500 | 500 | 0 | 0 |
| rob | R3_H2_L_d4 | 500 | 500 | 0 | 0 |
| rob | R3_H2_hb_d4 | 500 | 500 | 0 | 0 |
| rob | R3_H1_d8 | 500 | 500 | 0 | 0 |
| rob | R3_H2_L_d8 | 500 | 500 | 0 | 0 |
| rob | R3_H2_hb_d8 | 500 | 500 | 0 | 0 |
| rob2 | R2_H1_d4 | 500 | 500 | 0 | 0 |
| rob2 | R2_H2_L_d4 | 500 | 500 | 0 | 0 |
| rob2 | R2_H2_hb_d4 | 500 | 500 | 0 | 0 |

## 0. Inputs and checks

| Check | Value |
|---|---|
| Rows | 50,021; games 1,970; players 2,317 |
| Missing values | none except gap_12 and spread_15: 100 rows |
| Terminal successor positions (valued by rule) | h 12, best_20 14, each best_d 14 |
| HORIZON (k = 6), d = 2 | rows best_d ≠ best_20 25,240; HORIZON = 1 share 0.3356; fallback-Pq flags {'pv_shorter_than_k': 61, 'forcing_to_pv_end': 4} |
| HORIZON (k = 6), d = 4 | rows best_d ≠ best_20 23,956; HORIZON = 1 share 0.3400; fallback-Pq flags {'pv_shorter_than_k': 42, 'forcing_to_pv_end': 4} |
| HORIZON (k = 6), d = 8 | rows best_d ≠ best_20 18,277; HORIZON = 1 share 0.3424; fallback-Pq flags {'pv_shorter_than_k': 24, 'forcing_to_pv_end': 2} |
| HORIZON (k = 6), d = 12 | rows best_d ≠ best_20 12,414; HORIZON = 1 share 0.3351; fallback-Pq flags {'pv_shorter_than_k': 14, 'forcing_to_pv_end': 2} |
| HORIZON (k = 6), d = 15 | rows best_d ≠ best_20 8,772; HORIZON = 1 share 0.3298; fallback-Pq flags {'pv_shorter_than_k': 5, 'forcing_to_pv_end': 1} |
| A1.5 (d = 12 share within 20–80%) | yes: k = 6 stands |

## 1. H1 primary: V20(h) ~ V20(best_d) + V20(best_20) + difficulty + clock + elo + (1 | player) + (1 | game)

| d | N | β_d | 95% interval | λ_d | 95% interval | β_d / λ_d | 95% interval | b_d | Selected optimizer (full data) |
|---|---|---|---|---|---|---|---|---|---|
| 2 | 49,921 | 0.1963 | [0.1748, 0.2137] | 0.9473 | [0.9195, 0.9624] | 0.2072 | [0.1853, 0.2278] | 0.0526 | cg |
| 4 | 49,921 | 0.2091 | [0.1841, 0.2306] | 0.8983 | [0.8469, 0.9275] | 0.2328 | [0.2048, 0.2616] | 0.0909 | nm |
| 8 | 49,921 | 0.2355 | [0.1992, 0.2668] | 0.6482 | [0.4639, 0.7511] | 0.3632 | [0.2857, 0.5143] | 0.3470 | cg |

| Quantity | Estimate | 95% interval | Draws |
|---|---|---|---|
| Δ = β_2/λ_2 − β_8/λ_8 | -0.1560 | [-0.3064, -0.0784] | 2,000 |
| β_2/λ_2 − β_4/λ_4 | -0.0256 | [-0.0519, -0.0015] | 2,000 |
| β_4/λ_4 − β_8/λ_8 | -0.1305 | [-0.2748, -0.0580] | 2,000 |
| Raw β_2 − β_8 (observed) | -0.0392 | [-0.0738, -0.0027] | 2,000 |
| Noise benchmark: raw β_2 − β_8 implied by equal true coefficients, (λ_2 − λ_8) × β* | 0.0801 | [0.0477, 0.1519] | 2,000 |

β* = mean of β_d/λ_d over d ∈ {2, 4, 8} = 0.2677: the common true coefficient under the null of equal true coefficients, under which the disattenuated coefficients are equal (Δ = 0) and the raw coefficients differ only by attenuation, β_d = λ_d β*.

**Recorded prediction (A1.3): Δ < 0 with the interval excluding zero — PASS.**

Full-data convergence (five-optimizer sweep):

| Model | Optimizer | Converged | Log-likelihood | Degenerate | Seconds |
|---|---|---|---|---|---|
| H1_d2 | lbfgs | False | -149650.294 | False | 9.38 |
| H1_d2 | bfgs | False | -150194.971 | False | 6.65 |
| H1_d2 | powell | True | -149631.539 | False | 7.86 |
| H1_d2 | nm | True | -149631.495 | False | 7.94 |
| H1_d2 | cg | True | -149631.495 | False | 4.68 |
| H1_d4 | lbfgs | True | -150059.362 | False | 9.21 |
| H1_d4 | bfgs | False | -150389.073 | False | 6.45 |
| H1_d4 | powell | True | -149832.126 | False | 7.68 |
| H1_d4 | nm | True | -149832.076 | False | 8.25 |
| H1_d4 | cg | True | -149832.076 | False | 5.38 |
| H1_d8 | lbfgs | False | -150339.565 | False | 9.41 |
| H1_d8 | bfgs | False | -150746.398 | False | 6.57 |
| H1_d8 | powell | True | -150192.646 | False | 7.69 |
| H1_d8 | nm | True | -150192.601 | False | 8.17 |
| H1_d8 | cg | True | -150192.601 | False | 5.55 |

| Model | Player variance | Game variance | Residual variance |
|---|---|---|---|
| H1_d2 | 0.3453 | 0.7599 | 22.6139 |
| H1_d4 | 0.3729 | 0.7344 | 22.8038 |
| H1_d8 | 0.3742 | 0.7822 | 23.1144 |

## 2. H1 secondary

### 2a. Raw slope of L_h on e_d, all rows (OLS), next to b_d

| d | N | Raw slope | 95% interval | Draws | b_d (noise-implied raw slope) |
|---|---|---|---|---|---|
| 2 | 50,021 | 0.2431 | [0.2244, 0.2631] | 500 | 0.0526 |
| 4 | 50,021 | 0.2616 | [0.2384, 0.2881] | 500 | 0.0909 |
| 8 | 50,021 | 0.2993 | [0.2608, 0.3399] | 500 | 0.3470 |

### 2b. Binned E[L_h | e_d], deciles of e_d among rows with e_d > 0

| d | Decile | e_d range | N | Mean L_h | 95% interval |
|---|---|---|---|---|---|
| 2 | 1 | 0.038–0.548 | 2,182 | 1.6000 | [1.4446, 1.7519] |
| 2 | 2 | 0.548–1.008 | 2,181 | 1.5256 | [1.3881, 1.6568] |
| 2 | 3 | 1.008–1.500 | 2,183 | 1.7547 | [1.6208, 1.8839] |
| 2 | 4 | 1.500–2.101 | 2,180 | 2.0660 | [1.9337, 2.2313] |
| 2 | 5 | 2.101–2.760 | 2,183 | 2.4034 | [2.2614, 2.5797] |
| 2 | 6 | 2.760–3.588 | 2,181 | 2.7338 | [2.5788, 2.8966] |
| 2 | 7 | 3.588–4.818 | 2,182 | 3.1890 | [3.0269, 3.3724] |
| 2 | 8 | 4.818–6.768 | 2,182 | 3.6523 | [3.4721, 3.8627] |
| 2 | 9 | 6.768–10.773 | 2,182 | 4.8196 | [4.5694, 5.0869] |
| 2 | 10 | 10.773–69.775 | 2,182 | 7.0015 | [6.5845, 7.4590] |
| 4 | 1 | 0.016–0.460 | 2,041 | 1.4756 | [1.3340, 1.6141] |
| 4 | 2 | 0.460–0.918 | 2,053 | 1.6803 | [1.5074, 1.8421] |
| 4 | 3 | 0.918–1.375 | 2,044 | 1.7441 | [1.6132, 1.8856] |
| 4 | 4 | 1.375–1.841 | 2,049 | 1.9297 | [1.7958, 2.0848] |
| 4 | 5 | 1.841–2.482 | 2,047 | 2.3150 | [2.1742, 2.4722] |
| 4 | 6 | 2.482–3.256 | 2,047 | 2.6340 | [2.4765, 2.8000] |
| 4 | 7 | 3.256–4.233 | 2,047 | 2.9061 | [2.7371, 3.0966] |
| 4 | 8 | 4.233–5.804 | 2,047 | 3.4699 | [3.2909, 3.6692] |
| 4 | 9 | 5.804–9.011 | 2,047 | 4.3550 | [4.1060, 4.5948] |
| 4 | 10 | 9.011–69.775 | 2,047 | 6.5771 | [6.1805, 6.9955] |
| 8 | 1 | 0.033–0.367 | 1,461 | 1.4093 | [1.2527, 1.5790] |
| 8 | 2 | 0.367–0.707 | 1,462 | 1.5885 | [1.4403, 1.7428] |
| 8 | 3 | 0.707–1.012 | 1,461 | 1.7777 | [1.6093, 1.9378] |
| 8 | 4 | 1.012–1.378 | 1,462 | 2.1517 | [1.9201, 2.3656] |
| 8 | 5 | 1.378–1.821 | 1,461 | 2.0035 | [1.8373, 2.1807] |
| 8 | 6 | 1.821–2.313 | 1,463 | 2.2777 | [2.1198, 2.4614] |
| 8 | 7 | 2.313–2.997 | 1,461 | 2.8900 | [2.6632, 3.1230] |
| 8 | 8 | 2.997–4.041 | 1,461 | 3.2151 | [2.9788, 3.4500] |
| 8 | 9 | 4.041–6.025 | 1,462 | 4.0170 | [3.7511, 4.3217] |
| 8 | 10 | 6.025–54.774 | 1,462 | 5.9417 | [5.5631, 6.3170] |

### 2c. Covariate-adjusted: L_h ~ e_d_z + difficulty + clock + elo + (1 | player) + (1 | game)

| d | N | e_d_z coefficient | 95% interval | Draws |
|---|---|---|---|---|
| 2 | 49,921 | 0.9595 | [0.8687, 1.0444] | 500 |
| 4 | 49,921 | 0.8487 | [0.7517, 0.9407] | 500 |
| 8 | 49,921 | 0.5815 | [0.4923, 0.6601] | 500 |

### 2d. Common row set {best_8 ≠ best_20}: H1 primary at d = 2, 4, 8

| d | N | β_d | 95% interval | β_d / λ_d | 95% interval |
|---|---|---|---|---|---|
| 2 | 18,277 | 0.1721 | [0.1379, 0.2011] | 0.1816 | [0.1449, 0.2145] |
| 4 | 18,277 | 0.1746 | [0.1370, 0.2060] | 0.1943 | [0.1524, 0.2308] |
| 8 | 18,277 | 0.2300 | [0.1785, 0.2739] | 0.3548 | [0.2600, 0.5135] |

Δ on the common row set = -0.1732, 95% interval [-0.3345, -0.0892] (500 draws). λ_d from the full check rows, recomputed per draw.

## 3. H2: L_h ~ HORIZON + e_d_z + difficulty + clock + elo + (1 | player) + (1 | game), rows best_d ≠ best_20

| d | Outcome | N | HORIZON coefficient | 95% interval | Draws | Recorded prediction (negative, interval excluding zero) |
|---|---|---|---|---|---|---|
| 2 | L_h | 25,240 | -0.0076 | [-0.1767, 0.1174] | 2,000 | FAIL |
| 2 | 1[h = best_d] (linear probability) | 25,240 | 0.0254 | [0.0116, 0.0353] | 2,000 | no recorded prediction |
| 4 | L_h | 23,956 | -0.0502 | [-0.2010, 0.0669] | 2,000 | FAIL |
| 4 | 1[h = best_d] (linear probability) | 23,956 | 0.0333 | [0.0202, 0.0441] | 2,000 | no recorded prediction |
| 8 | L_h | 18,277 | 0.0542 | [-0.1086, 0.1858] | 2,000 | FAIL |
| 8 | 1[h = best_d] (linear probability) | 18,277 | 0.0351 | [0.0189, 0.0450] | 2,000 | no recorded prediction |

## 4. H3 (descriptive, point estimates, no test)

Terciles on all rows: Elo cut points [253, 2418, 2670, 3416]; clock (time_pressure) cut points [0.005, 0.763, 0.883, 1.15]. β_d/λ_d uses the full-sample λ_d.

| Split | Tercile | d | N (H1) | H1 β_d / λ_d | N (H2) | H2 HORIZON coefficient |
|---|---|---|---|---|---|---|
| elo | 1 | 2 | 16,698 | 0.2269 | 8,327 | 0.0973 |
| elo | 1 | 4 | 16,698 | 0.2236 | 7,928 | 0.0071 |
| elo | 1 | 8 | 16,698 | 0.2967 | 6,098 | 0.2645 |
| elo | 2 | 2 | 16,624 | 0.2092 | 8,458 | -0.1020 |
| elo | 2 | 4 | 16,624 | 0.2513 | 7,990 | -0.1596 |
| elo | 2 | 8 | 16,624 | 0.4182 | 6,146 | -0.1437 |
| elo | 3 | 2 | 16,599 | 0.1863 | 8,455 | -0.0120 |
| elo | 3 | 4 | 16,599 | 0.2244 | 8,038 | 0.0097 |
| elo | 3 | 8 | 16,599 | 0.3868 | 6,033 | 0.0336 |
| clock | 1 | 2 | 16,697 | 0.2355 | 8,439 | -0.1405 |
| clock | 1 | 4 | 16,697 | 0.2634 | 7,962 | -0.1458 |
| clock | 1 | 8 | 16,697 | 0.3364 | 6,137 | -0.1466 |
| clock | 2 | 2 | 16,665 | 0.2029 | 8,396 | 0.2505 |
| clock | 2 | 4 | 16,665 | 0.2051 | 7,936 | 0.0439 |
| clock | 2 | 8 | 16,665 | 0.4150 | 6,137 | 0.2070 |
| clock | 3 | 2 | 16,559 | 0.1466 | 8,405 | -0.1036 |
| clock | 3 | 4 | 16,559 | 0.1991 | 8,058 | -0.0599 |
| clock | 3 | 8 | 16,559 | 0.3601 | 6,003 | 0.1537 |

## 5. Descriptives: I_d against E_d

| d | E_d = mean e_d | 95% interval | Mean I_d | 95% interval | HORIZON = 1 share (best_d ≠ best_20) |
|---|---|---|---|---|---|
| 2 | 2.0074 | [1.9543, 2.0614] | -0.5090 | [-0.5779, -0.4384] | 0.3356 |
| 4 | 1.5962 | [1.5544, 1.6381] | -0.9202 | [-0.9834, -0.8485] | 0.3400 |
| 8 | 0.7562 | [0.7334, 0.7795] | -1.7602 | [-1.8242, -1.6932] | 0.3424 |
| 12 | 0.3163 | [0.3034, 0.3291] | -2.2002 | [-2.2672, -2.1299] | 0.3351 |
| 15 | 0.1330 | [0.1252, 0.1411] | -2.3834 | [-2.4509, -2.3134] | 0.3298 |

E* = mean L_h = 2.5164, 95% interval [2.4464, 2.5837]. By identity I_d = e_d − L_h row by row, so mean I_d = E_d − E*: the curve has slope one and crosses zero at E_d = E*. This is what the identity implies, not a finding. Figure: `figures/spec_v5/fig_Id_curve.png`. 2,000 draws.

## 6. Robustness

### 6.1 HORIZON with k = 4 and k = 8 (H2 refit)

| k | d | Outcome | N | HORIZON coefficient | 95% interval | Draws |
|---|---|---|---|---|---|---|
| 4 | 2 | L_h | 25,240 | -0.1740 | [-0.3579, -0.0342] | 500 |
| 4 | 2 | 1[h = best_d] | 25,240 | 0.0215 | [0.0075, 0.0327] | 500 |
| 4 | 4 | L_h | 23,956 | -0.1380 | [-0.2924, -0.0024] | 500 |
| 4 | 4 | 1[h = best_d] | 23,956 | 0.0369 | [0.0217, 0.0472] | 500 |
| 4 | 8 | L_h | 18,277 | -0.0556 | [-0.2093, 0.0905] | 500 |
| 4 | 8 | 1[h = best_d] | 18,277 | 0.0379 | [0.0221, 0.0487] | 500 |
| 8 | 2 | L_h | 25,240 | 0.0628 | [-0.0891, 0.1704] | 500 |
| 8 | 2 | 1[h = best_d] | 25,240 | 0.0233 | [0.0099, 0.0325] | 500 |
| 8 | 4 | L_h | 23,956 | 0.0016 | [-0.1418, 0.1044] | 500 |
| 8 | 4 | 1[h = best_d] | 23,956 | 0.0311 | [0.0184, 0.0409] | 500 |
| 8 | 8 | L_h | 18,277 | 0.0653 | [-0.0879, 0.1844] | 500 |
| 8 | 8 | 1[h = best_d] | 18,277 | 0.0354 | [0.0197, 0.0439] | 500 |

### 6.2 Depth-15 ruler, anchor best_15_singlepv, all rows

Pilot λ values on the depth-15 ruler admit depth 4 only (λ_4 = 0.810; no pilot λ at depths 2 and 8; depth 12 had Var(V20 − V15)/Var(e_12) = 1.6–1.9). Depth-15 evaluations after best_4 run for this item: 19,056; missing after the run: {'V15_h': 0, 'V15_b15': 0, 'V15_b4': 0, 'HORIZON15_4_on_dis_rows': 0}.

| Model | N | Coefficient | Estimate | 95% interval | Draws |
|---|---|---|---|---|---|
| H1 primary, d = 4 | 49,921 | β_4 on V15(best_4) | 0.1990 | [0.1744, 0.2214] | 500 |
| | | β_4 / 0.810 | 0.2456 | [0.2153, 0.2733] | |
| H2 (L15), d = 4 | 23,589 | HORIZON (depth-15 PV) | -0.0806 | [-0.2379, 0.0360] | 500 |
| H2 (1[h = best_4]), d = 4 | 23,589 | HORIZON (depth-15 PV) | 0.0300 | [0.0155, 0.0398] | 500 |

### 6.3 Deviation rows only (28,647 v3 rows)

| Model | d | N | Coefficient | Estimate | 95% interval | Draws |
|---|---|---|---|---|---|---|
| H1 primary | 2 | 28,647 | β_d | 0.1527 | [0.1281, 0.1741] | 500 |
| | | | β_d / λ_d | 0.1612 | [0.1349, 0.1866] | |
| H1 primary | 4 | 28,647 | β_d | 0.1458 | [0.1174, 0.1704] | 500 |
| | | | β_d / λ_d | 0.1623 | [0.1298, 0.1919] | |
| H1 primary | 8 | 28,647 | β_d | 0.1374 | [0.0925, 0.1723] | 500 |
| | | | β_d / λ_d | 0.2119 | [0.1364, 0.3105] | |
| H1 primary | Δ = β_2/λ_2 − β_8/λ_8 | | | -0.0508 | [-0.1517, 0.0181] | 500 |
| H2 (L_h) | 2 | 18,072 | HORIZON | 0.0003 | [-0.2191, 0.1370] | 500 |
| H2 (1[h = best_d]) | 2 | 18,072 | HORIZON | 0.0268 | [0.0100, 0.0401] | 500 |
| H2 (L_h) | 4 | 17,087 | HORIZON | -0.0247 | [-0.1848, 0.1387] | 500 |
| H2 (1[h = best_d]) | 4 | 17,087 | HORIZON | 0.0372 | [0.0202, 0.0503] | 500 |
| H2 (L_h) | 8 | 13,415 | HORIZON | 0.0782 | [-0.1137, 0.2352] | 500 |
| H2 (1[h = best_d]) | 8 | 13,415 | HORIZON | 0.0264 | [0.0077, 0.0397] | 500 |

## Recorded predictions

- H1 (A1.3): Δ = β_2/λ_2 − β_8/λ_8 < 0 with the interval excluding zero: Δ = -0.1560, [-0.3064, -0.0784] — **PASS**.
- H2, d = 2: HORIZON coefficient on L_h negative with the interval excluding zero: -0.0076, [-0.1767, 0.1174] — **FAIL**.
- H2, d = 4: HORIZON coefficient on L_h negative with the interval excluding zero: -0.0502, [-0.2010, 0.0669] — **FAIL**.
- H2, d = 8: HORIZON coefficient on L_h negative with the interval excluding zero: 0.0542, [-0.1086, 0.1858] — **FAIL**.

## Figures

- `figures/spec_v5/fig_H1_disattenuated.png`: β_d/λ_d against depth with 95% intervals; raw β_d; the noise benchmark (equal true coefficients: β* flat after disattenuation, λ_d β* before).
- `figures/spec_v5/fig_Id_curve.png`: mean I_d against E_d at d = 2, 4, 8, 12, 15 with 95% intervals; the line mean I_d = E_d − E* is the identity I_d = e_d − L_h.

## Limits (§8, plus the ruler resolution)

- One platform, fast time controls, titled players.
- The ruler is an engine (depth 20 by Amendment A1), not ground truth.
- HORIZON is a proxy for visibility, not a measure of what the player saw.
- The human's move is fixed, so nothing here measures what a human would do when shown a shallow engine.
- The v3 difficulty features were built for the opponent's error and are used for the mover's difficulty (§1).
- Ruler resolution: the engine disagrees with itself between adjacent depths by about one WP point in SD at both steps measured: SD(V20 − V15) = 1.35–1.46 on the 2,000-row subsample (pilot report §6, §12) and SD(V25 − V20) = 1.09–1.16 on 1,000 rows (`reports/spec_v5_A1_check.md` §1). Depths 12 and 15 are excluded from §6 because their Var(e_d) is of that order (λ_12 = −0.139, λ_15 = −1.503).

## Exploratory, post-results

Requested by the designer on 2026-09-28, after the results above were read. Not in the specification; no recorded prediction; same estimator, rows, covariates and bootstrap procedure (nm first, full sweep on non-convergence, λ_d recomputed per draw on the check rows of the drawn games).

### X.a H1 primary on rows with h ≠ best_d

| d | N | β_d | 95% interval | β_d / λ_d | 95% interval | Draws | nm / fallback / failed |
|---|---|---|---|---|---|---|---|
| 2 | 28,645 | -0.1840 | [-0.2062, -0.1616] | -0.1942 | [-0.2181, -0.1706] | 500 | 500 / 0 / 0 |
| 4 | 29,425 | -0.2131 | [-0.2374, -0.1893] | -0.2373 | [-0.2690, -0.2093] | 500 | 500 / 0 / 0 |
| 8 | 28,459 | -0.2668 | [-0.3160, -0.2293] | -0.4116 | [-0.6047, -0.3285] | 500 | 500 / 0 / 0 |

Δ = β_2/λ_2 − β_8/λ_8 on these rows = 0.2173, 95% interval [0.1380, 0.4064] (500 draws). Full-data optimizer: d = 2 lbfgs, d = 4 nm, d = 8 nm.

### X.b P(h = best_d)

| d | All rows: N | P(h = best_d) | Rows best_d ≠ best_20: N | P(h = best_d) among them |
|---|---|---|---|---|
| 2 | 50,021 | 0.4273 | 25,240 | 0.2491 |
| 4 | 50,021 | 0.4117 | 23,956 | 0.2227 |
| 8 | 50,021 | 0.4311 | 18,277 | 0.2345 |
| 12 | 50,021 | 0.4404 | 12,414 | 0.2391 |
| 15 | 50,021 | 0.4432 | 8,772 | 0.2429 |

For reference, P(h = best_20) = 0.4431 on all 50,021 rows.

### X.c H2 second outcome 1[h = best_d] with HORIZON at k = 4

Already estimated as part of robustness (1) (§6.1, models R1_hb_d{2,4,8}_k4, 500 draws); repeated here next to the L_h outcome at k = 4. No new fit.

| d | Outcome | N | HORIZON (k = 4) coefficient | 95% interval | Draws |
|---|---|---|---|---|---|
| 2 | L_h | 25,240 | -0.1740 | [-0.3579, -0.0342] | 500 |
| 2 | 1[h = best_d] | 25,240 | 0.0215 | [0.0075, 0.0327] | 500 |
| 4 | L_h | 23,956 | -0.1380 | [-0.2924, -0.0024] | 500 |
| 4 | 1[h = best_d] | 23,956 | 0.0369 | [0.0217, 0.0472] | 500 |
| 8 | L_h | 18,277 | -0.0556 | [-0.2093, 0.0905] | 500 |
| 8 | 1[h = best_d] | 18,277 | 0.0379 | [0.0221, 0.0487] | 500 |
