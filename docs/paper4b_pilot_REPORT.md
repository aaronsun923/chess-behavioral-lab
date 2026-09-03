# Paper 4b — Full-Sample Report (Section 6 deliverables)

_Generated 2026-08-25 03:50 UTC. Risk evaluation now covers **all 1,970 v1 games**._

> **Scope note — this is not a redraw.** The underlying game sample is still the locked v1 draw (2,000 games at `random_seed = 20260823`, 1,970 retrievable). What changed is that SPEC v2 §2's additional 500-game subsetting (`random_seed = 20260824`) has been lifted by the designer, so §3 risk evaluation now runs on every row v1 scored rather than on a subset of them. The original 500-game draw is preserved at `paper4b_cache/pilot4b_sample_games_500.csv`; every row it selected is a subset of what is reported here, and those rows were reused, not recomputed. No engine setting, definition, band, or model was changed — only the number of rows they are applied to.


## 0. Spec erratum on the §3.2 sign — ratified, read this first

§3.2 defines the dependent variable as

```
RISK_steep(m) = WP_self(opponent 1st choice) − WP_self(opponent 5th choice)
```

and then states in the same clause that *"the opponent's 1st choice gives my WP the **lowest**, the 5th choice the **highest**, therefore this value is non-negative."* Those two sentences cannot both hold: lowest − highest is **non-positive**, and it is the exact negation of the quantity the note describes.

The rest of the spec resolves which one is meant. §3.4 says `ΔRISK < 0` means *"the human chose the lower-risk move"*, and §4.1 says a **negative intercept** supports the hypothesis. Both require `RISK` to **increase** with risk. Only the non-negative orientation does that. Three statements (the §3.2 note, §3.4, §4.1) agree with each other; the operand order printed in the §3.2 formula is the outlier and reads as a transcription slip.

**SPEC ERRATUM — ratified.** The designer (Aaron) has confirmed that the printed operand order in §3.2 is a **typo**, and that the intended definition is the one stated in the §3.2 note, §3.4 and §4.1. The orientation used throughout this report is therefore the authoritative one:

```
RISK_steep(m) = WP_self(opponent 5th choice) − WP_self(opponent 1st choice)  ≥ 0
```

> **Erratum for the spec file.** `paper4b_spec_v2.md` §3.2 should read `WP_self(对手第5选择) − WP_self(对手第1选择)`. As printed, the formula is the negation of the quantity its own explanatory note, §3.4 and §4.1 all describe. No other clause is affected, and no locked parameter other than this typo was altered. Numbers in this report stand as written; the earlier "negate everything" caveat no longer applies.


## 1. Environment and measured cost

| item                                | value                                                 |
|-------------------------------------|-------------------------------------------------------|
| Stockfish                           | Stockfish 18  (same binary as v1)                     |
| depth / MultiPV / Threads / Hash    | 15 / 5 / 1 / 128 MB                                   |
| independent search per position     | yes (`ucinewgame` forced, as v1)                      |
| python-chess / pandas / statsmodels | 1.11.2 / 2.3.3 / 0.14.6                               |
| machine                             | macOS-26.5-arm64-arm-64bit (10 cores)                 |
| worker processes                    | 9                                                     |
| engine calls                        | 71,654                                                |
| **measured ms per call**            | **1606 ms**                                           |
| wall-clock                          | 213.2 min (total across 3 passes; see the note below) |
| evaluations stored                  | 57,294                                                |
| errors                              | none                                                  |

§5's estimate (25–40 min at ~500 ms/call) was written for the 500-game subset; that pass landed inside it at 37.0 min. Across all 3 passes (including work redone after the shard bug) the full sample cost **213 min** at **1606 ms/call** on 9 processes. The per-call figure is above 500 ms for the same reason documented in the v1 report §1 (MultiPV 5 costs ~5× MultiPV 1, plus contention); v1's uncontended benchmark was 492 ms/call.


> **A bug that destroyed data, and how it was caught.** The risk evaluation was extended from the 500-game subset to all 1,970 games as a *resumed* run. Resume worked correctly — it identified the 7,232 already-evaluated rows and skipped them — but the shard writer named its output `part-NNNN.parquet` with the counter restarting at zero on every run, so the second pass overwrote the first pass's files with its own. The rows that resume had just skipped were deleted by the run that skipped them. A post-run coverage check (rows needing evaluation vs. rows present, per game) caught it: 1,472 of 1,970 games covered instead of all of them, 7,180 rows missing. The writer now tags every file with a unique per-run token so no run can overwrite another's output, the same fix was applied to the v1 pipeline where the identical pattern was latent, and the lost rows were recomputed. **The v1 dataset was never affected** — it was written by a single run and its 50,021 rows across 1,970 games verify intact. The cost table above includes the recomputed work, so it reflects compute actually spent rather than the minimum this job needed.


> **One methodological note that changed a result.** statsmodels' `lbfgs` optimizer converged to a degenerate all-zero solution on every §4 model here — silently, reporting `converged=True` with all variance components at 0, the intercept at exactly 0, p = 1 and a 95% CI of roughly ±5×10⁷. Taken at face value it would have been reported as a clean null. `bfgs`, `cg`, `powell` and `nm` all agree with each other and with OLS on the same data, so the shared fitting helper now tries optimizers in order and rejects a degenerate optimum instead of returning it. The v1 report was regenerated under the fixed helper and every v1 coefficient is unchanged — `lbfgs` happened to work on v1's dependent variable.


All v1 infrastructure was reused, not recomputed: the WP formula, `pov_cp`, the engine configuration, the middlegame window, and the completed v1 shards supplying `WPL`, `gap_12`, `eval_volatility` and `time_pressure`. No new positions were added; §3 only evaluates the *successors* of moves v1 had already scored. v1 shards were not modified — 4b writes to `paper4b_results/`.


## 2. Sample composition

| quantity                                   | count      | note                                         |
|--------------------------------------------|------------|----------------------------------------------|
| v1 games covered                           | 1,970      | all of them — §2 subsetting lifted           |
| v1 position-move rows in those games       | 50,021     | no new positions added                       |
| rows with `m_played == m_best`             | 21,374     | 42.73%  → ΔRISK ≡ 0, evaluation skipped (§5) |
| rows evaluated (2 calls each)              | 28,647     | 57.27%                                       |
| **rows with WPL ∈ (0, 5]  [LOCKED §4.1]**  | **19,842** | **39.67%** of all rows                       |
| rows with WPL ∈ (0, 10]  [§4.3 robustness] | 25,012     | 50.00%                                       |
| rows with WPL > 10                         | 3,067      | 6.13%                                        |

The §4.1 band holds **39.67%** of all rows and **69.26%** of the rows that were actually evaluated. Rows where the human played the engine's top move have `WPL = 0` and are excluded by the band's open lower bound automatically — the §5 skip and the §4.1 band agree, so no row is both skipped and needed.


- Successor positions returning fewer than 5 PV lines (fewer legal replies), where the "5th choice" falls back to the last available line: **753** of 57,294 evaluations (1.31%).

- Successors that were terminal (mate/draw, risk defined as 0): 2 (0.00%) — {'checkmate': np.int64(2)}.


## 3. `ΔRISK_steep` distribution and sign test

`ΔRISK_steep = RISK_steep(m_played) − RISK_steep(m_best)`, in win-probability points. Negative = the human chose the **flatter, more recoverable** path (§3.4).

| sample                        | n      | mean   | median | p25    | p75    | sd     |
|-------------------------------|--------|--------|--------|--------|--------|--------|
| all rows                      | 50,021 | +1.274 | +0.000 | +0.000 | +1.717 | 10.408 |
| WPL ∈ (0,5] (the §4.1 sample) | 19,842 | +1.210 | +0.632 | -1.330 | +3.382 | 12.947 |

| quantile (§4.1 sample) | ΔRISK_steep |
|------------------------|-------------|
| 1%                     | -36.775     |
| 5%                     | -23.036     |
| 10%                    | -9.644      |
| 25%                    | -1.330      |
| 50%                    | +0.632      |
| 75%                    | +3.382      |
| 90%                    | +13.911     |
| 95%                    | +26.660     |
| 99%                    | +39.650     |

### Sign test (model-free, as §4.1 requires)

| sample              | n (non-zero) | negative | positive | % negative | binomial p |
|---------------------|--------------|----------|----------|------------|------------|
| all rows            | 28,633       | 10,659   | 17,974   | 37.23%     | 0          |
| WPL ∈ (0,5]  [§4.1] | 19,836       | 7,964    | 11,872   | 40.15%     | 1.81e-170  |
| WPL ∈ (0,10] [§4.3] | 25,004       | 9,668    | 15,336   | 38.67%     | 1.02e-283  |

**Reading.** In the §4.1 band, **40.15%** of deviations went toward the flatter path (median **+0.632** WP points, binomial p = 1.81e-170). The majority direction is toward **higher** risk, against the §1 prediction.


![dRISK distribution](paper4b_figures/drisk_distribution.png)


## 4. §4.1 main test — risk preference at equal expected loss

```
ΔRISK_steep ~ WPL_z + gap_12_z + eval_volatility_z + time_pressure_z + (1|player_id) + (1|game_id)
```

**The intercept is the core quantity.** Predictors are standardized *within the §4.1 estimation sample*, so the intercept is the expected `ΔRISK_steep` at the sample's mean deviation size, mean position sharpness and mean time pressure. A significantly negative intercept means: holding how far the human strayed from the engine fixed, the move they chose sits on a systematically flatter punishment curve.

**Linear mixed model — §4.1 primary**

Random intercepts `player_id` (group) + `game_id` (variance component), the same approximation to crossed effects documented in the v1 report §10.5.

| term              | coef (std.) | 95% CI             | p        |     |
|-------------------|-------------|--------------------|----------|-----|
| Intercept         | +1.2155     | [+1.0240, +1.4071] | 1.63e-35 | *** |
| WPL_z             | +0.2631     | [+0.0469, +0.4794] | 0.0171   | *   |
| gap_12_z          | -0.5841     | [-0.8017, -0.3664] | 1.44e-07 | *** |
| eval_volatility_z | +0.4562     | [+0.2730, +0.6394] | 1.06e-06 | *** |
| time_pressure_z   | -0.3338     | [-0.5212, -0.1464] | 0.000481 | *** |
- random-effect variance `game Var` = 0.0283

- N = 19842

**OLS with player-clustered SEs (robustness)**



| term              | coef (std.) | 95% CI             | p        |     |
|-------------------|-------------|--------------------|----------|-----|
| Intercept         | +1.2097     | [+1.0188, +1.4006] | 2.07e-35 | *** |
| WPL_z             | +0.2717     | [+0.0607, +0.4826] | 0.0116   | *   |
| gap_12_z          | -0.5902     | [-0.8244, -0.3559] | 7.94e-07 | *** |
| eval_volatility_z | +0.4606     | [+0.2156, +0.7057] | 0.00023  | *** |
| time_pressure_z   | -0.3015     | [-0.5084, -0.0946] | 0.00429  | **  |

- N = 19842


### The core number

Intercept = **+1.2155** WP points (95% CI [+1.0240, +1.4071], p = 1.63e-35).


The intercept is **positive and significant** — the *opposite* of the §1 direction. Controlling for deviation size, humans chose moves that are **sharper** than the engine's top choice, not flatter. This is the opposite of the §1 hypothesis and, on the full sample, is a finding in its own right rather than a null.


(§0 erratum: the sign convention here is the ratified one; no negation applies.)


### Liquidation diagnostic (added at the designer's request)

Tests the confound flagged in the first pilot: a flatter successor may simply be a *simplified* one. Two position-level covariates are added to the §4.1 model and nothing else changes.

- `played_is_capture` — 1 if `m_played` is a capture (en passant included), else 0.
- `dmat` — **material change after `m_played` minus material change after `m_best`**, where material change is the change in **total material on the board** (both sides, P=1 N=3 B=3 R=5 Q=9, kings excluded) caused by that move. It is ≤ 0 for a capture, 0 for a quiet move, and positive for a promotion. `dmat < 0` therefore means the human's move liquidated **more** than the engine's choice — exactly the direction the confound predicts should drive `ΔRISK_steep` down.

Both covariates are **mean-centred**, so the intercept keeps the same meaning as in the model above (expected `ΔRISK_steep` at sample-average conditions) and the two intercepts are directly comparable.


| quantity                            | count          | share  |
|-------------------------------------|----------------|--------|
| rows in the §4.1 band               | 19,842         |        |
| `m_played` is a capture             | 2,893          | 14.58% |
| `m_best` is a capture               | 2,560          | 12.90% |
| `dmat` < 0 (human liquidated more)  | 2,055          | 10.36% |
| `dmat` > 0 (engine liquidated more) | 1,705          | 8.59%  |
| `dmat` mean / sd                    | -0.037 / 1.329 |        |
**Linear mixed model — §4.1 + liquidation controls**

Identical to the §4.1 primary model plus the two centred covariates.

| term                | coef (std.) | 95% CI             | p        |     |
|---------------------|-------------|--------------------|----------|-----|
| Intercept           | +1.2146     | [+1.0685, +1.3607] | 1.11e-59 | *** |
| WPL_z               | +0.5317     | [+0.3637, +0.6996] | 5.48e-10 | *** |
| gap_12_z            | -0.4739     | [-0.6444, -0.3034] | 5.1e-08  | *** |
| eval_volatility_z   | +0.0970     | [-0.0452, +0.2392] | 0.181    |     |
| time_pressure_z     | -0.2266     | [-0.3708, -0.0824] | 0.00208  | **  |
| played_is_capture_c | +2.5981     | [+2.1367, +3.0595] | 2.58e-28 | *** |
| dmat_c              | -5.8055     | [-5.9266, -5.6844] | 0        | *** |
- random-effect variance `game Var` = 0.0218

- N = 19842


| model                                  | intercept | 95% CI             | p        |
|----------------------------------------|-----------|--------------------|----------|
| §4.1 primary (no liquidation controls) | +1.2155   | [+1.0240, +1.4071] | 1.63e-35 |
| §4.1 + `played_is_capture` + `dmat`    | +1.2146   | [+1.0685, +1.3607] | 1.11e-59 |

### Does the intercept survive?

**Yes.** The intercept moves from **+1.2155** to **+1.2146** (a 0.1% reduction), p = 1.11e-59. It stays positive and significant, so the §4.1 result is **not** an artefact of the human simply trading pieces more often than the engine: even comparing moves that liquidate the same amount, the human's choice sits on the steeper punishment curve.

- `dmat_c` = **-5.8055** (p = 0) — differential liquidation does predict `ΔRISK_steep`; the sign says that removing more material than the engine did is associated with a steeper successor (recall `dmat < 0` = human liquidated more).

- `played_is_capture_c` = **+2.5981** (p = 2.58e-28) — the move being a capture does predict `ΔRISK_steep`.


> **The confound does not merely fail to explain the result — it runs the other way.** I flagged the worry that a flatter successor might just be a *simplified* one, so that liquidation would manufacture the effect. The data reject that premise: the `dmat_c` coefficient is **negative**, and since `dmat < 0` means the human removed more material than the engine would have, removing more material predicts a **steeper** successor, not a flatter one. On reflection this is the more sensible chess: a capture typically obliges a recapture, and a position where one reply is forced and the alternatives lose material has a *wide* spread across the opponent's top five, not a narrow one. Simplification in the sense of 'fewer pieces' is not the same thing as flatness in the sense of 'replies matter less'. My original caveat conflated them.


_Definitional check: `dmat` above is total board material (the liquidation reading). Using the material-**balance** reading instead leaves the intercept at +0.9823 (p = 4.4e-39, OLS with player-clustered SEs), so the conclusion does not turn on which reading of "material change" is intended._


### Time-pressure moderation of the mean

`time_pressure` = clock remaining ÷ base time, so **low `time_pressure` = little time left**. Note first that `time_pressure_z` is **already a term in the pre-specified §4.1 model** — and because the intercept is a constant, "moderation of the mean" by time pressure *is* that main effect. There is no separate product term to identify against a constant, so no re-fit can change the number; what follows reads the coefficient that is already there rather than adding a variant.


**Moderation coefficient: `time_pressure_z` = -0.3338** WP points per SD (95% CI [-0.5212, -0.1464], p = 0.000481).


| time_pressure_z | reading             | clock fraction remaining | predicted ΔRISK_steep |
|-----------------|---------------------|--------------------------|-----------------------|
| -2 SD           | severe time trouble | 0.510                    | +1.8831               |
| -1 SD           | low on time         | 0.658                    | +1.5493               |
| +0 SD           | average             | 0.806                    | +1.2155               |
| +1 SD           | comfortable         | 0.954                    | +0.8817               |
| +2 SD           | lots of time        | 1.102                    | +0.5479               |

**Verdict: the positive intercept is amplified at low remaining time.** The coefficient is negative, and since less time means a *lower* `time_pressure` value, moving one SD toward the clock raises expected `ΔRISK_steep` from +1.2155 to +1.5493 — a 27% increase per SD. Under time pressure these players do not retreat to safer, flatter continuations; they deviate toward *sharper* ones, and they do so more than when they have time to think. That runs in the same direction as the §4.1 headline and makes the §1 risk-management reading harder still to sustain — the moment when a risk-averse agent would most want a recoverable position is exactly where the effect is strongest.


_Descriptive check (not a model variant): observed mean `ΔRISK_steep` by `time_pressure` decile, to confirm the linear term is not smoothing over a non-monotone pattern._


| decile (1 = least time) | median clock fraction | observed mean ΔRISK_steep | n     |
|-------------------------|-----------------------|---------------------------|-------|
| 1                       | 0.523                 | +1.704                    | 1,985 |
| 2                       | 0.663                 | +1.587                    | 1,997 |
| 3                       | 0.735                 | +1.234                    | 1,971 |
| 4                       | 0.784                 | +1.763                    | 1,987 |
| 5                       | 0.824                 | +1.195                    | 2,006 |
| 6                       | 0.857                 | +1.244                    | 1,983 |
| 7                       | 0.886                 | +1.184                    | 1,963 |
| 8                       | 0.913                 | +1.021                    | 1,984 |
| 9                       | 0.939                 | +0.702                    | 1,992 |
| 10                      | 0.973                 | +0.458                    | 1,974 |

Lowest-time decile **+1.704** vs highest-time decile **+0.458** — the descriptive gradient agrees with the fitted coefficient.


## 5. §4.2 — does Paper 1 style predict risk preference?

Paper 1 PC1 rebuilt on the male titled roster with the construction from `style_skill_analysis.py` (n_games-weighted player aggregation, correlation-matrix PCA via SVD, oriented so `exchange_rate` + `forcing_move_rate` load positive). PC1 explains **35.10%** of variance; PC2 19.73%.


| indicator               | PC1 loading |
|-------------------------|-------------|
| exchange_rate           | +0.4314     |
| tension_duration        | -0.4232     |
| forcing_move_rate       | +0.4177     |
| reactive_move_rate      | +0.4114     |
| avg_mobility            | -0.3788     |
| center_control_score    | -0.3536     |
| pawn_storm_indicator    | -0.1254     |
| castling_ply            | -0.0703     |
| king_shelter_score      | -0.0412     |
| advanced_pawn_push_rate | -0.0100     |

**Positive PC1 = attacking/sharp pole; negative PC1 = positional pole.** The §4.2 pre-specified hypothesis is that the positional pole (PC1 negative) predicts a **more negative** ΔRISK — i.e. a *positive* slope on PC1.


Player-level sample: **578 roster players** with both a style vector and at least one §4.1-band row (median 16 rows per player).

**Player-level OLS — §4.2 pre-specified**

DV = player mean ΔRISK_steep over WPL ∈ (0,5] rows; roster members only.

| term      | coef (std.) | 95% CI             | p        |     |
|-----------|-------------|--------------------|----------|-----|
| Intercept | +1.2108     | [+0.8913, +1.5303] | 3.61e-13 | *** |
| PC1       | +0.1605     | [-0.0099, +0.3309] | 0.0649   |     |

- N = 578


Slope on PC1 = **+0.1605** (p = 0.0649); Pearson r = +0.0768, R² = 0.0059.


**Direction check against the pre-specified hypothesis.** The hypothesis predicts a positive slope (positional pole → more negative ΔRISK). The observed slope is positive and not significant at 5%, so the data is **uninformative** about it — the slope cannot be separated from zero.

> **This is where the full sample changed the answer, and it is worth saying plainly.** On the 500-game subset this slope was **+0.5207 (p = 0.0023)** across 348 players and was reported as matching the pre-specified direction. On all 1,970 games it is **+0.1605 (p = 0.0649)** across 578 players — the point estimate shrank by roughly 69% and no longer clears the 5% level. The sign is unchanged, so this is a weakening rather than a reversal, but the subset result was a stronger claim than the data support. Four times the games and twice the players moved the estimate *toward zero*, which is the signature of a small-sample overestimate rather than of a real effect awaiting power. **§4.2 should be read as unsupported.** The §4.1 intercept, by contrast, was stable across the same expansion (+1.1658 → +1.2155).



_Not pre-specified, shown only because it is the obvious confound: adding mean Elo gives PC1 slope +0.1621 (p = 0.0672). It is reported for interpretation, not as a §4.2 result._


![style vs dRISK](paper4b_figures/style_vs_drisk.png)


## 6. §4.3 robustness — the two specified variants, and only those


### 6.1 `RISK_var` in place of `RISK_steep`

**ΔRISK_var, WPL ∈ (0,5]**

Same model, sensitivity DV (§3.3).

| term              | coef (std.) | 95% CI             | p        |     |
|-------------------|-------------|--------------------|----------|-----|
| Intercept         | +0.4491     | [+0.3698, +0.5283] | 1.17e-28 | *** |
| WPL_z             | +0.0761     | [-0.0133, +0.1656] | 0.0951   |     |
| gap_12_z          | -0.2320     | [-0.3219, -0.1420] | 4.36e-07 | *** |
| eval_volatility_z | +0.1894     | [+0.1136, +0.2651] | 9.57e-07 | *** |
| time_pressure_z   | -0.1345     | [-0.2120, -0.0570] | 0.000673 | *** |
- random-effect variance `game Var` = 0.0287

- N = 19842

- sign test: 40.17% negative of 19,842 non-zero rows (binomial p = 6.73e-170); median +0.2287.


### 6.2 WPL band widened to (0, 10]

**ΔRISK_steep, WPL ∈ (0,10]**

Same model, wider band (§4.3).

| term              | coef (std.) | 95% CI             | p        |     |
|-------------------|-------------|--------------------|----------|-----|
| Intercept         | +1.4749     | [+1.2979, +1.6519] | 5.69e-60 | *** |
| WPL_z             | +0.9355     | [+0.7375, +1.1335] | 2.04e-20 | *** |
| gap_12_z          | -0.9518     | [-1.1511, -0.7525] | 7.93e-21 | *** |
| eval_volatility_z | +0.4734     | [+0.3061, +0.6407] | 2.92e-08 | *** |
| time_pressure_z   | -0.3134     | [-0.4849, -0.1419] | 0.000341 | *** |
- random-effect variance `game Var` = 0.0312

- N = 25012


### 6.3 The three intercepts side by side

| model                             | intercept | 95% CI             | p        | N      |
|-----------------------------------|-----------|--------------------|----------|--------|
| §4.1 primary — ΔRISK_steep, (0,5] | +1.2155   | [+1.0240, +1.4071] | 1.63e-35 | 19,842 |
| §4.3a — ΔRISK_var, (0,5]          | +0.4491   | [+0.3698, +0.5283] | 1.17e-28 | 19,842 |
| §4.3b — ΔRISK_steep, (0,10]       | +1.4749   | [+1.2979, +1.6519] | 5.69e-60 | 25,012 |

[LOCKED §4.3] No further variants were fitted and no subgroup was examined.


## 7. Sign check — 10 positions, human-readable

Verify by eye that the perspective flip in §3.1 is right. `WP_self` is always from the point of view of **the side that played the move**, evaluated in the successor position where the *opponent* is to move. `RISK_steep` is how much win probability the mover stands to regain if the opponent slips from their best reply to their 5th — so it must be ≥ 0, and a forcing/sharp move should show a larger value than a quiet consolidating one.

| game_id      | ply | stm   | m_played | m_best | WPL  | RISK(played) | RISK(best) | ΔRISK  |
|--------------|-----|-------|----------|--------|------|--------------|------------|--------|
| 169172941228 | 38  | white | Qc2      | Qe2    | 1.65 | 1.38         | 0.55       | +0.83  |
| 98581527795  | 25  | black | Qb6      | a5     | 0.99 | 0.63         | 1.79       | -1.17  |
| 169321030254 | 36  | white | Nb5      | h4     | 4.77 | 6.16         | 2.82       | +3.33  |
| 115687075019 | 22  | white | c3       | h3     | 4.40 | 2.29         | 3.59       | -1.30  |
| 166148848516 | 21  | black | dxe5     | Nxe5   | 0.90 | 1.08         | 7.94       | -6.86  |
| 169142337646 | 16  | white | Qxa4+    | cxd4   | 0.27 | 6.99         | 5.67       | +1.32  |
| 77763685657  | 18  | white | dxe5     | Nbd2   | 4.47 | 28.65        | 2.97       | +25.69 |
| 5440523670   | 22  | white | g4       | axb5   | 1.47 | 5.88         | 13.19      | -7.31  |
| 168482983138 | 25  | black | Nb4      | Qd6    | 4.32 | 5.44         | 3.10       | +2.34  |
| 147608457042 | 29  | black | Nf6      | f6     | 3.06 | 2.07         | 1.82       | +0.25  |

<details><summary>FEN for each of the 10 positions</summary>

- `169172941228` ply 38 (white to move): `3r1rk1/1pq2pbp/p5p1/4p3/8/1PP3N1/1P1Q1PPP/R3R1K1 w - - 1 20`
- `98581527795` ply 25 (black to move): `r2qkb1r/1b1n1p2/p1n1p1p1/1p1pP2p/2pP1P2/2P2NPP/PP2N1B1/R1BQ1RK1 b kq - 0 13`
- `169321030254` ply 36 (white to move): `2r2rk1/pp3ppb/1n2p2p/3pP3/3N1P2/6P1/PP3PBP/2R2RK1 w - - 0 19`
- `115687075019` ply 22 (white to move): `r2qr1k1/ppp2ppp/2n2n2/2bp4/5Nb1/5NP1/PPP1PPBP/R1BQ1RK1 w - - 12 12`
- `166148848516` ply 21 (black to move): `r1b2rk1/1pqn1pbp/2pp1np1/p3P3/P3P3/2PBBN1P/1P1N1PP1/R2Q1RK1 b - - 0 11`
- `169142337646` ply 16 (white to move): `r1bqkbnr/p4ppp/4p3/3pP3/p2p4/P1P2N2/1P3PPP/RNBQ1RK1 w kq - 0 9`
- `77763685657` ply 18 (white to move): `r2n1rk1/pppqbppp/3p1n2/1P2p3/2BPP1b1/2P2N2/P4PPP/RNBQR1K1 w - - 1 10`
- `5440523670` ply 22 (white to move): `1rbq1rk1/3nppbp/p1np2p1/1pp5/P3PP2/3P1NPP/1PP1N1B1/R1BQ1RK1 w - - 1 12`
- `168482983138` ply 25 (black to move): `2rq1rk1/1p2ppbp/p1n3p1/3p1b1n/N2P4/1P2BNP1/P3PPBP/2RQ1RK1 b - - 4 13`
- `147608457042` ply 29 (black to move): `r2q2k1/pp1nrppp/2p1b1n1/3p4/3P4/2NBPPN1/PP3QPP/3R1RK1 b - - 1 15`

</details>


**Automated checks across all 28,647 evaluated rows:**
- `RISK_steep < 0` anywhere: **0** (must be 0 — the metric is non-negative by construction under the §0 orientation).
- mean `RISK_steep(m_best)` = 4.333, mean `RISK_steep(m_played)` = 5.607 WP points.
- correlation between the two = +0.3590 (high is expected: both describe the same parent position).
- The §3.1 test suite (`python3 paper4b_pilot.py selftest`) passes all 7 assertions, including `WP_self + WP_opp == 100` line by line, `RISK_steep` in WP_self equalling the opponent's own top-to-5th gap in WP_opp, and a cross-check that `WP_self(opponent's best reply)` reproduces v1's independently-written `_wp_after`.


## 8. Where this leaves the hypothesis

- §4.1 intercept: **+1.2155** (p = 1.63e-35) — contradicts the §1 proposition, under the §0 orientation.

- §4.1 model-free sign test: 40.15% of deviations toward the flatter path, i.e. 59.85% toward the sharper one (binomial p = 1.81e-170).

- Time-pressure moderation of the mean: `time_pressure_z` = -0.3338 (p = 0.000481) — the positive intercept is **amplified** when little time remains (+1.70 in the lowest-time decile vs +0.46 in the highest).

- §4.2 style link: PC1 slope +0.1605 (p = 0.0649), uninformative about the pre-specified direction.


On the full sample these bullets tell one story rather than two. The population-level result is clear and runs **against** §1: deviations are sharper than the engine's choice, not flatter, by every measure tested — the model intercept, the model-free sign test, both §4.3 variants, and the liquidation-controlled model. The cross-player style gradient that looked supportive on the 500-game subset does not hold up on the full data. **The §1 proposition is not supported, and the direction of the evidence is the opposite of the one it predicts.** That is a substantive result, not a null: at equal expected loss these players systematically prefer the sharper continuation.


The §1 proposition is about *risk preference at equal expected loss*, and this analysis tests it by conditioning on `WPL` rather than by manipulating it. Of the three limits below, the liquidation one has now been tested and withdrawn; two remain open:
1. **`RISK_steep` and `WPL` are not independent.** Both are read off the same engine evaluation tree, and sharper positions produce larger values of both. Conditioning on `WPL_z` linearly may not remove that dependence, so part of any intercept can be functional-form residue rather than preference.
2. ~~**A flatter successor may be a consequence of the move rather than a reason for it.**~~ **Tested and resolved** — see the liquidation diagnostic in §4. Adding a capture indicator and the differential material change leaves the intercept essentially untouched (+1.2155 → +1.2146), and the liquidation coefficient carries the *opposite* sign to the one this worry assumed: trading more material than the engine predicts a **steeper** successor. Fewer pieces on the board is not the same thing as replies mattering less. This limitation is withdrawn.
3. **The `WPL` band is a conditioning set, not a matching.** Within (0, 5] the human and engine moves still differ in expected loss, and `WPL_z` enters linearly. A tighter test would match moves on `WPL` rather than regress it away.


---

**Full-sample run complete. Stopping here as instructed — no new model variants and no subgroups were added beyond the pre-specified §4.1, the two §4.3 robustness variants, the §4.2 style link, and the liquidation diagnostic.**

