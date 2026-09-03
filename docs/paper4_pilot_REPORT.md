# Paper 4 — Pilot Report (Section 9 deliverables)

_Generated 2026-08-25 00:20 UTC. Pilot only (spec §8.1): 2000 games, `random_seed = 20260823`. Full-scale execution has NOT been run._


## 0. `%clk` coverage — reported first, before anything else

| quantity                              | count           | share   |
|---------------------------------------|-----------------|---------|
| games in locked sample                | 2000            | 100.00% |
| games retrieved & parsed              | 1970            | 98.50%  |
| games with `%clk` on EVERY ply        | 1970            | 100.00% |
| games with `%clk` on ≥1 ply           | 1970            | 100.00% |
| games with NO `%clk` (§5.4 exclusion) | 0               | 0.00%   |
| plies carrying `%clk`                 | 164153 / 164153 | 100.00% |

**Coverage is 100.00%.** Chess.com embeds `[%clk ...]` on every ply of every live game, so the §5.4 rule (*exclude the whole game where `%clk` is absent*) removes **0 games**. Time-pressure analyses therefore run on the same sample as everything else, and no imputation was needed or performed.

- Time controls parsed for 100.00% of games (`base+increment`, e.g. `600+5`); `time_pressure` = clock remaining at that move ÷ base time.


## 1. Environment and versions

| item                                                | value                                                      |
|-----------------------------------------------------|------------------------------------------------------------|
| Stockfish                                           | Stockfish 18                                               |
| engine binary                                       | official `stockfish-macos-m1-apple-silicon`, sf_18 release |
| python-chess                                        | 1.11.2                                                     |
| pandas / numpy / statsmodels                        | 2.3.3 / 2.0.2 / 0.14.6                                     |
| python                                              | 3.9.6                                                      |
| machine                                             | macOS-26.5-arm64-arm-64bit (10 cores)                      |
| depth / MultiPV / Threads / Hash                    | 15 / 5 / 1 / 128 MB                                        |
| worker processes                                    | 9                                                          |
| positions evaluated                                 | 63,429                                                     |
| measured ms/position (per worker, under contention) | 1341.1 ms                                                  |
| benchmarked ms/position (single core, idle machine) | 492 ms                                                     |
| wall-clock for pilot                                | 157.8 min                                                  |

### ⚠ Per-position time is outside the §8.2 band — reported as §8.2 requires

Measured **1341 ms/position**; the spec anticipates 80–150 ms. §8.2 says this "usually means the engine is misconfigured". It is **not** misconfiguration here — the configuration is exactly as locked. Benchmarked on 20 real middlegame positions:

| configuration                                                 | ms/pos | note                        |
|---------------------------------------------------------------|--------|-----------------------------|
| depth 15, **MultiPV 1**, fresh search                         | 97 ms  | inside the §8.2 band        |
| depth 15, **MultiPV 5**, fresh search — **the locked config** | 492 ms | ≈5× the band                |
| depth 15, MultiPV 5, search-tree reuse allowed                | 411 ms | reuse is forbidden by §3    |
| depth 15, MultiPV 5, Hash 16 MB                               | 478 ms | hash size is not the driver |
| depth 12, MultiPV 5, fresh search                             | 129 ms | depth is locked at 15       |

**Conclusion:** the 80–150 ms figure is MultiPV-1 timing. Asking for the top 5 lines costs ~5× because Stockfish must search 5 root moves to full depth instead of pruning everything below the best. Forcing an independent search per position (§3) adds a further ~20%. Nothing was changed — depth 15, MultiPV 5, Threads 1, Hash 128 all stand as locked.

**Consequence for the full sample (59,321 games):** extrapolating this pilot's measured wall-clock, **≈79 h** on this 10-core machine at 9 processes — against §8.2's estimate of 5–9 h on 8 processes. This is a go/no-go input for scaling up; see §10 of this report.


## 2. Data integrity

| quantity                        | value  |
|---------------------------------|--------|
| games in locked sample          | 2,000  |
| games retrieved (PGN)           | 1,970  |
| games not retrievable           | 30     |
| games analysed                  | 1,970  |
| position-move rows              | 50,021 |
| rows per analysed game (mean)   | 25.39  |
| distinct players (side to move) | 2,317  |
| engine positions evaluated      | 63,429 |

**Failures / skips.** 30 of 2000 sampled games (1.5%) could not be retrieved. All 30 failed with `no_archives`: the Chess.com account has since been closed or renamed, so its game archive is gone. This is attrition in the *re-download*, not in the analysis — see the note on provenance in §10. Analysis-stage failures:


_None — every retrieved game analysed cleanly._


## 3. `WPL` distribution (before and after winsorization)

| quantile | WPL_raw | WPL (winsorized) |
|----------|---------|------------------|
| 0%       | 0.000   | 0.000            |
| 1%       | 0.000   | 0.000            |
| 5%       | 0.000   | 0.000            |
| 10%      | 0.000   | 0.000            |
| 25%      | 0.000   | 0.000            |
| 50%      | 0.409   | 0.409            |
| 75%      | 3.154   | 3.154            |
| 90%      | 7.386   | 7.386            |
| 95%      | 11.196  | 11.196           |
| 99%      | 22.827  | 22.818           |
| 100%     | 80.475  | 22.827           |
| mean     | 2.520   | 2.430            |
| sd       | 4.785   | 4.196            |
| max      | 80.475  | 22.827           |

- [LOCKED §5.2] winsorization cut = 99th percentile of `WPL_raw` = **22.827 WP points**; 501 rows (1.00%) were clipped.
- `WPL_raw` is retained in every shard for sensitivity analysis.
- The tail is exactly the problem §5.2 anticipates: the top 1% of moves carry 12.6% of all summed loss.


![WPL distribution](paper4_figures/wpl_distribution.png)


## 4. Sign check — 20 random positions, human-readable

Verify by eye: `WPL = wp_best − wp_played ≥ 0`, and both WP values are from the **side to move**'s perspective. Where `move_played == move_engine_best`, `WPL` must be 0.

| game_id      | ply | stm   | engine best | played | wp_best | wp_played | WPL   |
|--------------|-----|-------|-------------|--------|---------|-----------|-------|
| 169232557846 | 35  | black | Qd7         | Qd7    | 61.92   | 61.92     | 0.00  |
| 169107282684 | 32  | white | exd5        | exd5   | 42.33   | 42.33     | 0.00  |
| 169280749562 | 37  | black | Bxd5        | Nxd5   | 48.53   | 39.92     | 8.61  |
| 102685812035 | 30  | white | Qh6         | Na3    | 76.26   | 55.41     | 20.85 |
| 168712782376 | 27  | black | Bd6         | Bd6    | 47.52   | 47.52     | 0.00  |
| 132218400577 | 22  | white | d5          | Rc1    | 55.50   | 51.84     | 3.66  |
| 26073016383  | 37  | black | Rxc8        | Rxc8   | 62.09   | 62.09     | 0.00  |
| 84663835919  | 14  | white | Qxb7        | Qxb7   | 59.10   | 59.10     | 0.00  |
| 169067888312 | 27  | black | cxb6        | cxb6   | 32.70   | 32.70     | 0.00  |
| 168887618762 | 17  | black | f6          | f6     | 47.88   | 47.88     | 0.00  |
| 136891889374 | 16  | white | dxc5        | c4     | 58.39   | 53.03     | 5.35  |
| 168480679116 | 28  | white | Qa4         | Qd1    | 48.25   | 46.51     | 1.74  |
| 105808883177 | 32  | white | g3          | Rb5    | 59.46   | 58.21     | 1.25  |
| 173264572597 | 29  | black | Bxf3        | Bxf3   | 54.59   | 54.59     | 0.00  |
| 169274457424 | 29  | black | cxd4        | cxd4   | 27.96   | 27.96     | 0.00  |
| 169276496716 | 15  | black | O-O         | O-O    | 54.50   | 54.50     | 0.00  |
| 169224058152 | 34  | white | Nxb6        | Rfe1   | 58.92   | 58.57     | 0.36  |
| 112214475307 | 33  | black | Nc7         | b6     | 42.69   | 40.63     | 2.06  |
| 104955064469 | 23  | black | h6          | a5     | 40.36   | 39.48     | 0.88  |
| 169308844454 | 26  | white | Re1         | Nc4    | 57.58   | 40.72     | 16.86 |

<details><summary>FENs for the 20 positions above</summary>

- `169232557846` ply 35 (black to move): `r2qk2r/1p2bpn1/p3p3/n2pP1pp/2pP2P1/P1P2N1Q/1P1N1P1P/1RBR2K1 b kq - 0 18`
- `169107282684` ply 32 (white to move): `r2q1rk1/3n1pbp/p2p1np1/3b4/1p2PP2/4B1PP/1PPQN1B1/R4RK1 w - - 0 17`
- `169280749562` ply 37 (black to move): `2rq1r1k/pp2pp1p/3pbn1P/3Nn1p1/4P1P1/1N3P2/PPP2Q2/2KR1B1R b - - 2 19`
- `102685812035` ply 30 (white to move): `r2q1rk1/p3pp1p/1p4p1/5P2/1n1p1Q2/1P3N2/P3BPPP/bN1R2K1 w - - 0 16`
- `168712782376` ply 27 (black to move): `r2qkbnr/5pp1/p1p1p1b1/3p2Pp/N2P1B1P/5P2/PPPQ4/R3KB1R b KQkq - 2 14`
- `132218400577` ply 22 (white to move): `2r1k2r/1bqnbppp/pp1ppn2/2p5/2PP4/1P2PN1P/PB1NBPP1/R2QR1K1 w k - 1 12`
- `26073016383` ply 37 (black to move): `r1B1nrk1/pp3qb1/1n5p/2pPp3/2P2p1N/P1N1B1P1/5P1P/R2QR1K1 b - - 0 19`
- `84663835919` ply 14 (white to move): `rn1qkb1r/pp3ppp/2p1bn2/8/8/1QN5/PP1PPPBP/R1B1K1NR w KQkq - 0 8`
- `169067888312` ply 27 (black to move): `r2q1k1r/ppp2p2/1Nnp1npp/4p3/1P2P3/2PP1Q2/1P2NPPP/R1B2RK1 b - - 0 14`
- `168887618762` ply 17 (black to move): `r1b1kb1r/pp1n1ppp/1qn1p3/3pP3/3P4/P4N2/1P2NPPP/R1BQKB1R b KQkq - 0 9`
- `136891889374` ply 16 (white to move): `rn1q1rk1/1b1pbppp/p3pn2/1pp5/3P4/1P1BPN2/PBPN1PPP/R2Q1RK1 w - - 7 9`
- `168480679116` ply 28 (white to move): `rn3rk1/p5pp/1p1qpp2/1B1p1b2/2pP4/1QP1P3/PP1N1PPP/R4RK1 w - - 0 15`
- `105808883177` ply 32 (white to move): `2k1r3/pppn1pp1/6rp/5q2/P2P4/2PN4/2P2PPP/1R1Q1RK1 w - - 1 17`
- `173264572597` ply 29 (black to move): `r2q1rk1/p3n2p/2pp2pP/2p1p3/4Ppb1/2NP1N2/PPPQ1PP1/2K3RR b - - 4 15`
- `169274457424` ply 29 (black to move): `r1bq1rk1/pp2nppp/8/2pPP3/2PN4/P7/1B3PPP/R2QKB1R b KQ - 0 15`
- `169276496716` ply 15 (black to move): `r1bqk2r/pp2npbp/2np2p1/2p1p3/4P3/3P1NP1/PPPN1PBP/R1BQR1K1 b kq - 3 8`
- `169224058152` ply 34 (white to move): `2r2rk1/p2nqpp1/1bp1b2p/8/N3B3/1P4P1/PBQ2P1P/3R1RK1 w - - 0 18`
- `112214475307` ply 33 (black to move): `r1r5/pp1kppbp/n1n3p1/1N1p4/3P2P1/BP1NP3/P3KP1P/2R4R b - - 0 17`
- `104955064469` ply 23 (black to move): `r1bq1rk1/5pbp/pn1p1np1/2pPp1B1/2P1P3/2NB1N2/1P3PPP/R2Q1RK1 b - - 1 12`
- `169308844454` ply 26 (white to move): `1r1qk2r/2nbppbp/p2p1np1/2pP4/N3P3/2P5/1P1NBPPP/R1BQ1RK1 w k - 1 14`

</details>


**Automated checks on all 50,021 rows:**

- `WPL_raw < 0`: **0** rows (must be 0 by construction).
- rows where the played move *is* the engine's top move: 21,374 (42.7%); their mean `WPL_raw` = **0.0000** (must be ≈0), max = 0.000.
- `wp_best` mean = 51.40 WP — close to 50 as expected for balanced titled-vs-titled middlegames, confirming no systematic side bias.
- white-to-move mean `wp_best` = 53.53, black-to-move = 49.25 (both near 50 ⇒ perspective is applied per side, not fixed to White).


The standalone perspective test suite (`python3 paper4_pilot.py selftest`) passes all 9 assertions, including a colour-mirror test where `board.mirror()` must reproduce the identical WP for the side to move.


## 5. Binned mean `WPL` against Elo (100-Elo bins)

| Elo bin | n rows | mean WPL (raw) | mean WPL (complexity-adjusted) |
|---------|--------|----------------|--------------------------------|
| 500     | 54     | 5.801          | 5.393                          |
| 1000    | 52     | 2.078          | 2.446                          |
| 1100    | 97     | 2.870          | 2.981                          |
| 1200    | 113    | 3.813          | 4.003                          |
| 1300    | 78     | 2.709          | 2.611                          |
| 1400    | 296    | 4.395          | 4.107                          |
| 1500    | 130    | 3.084          | 3.090                          |
| 1600    | 304    | 3.531          | 3.371                          |
| 1700    | 822    | 3.179          | 3.109                          |
| 1800    | 599    | 3.058          | 2.950                          |
| 1900    | 981    | 2.585          | 2.636                          |
| 2000    | 1,213  | 2.697          | 2.672                          |
| 2100    | 2,038  | 2.858          | 2.794                          |
| 2200    | 3,805  | 2.765          | 2.743                          |
| 2300    | 4,922  | 2.571          | 2.545                          |
| 2400    | 6,135  | 2.569          | 2.548                          |
| 2500    | 7,246  | 2.396          | 2.393                          |
| 2600    | 6,286  | 2.269          | 2.288                          |
| 2700    | 5,949  | 2.248          | 2.262                          |
| 2800    | 4,599  | 2.047          | 2.111                          |
| 2900    | 2,393  | 1.966          | 2.074                          |
| 3000    | 1,163  | 1.749          | 1.820                          |
| 3100    | 416    | 1.368          | 1.487                          |
| 3200    | 117    | 2.120          | 2.293                          |
| 3300    | 91     | 1.652          | 1.856                          |

- Bins with <50 rows suppressed. Pearson r(player_elo, WPL) = **-0.0802** raw, **-0.0735** after complexity adjustment.


> **Who is in these bins.** [LOCKED §4] takes *both* sides' middlegame moves, so the rows are not the titled roster. The pilot covers **2,317 distinct players** drawn from 1,970 games, against a roster of 630 titled players; only **51.0%** of rows have a roster member as the side to move. The remainder are their opponents, who are mostly untitled and span the full rating range — hence bins down to 500. This is correct under §4 and is what makes the §7.2 test possible at all, but it has two consequences worth stating before the full run: `elo_z` in §7.1 is estimated over a mixed titled/untitled population rather than within titled players, and Paper 1's careful title- and gender-composition of the frame does not describe roughly half these rows. If §7.1's Elo effect is meant to be a within-titled-player statement, the model needs a roster-membership indicator or a restriction — a design call, not something I should decide here.


![WPL by Elo](paper4_figures/wpl_by_elo.png)


## 6. Correlation among the complexity proxies

|                 | gap_12 | spread_15 | n_legal | n_reasonable | eval_volatility |
|-----------------|--------|-----------|---------|--------------|-----------------|
| gap_12          | +1.000 | +0.704    | -0.131  | -0.609       | +0.209          |
| spread_15       | +0.704 | +1.000    | -0.127  | -0.735       | +0.216          |
| n_legal         | -0.131 | -0.127    | +1.000  | +0.086       | +0.001          |
| n_reasonable    | -0.609 | -0.735    | +0.086  | +1.000       | -0.275          |
| eval_volatility | +0.209 | +0.216    | +0.001  | -0.275       | +1.000          |

**Collinearity verdict.** Highest |r| among the four §5.3 proxies is 0.735. Pairs at |r| ≥ 0.7: `gap_12`–`spread_15` (+0.70), `spread_15`–`n_reasonable` (-0.74). These carry largely the same information; the §7.1 model keeps both as the spec requires, but the full run should consider collapsing them (or dropping `spread_15`, which is the wider-window duplicate of `gap_12`) and reporting VIFs.


| variable        | VIF  |
|-----------------|------|
| gap_12          | 2.07 |
| spread_15       | 2.83 |
| n_legal         | 1.02 |
| n_reasonable    | 2.32 |
| eval_volatility | 1.09 |



## 7. `n_reasonable` censoring (spec §5.3 flag)

| n_reasonable | rows   | share  |
|--------------|--------|--------|
| 1            | 9,574  | 19.14% |
| 2            | 6,808  | 13.61% |
| 3            | 4,661  | 9.32%  |
| 4            | 3,887  | 7.77%  |
| 5            | 25,091 | 50.16% |

**50.16% of positions sit at the censoring value of 5.** `n_reasonable` counts MultiPV-5 lines within 5 WP points of the top move, so it is right-censored at 5 by construction: whenever six or more moves are near-equal the variable cannot tell 6 from 20. At this censoring rate the variable is close to a constant over much of the sample and its coefficient must not be read as a dose-response effect of "number of good moves". Raising MultiPV would fix it but MultiPV=5 is [LOCKED §3]; the honest alternatives for the full run are to treat it as ordinal/censored or to lean on `gap_12` and `spread_15`, which are not censored.

- `n_legal` (uncensored) mean = 36.3, range 1–65.

- Positions where fewer than 5 PV lines were returned (fewer legal moves): 821 (1.64%).


## 8. Model §7.1 — deviation structure

Pre-specified model (§7.1), standardized continuous predictors, `(1|player_id) + (1|game_id)`:

```
WPL ~ elo_z + gap_12_z + spread_15_z + n_legal_z + eval_volatility_z + time_pressure_z + elo_z:gap_12_z + elo_z:time_pressure_z
```


### 8.1 Primary — restricted to titled roster members

Rows where the side to move is one of the 630 titled players in `analysis_dataset_male_titled_raw.csv`. Opponents' moves are excluded from *this* model only; they remain in the dataset and in §7.2, which requires them. Predictors were **re-standardized within the restricted sample**, so coefficients are per within-titled-player SD and are not numerically comparable to §8.2 below.

| quantity                 | value     | note                 |
|--------------------------|-----------|----------------------|
| rows                     | 25,509    | 51.0% of all rows    |
| distinct players         | 578       | of 630 on the roster |
| distinct games           | 1,970     |                      |
| Elo range (side to move) | 1179–3416 | median 2554          |
**Linear mixed model — roster members only (PRIMARY)**

Random intercepts: `player_id` (group) + `game_id` (variance component).

| term                  | coef (std.) | 95% CI             | p        |     |
|-----------------------|-------------|--------------------|----------|-----|
| Intercept             | +2.3809     | [+2.3227, +2.4392] | 0        | *** |
| elo_z                 | -0.2346     | [-0.2930, -0.1763] | 3.3e-15  | *** |
| gap_12_z              | -0.0057     | [-0.0770, +0.0656] | 0.876    |     |
| spread_15_z           | -0.1557     | [-0.2273, -0.0840] | 2.07e-05 | *** |
| n_legal_z             | +0.3112     | [+0.2567, +0.3658] | 5.09e-29 | *** |
| eval_volatility_z     | +0.4849     | [+0.4301, +0.5396] | 1.49e-67 | *** |
| time_pressure_z       | -0.4288     | [-0.4840, -0.3735] | 2.93e-52 | *** |
| elo_z:gap_12_z        | -0.0291     | [-0.0762, +0.0180] | 0.226    |     |
| elo_z:time_pressure_z | -0.0392     | [-0.0893, +0.0109] | 0.125    |     |
- random-effect variance `game Var` = 0.0303

- N = 25457

**OLS with player-clustered SEs (robustness)**

Same fixed effects; SEs clustered on `player_id`.

| term                  | coef (std.) | 95% CI             | p        |     |
|-----------------------|-------------|--------------------|----------|-----|
| Intercept             | +2.3778     | [+2.3100, +2.4456] | 0        | *** |
| elo_z                 | -0.2304     | [-0.3006, -0.1602] | 1.26e-10 | *** |
| gap_12_z              | -0.0139     | [-0.0897, +0.0618] | 0.718    |     |
| spread_15_z           | -0.1585     | [-0.2323, -0.0847] | 2.57e-05 | *** |
| n_legal_z             | +0.2730     | [+0.2168, +0.3292] | 1.76e-21 | *** |
| eval_volatility_z     | +0.5634     | [+0.4841, +0.6427] | 4.16e-44 | *** |
| time_pressure_z       | -0.4078     | [-0.4668, -0.3488] | 7.24e-42 | *** |
| elo_z:gap_12_z        | -0.0295     | [-0.0920, +0.0331] | 0.356    |     |
| elo_z:time_pressure_z | -0.0448     | [-0.1067, +0.0171] | 0.156    |     |

- N = 25457


### 8.2 Reference — all rows, both sides (the §4 sample)

Retained for comparison, not as the headline. Predictors standardized over the full sample, which mixes titled players with their mostly-untitled opponents.

**Linear mixed model — all rows**

Random intercepts: `player_id` (group) + `game_id` (variance component).

| term                  | coef (std.) | 95% CI             | p         |     |
|-----------------------|-------------|--------------------|-----------|-----|
| Intercept             | +2.4397     | [+2.3980, +2.4813] | 0         | *** |
| elo_z                 | -0.3018     | [-0.3436, -0.2600] | 1.79e-45  | *** |
| gap_12_z              | +0.0272     | [-0.0237, +0.0782] | 0.295     |     |
| spread_15_z           | -0.1666     | [-0.2179, -0.1154] | 1.91e-10  | *** |
| n_legal_z             | +0.3233     | [+0.2841, +0.3625] | 9.74e-59  | *** |
| eval_volatility_z     | +0.5012     | [+0.4618, +0.5406] | 3.35e-137 | *** |
| time_pressure_z       | -0.4018     | [-0.4415, -0.3621] | 1.63e-87  | *** |
| elo_z:gap_12_z        | -0.0476     | [-0.0845, -0.0107] | 0.0115    | *   |
| elo_z:time_pressure_z | -0.0372     | [-0.0712, -0.0032] | 0.0318    | *   |
- random-effect variance `game Var` = 0.0289

- N = 49921

**OLS with player-clustered SEs**

SEs clustered on `player_id`.

| term                  | coef (std.) | 95% CI             | p        |     |
|-----------------------|-------------|--------------------|----------|-----|
| Intercept             | +2.4360     | [+2.3910, +2.4809] | 0        | *** |
| elo_z                 | -0.2942     | [-0.3425, -0.2458] | 9.64e-33 | *** |
| gap_12_z              | +0.0195     | [-0.0346, +0.0737] | 0.48     |     |
| spread_15_z           | -0.1694     | [-0.2208, -0.1180] | 1.05e-10 | *** |
| n_legal_z             | +0.2860     | [+0.2455, +0.3264] | 1.2e-43  | *** |
| eval_volatility_z     | +0.5775     | [+0.5210, +0.6339] | 2.04e-89 | *** |
| time_pressure_z       | -0.3763     | [-0.4211, -0.3316] | 4.53e-61 | *** |
| elo_z:gap_12_z        | -0.0464     | [-0.0965, +0.0037] | 0.0692   |     |
| elo_z:time_pressure_z | -0.0378     | [-0.0855, +0.0098] | 0.12     |     |

- N = 49921


### 8.3 What the restriction changes

| term                  | roster only | p        | all rows | p         |
|-----------------------|-------------|----------|----------|-----------|
| elo_z                 | -0.2346     | 3.3e-15  | -0.3018  | 1.79e-45  |
| gap_12_z              | -0.0057     | 0.876    | +0.0272  | 0.295     |
| spread_15_z           | -0.1557     | 2.07e-05 | -0.1666  | 1.91e-10  |
| n_legal_z             | +0.3112     | 5.09e-29 | +0.3233  | 9.74e-59  |
| eval_volatility_z     | +0.4849     | 1.49e-67 | +0.5012  | 3.35e-137 |
| time_pressure_z       | -0.4288     | 2.93e-52 | -0.4018  | 1.63e-87  |
| elo_z:gap_12_z        | -0.0291     | 0.226    | -0.0476  | 0.0115    |
| elo_z:time_pressure_z | -0.0392     | 0.125    | -0.0372  | 0.0318    |

Elo SD is 305 within the roster vs 343 over all rows, so the two `elo_z` columns are per-SD on different rulers and the comparison is qualitative, not a difference test.


**What survives.** The Elo effect is not an artefact of pooling titled players with much weaker opponents: restricting to roster members shrinks it from -0.302 to -0.235 but it stays large and unambiguous (p = 3e-15). Stronger titled players deviate less from the engine, measured *within* the titled population. The complexity and time-pressure terms are essentially untouched — `eval_volatility` and `time_pressure` move by under 0.05 — which is what you would expect from position-level controls that were never about who was moving.


**What does not survive.** Both Elo interactions lose significance under the restriction: `elo_z:gap_12_z` goes from p = 0.0115 to p = 0.226, and `elo_z:time_pressure_z` from p = 0.0318 to p = 0.125. Halving the sample costs power, so this is not evidence of absence — but neither interaction was ever large, and in the pooled fit both were marginal (p ≈ 0.01–0.03) on the sample that included untitled opponents. The honest reading is that §7.1's interaction terms are unsupported within titled players on a pilot of this size, and the full run is where they get a fair test.


_`%clk` coverage is 100%, so the time-pressure terms cost no sample in either fit (§5.4 excluded nothing)._


## 9. Model §7.2 — the core complementarity test

**Pairing (per the added requirement).** Consecutive-ply pairs `(t, t+1)` are used only where **both plies were evaluated**, both belong to the same game, and the side to move alternates.

| quantity                                          | count  | share   |
|---------------------------------------------------|--------|---------|
| position-move rows                                | 50,021 | 100.00% |
| rows that are pairable (t and t+1 both evaluated) | 48,051 | 96.06%  |
| rows not pairable                                 | 1,970  | 3.94%   |

The unpairable remainder is structural, not data loss: the last evaluated ply of each game (ply 39, or the game's final ply if it ended earlier) has no in-window successor. With a 26-ply window the ceiling is 25/26 = 96.15%.


```
WPL_opponent_next ~ WPL_self_z * gap_12_z * elo_diff_z + n_legal_z + eval_volatility_z + time_pressure_z
```

**Linear mixed model (primary result of the paper)**

Controls are taken at the **actor's** position `t`. DV is the opponent's winsorized `WPL` at `t+1`.

| term                           | coef (std.) | 95% CI             | p        |     |
|--------------------------------|-------------|--------------------|----------|-----|
| Intercept                      | +2.4840     | [+2.4429, +2.5251] | 0        | *** |
| WPL_self_z                     | +0.8315     | [+0.7916, +0.8714] | 0        | *** |
| gap_12_z                       | -0.0209     | [-0.0614, +0.0196] | 0.312    |     |
| WPL_self_z:gap_12_z            | -0.0986     | [-0.1335, -0.0637] | 3.1e-08  | *** |
| elo_diff_z                     | +0.2199     | [+0.1787, +0.2611] | 1.32e-25 | *** |
| WPL_self_z:elo_diff_z          | +0.1136     | [+0.0772, +0.1500] | 9.38e-10 | *** |
| gap_12_z:elo_diff_z            | +0.0525     | [+0.0151, +0.0899] | 0.00589  | **  |
| WPL_self_z:gap_12_z:elo_diff_z | +0.1167     | [+0.0712, +0.1623] | 5.03e-07 | *** |
| n_legal_z                      | +0.0674     | [+0.0277, +0.1071] | 0.000877 | *** |
| eval_volatility_z              | +0.2146     | [+0.1736, +0.2557] | 1.22e-24 | *** |
| time_pressure_z                | -0.1935     | [-0.2343, -0.1527] | 1.35e-20 | *** |
- random-effect variance `game Var` = 0.0211

- N = 47959

**OLS with player-clustered SEs (robustness)**



| term                           | coef (std.) | 95% CI             | p         |     |
|--------------------------------|-------------|--------------------|-----------|-----|
| Intercept                      | +2.4805     | [+2.4372, +2.5239] | 0         | *** |
| WPL_self_z                     | +0.8576     | [+0.7884, +0.9268] | 3.14e-130 | *** |
| gap_12_z                       | -0.0003     | [-0.0503, +0.0496] | 0.989     |     |
| WPL_self_z:gap_12_z            | -0.0971     | [-0.1666, -0.0275] | 0.00623   | **  |
| elo_diff_z                     | +0.2163     | [+0.1690, +0.2637] | 3.59e-19  | *** |
| WPL_self_z:elo_diff_z          | +0.1117     | [+0.0523, +0.1711] | 0.000227  | *** |
| gap_12_z:elo_diff_z            | +0.0541     | [-0.0113, +0.1194] | 0.105     |     |
| WPL_self_z:gap_12_z:elo_diff_z | +0.1191     | [+0.0039, +0.2343] | 0.0427    | *   |
| n_legal_z                      | +0.0826     | [+0.0421, +0.1231] | 6.5e-05   | *** |
| eval_volatility_z              | +0.2610     | [+0.2070, +0.3149] | 2.56e-21  | *** |
| time_pressure_z                | -0.1717     | [-0.2162, -0.1271] | 4.09e-14  | *** |

- N = 47959

**Robustness: controls at the opponent's position `t+1`**

The spec does not say whose position `n_legal`/`eval_volatility`/`time_pressure` describe in §7.2. Reported both ways; see §10.

| term                           | coef (std.) | 95% CI             | p         |     |
|--------------------------------|-------------|--------------------|-----------|-----|
| Intercept                      | +2.4605     | [+2.4182, +2.5028] | 0         | *** |
| WPL_self_z                     | +0.7564     | [+0.7116, +0.8011] | 1.07e-240 | *** |
| gap_12_z                       | -0.0045     | [-0.0442, +0.0353] | 0.826     |     |
| WPL_self_z:gap_12_z            | -0.0703     | [-0.1050, -0.0356] | 7.19e-05  | *** |
| elo_diff_z                     | +0.1932     | [+0.1508, +0.2356] | 4.32e-19  | *** |
| WPL_self_z:elo_diff_z          | +0.1148     | [+0.0785, +0.1511] | 5.79e-10  | *** |
| gap_12_z:elo_diff_z            | +0.0500     | [+0.0128, +0.0872] | 0.00846   | **  |
| WPL_self_z:gap_12_z:elo_diff_z | +0.1128     | [+0.0674, +0.1581] | 1.1e-06   | *** |
| opp_n_legal_z                  | +0.3178     | [+0.2790, +0.3566] | 5.11e-58  | *** |
| opp_eval_volatility_z          | +0.1240     | [+0.0801, +0.1679] | 3.13e-08  | *** |
| opp_time_pressure_z            | -0.3524     | [-0.3922, -0.3127] | 1.34e-67  | *** |
- random-effect variance `game Var` = 0.0291

- N = 47959


### Reading the primary coefficient

`WPL_self_z` = **+0.8315** WP points per SD (95% CI [+0.7916, +0.8714], p = 0).

The coefficient is **positive** and statistically distinguishable from zero at the 5% level on the pilot. A positive sign is the direction §7.2 predicts for complementarity: an engine-suboptimal move is followed by a larger opponent error. This is a 2,000-game pilot reported for pipeline validation and effect direction; it is not the paper's finding and no subgroup was searched for significance (§7.2 final [LOCKED] clause).


**The main threat to this coefficient is shared position difficulty, and the pilot cannot rule it out.** Plies `t` and `t+1` are the same position one move apart, so a sharp, hard, or time-scrambled moment inflates *both* players' `WPL` at once. That alone produces a positive `WPL_self_z` with no complementarity whatever. The §7.2 controls sit at the actor's position `t`, which does not absorb the difficulty the *opponent* faces; the `t+1`-control model above is the bound in the other direction, and it over-corrects by absorbing the mechanism itself. Neither is decisive. Before the full run is interpreted as evidence, the design needs something that separates 'the position got harder for everyone' from 'this player made it harder for *you*' — a within-position comparison, or an instrument for the actor's deviation that is independent of position sharpness. I flag this rather than pick one, since §7.2 is [LOCKED] and the choice is the paper's central inferential claim.


### Game-outcome version (logistic) — interpretation explicitly limited

**Logistic model, DV = win for the side to move**

Draws excluded (3825 rows); SEs clustered on `player_id`.

| term                           | coef (std.) | 95% CI             | p        |     |
|--------------------------------|-------------|--------------------|----------|-----|
| Intercept                      | +0.0046     | [-0.0691, +0.0783] | 0.903    |     |
| WPL_self_z                     | -0.1275     | [-0.1542, -0.1008] | 7.25e-21 | *** |
| gap_12_z                       | +0.0971     | [+0.0719, +0.1223] | 4.35e-14 | *** |
| WPL_self_z:gap_12_z            | +0.0057     | [-0.0157, +0.0271] | 0.603    |     |
| elo_diff_z                     | +2.0908     | [+1.8044, +2.3772] | 1.95e-46 | *** |
| WPL_self_z:elo_diff_z          | +0.2251     | [+0.0651, +0.3852] | 0.00584  | **  |
| gap_12_z:elo_diff_z            | +0.0702     | [-0.0289, +0.1693] | 0.165    |     |
| WPL_self_z:gap_12_z:elo_diff_z | +0.0595     | [-0.0349, +0.1538] | 0.217    |     |
| n_legal_z                      | +0.1118     | [+0.0643, +0.1593] | 3.93e-06 | *** |
| eval_volatility_z              | +0.0088     | [-0.0161, +0.0337] | 0.488    |     |
| time_pressure_z                | +0.1444     | [+0.0918, +0.1969] | 7.28e-08 | *** |

- N = 46102


> **The two models point in opposite directions, and that matters more than either one alone.** The mechanism variable says a suboptimal move is followed by a *larger* opponent error (`WPL_self_z` = +0.831), while the outcome model says the same move makes the player *less* likely to win (`WPL_self_z` = -0.127). Genuine complementarity — deliberately entering positions the engine dislikes because the opponent errs there — should eventually show up in results, not just in the opponent's next move. The simplest reading consistent with both is the confound named above: sharp positions raise *both* players' error rates (positive mechanism coefficient) while a real evaluation loss still costs you the game (negative outcome coefficient). On the pilot, the deviation looks like plain suboptimality rather than productive risk-taking. This is a null-to-negative signal for the §7.2 hypothesis and §10 of the spec says to report it as it comes.


**[LOCKED §7.2] Causal interpretation is not licensed here.** The outcome is a game-level quantity while the predictor is a single ply, so every later move — and whatever made the player choose this one — sits between them. Opponent next-move `WPL` above is the cleaner mechanism variable and is the primary result.


## 10. Implementation notes, and where I disagree with the spec

Per §0 and §10, **no [LOCKED] parameter was modified.** Everything below is either a required disclosure or a disagreement stated rather than acted on.


### 10.1 Middlegame boundary — reused, as §2 requires

- Source: **`chess_pipeline_v2.py`**, constants `MIDDLEGAME_START = 14` and `MIDDLEGAME_END = 40` (lines 43–44), applied inside **`chess_pipeline_v2.analyze_game()`** (line 321, the boundary test is at line 390: `if not (MIDDLEGAME_START <= i < MIDDLEGAME_END)`).
- `paper4_pilot.py` imports the module and reads those constants rather than restating them, so the two papers cannot drift apart.
- Paper 1's minimum-length guard (`len(moves) < MIDDLEGAME_START + 5`, i.e. 19 plies) is also reused.
- Per [LOCKED §4] the window is applied to **both sides**, unlike Paper 1 which kept only the focal player's moves.


### 10.2 The §4 30-move cap can never bind

The window is plies 14–39, i.e. at most **26 half-moves**, which is already below the cap of 30. The even-interval sampling rule in §4 is implemented but never fires (0 games triggered it). If §4's "30 middlegame moves" was meant as 30 *full* moves per side, or if the window was meant to extend to the end of the game, then the Paper 1 boundary in §2 and the cap in §4 are describing different things — worth resolving before the full run, since it changes how much of each game is analysed. I did not change either one.


### 10.3 Compute estimate in §8.2 is off by roughly an order of magnitude

See §1. Single-core, uncontended: **~492 ms/position** at the locked settings. Under 9-way parallelism on 10 cores the *observed* figure is **1341 ms/position** — memory-bandwidth contention roughly doubles it again, and the 128 MB hash clear that §3's independence requirement forces before every single search is a large part of that. Extrapolating the pilot's measured wall-clock:

| job                       | measured / extrapolated wall-clock | spec estimate            |
|---------------------------|------------------------------------|--------------------------|
| pilot, 1,970 games        | 158 min                            | §8.2 predicted 10–20 min |
| full sample, 59,321 games | 79 h                               | §8.2 predicted 5–9 h     |

This is a scheduling fact, not a bug, and I did not touch depth, MultiPV, Threads or Hash to make it faster. It does mean the full run needs either more machines or a deliberate decision to spend the time.


### 10.4 Data provenance — the one thing I could not take from the spec

§2 says to use "the existing Paper 1 PGN dataset". **There is no stored PGN dataset.** Paper 1's pipeline streamed each game from the provider, computed its 11 indicators, and discarded the moves; `analysis_dataset_male_titled_raw.csv` holds one row per player-game with indicator values and a game URL, and no moves, clocks or opponent Elo. The PGNs were therefore **re-downloaded from the game URLs**. Consequences:
- 30 of 2000 sampled games (1.5%) are unrecoverable — the accounts were closed or renamed, so their archives no longer exist. This attrition is not random with respect to players, and it will recur at full scale.
- The source is **Chess.com**, not Lichess as §5.1/§5.4 imply. The Lichess win-probability formula in §5.1 is still applied exactly as locked; `%clk` is a Chess.com PGN feature too, hence the 100% coverage in §0.
- The frame is `analysis_dataset_male_titled_raw.csv` (59,425 rows / **59,321 unique games**, 630 players), which is the only file matching §8.2's "~59,425 games". That file is the **male** half of Paper 1. Whether Paper 4 should instead cover Paper 1's full roster — adding the female half, `analysis_dataset_raw.csv`, 176,679 rows — is a **design decision that has been deliberately deferred to the researcher**, not an execution detail, and this pilot was deliberately *not* redrawn. Everything in this report describes the male frame as sampled. Note that widening the frame later would require redrawing under §8.1's locked seed, since a seed selects from whatever frame it is applied to: this pilot would not be a subset of that larger sample.


### 10.5 Choices the spec leaves open (stated, not smuggled)

- **WP of the played move.** When the played move is one of the MultiPV-5 lines its root score is used (81.1% of rows). Otherwise the child position is searched to the same depth 15 and the score negated. The two are not perfectly commensurable (root vs child search); the alternative — dropping non-top-5 moves — would throw away exactly the large deviations the paper is about.
- **`eval_volatility` at the window edge.** It needs the position two plies earlier, which does not exist for plies 14 and 15. Two extra "context" positions (plies 12, 13) are evaluated purely to define it, and are **not** emitted as analysis rows. This adds engine calls but changes no locked selection rule.
- **`time_pressure`** uses the clock reading attached to that move (Chess.com records time remaining *after* the move), divided by base time. With increments it can exceed 1.0.
- **§7.2 controls.** The spec does not say whether `n_legal`/`eval_volatility`/`time_pressure` in §7.2 describe the actor's position `t` or the opponent's `t+1`. Controlling at `t+1` partials out part of the very mechanism being tested (the actor made the opponent's position harder), so the actor's position is primary and the other is reported as robustness. This needs a ruling before the full run.
- **Crossed random effects.** §7 asks for `(1|player_id) + (1|game_id)`, which are crossed, not nested. statsmodels cannot fit truly crossed effects at this scale, so `game_id` enters as a variance component within `player_id` and OLS with player-clustered SEs is reported alongside. The full run should use `lme4` or Julia `MixedModels` for the exact specification.


### 10.6 Storage and resumability (§6)

- 160 Parquet shards under `paper4_results/bucket=NN/`, bucketed by `md5(game_id) % 16` as locked.
- `(game_id, ply)` is the unique key; `analyze` reads the existing shards on start and skips completed work, so the job survives interruption. This was exercised in practice — the fetch stage was restarted twice.


---

**Pilot complete. Stopping here as §8.1 requires — full-scale execution awaits confirmation.**

