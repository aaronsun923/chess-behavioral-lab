# Paper 4 correction: random-effects estimator — report

_Generated 2026-09-11 21:07. Executes `specs/paper4_correction_spec.md` (LOCKED 2026-09-11). Code: `code/paper4_mixed_v2.py` (the §2 estimator), `code/paper4_correction_run.py` (sandbox, §3.4, re-run), `code/paper4_correction_report.py` (this file)._


## 0. Summary

- §3.4 verification of the v3 expected-error model: **PASSED** (10/10 fold fits converged at the maximum; `E_played`/`E_best` reproduction passed).
- Re-run list: 23 models; 23 completed every check; 0 stopped.
- §4 reading on the 29 core coefficients of the completed models: **0 changes**.


## 1. Environment and integrity

| item | value |
|---|---|
| python | 3.9.6 |
| statsmodels | 0.14.6 (on record: 0.14.6) |
| lightgbm | 4.6.0 |
| platform | Darwin arm64, 10 cores |
| `code/paper4_report.py` SHA-256 before | `e3a25f66df06910728b9bb88a9b86883f0d1d238f449e566ead0edcb116c2695` |
| `code/paper4_report.py` SHA-256 after | `e3a25f66df06910728b9bb88a9b86883f0d1d238f449e566ead0edcb116c2695` (unchanged) |
| sandbox | scripts ran unmodified in a scratch directory with read-only links to the inputs and private copies of every file they write; no engine binary was reachable |
| files under the data root modified since setup | none |

`git status --porcelain` immediately before this report was written:

```
?? behavioral-lab-logo-under-1mb.png
?? code/paper4_correction_report.py
?? code/paper4_correction_run.py
?? code/paper4_mixed_v2.py
?? docs/paper4_correction_REPORT.md
```


## 2. Verification of the v3 expected-error model (§3.4)

Each fold fit of `crossfit(kind='lmm')` was fitted with all five optimizers while `p4_v3_analysis.py` ran; the `lbfgs` fit, which v3 used, was handed back so the script proceeded exactly as in v3. No model on the re-run list was fitted in this stage. "At the maximum" = `lbfgs` converged and its log-likelihood is no more than 0.1 below the highest converged log-likelihood in the fold's sweep.

| training set | fold | rows | players | lbfgs | bfgs | powell | nm | cg | lbfgs gap to max | at maximum |
|---|---|---|---|---|---|---|---|---|---|---|
| main training set | 1 | 16,315 | 1,971 | conv -44507.451 | conv -44507.451 | conv -44507.451 | conv -44507.451 | conv -44507.451 | 0.0000 | yes |
| main training set | 2 | 16,376 | 1,974 | conv -44607.129 | conv -44607.129 | conv -44607.129 | conv -44607.129 | conv -44607.129 | 0.0000 | yes |
| main training set | 3 | 16,223 | 1,959 | conv -44441.283 | conv -44441.283 | conv -44441.283 | conv -44441.283 | NOT conv -44456.464 | 0.0000 | yes |
| main training set | 4 | 16,393 | 1,976 | conv -44813.040 | conv -44813.040 | conv -44813.040 | conv -44813.040 | conv -44813.040 | 0.0000 | yes |
| main training set | 5 | 16,241 | 1,965 | conv -44237.502 | conv -44237.502 | conv -44237.502 | conv -44237.502 | conv -44237.502 | 0.0000 | yes |
| unrestricted training set, §7.2 | 1 | 39,795 | 1,975 | conv -112169.449 | conv -112169.449 | conv -112169.449 | conv -112169.449 | NOT conv -113450.985 | 0.0000 | yes |
| unrestricted training set, §7.2 | 2 | 40,150 | 1,982 | conv -112863.198 | conv -112863.198 | conv -112863.198 | conv -112863.198 | NOT conv -114121.443 | 0.0000 | yes |
| unrestricted training set, §7.2 | 3 | 39,823 | 1,968 | conv -112474.177 | conv -112474.177 | conv -112474.177 | conv -112474.177 | NOT conv -113732.170 | 0.0000 | yes |
| unrestricted training set, §7.2 | 4 | 40,157 | 1,984 | conv -113214.442 | conv -113214.442 | conv -113214.442 | conv -113214.442 | NOT conv -114528.857 | 0.0000 | yes |
| unrestricted training set, §7.2 | 5 | 39,759 | 1,973 | conv -112027.598 | conv -112027.598 | conv -112027.598 | conv -112027.598 | NOT conv -113281.569 | 0.0000 | yes |

**Reproduction (§3.4 item 4).** The re-executed `lbfgs` fits regenerated `p4_v3_rows_analysis.parquet` inside the sandbox; against the stored file (28,603 rows; 0 unmatched keys): `E_played` max |difference| = 0 over 27,467 rows (0 missing-value mismatches); `E_best` max |difference| = 0 over 27,452 rows (0 missing-value mismatches). Tolerance 1e-9. The §7.2 predictions are not stored; their reproduction is checked through T-10 (§3 below).


**Outcome (§3.4 item 5).** All 10 fold fits converged at the maximum and the stored predictions reproduce. The expected-error model stands; `RES`, `CF` and `NET_realized` are unchanged, and the re-run proceeded on the stored values.


Warnings raised during the sweep (all optimizers, all folds): "Gradient optimization failed, |grad| = 1573.750183"; "Gradient optimization failed, |grad| = 1573.824508"; "Gradient optimization failed, |grad| = 1575.253965"; "Gradient optimization failed, |grad| = 1585.881780"; "Gradient optimization failed, |grad| = 1603.324545"; "Gradient optimization failed, |grad| = 366.810442"; "Maximum Likelihood optimization failed to converge. Check mle_retvals"; "MixedLM optimization failed, trying a different optimizer may help."; "Random effects covariance is singular"; "The Hessian matrix at the estimated parameter values is not positive definite.".


## 3. Side-by-side table (§3.1 item 5)

Old coefficient and CI: as published. Old fit: the optimizer the unchanged `fit_mixed` selected on the rebuilt rows and that fit's `converged` flag. Variance components on the natural scale, player / game / residual; the old fits estimated no player variance (spec §1.1). New fit: `fit_mixed_v2`. §4 reading: sign and whether the 95% CI excludes zero, old (published) vs new.

| ID | core coefficient | old coef [95% CI] (published) | new coef [95% CI] | old fit | new fit | old variance (player / game / residual) | new variance (player / game / residual) | §4 reading |
|---|---|---|---|---|---|---|---|---|
| V1-1 | `elo_z` | -0.2346 [-0.2930, -0.1763] | -0.2308 [-0.2985, -0.1632] | lbfgs, converged=True | nm, converged=True | not estimated / 0.4890 / 16.1394 | 0.2407 / 0.2528 / 16.1383 | stands |
| V1-1 | `elo_z:gap_12_z` | -0.0291 [-0.0762, +0.0180] | -0.0283 [-0.0753, +0.0187] | lbfgs, converged=True | nm, converged=True | not estimated / 0.4890 / 16.1394 | 0.2407 / 0.2528 / 16.1383 | stands |
| V1-1 | `elo_z:time_pressure_z` | -0.0392 [-0.0893, +0.0109] | -0.0398 [-0.0901, +0.0105] | lbfgs, converged=True | nm, converged=True | not estimated / 0.4890 / 16.1394 | 0.2407 / 0.2528 / 16.1383 | stands |
| V1-2 | `elo_z` | -0.3018 [-0.3436, -0.2600] | -0.3021 [-0.3467, -0.2575] | lbfgs, converged=True | nm, converged=True | not estimated / 0.4754 / 16.4472 | 0.2391 / 0.2400 / 16.4463 | stands |
| V1-2 | `elo_z:gap_12_z` | -0.0476 [-0.0845, -0.0107] | -0.0474 [-0.0842, -0.0105] | lbfgs, converged=True | nm, converged=True | not estimated / 0.4754 / 16.4472 | 0.2391 / 0.2400 / 16.4463 | stands |
| V1-2 | `elo_z:time_pressure_z` | -0.0372 [-0.0712, -0.0032] | -0.0381 [-0.0721, -0.0041] | lbfgs, converged=True | nm, converged=True | not estimated / 0.4754 / 16.4472 | 0.2391 / 0.2400 / 16.4463 | stands |
| V1-3 | `WPL_self_z` | +0.8315 [+0.7916, +0.8714] | +0.8287 [+0.7888, +0.8686] | lbfgs, converged=True | nm, converged=True | not estimated / 0.3506 / 16.6454 | 0.1423 / 0.2100 / 16.6449 | stands |
| V1-4 | `WPL_self_z` | +0.7564 [+0.7116, +0.8011] | +0.7539 [+0.7091, +0.7986] | lbfgs, converged=True | nm, converged=True | not estimated / 0.4771 / 16.4024 | 0.1625 / 0.3164 / 16.4019 | stands |
| B-1 | `Intercept` | +1.2155 [+1.0240, +1.4071] | +1.2155 [+1.0239, +1.4071] | bfgs, converged=True | powell, converged=True | not estimated / 4.6075 / 162.5266 | 0.0000 / 4.6074 / 162.5267 | stands |
| B-2 | `Intercept` | +1.2146 [+1.0685, +1.3607] | +1.2146 [+1.0683, +1.3608] | bfgs, converged=True | nm, converged=True | not estimated / 2.1278 / 97.7478 | 0.0000 / 2.1268 / 97.7487 | stands |
| B-2 | `dmat_c` | -5.8055 [-5.9266, -5.6844] | -5.8055 [-5.9266, -5.6844] | bfgs, converged=True | nm, converged=True | not estimated / 2.1278 / 97.7478 | 0.0000 / 2.1268 / 97.7487 | stands |
| B-3 | `Intercept` | +0.4491 [+0.3698, +0.5283] | +0.4491 [+0.3698, +0.5284] | bfgs, converged=True | powell, converged=True | not estimated / 0.7976 / 27.7732 | 0.0000 / 0.7976 / 27.7732 | stands |
| B-4 | `Intercept` | +1.4749 [+1.2979, +1.6519] | +1.4749 [+1.2979, +1.6519] | bfgs, converged=True | powell, converged=True | not estimated / 5.2225 / 167.3927 | 0.0000 / 5.2234 / 167.3920 | stands |
| B-5 | `Intercept` | +1.166 [+0.787, +1.544] | +1.1778 [+0.7910, +1.5645] | bfgs, converged=True | nm, converged=True | not estimated / 3.4969 / 169.0712 | 3.6435 / 0.0000 / 168.9191 | stands |
| T-1 | `Intercept` | -1.7223 [-1.7890, -1.6556] | -1.7504 [-1.8101, -1.6907] | bfgs, converged=False | nm, converged=True | not estimated / 1.4345 / 13.8511 | 0.0459 / 0.3595 / 14.5727 | stands |
| T-2 | `delta_risk_steep_z` | -0.4751 [-0.5272, -0.4229] | -0.4754 [-0.5276, -0.4232] | lbfgs, converged=True | nm, converged=True | not estimated / 0.4511 / 13.0172 | 0.0868 / 0.3635 / 13.0180 | stands |
| T-3 | `delta_risk_steep_z:time_pressure_opp_z` | +0.0130 [-0.0381, +0.0642] | +0.0129 [-0.0382, +0.0641] | lbfgs, converged=True | nm, converged=True | not estimated / 0.4512 / 13.0183 | 0.0867 / 0.3637 / 13.0191 | stands |
| T-3 | `delta_risk_steep_z:elo_diff_opp_z` | -0.0045 [-0.0530, +0.0441] | -0.0046 [-0.0531, +0.0439] | lbfgs, converged=True | nm, converged=True | not estimated / 0.4512 / 13.0183 | 0.0867 / 0.3637 / 13.0191 | stands |
| T-4 | `delta_risk_steep_z` | -0.0854 [-0.1372, -0.0337] | -0.0862 [-0.1380, -0.0343] | bfgs, converged=False | lbfgs, converged=True | not estimated / 0.9761 / 12.4528 | 0.0801 / 0.3551 / 12.8599 | stands |
| T-5 | `delta_risk_steep_z` | -0.3899 [-0.3970, -0.3827] | -0.3899 [-0.3971, -0.3828] | bfgs, converged=True | nm, converged=True | not estimated / 0.0038 / 0.2491 | 0.0008 / 0.0029 / 0.2491 | stands |
| T-6 | `WPL_self_z` | +0.2091 [+0.1445, +0.2736] | +0.2082 [+0.1437, +0.2727] | lbfgs, converged=True | nm, converged=True | not estimated / 0.2571 / 12.6836 | 0.0874 / 0.1706 / 12.6828 | stands |
| T-7 | `delta_risk_steep_z` | -0.4756 [-0.5257, -0.4255] | -0.4759 [-0.5260, -0.4258] | lbfgs, converged=True | nm, converged=True | not estimated / 0.4659 / 15.2011 | 0.0685 / 0.3972 / 15.2014 | stands |
| T-8 | `delta_risk_steep_z` | -0.0755 [-0.1252, -0.0258] | -0.0758 [-0.1255, -0.0261] | bfgs, converged=True | nm, converged=True | not estimated / 0.4606 / 14.9617 | 0.0795 / 0.3817 / 14.9613 | stands |
| T-9 | `delta_risk_steep_z` | -0.4012 [-0.4081, -0.3942] | -0.4013 [-0.4082, -0.3943] | bfgs, converged=True | nm, converged=True | not estimated / 0.0044 / 0.2958 | 0.0010 / 0.0034 / 0.2958 | stands |
| T-10 | `delta_risk_steep_z` | -0.1298 [-0.1818, -0.0778] | -0.1295 [-0.1814, -0.0776] | bfgs, converged=False | lbfgs, converged=True | not estimated / 0.3289 / 13.0448 | 0.1048 / 0.5895 / 12.7223 | stands |
| T-11 | `delta_risk_steep_z` | -0.1002 [-0.1504, -0.0501] | -0.1005 [-0.1506, -0.0504] | bfgs, converged=True | nm, converged=True | not estimated / 0.2696 / 12.6390 | 0.0565 / 0.2133 / 12.6390 | stands |
| T-12 | `delta_risk_steep_z` | -0.3548 [-0.3699, -0.3396] | -0.3546 [-0.3698, -0.3395] | bfgs, converged=True | nm, converged=True | not estimated / 0.0182 / 1.1592 | 0.0062 / 0.0121 / 1.1591 | stands |
| T-13 | `delta_risk_steep_z` | +0.2179 [+0.1813, +0.2546] | +0.2179 [+0.1813, +0.2545] | lbfgs, converged=True | lbfgs, converged=True | not estimated / 0.1808 / 5.0085 | 0.0305 / 0.1498 / 5.0090 | stands |
| T-14 | `delta_risk_steep_z` | +0.4511 [+0.3052, +0.5970] | +0.4511 [+0.3052, +0.5970] | lbfgs, converged=True | nm, converged=True | not estimated / 2.4397 / 19.5828 | 0.0359 / 2.4028 / 19.5837 | stands |

**T-1 TOST (§4).** Published: overall p = 1, not equivalent. Re-executed old fit: p = 1 (not equivalent). New fit: p = 1 (p lower 1, p upper 0) → **not equivalent** at α = .05 against ±0.5 WP points; verdict unchanged.


## 4. Checks and per-optimizer record


### 4.1 N and reproduction (§3.1 items 1–2)

| ID | published N | rebuilt N | core values: published vs re-executed fit_mixed (printed precision) | status |
|---|---|---|---|---|
| V1-1 | 25,457 | 25,457 | `elo_z` ✓ (published -0.2346 [-0.2930, -0.1763], re-executed -0.2346 [-0.2930, -0.1763]); `elo_z:gap_12_z` ✓ (published -0.0291 [-0.0762, +0.0180], re-executed -0.0291 [-0.0762, +0.0180]); `elo_z:time_pressure_z` ✓ (published -0.0392 [-0.0893, +0.0109], re-executed -0.0392 [-0.0893, +0.0109]) | ok |
| V1-2 | 49,921 | 49,921 | `elo_z` ✓ (published -0.3018 [-0.3436, -0.2600], re-executed -0.3018 [-0.3436, -0.2600]); `elo_z:gap_12_z` ✓ (published -0.0476 [-0.0845, -0.0107], re-executed -0.0476 [-0.0845, -0.0107]); `elo_z:time_pressure_z` ✓ (published -0.0372 [-0.0712, -0.0032], re-executed -0.0372 [-0.0712, -0.0032]) | ok |
| V1-3 | 47,959 | 47,959 | `WPL_self_z` ✓ (published +0.8315 [+0.7916, +0.8714], re-executed +0.8315 [+0.7916, +0.8714]) | ok |
| V1-4 | 47,959 | 47,959 | `WPL_self_z` ✓ (published +0.7564 [+0.7116, +0.8011], re-executed +0.7564 [+0.7116, +0.8011]) | ok |
| B-1 | 19,842 | 19,842 | `Intercept` ✓ (published +1.2155 [+1.0240, +1.4071], re-executed +1.2155 [+1.0240, +1.4071]) | ok |
| B-2 | 19,842 | 19,842 | `Intercept` ✓ (published +1.2146 [+1.0685, +1.3607], re-executed +1.2146 [+1.0685, +1.3607]); `dmat_c` ✓ (published -5.8055 [-5.9266, -5.6844], re-executed -5.8055 [-5.9266, -5.6844]) | ok |
| B-3 | 19,842 | 19,842 | `Intercept` ✓ (published +0.4491 [+0.3698, +0.5283], re-executed +0.4491 [+0.3698, +0.5283]) | ok |
| B-4 | 25,012 | 25,012 | `Intercept` ✓ (published +1.4749 [+1.2979, +1.6519], re-executed +1.4749 [+1.2979, +1.6519]) | ok |
| B-5 | not published | 5,085 | `Intercept` ✓ (published +1.166 [+0.787, +1.544], re-executed +1.166 [+0.787, +1.544]) | ok |
| T-1 | 18,903 | 18,903 | `Intercept` ✓ (published -1.7223 [-1.7890, -1.6556], re-executed -1.7223 [-1.7890, -1.6556]) | ok |
| T-2 | 18,903 | 18,903 | `delta_risk_steep_z` ✓ (published -0.4751 [-0.5272, -0.4229], re-executed -0.4751 [-0.5272, -0.4229]) | ok |
| T-3 | 18,903 | 18,903 | `delta_risk_steep_z:time_pressure_opp_z` ✓ (published +0.0130 [-0.0381, +0.0642], re-executed +0.0130 [-0.0381, +0.0642]); `delta_risk_steep_z:elo_diff_opp_z` ✓ (published -0.0045 [-0.0530, +0.0441], re-executed -0.0045 [-0.0530, +0.0441]) | ok |
| T-4 | 18,905 | 18,905 | `delta_risk_steep_z` ✓ (published -0.0854 [-0.1372, -0.0337], re-executed -0.0854 [-0.1372, -0.0337]) | ok |
| T-5 | 18,885 | 18,885 | `delta_risk_steep_z` ✓ (published -0.3899 [-0.3970, -0.3827], re-executed -0.3899 [-0.3970, -0.3827]) | ok |
| T-6 | 19,204 | 19,204 | `WPL_self_z` ✓ (published +0.2091 [+0.1445, +0.2736], re-executed +0.2091 [+0.1445, +0.2736]) | ok |
| T-7 | 23,920 | 23,920 | `delta_risk_steep_z` ✓ (published -0.4756 [-0.5257, -0.4255], re-executed -0.4756 [-0.5257, -0.4255]) | ok |
| T-8 | 23,928 | 23,928 | `delta_risk_steep_z` ✓ (published -0.0755 [-0.1252, -0.0258], re-executed -0.0755 [-0.1252, -0.0258]) | ok |
| T-9 | 23,897 | 23,897 | `delta_risk_steep_z` ✓ (published -0.4012 [-0.4081, -0.3942], re-executed -0.4012 [-0.4081, -0.3942]) | ok |
| T-10 | 18,905 | 18,905 | `delta_risk_steep_z` ✓ (published -0.1298 [-0.1818, -0.0778], re-executed -0.1298 [-0.1818, -0.0778]) | ok |
| T-11 | 19,812 | 19,812 | `delta_risk_steep_z` ✓ (published -0.1002 [-0.1504, -0.0501], re-executed -0.1002 [-0.1504, -0.0501]) | ok |
| T-12 | 19,812 | 19,812 | `delta_risk_steep_z` ✓ (published -0.3548 [-0.3699, -0.3396], re-executed -0.3548 [-0.3699, -0.3396]) | ok |
| T-13 | 14,894 | 14,894 | `delta_risk_steep_z` ✓ (published +0.2179 [+0.1813, +0.2546], re-executed +0.2179 [+0.1813, +0.2546]) | ok |
| T-14 | 4,011 | 4,011 | `delta_risk_steep_z` ✓ (published +0.4511 [+0.3052, +0.5970], re-executed +0.4511 [+0.3052, +0.5970]) | ok |

Sources of published values: V1-1: paper4_pilot_REPORT.md, table "Linear mixed model — roster members only (PRIMARY)"; V1-2: paper4_pilot_REPORT.md, table "Linear mixed model — all rows"; V1-3: paper4_pilot_REPORT.md, table "Linear mixed model (primary result of the paper)"; V1-4: paper4_pilot_REPORT.md, table "Robustness: controls at the opponent's position"; B-1: paper4b_pilot_REPORT.md, table "Linear mixed model — §4.1 primary"; B-2: paper4b_pilot_REPORT.md, table "Linear mixed model — §4.1 + liquidation controls"; B-3: paper4b_pilot_REPORT.md, table "ΔRISK_var, WPL ∈ (0,5]"; B-4: paper4b_pilot_REPORT.md, table "ΔRISK_steep, WPL ∈ (0,10]"; B-5: figures/paper4/figB_pilot_vs_full.png (no N printed); T-1: paper4_v3_REPORT.md, table "H1: intercept-only mixed model"; T-2: paper4_v3_REPORT.md, table "H2: net realised gain"; T-3: paper4_v3_REPORT.md, table "H3: two pre-specified interactions"; T-4: paper4_v3_REPORT.md, table "H4a: RES"; T-5: paper4_v3_REPORT.md, table "H4b: CF"; T-6: paper4_v3_REPORT.md, table "for comparison only, not interpreted"; T-7: paper4_v3_REPORT.md, table "H2 on (0, 10]"; T-8: paper4_v3_REPORT.md, table "H4a on (0, 10]"; T-9: paper4_v3_REPORT.md, table "H4b on (0, 10]"; T-10: paper4_v3_REPORT.md, table "H4a with the unrestricted training set"; T-11: paper4_v3_REPORT.md, table "H4a with the LightGBM nuisance model"; T-12: paper4_v3_REPORT.md, table "H4b with the LightGBM nuisance model"; T-13: paper4_v3_REPORT.md, post-hoc §C table (n = subgroup rows); T-14: paper4_v3_REPORT.md, post-hoc §C table (n = subgroup rows).


### 4.2 Figure fits covered by report models (§3.1 item 3)

| figure fit | report model | N | report model N | figure intercept [CI] | re-executed intercept [CI] | result |
|---|---|---|---|---|---|---|
| `figB-full` | B-1 | 19,842 | 19,842 | +1.216 [+1.024, +1.407] | +1.216 [+1.024, +1.407] | covered |
| `figC-primary` | B-1 | 19,842 | 19,842 | +1.216 [+1.024, +1.407] | +1.216 [+1.024, +1.407] | covered |
| `figC-var` | B-3 | 19,842 | 19,842 | +0.449 [+0.370, +0.528] | +0.449 [+0.370, +0.528] | covered |
| `figC-band10` | B-4 | 25,012 | 25,012 | +1.475 [+1.298, +1.652] | +1.475 [+1.298, +1.652] | covered |
| `figC-liq` | B-2 | 19,842 | 19,842 | +1.215 [+1.068, +1.361] | +1.215 [+1.068, +1.361] | covered |

Every `fit_mixed` call made by the four scripts is either on the re-run list or a covered figure fit.


### 4.3 Per-optimizer record of `fit_mixed_v2` (§2 items 4, 9)

Each cell: converged flag and log-likelihood; **bold** = selected. "degenerate" per §2 item 5.

| ID | rows | lbfgs | bfgs | powell | nm | cg | status |
|---|---|---|---|---|---|---|---|
| V1-1 | 25,457 | NOT conv -71846.433 | NOT conv -72253.338 | conv -71844.847 | **conv -71844.839** | NOT conv -71875.045 | ok |
| V1-2 | 49,921 | conv -141462.143 | NOT conv -141969.901 | conv -141340.668 | **conv -141340.373** | NOT conv -144801.030 | ok |
| V1-3 | 47,959 | NOT conv -136092.760 | NOT conv -136591.188 | conv -135952.385 | **conv -135951.564** | NOT conv -139453.969 | ok |
| V1-4 | 47,959 | NOT conv -135812.572 | NOT conv -136348.794 | conv -135745.802 | **conv -135744.314** | NOT conv -139113.255 | ok |
| B-1 | 19,842 | conv -78937.796 | NOT conv -78945.421 | **conv -78925.489** | conv -78925.489 | NOT conv -78939.177 | ok |
| B-2 | 19,842 | conv -73833.478 | NOT conv -73848.929 | conv -73827.051 | **conv -73827.051** | NOT conv -76050.518 | ok |
| B-3 | 19,842 | NOT conv -61417.576 | NOT conv -61425.326 | **conv -61404.913** | conv -61404.913 | NOT conv -61419.223 | ok |
| B-4 | 25,012 | conv -99885.585 | NOT conv -100048.499 | **conv -99883.290** | conv -99883.290 | NOT conv -102452.117 | ok |
| B-5 | 5,085 | conv -20309.286 | NOT conv -20328.574 | conv -20309.085 | **conv -20308.502** | NOT conv -20933.633 | ok |
| T-1 | 18,903 | conv -52390.119 | NOT conv -52396.259 | conv -52390.158 | **conv -52390.119** | NOT conv -54336.476 | ok |
| T-2 | 18,903 | conv -51390.259 | NOT conv -51391.012 | conv -51390.332 | **conv -51390.259** | NOT conv -53253.142 | ok |
| T-3 | 18,903 | conv -51395.632 | NOT conv -51396.383 | conv -51395.704 | **conv -51395.632** | NOT conv -53257.736 | ok |
| T-4 | 18,905 | **conv -51274.502** | NOT conv -51275.735 | conv -51274.580 | conv -51274.502 | NOT conv -53144.057 | ok |
| T-5 | 18,885 | NOT conv -13841.946 | NOT conv -13862.617 | conv -13839.252 | **conv -13839.190** | NOT conv -13841.179 | ok |
| T-6 | 19,204 | conv -51847.577 | NOT conv -51854.951 | conv -51847.701 | **conv -51847.577** | NOT conv -53814.879 | ok |
| T-7 | 23,920 | conv -66845.447 | NOT conv -66854.413 | conv -66836.267 | **conv -66836.153** | NOT conv -69159.905 | ok |
| T-8 | 23,928 | conv -66680.880 | NOT conv -66688.575 | conv -66669.726 | **conv -66669.684** | NOT conv -68989.324 | ok |
| T-9 | 23,897 | NOT conv -19572.199 | NOT conv -19742.274 | conv -19552.409 | **conv -19552.313** | NOT conv -22132.059 | ok |
| T-10 | 18,905 | **conv -51329.467** | NOT conv -51342.626 | conv -51329.589 | conv -51329.467 | NOT conv -51360.264 | ok |
| T-11 | 19,812 | conv -53461.627 | NOT conv -53465.694 | conv -53455.344 | **conv -53455.289** | NOT conv -55473.253 | ok |
| T-12 | 19,812 | NOT conv -29750.764 | NOT conv -29779.647 | conv -29747.095 | **conv -29747.018** | NOT conv -29749.248 | ok |
| T-13 | 14,894 | **conv -33397.080** | NOT conv -33482.099 | conv -33397.151 | conv -33397.080 | NOT conv -33402.356 | ok |
| T-14 | 4,011 | conv -11887.656 | NOT conv -11894.039 | conv -11887.658 | **conv -11887.656** | NOT conv -11895.461 | ok |

Messages printed by the unchanged `fit_mixed` during re-execution: B-1: "[4.1] lbfgs degenerate; used method=bfgs"; B-2: "[4.1-liquidation] lbfgs degenerate; used method=bfgs"; B-3: "[4.3a] lbfgs degenerate; used method=bfgs"; B-4: "[4.3b] lbfgs degenerate; used method=bfgs"; B-5: "[figB-500] lbfgs degenerate; used method=bfgs"; T-1: "mixedlm(lbfgs) failed for H1: Singular matrix |   [H1] lbfgs degenerate; used method=bfgs"; T-4: "[H4-RES] lbfgs degenerate; used method=bfgs"; T-5: "[H4-CF] lbfgs degenerate; used method=bfgs"; T-8: "[R1-RES] lbfgs degenerate; used method=bfgs"; T-9: "[R1-CF] lbfgs degenerate; used method=bfgs"; T-10: "[R2-RES] lbfgs degenerate; used method=bfgs"; T-11: "[R3-RES] lbfgs degenerate; used method=bfgs"; T-12: "[R3-CF] lbfgs degenerate; used method=bfgs".


## 5. Sentences that must change (§4, §5 item 3)

Source: `docs/Sharper_Not_Safer_v7.docx`.


No core coefficient changed sign or CI-excludes-zero status, and the T-1 TOST verdict is unchanged. Under §4 every published conclusion on the re-run list stands and no sentence must change.



## 6. Corrected text of v3 Amendment 2 (§5 item 4)

Delivered as text; `specs/` is not edited.

_2026-09-11: this corrected text was applied to `specs/paper4_spec_v3_en.md` in the commit after b6efaff._


> ## Amendment 2 (2026-09-05, after lock, during execution; corrected 2026-09-11)
>
> **Trigger**: implementation review of how the [LOCKED] random-effects structures are actually estimated, plus one feature-definition convention that belongs on the record. This amendment records existing practice. No estimate, parameter, or model specification changes under it.
>
> **Correction (2026-09-11, `specs/paper4_correction_spec.md`)**: items 1 to 3 as first written described an estimator that was not the one used. The text below is the corrected record. The effect on every reported estimate is in `docs/paper4_correction_REPORT.md`.
>
> **Decisions**:
>
> 1. **Random effects in §6.** The [LOCKED] structure `(1 | player_id) + (1 | game_id)` in §6.1 through §6.5, and in the §7 robustness refits that reuse those model forms, was fitted with v1's `fit_mixed` (`paper4_report.py:74`). That function calls `MixedLM` grouped on `player_id` with `game_id` as a variance component and without `re_formula`; in statsmodels 0.14.6 this estimates no player random intercept. Every §6 and §7 model as reported therefore carried a game random intercept only, with a game that contributes rows from two players receiving one independent intercept per player. The fit is retried across optimizers with a guard that rejects the degenerate all-zero optimum; the guard does not check convergence, so a non-converged fit could be returned. The "random-effect variance" printed under each table is the variance divided by the residual variance. An OLS fit with player-clustered standard errors is reported alongside on the same rows and does not depend on the random-effects structure. The same function fitted v1's §7.2 model, so §6.5's rerun of it is a like-for-like comparison of estimators, with the same omission on both sides. The corrected estimator is `fit_mixed_v2` (`code/paper4_mixed_v2.py`): a player random intercept, `game_id` as a variance component nested in `player_id`, a sweep of five optimizers, selection of the converged, non-degenerate fit with the highest log-likelihood, and variance components on the natural scale.
>
> 2. **The crossing is real, not incidental.** In the (0, 5] analysis band, 1,937 of 1,967 games (98.5%) contribute rows from both players, so `game_id` genuinely crosses `player_id` rather than nesting inside it. The reported fits did not approximate this crossing; they omitted the player intercept altogether (item 1). Under the corrected estimator, which nests `game_id` in `player_id`, what the approximation drops is the sharing of one game intercept across that game's two players, and it is flagged in every mixed-model coefficient table.
>
> 3. **§4.2 is not affected by item 1.** The nuisance model carries a single grouping factor, `(1 | player_id)`, fitted with `MixedLM` grouped on `player_id` and its default random intercept, which is estimated. No nesting approximation is involved there. It is fitted with `lbfgs` alone, without a convergence check; the correction's verification (correction spec §3.4) found all ten fold fits, on the main and the §7.2 training sets, converged at the maximum across five optimizers, and the stored predictions reproduce exactly. Its printed `Group Var` is likewise a ratio to the residual variance.
>
> 4. **`spread_15` convention.** §3.2 defines `spread_15` as `WP_opp(1st) − WP_opp(5th)`. It is computed against the last available MultiPV line, which is v1's own convention for the same feature (`wp_best - wps[-1]`). The two are identical wherever the engine returned five lines — 56,541 of 57,294 successor positions, 98.7% — and differ only where it returned fewer. Matching v1 keeps the nuisance model's training features and its prediction features on a single definition, which §4.2 requires.


## 7. Corrected text of `README.md` line 34 (§5 item 5)

Delivered as text; `README.md` is not edited.

_2026-09-11: this corrected line was applied to `README.md` in the commit after b6efaff._


**Old:**

> - `specs/` — the locked specifications for the Paper 4 analyses: v1 (deviation structure and the complementarity test), v2 (the risk-direction analysis), and v3 (the §7.2 identification redesign; `paper4_spec_v3_en.md` is the governing English version, `paper4_spec_v3_zh_lock.md` the original-language lock record). v3 carries three amendments, all recorded in the English file: 1 permits re-evaluating the successor positions to recover the MultiPV lines v2 did not persist, 2 records how the crossed random effects are estimated, and 3 withdraws an invalid diagnostic and replaces it. Amendments 1 and 2 predate any results; 3 is dated and marked as recorded after them.


**New:**

> - `specs/` — the locked specifications for the Paper 4 analyses: v1 (deviation structure and the complementarity test), v2 (the risk-direction analysis), and v3 (the §7.2 identification redesign; `paper4_spec_v3_en.md` is the governing English version, `paper4_spec_v3_zh_lock.md` the original-language lock record). v3 carries three amendments, all recorded in the English file: 1 permits re-evaluating the successor positions to recover the MultiPV lines v2 did not persist, 2 records how the random effects are estimated (its original description was incorrect: the fitted models carried no player intercept; corrected under `paper4_correction_spec.md`, with the refitted estimates in `docs/paper4_correction_REPORT.md`), and 3 withdraws an invalid diagnostic and replaces it. Amendments 1 and 2 predate any results; 3, and the 2026-09-11 correction of 2, are dated and recorded after them.


## Appendix. Full coefficient tables, old and new, all 23 models

Old = the unchanged `fit_mixed` re-executed on the rebuilt rows; new = `fit_mixed_v2`. Wald 95% CIs.


### V1-1 — v1 §8.1 (roster only)


`WPL ~ elo_z + gap_12_z + spread_15_z + n_legal_z + eval_volatility_z + time_pressure_z + elo_z:gap_12_z + elo_z:time_pressure_z` — rows 25,457

| term | old coef [95% CI] | old p | new coef [95% CI] | new p |
|---|---|---|---|---|
| `Intercept` | +2.3809 [+2.3227, +2.4392] | 0 | +2.3802 [+2.3109, +2.4495] | 0 |
| `elo_z` | -0.2346 [-0.2930, -0.1763] | 3.3e-15 | -0.2308 [-0.2985, -0.1632] | 2.26e-11 |
| `gap_12_z` | -0.0057 [-0.0770, +0.0656] | 0.876 | -0.0040 [-0.0753, +0.0672] | 0.912 |
| `spread_15_z` | -0.1557 [-0.2273, -0.0840] | 2.07e-05 | -0.1541 [-0.2257, -0.0825] | 2.47e-05 |
| `n_legal_z` | +0.3112 [+0.2567, +0.3658] | 5.09e-29 | +0.3172 [+0.2630, +0.3715] | 2.14e-30 |
| `eval_volatility_z` | +0.4849 [+0.4301, +0.5396] | 1.49e-67 | +0.4817 [+0.4270, +0.5363] | 6.55e-67 |
| `time_pressure_z` | -0.4288 [-0.4840, -0.3735] | 2.93e-52 | -0.4414 [-0.4970, -0.3859] | 9.14e-55 |
| `elo_z:gap_12_z` | -0.0291 [-0.0762, +0.0180] | 0.226 | -0.0283 [-0.0753, +0.0187] | 0.238 |
| `elo_z:time_pressure_z` | -0.0392 [-0.0893, +0.0109] | 0.125 | -0.0398 [-0.0901, +0.0105] | 0.121 |

Variance components (player / game / residual): old not estimated / 0.4890 / 16.1394; new 0.2407 / 0.2528 / 16.1383.


### V1-2 — v1 §8.2 (all rows)


`WPL ~ elo_z + gap_12_z + spread_15_z + n_legal_z + eval_volatility_z + time_pressure_z + elo_z:gap_12_z + elo_z:time_pressure_z` — rows 49,921

| term | old coef [95% CI] | old p | new coef [95% CI] | new p |
|---|---|---|---|---|
| `Intercept` | +2.4397 [+2.3980, +2.4813] | 0 | +2.4487 [+2.4031, +2.4944] | 0 |
| `elo_z` | -0.3018 [-0.3436, -0.2600] | 1.79e-45 | -0.3021 [-0.3467, -0.2575] | 3.02e-40 |
| `gap_12_z` | +0.0272 [-0.0237, +0.0782] | 0.295 | +0.0279 [-0.0230, +0.0789] | 0.283 |
| `spread_15_z` | -0.1666 [-0.2179, -0.1154] | 1.91e-10 | -0.1652 [-0.2164, -0.1139] | 2.71e-10 |
| `n_legal_z` | +0.3233 [+0.2841, +0.3625] | 9.74e-59 | +0.3269 [+0.2878, +0.3660] | 2.54e-60 |
| `eval_volatility_z` | +0.5012 [+0.4618, +0.5406] | 3.35e-137 | +0.4995 [+0.4601, +0.5388] | 1.75e-136 |
| `time_pressure_z` | -0.4018 [-0.4415, -0.3621] | 1.63e-87 | -0.4089 [-0.4488, -0.3691] | 5.06e-90 |
| `elo_z:gap_12_z` | -0.0476 [-0.0845, -0.0107] | 0.0115 | -0.0474 [-0.0842, -0.0105] | 0.0118 |
| `elo_z:time_pressure_z` | -0.0372 [-0.0712, -0.0032] | 0.0318 | -0.0381 [-0.0721, -0.0041] | 0.0281 |

Variance components (player / game / residual): old not estimated / 0.4754 / 16.4472; new 0.2391 / 0.2400 / 16.4463.


### V1-3 — v1 §9 primary


`WPL_opponent_next ~ WPL_self_z * gap_12_z * elo_diff_z + n_legal_z + eval_volatility_z + time_pressure_z` — rows 47,959

| term | old coef [95% CI] | old p | new coef [95% CI] | new p |
|---|---|---|---|---|
| `Intercept` | +2.4840 [+2.4429, +2.5251] | 0 | +2.4830 [+2.4393, +2.5267] | 0 |
| `WPL_self_z` | +0.8315 [+0.7916, +0.8714] | 0 | +0.8287 [+0.7888, +0.8686] | 0 |
| `gap_12_z` | -0.0209 [-0.0614, +0.0196] | 0.312 | -0.0198 [-0.0603, +0.0207] | 0.337 |
| `WPL_self_z:gap_12_z` | -0.0986 [-0.1335, -0.0637] | 3.1e-08 | -0.0976 [-0.1325, -0.0627] | 4.23e-08 |
| `elo_diff_z` | +0.2199 [+0.1787, +0.2611] | 1.32e-25 | +0.2217 [+0.1801, +0.2633] | 1.43e-25 |
| `WPL_self_z:elo_diff_z` | +0.1136 [+0.0772, +0.1500] | 9.38e-10 | +0.1129 [+0.0765, +0.1493] | 1.18e-09 |
| `gap_12_z:elo_diff_z` | +0.0525 [+0.0151, +0.0899] | 0.00589 | +0.0524 [+0.0150, +0.0898] | 0.00598 |
| `WPL_self_z:gap_12_z:elo_diff_z` | +0.1167 [+0.0712, +0.1623] | 5.03e-07 | +0.1169 [+0.0714, +0.1625] | 4.78e-07 |
| `n_legal_z` | +0.0674 [+0.0277, +0.1071] | 0.000877 | +0.0702 [+0.0305, +0.1099] | 0.000526 |
| `eval_volatility_z` | +0.2146 [+0.1736, +0.2557] | 1.22e-24 | +0.2129 [+0.1718, +0.2539] | 2.87e-24 |
| `time_pressure_z` | -0.1935 [-0.2343, -0.1527] | 1.35e-20 | -0.1933 [-0.2342, -0.1524] | 1.87e-20 |

Variance components (player / game / residual): old not estimated / 0.3506 / 16.6454; new 0.1423 / 0.2100 / 16.6449.


### V1-4 — v1 §9 robustness, controls at t+1


`WPL_opponent_next ~ WPL_self_z * gap_12_z * elo_diff_z + opp_n_legal_z + opp_eval_volatility_z + opp_time_pressure_z` — rows 47,959

| term | old coef [95% CI] | old p | new coef [95% CI] | new p |
|---|---|---|---|---|
| `Intercept` | +2.4605 [+2.4182, +2.5028] | 0 | +2.4561 [+2.4109, +2.5013] | 0 |
| `WPL_self_z` | +0.7564 [+0.7116, +0.8011] | 1.07e-240 | +0.7539 [+0.7091, +0.7986] | 4.79e-239 |
| `gap_12_z` | -0.0045 [-0.0442, +0.0353] | 0.826 | -0.0040 [-0.0437, +0.0358] | 0.844 |
| `WPL_self_z:gap_12_z` | -0.0703 [-0.1050, -0.0356] | 7.19e-05 | -0.0692 [-0.1039, -0.0345] | 9.23e-05 |
| `elo_diff_z` | +0.1932 [+0.1508, +0.2356] | 4.32e-19 | +0.1944 [+0.1516, +0.2372] | 5.68e-19 |
| `WPL_self_z:elo_diff_z` | +0.1148 [+0.0785, +0.1511] | 5.79e-10 | +0.1139 [+0.0776, +0.1502] | 7.78e-10 |
| `gap_12_z:elo_diff_z` | +0.0500 [+0.0128, +0.0872] | 0.00846 | +0.0500 [+0.0128, +0.0872] | 0.00838 |
| `WPL_self_z:gap_12_z:elo_diff_z` | +0.1128 [+0.0674, +0.1581] | 1.1e-06 | +0.1131 [+0.0678, +0.1585] | 1e-06 |
| `opp_n_legal_z` | +0.3178 [+0.2790, +0.3566] | 5.11e-58 | +0.3197 [+0.2810, +0.3585] | 7.84e-59 |
| `opp_eval_volatility_z` | +0.1240 [+0.0801, +0.1679] | 3.13e-08 | +0.1234 [+0.0795, +0.1672] | 3.62e-08 |
| `opp_time_pressure_z` | -0.3524 [-0.3922, -0.3127] | 1.34e-67 | -0.3505 [-0.3903, -0.3108] | 4.53e-67 |

Variance components (player / game / residual): old not estimated / 0.4771 / 16.4024; new 0.1625 / 0.3164 / 16.4019.


### B-1 — 4b §4 primary


`dRISK_steep ~ WPL_z + gap_12_z + eval_volatility_z + time_pressure_z` — rows 19,842

| term | old coef [95% CI] | old p | new coef [95% CI] | new p |
|---|---|---|---|---|
| `Intercept` | +1.2155 [+1.0240, +1.4071] | 1.63e-35 | +1.2155 [+1.0239, +1.4071] | 1.66e-35 |
| `WPL_z` | +0.2631 [+0.0469, +0.4794] | 0.0171 | +0.2631 [+0.0469, +0.4794] | 0.0171 |
| `gap_12_z` | -0.5841 [-0.8017, -0.3664] | 1.44e-07 | -0.5841 [-0.8017, -0.3664] | 1.44e-07 |
| `eval_volatility_z` | +0.4562 [+0.2730, +0.6394] | 1.06e-06 | +0.4562 [+0.2730, +0.6394] | 1.06e-06 |
| `time_pressure_z` | -0.3338 [-0.5212, -0.1464] | 0.000481 | -0.3338 [-0.5212, -0.1464] | 0.000482 |

Variance components (player / game / residual): old not estimated / 4.6075 / 162.5266; new 0.0000 / 4.6074 / 162.5267.


### B-2 — 4b §4 liquidation


`dRISK_steep ~ WPL_z + gap_12_z + eval_volatility_z + time_pressure_z + played_is_capture_c + dmat_c` — rows 19,842

| term | old coef [95% CI] | old p | new coef [95% CI] | new p |
|---|---|---|---|---|
| `Intercept` | +1.2146 [+1.0685, +1.3607] | 1.11e-59 | +1.2146 [+1.0683, +1.3608] | 1.4e-59 |
| `WPL_z` | +0.5317 [+0.3637, +0.6996] | 5.48e-10 | +0.5317 [+0.3637, +0.6996] | 5.49e-10 |
| `gap_12_z` | -0.4739 [-0.6444, -0.3034] | 5.1e-08 | -0.4739 [-0.6444, -0.3034] | 5.12e-08 |
| `eval_volatility_z` | +0.0970 [-0.0452, +0.2392] | 0.181 | +0.0970 [-0.0452, +0.2392] | 0.181 |
| `time_pressure_z` | -0.2266 [-0.3708, -0.0824] | 0.00208 | -0.2266 [-0.3709, -0.0823] | 0.00208 |
| `played_is_capture_c` | +2.5981 [+2.1367, +3.0595] | 2.58e-28 | +2.5981 [+2.1367, +3.0595] | 2.58e-28 |
| `dmat_c` | -5.8055 [-5.9266, -5.6844] | 0 | -5.8055 [-5.9266, -5.6844] | 0 |

Variance components (player / game / residual): old not estimated / 2.1278 / 97.7478; new 0.0000 / 2.1268 / 97.7487.


### B-3 — 4b §6.1 ΔRISK_var


`dRISK_var ~ WPL_z + gap_12_z + eval_volatility_z + time_pressure_z` — rows 19,842

| term | old coef [95% CI] | old p | new coef [95% CI] | new p |
|---|---|---|---|---|
| `Intercept` | +0.4491 [+0.3698, +0.5283] | 1.17e-28 | +0.4491 [+0.3698, +0.5284] | 1.22e-28 |
| `WPL_z` | +0.0761 [-0.0133, +0.1656] | 0.0951 | +0.0761 [-0.0133, +0.1656] | 0.0951 |
| `gap_12_z` | -0.2320 [-0.3219, -0.1420] | 4.36e-07 | -0.2320 [-0.3219, -0.1420] | 4.36e-07 |
| `eval_volatility_z` | +0.1894 [+0.1136, +0.2651] | 9.57e-07 | +0.1894 [+0.1136, +0.2651] | 9.57e-07 |
| `time_pressure_z` | -0.1345 [-0.2120, -0.0570] | 0.000673 | -0.1345 [-0.2120, -0.0569] | 0.000675 |

Variance components (player / game / residual): old not estimated / 0.7976 / 27.7732; new 0.0000 / 0.7976 / 27.7732.


### B-4 — 4b §6.2 band (0, 10]


`dRISK_steep ~ WPL_z + gap_12_z + eval_volatility_z + time_pressure_z` — rows 25,012

| term | old coef [95% CI] | old p | new coef [95% CI] | new p |
|---|---|---|---|---|
| `Intercept` | +1.4749 [+1.2979, +1.6519] | 5.69e-60 | +1.4749 [+1.2979, +1.6519] | 5.73e-60 |
| `WPL_z` | +0.9355 [+0.7375, +1.1335] | 2.04e-20 | +0.9355 [+0.7375, +1.1336] | 2.05e-20 |
| `gap_12_z` | -0.9518 [-1.1511, -0.7525] | 7.93e-21 | -0.9518 [-1.1511, -0.7525] | 7.94e-21 |
| `eval_volatility_z` | +0.4734 [+0.3061, +0.6407] | 2.92e-08 | +0.4734 [+0.3061, +0.6407] | 2.93e-08 |
| `time_pressure_z` | -0.3134 [-0.4849, -0.1419] | 0.000341 | -0.3134 [-0.4850, -0.1419] | 0.000342 |

Variance components (player / game / residual): old not estimated / 5.2225 / 167.3927; new 0.0000 / 5.2234 / 167.3920.


### B-5 — figure B, 500 games


`dRISK_steep ~ WPL_z + gap_12_z + eval_volatility_z + time_pressure_z` — rows 5,085

| term | old coef [95% CI] | old p | new coef [95% CI] | new p |
|---|---|---|---|---|
| `Intercept` | +1.1658 [+0.7872, +1.5444] | 1.59e-09 | +1.1778 [+0.7910, +1.5645] | 2.39e-09 |
| `WPL_z` | -0.1964 [-0.6279, +0.2352] | 0.372 | -0.2003 [-0.6318, +0.2312] | 0.363 |
| `gap_12_z` | -0.4517 [-0.8861, -0.0174] | 0.0415 | -0.4476 [-0.8817, -0.0135] | 0.0433 |
| `eval_volatility_z` | +0.5204 [+0.1536, +0.8873] | 0.00543 | +0.5188 [+0.1519, +0.8856] | 0.00558 |
| `time_pressure_z` | -0.6174 [-0.9928, -0.2420] | 0.00127 | -0.6085 [-0.9847, -0.2323] | 0.00152 |

Variance components (player / game / residual): old not estimated / 3.4969 / 169.0712; new 3.6435 / 0.0000 / 168.9191.


### T-1 — v3 §6.1 H1


`NET_realized ~ 1` — rows 18,903

| term | old coef [95% CI] | old p | new coef [95% CI] | new p |
|---|---|---|---|---|
| `Intercept` | -1.7223 [-1.7890, -1.6556] | 0 | -1.7504 [-1.8101, -1.6907] | 0 |

Variance components (player / game / residual): old not estimated / 1.4345 / 13.8511; new 0.0459 / 0.3595 / 14.5727.


### T-2 — v3 §6.2 H2


`NET_realized ~ delta_risk_steep_z + WPL_self_z + gap_12_orig_z + eval_volatility_orig_z + time_pressure_opp_z + elo_diff_opp_z` — rows 18,903

| term | old coef [95% CI] | old p | new coef [95% CI] | new p |
|---|---|---|---|---|
| `Intercept` | -1.7355 [-1.7921, -1.6789] | 0 | -1.7384 [-1.7964, -1.6804] | 0 |
| `delta_risk_steep_z` | -0.4751 [-0.5272, -0.4229] | 2.92e-71 | -0.4754 [-0.5276, -0.4232] | 2.27e-71 |
| `WPL_self_z` | -1.1637 [-1.2265, -1.1009] | 5.01e-289 | -1.1642 [-1.2270, -1.1015] | 2.4e-289 |
| `gap_12_orig_z` | +0.0621 [-0.0010, +0.1252] | 0.0538 | +0.0621 [-0.0010, +0.1252] | 0.0538 |
| `eval_volatility_orig_z` | +0.2225 [+0.1693, +0.2756] | 2.41e-16 | +0.2218 [+0.1686, +0.2750] | 3.02e-16 |
| `time_pressure_opp_z` | +0.0361 [-0.0190, +0.0912] | 0.199 | +0.0369 [-0.0182, +0.0920] | 0.189 |
| `elo_diff_opp_z` | -0.0902 [-0.1472, -0.0332] | 0.00192 | -0.0900 [-0.1472, -0.0328] | 0.00205 |

Variance components (player / game / residual): old not estimated / 0.4511 / 13.0172; new 0.0868 / 0.3635 / 13.0180.


### T-3 — v3 §6.3 H3


`NET_realized ~ delta_risk_steep_z + WPL_self_z + gap_12_orig_z + eval_volatility_orig_z + time_pressure_opp_z + elo_diff_opp_z + delta_risk_steep_z:time_pressure_opp_z + delta_risk_steep_z:elo_diff_opp_z` — rows 18,903

| term | old coef [95% CI] | old p | new coef [95% CI] | new p |
|---|---|---|---|---|
| `Intercept` | -1.7354 [-1.7920, -1.6788] | 0 | -1.7383 [-1.7963, -1.6803] | 0 |
| `delta_risk_steep_z` | -0.4733 [-0.5260, -0.4207] | 2e-69 | -0.4737 [-0.5263, -0.4210] | 1.58e-69 |
| `WPL_self_z` | -1.1639 [-1.2267, -1.1011] | 4.83e-289 | -1.1645 [-1.2273, -1.1017] | 2.31e-289 |
| `gap_12_orig_z` | +0.0621 [-0.0010, +0.1252] | 0.0537 | +0.0621 [-0.0010, +0.1252] | 0.0537 |
| `eval_volatility_orig_z` | +0.2229 [+0.1697, +0.2760] | 2.2e-16 | +0.2222 [+0.1690, +0.2754] | 2.77e-16 |
| `time_pressure_opp_z` | +0.0365 [-0.0187, +0.0916] | 0.195 | +0.0372 [-0.0179, +0.0923] | 0.185 |
| `elo_diff_opp_z` | -0.0899 [-0.1471, -0.0327] | 0.00207 | -0.0896 [-0.1470, -0.0322] | 0.00222 |
| `delta_risk_steep_z:time_pressure_opp_z` | +0.0130 [-0.0381, +0.0642] | 0.618 | +0.0129 [-0.0382, +0.0641] | 0.62 |
| `delta_risk_steep_z:elo_diff_opp_z` | -0.0045 [-0.0530, +0.0441] | 0.856 | -0.0046 [-0.0531, +0.0439] | 0.853 |

Variance components (player / game / residual): old not estimated / 0.4512 / 13.0183; new 0.0867 / 0.3637 / 13.0191.


### T-4 — v3 §6.4 H4a


`RES ~ delta_risk_steep_z + WPL_self_z + gap_12_orig_z + eval_volatility_orig_z + time_pressure_opp_z + elo_diff_opp_z` — rows 18,905

| term | old coef [95% CI] | old p | new coef [95% CI] | new p |
|---|---|---|---|---|
| `Intercept` | +0.1396 [+0.0790, +0.2002] | 6.31e-06 | +0.1196 [+0.0621, +0.1770] | 4.52e-05 |
| `delta_risk_steep_z` | -0.0854 [-0.1372, -0.0337] | 0.00122 | -0.0862 [-0.1380, -0.0343] | 0.00112 |
| `WPL_self_z` | +0.1362 [+0.0739, +0.1985] | 1.84e-05 | +0.1374 [+0.0751, +0.1998] | 1.58e-05 |
| `gap_12_orig_z` | +0.0820 [+0.0193, +0.1446] | 0.0103 | +0.0937 [+0.0310, +0.1564] | 0.00339 |
| `eval_volatility_orig_z` | +0.2051 [+0.1522, +0.2580] | 3.05e-14 | +0.2298 [+0.1770, +0.2826] | 1.49e-17 |
| `time_pressure_opp_z` | +0.0265 [-0.0299, +0.0830] | 0.357 | +0.0486 [-0.0062, +0.1033] | 0.0819 |
| `elo_diff_opp_z` | -0.0835 [-0.1444, -0.0225] | 0.00727 | -0.0815 [-0.1382, -0.0247] | 0.00489 |

Variance components (player / game / residual): old not estimated / 0.9761 / 12.4528; new 0.0801 / 0.3551 / 12.8599.


### T-5 — v3 §6.4 H4b


`CF ~ delta_risk_steep_z + WPL_self_z + gap_12_orig_z + eval_volatility_orig_z + time_pressure_opp_z + elo_diff_opp_z` — rows 18,885

| term | old coef [95% CI] | old p | new coef [95% CI] | new p |
|---|---|---|---|---|
| `Intercept` | +0.0414 [+0.0340, +0.0488] | 9.36e-28 | +0.0414 [+0.0339, +0.0489] | 3.99e-27 |
| `delta_risk_steep_z` | -0.3899 [-0.3970, -0.3827] | 0 | -0.3899 [-0.3971, -0.3828] | 0 |
| `WPL_self_z` | +0.0775 [+0.0689, +0.0861] | 1.74e-69 | +0.0774 [+0.0688, +0.0861] | 1.98e-69 |
| `gap_12_orig_z` | -0.0311 [-0.0397, -0.0224] | 1.86e-12 | -0.0311 [-0.0397, -0.0224] | 1.85e-12 |
| `eval_volatility_orig_z` | -0.0076 [-0.0148, -0.0004] | 0.0375 | -0.0077 [-0.0149, -0.0005] | 0.0367 |
| `time_pressure_opp_z` | -0.0128 [-0.0202, -0.0054] | 0.000675 | -0.0128 [-0.0202, -0.0054] | 0.000687 |
| `elo_diff_opp_z` | -0.0086 [-0.0161, -0.0011] | 0.0252 | -0.0085 [-0.0160, -0.0010] | 0.0272 |

Variance components (player / game / residual): old not estimated / 0.0038 / 0.2491; new 0.0008 / 0.0029 / 0.2491.


### T-6 — v3 §6.5 control


`WPL_opponent_next ~ WPL_self_z * gap_12_z * elo_diff_z + n_legal_z + eval_volatility_z + time_pressure_z` — rows 19,204

| term | old coef [95% CI] | old p | new coef [95% CI] | new p |
|---|---|---|---|---|
| `Intercept` | +2.2398 [+2.1772, +2.3024] | 0 | +2.2396 [+2.1758, +2.3033] | 0 |
| `WPL_self_z` | +0.2091 [+0.1445, +0.2736] | 2.13e-10 | +0.2082 [+0.1437, +0.2727] | 2.53e-10 |
| `gap_12_z` | +0.1436 [+0.0572, +0.2299] | 0.00112 | +0.1426 [+0.0563, +0.2290] | 0.00121 |
| `WPL_self_z:gap_12_z` | -0.0545 [-0.1130, +0.0040] | 0.0681 | -0.0539 [-0.1124, +0.0046] | 0.0711 |
| `elo_diff_z` | +0.2276 [+0.1643, +0.2908] | 1.81e-12 | +0.2280 [+0.1646, +0.2915] | 1.87e-12 |
| `WPL_self_z:elo_diff_z` | +0.0198 [-0.0442, +0.0838] | 0.544 | +0.0196 [-0.0444, +0.0835] | 0.548 |
| `gap_12_z:elo_diff_z` | +0.0072 [-0.0813, +0.0956] | 0.874 | +0.0073 [-0.0811, +0.0957] | 0.872 |
| `WPL_self_z:gap_12_z:elo_diff_z` | -0.0367 [-0.0962, +0.0229] | 0.228 | -0.0371 [-0.0967, +0.0224] | 0.222 |
| `n_legal_z` | +0.1012 [+0.0488, +0.1536] | 0.000153 | +0.1020 [+0.0495, +0.1544] | 0.000138 |
| `eval_volatility_z` | +0.2736 [+0.2200, +0.3271] | 1.27e-23 | +0.2721 [+0.2185, +0.3256] | 2.34e-23 |
| `time_pressure_z` | -0.2223 [-0.2771, -0.1676] | 1.73e-15 | -0.2219 [-0.2768, -0.1671] | 2.11e-15 |

Variance components (player / game / residual): old not estimated / 0.2571 / 12.6836; new 0.0874 / 0.1706 / 12.6828.


### T-7 — v3 §7.1 H2 (0, 10]


`NET_realized ~ delta_risk_steep_z + WPL_self_z + gap_12_orig_z + eval_volatility_orig_z + time_pressure_opp_z + elo_diff_opp_z` — rows 23,920

| term | old coef [95% CI] | old p | new coef [95% CI] | new p |
|---|---|---|---|---|
| `Intercept` | -2.5785 [-2.6329, -2.5241] | 0 | -2.5808 [-2.6364, -2.5252] | 0 |
| `delta_risk_steep_z` | -0.4756 [-0.5257, -0.4255] | 2.78e-77 | -0.4759 [-0.5260, -0.4258] | 2.22e-77 |
| `WPL_self_z` | -1.9861 [-2.0470, -1.9252] | 0 | -1.9867 [-2.0477, -1.9258] | 0 |
| `gap_12_orig_z` | -0.0424 [-0.1037, +0.0188] | 0.174 | -0.0425 [-0.1038, +0.0187] | 0.173 |
| `eval_volatility_orig_z` | +0.1746 [+0.1231, +0.2262] | 3.05e-11 | +0.1739 [+0.1224, +0.2254] | 3.73e-11 |
| `time_pressure_opp_z` | +0.0495 [-0.0036, +0.1027] | 0.0678 | +0.0499 [-0.0033, +0.1031] | 0.0658 |
| `elo_diff_opp_z` | -0.1335 [-0.1882, -0.0787] | 1.81e-06 | -0.1332 [-0.1881, -0.0782] | 2.05e-06 |

Variance components (player / game / residual): old not estimated / 0.4659 / 15.2011; new 0.0685 / 0.3972 / 15.2014.


### T-8 — v3 §7.1 H4a (0, 10]


`RES ~ delta_risk_steep_z + WPL_self_z + gap_12_orig_z + eval_volatility_orig_z + time_pressure_opp_z + elo_diff_opp_z` — rows 23,928

| term | old coef [95% CI] | old p | new coef [95% CI] | new p |
|---|---|---|---|---|
| `Intercept` | +0.2817 [+0.2277, +0.3357] | 1.57e-24 | +0.2788 [+0.2235, +0.3342] | 5.29e-23 |
| `delta_risk_steep_z` | -0.0755 [-0.1252, -0.0258] | 0.00289 | -0.0758 [-0.1255, -0.0261] | 0.0028 |
| `WPL_self_z` | +0.3202 [+0.2598, +0.3806] | 2.8e-25 | +0.3194 [+0.2590, +0.3798] | 3.69e-25 |
| `gap_12_orig_z` | +0.0355 [-0.0252, +0.0963] | 0.252 | +0.0354 [-0.0253, +0.0962] | 0.253 |
| `eval_volatility_orig_z` | +0.2042 [+0.1533, +0.2551] | 3.83e-15 | +0.2033 [+0.1524, +0.2542] | 5.07e-15 |
| `time_pressure_opp_z` | +0.0572 [+0.0044, +0.1099] | 0.0337 | +0.0576 [+0.0049, +0.1104] | 0.0322 |
| `elo_diff_opp_z` | -0.1253 [-0.1797, -0.0709] | 6.32e-06 | -0.1251 [-0.1797, -0.0705] | 7.08e-06 |

Variance components (player / game / residual): old not estimated / 0.4606 / 14.9617; new 0.0795 / 0.3817 / 14.9613.


### T-9 — v3 §7.1 H4b (0, 10]


`CF ~ delta_risk_steep_z + WPL_self_z + gap_12_orig_z + eval_volatility_orig_z + time_pressure_opp_z + elo_diff_opp_z` — rows 23,897

| term | old coef [95% CI] | old p | new coef [95% CI] | new p |
|---|---|---|---|---|
| `Intercept` | +0.0969 [+0.0896, +0.1041] | 2.77e-151 | +0.0969 [+0.0895, +0.1043] | 1.26e-146 |
| `delta_risk_steep_z` | -0.4012 [-0.4081, -0.3942] | 0 | -0.4013 [-0.4082, -0.3943] | 0 |
| `WPL_self_z` | +0.1821 [+0.1737, +0.1906] | 0 | +0.1821 [+0.1737, +0.1906] | 0 |
| `gap_12_orig_z` | -0.0723 [-0.0807, -0.0638] | 1.09e-62 | -0.0723 [-0.0808, -0.0638] | 8.93e-63 |
| `eval_volatility_orig_z` | -0.0287 [-0.0358, -0.0217] | 1.83e-15 | -0.0288 [-0.0359, -0.0217] | 1.74e-15 |
| `time_pressure_opp_z` | -0.0114 [-0.0186, -0.0042] | 0.00183 | -0.0114 [-0.0186, -0.0042] | 0.00184 |
| `elo_diff_opp_z` | -0.0086 [-0.0160, -0.0013] | 0.0207 | -0.0085 [-0.0159, -0.0012] | 0.0231 |

Variance components (player / game / residual): old not estimated / 0.0044 / 0.2958; new 0.0010 / 0.0034 / 0.2958.


### T-10 — v3 §7.2 H4a unrestricted


`RES ~ delta_risk_steep_z + WPL_self_z + gap_12_orig_z + eval_volatility_orig_z + time_pressure_opp_z + elo_diff_opp_z` — rows 18,905

| term | old coef [95% CI] | old p | new coef [95% CI] | new p |
|---|---|---|---|---|
| `Intercept` | -0.0608 [-0.1161, -0.0055] | 0.0313 | -0.0528 [-0.1129, +0.0073] | 0.0851 |
| `delta_risk_steep_z` | -0.1298 [-0.1818, -0.0778] | 9.9e-07 | -0.1295 [-0.1814, -0.0776] | 1.03e-06 |
| `WPL_self_z` | +0.0697 [+0.0071, +0.1323] | 0.0291 | +0.0691 [+0.0066, +0.1316] | 0.0303 |
| `gap_12_orig_z` | +0.0892 [+0.0263, +0.1521] | 0.00544 | +0.0808 [+0.0180, +0.1437] | 0.0117 |
| `eval_volatility_orig_z` | +0.1536 [+0.1009, +0.2064] | 1.13e-08 | +0.1364 [+0.0836, +0.1891] | 4.06e-07 |
| `time_pressure_opp_z` | +0.0940 [+0.0395, +0.1484] | 0.000714 | +0.0803 [+0.0247, +0.1359] | 0.00463 |
| `elo_diff_opp_z` | -0.1069 [-0.1627, -0.0511] | 0.000174 | -0.1082 [-0.1672, -0.0491] | 0.000331 |

Variance components (player / game / residual): old not estimated / 0.3289 / 13.0448; new 0.1048 / 0.5895 / 12.7223.


### T-11 — v3 §7.3 H4a LightGBM


`RES ~ delta_risk_steep_z + WPL_self_z + gap_12_orig_z + eval_volatility_orig_z + time_pressure_opp_z + elo_diff_opp_z` — rows 19,812

| term | old coef [95% CI] | old p | new coef [95% CI] | new p |
|---|---|---|---|---|
| `Intercept` | +0.0194 [-0.0333, +0.0722] | 0.47 | +0.0176 [-0.0361, +0.0713] | 0.521 |
| `delta_risk_steep_z` | -0.1002 [-0.1504, -0.0501] | 8.88e-05 | -0.1005 [-0.1506, -0.0504] | 8.49e-05 |
| `WPL_self_z` | +0.0289 [-0.0313, +0.0890] | 0.347 | +0.0285 [-0.0317, +0.0887] | 0.353 |
| `gap_12_orig_z` | +0.0688 [+0.0082, +0.1295] | 0.0262 | +0.0688 [+0.0081, +0.1295] | 0.0263 |
| `eval_volatility_orig_z` | +0.1956 [+0.1440, +0.2472] | 1.08e-13 | +0.1951 [+0.1435, +0.2467] | 1.28e-13 |
| `time_pressure_opp_z` | +0.0144 [-0.0379, +0.0667] | 0.59 | +0.0147 [-0.0376, +0.0670] | 0.581 |
| `elo_diff_opp_z` | -0.1001 [-0.1528, -0.0474] | 0.000199 | -0.0996 [-0.1525, -0.0467] | 0.000224 |

Variance components (player / game / residual): old not estimated / 0.2696 / 12.6390; new 0.0565 / 0.2133 / 12.6390.


### T-12 — v3 §7.3 H4b LightGBM


`CF ~ delta_risk_steep_z + WPL_self_z + gap_12_orig_z + eval_volatility_orig_z + time_pressure_opp_z + elo_diff_opp_z` — rows 19,812

| term | old coef [95% CI] | old p | new coef [95% CI] | new p |
|---|---|---|---|---|
| `Intercept` | +0.1801 [+0.1645, +0.1958] | 2.26e-112 | +0.1803 [+0.1643, +0.1963] | 4.6e-108 |
| `delta_risk_steep_z` | -0.3548 [-0.3699, -0.3396] | 0 | -0.3546 [-0.3698, -0.3395] | 0 |
| `WPL_self_z` | +0.1775 [+0.1593, +0.1956] | 1.22e-81 | +0.1774 [+0.1592, +0.1955] | 1.41e-81 |
| `gap_12_orig_z` | -0.0739 [-0.0922, -0.0556] | 2.63e-15 | -0.0738 [-0.0921, -0.0555] | 2.72e-15 |
| `eval_volatility_orig_z` | -0.0346 [-0.0500, -0.0192] | 1.06e-05 | -0.0347 [-0.0501, -0.0193] | 9.88e-06 |
| `time_pressure_opp_z` | -0.0401 [-0.0557, -0.0245] | 4.5e-07 | -0.0401 [-0.0557, -0.0245] | 4.56e-07 |
| `elo_diff_opp_z` | -0.0135 [-0.0292, +0.0022] | 0.093 | -0.0133 [-0.0290, +0.0025] | 0.1 |

Variance components (player / game / residual): old not estimated / 0.0182 / 1.1592; new 0.0062 / 0.0121 / 1.1591.


### T-13 — v3 post-hoc §C inside MultiPV-5


`RES ~ delta_risk_steep_z + WPL_self_z + gap_12_orig_z + eval_volatility_orig_z + time_pressure_opp_z + elo_diff_opp_z` — rows 14,894

| term | old coef [95% CI] | old p | new coef [95% CI] | new p |
|---|---|---|---|---|
| `Intercept` | -0.9580 [-0.9969, -0.9190] | 0 | -0.9606 [-1.0004, -0.9208] | 0 |
| `delta_risk_steep_z` | +0.2179 [+0.1813, +0.2546] | 1.94e-31 | +0.2179 [+0.1813, +0.2545] | 1.97e-31 |
| `WPL_self_z` | +0.0613 [+0.0173, +0.1053] | 0.00629 | +0.0616 [+0.0177, +0.1056] | 0.006 |
| `gap_12_orig_z` | +0.0569 [+0.0126, +0.1012] | 0.0119 | +0.0565 [+0.0122, +0.1008] | 0.0124 |
| `eval_volatility_orig_z` | +0.1730 [+0.1357, +0.2103] | 9.95e-20 | +0.1733 [+0.1359, +0.2106] | 8.97e-20 |
| `time_pressure_opp_z` | +0.2060 [+0.1678, +0.2441] | 3.55e-26 | +0.2060 [+0.1679, +0.2442] | 3.38e-26 |
| `elo_diff_opp_z` | +0.0211 [-0.0178, +0.0599] | 0.288 | +0.0210 [-0.0180, +0.0600] | 0.291 |

Variance components (player / game / residual): old not estimated / 0.1808 / 5.0085; new 0.0305 / 0.1498 / 5.0090.


### T-14 — v3 post-hoc §C freshly evaluated


`RES ~ delta_risk_steep_z + WPL_self_z + gap_12_orig_z + eval_volatility_orig_z + time_pressure_opp_z + elo_diff_opp_z` — rows 4,011

| term | old coef [95% CI] | old p | new coef [95% CI] | new p |
|---|---|---|---|---|
| `Intercept` | +4.1407 [+3.9859, +4.2956] | 0 | +4.1407 [+3.9856, +4.2958] | 0 |
| `delta_risk_steep_z` | +0.4511 [+0.3052, +0.5970] | 1.38e-09 | +0.4511 [+0.3052, +0.5970] | 1.38e-09 |
| `WPL_self_z` | +0.3783 [+0.2046, +0.5521] | 1.98e-05 | +0.3783 [+0.2045, +0.5520] | 1.98e-05 |
| `gap_12_orig_z` | +0.4294 [+0.2531, +0.6057] | 1.81e-06 | +0.4296 [+0.2532, +0.6060] | 1.8e-06 |
| `eval_volatility_orig_z` | +0.6734 [+0.5237, +0.8231] | 1.19e-18 | +0.6735 [+0.5238, +0.8232] | 1.18e-18 |
| `time_pressure_opp_z` | -0.2073 [-0.3588, -0.0558] | 0.00732 | -0.2073 [-0.3588, -0.0558] | 0.00732 |
| `elo_diff_opp_z` | -0.0225 [-0.1791, +0.1340] | 0.778 | -0.0225 [-0.1792, +0.1341] | 0.778 |

Variance components (player / game / residual): old not estimated / 2.4397 / 19.5828; new 0.0359 / 2.4028 / 19.5837.

