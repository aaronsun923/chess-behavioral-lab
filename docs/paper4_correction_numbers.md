# Paper 4 correction: mixed-model numbers quoted in the paper

_Generated 2026-09-11 21:16 by `code/paper4_correction_numbers.py`. Companion to `docs/paper4_correction_REPORT.md`. Paper: `docs/Sharper_Not_Safer_v7.docx`._


**Old** = the unchanged `fit_mixed` re-executed on the rebuilt rows; it reproduces the published reports to printed precision (correction report §4.1). **New** = `fit_mixed_v2` on the same rows. "New as printed" formats the new value at the precision and in the style the paper uses. The ±2 SD predicted means use the delta method exactly as `paper4b_figures.py:fig_c` computes them, applied to each fit (rows 19,842; new fit selected `powell`). A change at printed precision is not a §4 reading; the §4 outcome is in the correction report (no conclusion changes).


## Summary

- 51 mixed-model numbers located in the paper.
- 27 are identical at the paper's printed precision under the new estimator; **24** differ:
  - #2 Abstract: `p = 1.6 × 10⁻³⁵` → `p = 1.7 × 10⁻³⁵`
  - #3 Abstract: `1.72` → `1.75`
  - #6 §3: `−0.235` → `−0.231`
  - #7 §3: `p = 3 × 10⁻¹⁵` → `p = 2 × 10⁻¹¹`
  - #8 §3: `+0.485` → `+0.482`
  - #9 §3: `p = 1 × 10⁻⁶⁷` → `p = 7 × 10⁻⁶⁷`
  - #10 §3: `+0.311` → `+0.317`
  - #11 §3: `−0.156` → `−0.154`
  - #12 §3: `−0.429` → `−0.441`
  - #13 §3: `p = 3 × 10⁻⁵²` → `p = 9 × 10⁻⁵⁵`
  - #16 §4.1, paragraph 2: `p = 1.6 × 10⁻³⁵` → `p = 1.7 × 10⁻³⁵`
  - #20 §4.2: `p = 1.3 × 10⁻⁴⁵` → `p = 1.4 × 10⁻⁵⁹`
  - #28 Figure B caption: `+1.166` → `+1.178`
  - #31 Figure B, left panel, "500 games": `+1.166 [+0.787, +1.544]` → `+1.178 [+0.791, +1.565]`
  - #39 §4.5, paragraph 3: `1.722` → `1.750`
  - #40 §4.5, paragraph 3: `[−1.789, −1.656]` → `[−1.810, −1.691]`
  - #42 §4.5, paragraph 3: `[−0.527, −0.423]` → `[−0.528, −0.423]`
  - #43 §4.5, paragraph 3: `p = 2.9 × 10⁻⁷¹` → `p = 2.3 × 10⁻⁷¹`
  - #44 §4.5, paragraph 3: `−0.085` → `−0.086`
  - #45 §4.5, paragraph 3: `[−0.137, −0.034]` → `[−0.138, −0.034]`
  - #46 §4.5, paragraph 3: `p = .0012` → `p = .0011`
  - #49 §4.5, paragraph 4: `+0.209` → `+0.208`
  - #50 §4.5, paragraph 4: `1.72` → `1.75`
  - #51 §6, "A silent false null": `+1.17` → `+1.18`
- Paper values that do not equal the old model output at their printed precision: 1:
  - #20 §4.2: paper `p = 1.3 × 10⁻⁴⁵`, old model output `p = 1.1 × 10⁻⁵⁹`


## Values

| # | location in the paper | as printed | source (model ID, term) | old | new | new as printed | paper = old at printed precision | changes at printed precision |
|---|---|---|---|---|---|---|---|---|
| 1 | Abstract | `+1.22` | B-1 `Intercept` (4b §4.1 primary) | +1.215511 | +1.215511 | `+1.22` | yes | no |
| 2 | Abstract | `p = 1.6 × 10⁻³⁵` | B-1 `Intercept` p | 1.635e-35 | 1.661e-35 | `p = 1.7 × 10⁻³⁵` | yes | **yes** |
| 3 | Abstract | `1.72` | T-1 `Intercept` (v3 H1), stated as a loss (−coefficient) | +1.722266 | +1.750410 | `1.75` | yes | **yes** |
| 4 | Abstract | `−0.48` | T-2 `delta_risk_steep_z` (v3 H2) | -0.475078 | -0.475397 | `−0.48` | yes | no |
| 5 | Abstract | `−0.09` | T-4 `delta_risk_steep_z` (v3 H4a) | -0.085439 | -0.086152 | `−0.09` | yes | no |
| 6 | §3 | `−0.235` | V1-1 `elo_z` (v1 §8.1) | -0.234611 | -0.230840 | `−0.231` | yes | **yes** |
| 7 | §3 | `p = 3 × 10⁻¹⁵` | V1-1 `elo_z` p | 3.297e-15 | 2.262e-11 | `p = 2 × 10⁻¹¹` | yes | **yes** |
| 8 | §3 | `+0.485` | V1-1 `eval_volatility_z` | +0.484859 | +0.481662 | `+0.482` | yes | **yes** |
| 9 | §3 | `p = 1 × 10⁻⁶⁷` | V1-1 `eval_volatility_z` p | 1.494e-67 | 6.551e-67 | `p = 7 × 10⁻⁶⁷` | yes | **yes** |
| 10 | §3 | `+0.311` | V1-1 `n_legal_z` | +0.311219 | +0.317217 | `+0.317` | yes | **yes** |
| 11 | §3 | `−0.156` | V1-1 `spread_15_z` | -0.155673 | -0.154094 | `−0.154` | yes | **yes** |
| 12 | §3 | `−0.429` | V1-1 `time_pressure_z` | -0.428770 | -0.441446 | `−0.441` | yes | **yes** |
| 13 | §3 | `p = 3 × 10⁻⁵²` | V1-1 `time_pressure_z` p | 2.931e-52 | 9.143e-55 | `p = 9 × 10⁻⁵⁵` | yes | **yes** |
| 14 | §4.1, paragraph 2 | `+1.216` | B-1 `Intercept` | +1.215511 | +1.215511 | `+1.216` | yes | no |
| 15 | §4.1, paragraph 2 | `[+1.02, +1.41]` | B-1 `Intercept` 95% CI | [+1.023965, +1.407057] | [+1.023945, +1.407076] | `[+1.02, +1.41]` | yes | no |
| 16 | §4.1, paragraph 2 | `p = 1.6 × 10⁻³⁵` | B-1 `Intercept` p | 1.635e-35 | 1.661e-35 | `p = 1.7 × 10⁻³⁵` | yes | **yes** |
| 17 | §4.1, paragraph 2 | `+0.449` | B-3 `Intercept` (4b §6.1, ΔRISK_var) | +0.449079 | +0.449079 | `+0.449` | yes | no |
| 18 | §4.1, paragraph 2 | `+1.475` | B-4 `Intercept` (4b §6.2, band (0, 10]) | +1.474913 | +1.474915 | `+1.475` | yes | no |
| 19 | §4.2 | `+1.215` | B-2 `Intercept` (4b §4 liquidation control) | +1.214576 | +1.214575 | `+1.215` | yes | no |
| 20 | §4.2 | `p = 1.3 × 10⁻⁴⁵` | B-2 `Intercept` p | 1.107e-59 | 1.404e-59 | `p = 1.4 × 10⁻⁵⁹` | **no** (old gives `p = 1.1 × 10⁻⁵⁹`) | **yes** |
| 21 | §4.2 | `0.1%` | intercept shift B-1 → B-2, (B-1 − B-2) / B-1 | 0.077% | 0.077% | `0.1%` | yes | no |
| 22 | §4.3 | `−0.334` | B-1 `time_pressure_z` | -0.333808 | -0.333807 | `−0.334` | yes | no |
| 23 | §4.3 | `[−0.521, −0.146]` | B-1 `time_pressure_z` 95% CI | [-0.521213, -0.146403] | [-0.521247, -0.146367] | `[−0.521, −0.146]` | yes | no |
| 24 | §4.3 | `p = 4.8 × 10⁻⁴` | B-1 `time_pressure_z` p | 0.000481 | 0.0004822 | `p = 4.8 × 10⁻⁴` | yes | no |
| 25 | §4.3 | `+0.55` | B-1 predicted mean ΔRISK_steep at `time_pressure_z` = +2 | +0.547895 | +0.547897 | `+0.55` | yes | no |
| 26 | §4.3 | `+1.88` | B-1 predicted mean ΔRISK_steep at `time_pressure_z` = −2 | +1.883127 | +1.883124 | `+1.88` | yes | no |
| 27 | §4.3 | `27%` | B-1 increase per SD toward the clock, −`time_pressure_z` / `Intercept` | 27.462% | 27.462% | `27%` | yes | no |
| 28 | Figure B caption | `+1.166` | B-5 `Intercept` (500 games) | +1.165817 | +1.177779 | `+1.178` | yes | **yes** |
| 29 | Figure B caption | `+1.216` | B-1 `Intercept` (1,970 games; figB-full = B-1) | +1.215511 | +1.215511 | `+1.216` | yes | no |
| 30 | Figure B caption | `both CIs exclude zero` | B-5 and B-1 `Intercept` 95% CIs | [+0.7872, +1.5444]; [+1.0240, +1.4071] | [+0.7910, +1.5645]; [+1.0239, +1.4071] | `both CIs exclude zero` | yes | no |
| 31 | Figure B, left panel, "500 games" | `+1.166 [+0.787, +1.544]` | B-5 `Intercept` and 95% CI | +1.165817 [+0.787214, +1.544420] | +1.177779 [+0.791048, +1.564509] | `+1.178 [+0.791, +1.565]` | yes | **yes** |
| 32 | Figure B, left panel, "1,970 games" | `+1.216 [+1.024, +1.407]` | B-1 `Intercept` and 95% CI (figB-full) | +1.215511 [+1.023965, +1.407057] | +1.215511 [+1.023945, +1.407076] | `+1.216 [+1.024, +1.407]` | yes | no |
| 33 | Figure C, "§4.1 primary" | `+1.216 [+1.024, +1.407]` | B-1 `Intercept` and 95% CI (figC-primary) | +1.215511 [+1.023965, +1.407057] | +1.215511 [+1.023945, +1.407076] | `+1.216 [+1.024, +1.407]` | yes | no |
| 34 | Figure C, "§4.3a ΔRISK_var" | `+0.449 [+0.370, +0.528]` | B-3 `Intercept` and 95% CI (figC-var) | +0.449079 [+0.369826, +0.528333] | +0.449079 [+0.369801, +0.528357] | `+0.449 [+0.370, +0.528]` | yes | no |
| 35 | Figure C, "§4.3b ΔRISK_steep, WPL ∈ (0,10]" | `+1.475 [+1.298, +1.652]` | B-4 `Intercept` and 95% CI (figC-band10) | +1.474913 [+1.297931, +1.651896] | +1.474915 [+1.297927, +1.651903] | `+1.475 [+1.298, +1.652]` | yes | no |
| 36 | Figure C, "liquidation-controlled" | `+1.215 [+1.068, +1.361]` | B-2 `Intercept` and 95% CI (figC-liq) | +1.214576 [+1.068469, +1.360684] | +1.214575 [+1.068337, +1.360812] | `+1.215 [+1.068, +1.361]` | yes | no |
| 37 | Figure C, "time pressure −2 SD" | `+1.883 [+1.462, +2.304]` | B-1 predicted mean at `time_pressure_z` = −2, delta-method 95% CI | +1.883127 [+1.462060, +2.304193] | +1.883124 [+1.461940, +2.304308] | `+1.883 [+1.462, +2.304]` | yes | no |
| 38 | Figure C, "time pressure +2 SD" | `+0.548 [+0.127, +0.969]` | B-1 predicted mean at `time_pressure_z` = +2, delta-method 95% CI | +0.547895 [+0.127108, +0.968682] | +0.547897 [+0.127087, +0.968707] | `+0.548 [+0.127, +0.969]` | yes | no |
| 39 | §4.5, paragraph 3 | `1.722` | T-1 `Intercept` (H1), stated as a loss | +1.722266 | +1.750410 | `1.750` | yes | **yes** |
| 40 | §4.5, paragraph 3 | `[−1.789, −1.656]` | T-1 `Intercept` 95% CI | [-1.788952, -1.655581] | [-1.810129, -1.690691] | `[−1.810, −1.691]` | yes | **yes** |
| 41 | §4.5, paragraph 3 | `−0.475` | T-2 `delta_risk_steep_z` (H2) | -0.475078 | -0.475397 | `−0.475` | yes | no |
| 42 | §4.5, paragraph 3 | `[−0.527, −0.423]` | T-2 95% CI | [-0.527244, -0.422912] | [-0.527557, -0.423237] | `[−0.528, −0.423]` | yes | **yes** |
| 43 | §4.5, paragraph 3 | `p = 2.9 × 10⁻⁷¹` | T-2 p | 2.915e-71 | 2.266e-71 | `p = 2.3 × 10⁻⁷¹` | yes | **yes** |
| 44 | §4.5, paragraph 3 | `−0.085` | T-4 `delta_risk_steep_z` (H4a) | -0.085439 | -0.086152 | `−0.086` | yes | **yes** |
| 45 | §4.5, paragraph 3 | `[−0.137, −0.034]` | T-4 95% CI | [-0.137222, -0.033657] | [-0.137967, -0.034336] | `[−0.138, −0.034]` | yes | **yes** |
| 46 | §4.5, paragraph 3 | `p = .0012` | T-4 p | 0.001221 | 0.001119 | `p = .0011` | yes | **yes** |
| 47 | §4.5, paragraph 3 | `−0.390` | T-5 `delta_risk_steep_z` (H4b) | -0.389863 | -0.389947 | `−0.390` | yes | no |
| 48 | §4.5, paragraph 3 | `[−0.397, −0.383]` | T-5 95% CI | [-0.397027, -0.382699] | [-0.397112, -0.382781] | `[−0.397, −0.383]` | yes | no |
| 49 | §4.5, paragraph 4 | `+0.209` | T-6 `WPL_self_z` (v3 §6.5 control) | +0.209065 | +0.208187 | `+0.208` | yes | **yes** |
| 50 | §4.5, paragraph 4 | `1.72` | T-1 `Intercept`, as a loss ("the 1.72-point cost") | +1.722266 | +1.750410 | `1.75` | yes | **yes** |
| 51 | §6, "A silent false null" | `+1.17` | B-5 `Intercept` ("+1.17 at pilot scale") | +1.165817 | +1.177779 | `+1.18` | yes | **yes** |

## Notes

- Model IDs are those of `specs/paper4_correction_spec.md` §3.2. Figure B "1,970 games" and the four model rows of Figure C come from figure fits that the correction report §4.2 confirms are the same fits as B-1, B-2, B-3 and B-4; their values are taken from those models.
- Figure values are the numbers printed in `figures/paper4/figB_pilot_vs_full.png` and `figC_robustness_ladder.png`.
- §6 "+1.17 at pilot scale" refers to the 500-game pilot estimate of the §4.1 model, which is B-5.
- "1.72" / "1.722" state the H1 intercept as a loss, so the value shown is the negated intercept.

## Numbers in the paper that are not from a mixed model (not listed above)

| location | values | source |
|---|---|---|
| Abstract, §2 | sample and evaluation counts (1,970 games; 50,021 position-moves; 126,449, 63,429, 57,294, 5,726 evaluations; 2,317 and 578 players; 51.0%; 30 of 2,000 games) | counts |
| Abstract, §4.1, Figure A caption | 59.85%, sign-test p = 1.8 × 10⁻¹⁷⁰, median ΔRISK +0.63, 19,836 non-zero deviations, n = 19,842, 295 moves beyond ±40 WP | model-free sign test and descriptives |
| §4.1 | 39.7% and 42.7% of rows | counts |
| §4.3 | decile profile +0.46 and +1.70 | observed decile means, no model |
| §4.4, Figure B right panel and caption | PC1 slope +0.521 (p = .0023, n = 348; CI [+0.188, +0.854]), +0.161 (p = .065, n = 578), +0.160 [−0.010, +0.331], 69% | OLS on player means (`paper4b_figures.py:pc1_slope`, 4b §5) |
| §4.5 | 20,387 training moves; 44 rows, p = .98; one fifth of replies; +0.22 depth offset; 2,000 re-evaluated replies | counts, χ² test, depth check |
| §4.5, paragraph 4 | +0.11 points | two-way cluster-robust mean of `RES` (v3 post-hoc §B), not a mixed model |
| §4.5, paragraph 4 | 99.2% and 74.4% | descriptive shares by decile |
| §6 | 7,232 rows, 25% | coverage counts |
| §6 | weighted overall −0.02 points | common-support calibration (v3 post-hoc §A) |
| §6 | "an intercept of exactly zero, and p = 1" | the degenerate lbfgs output being described, not an estimate |
