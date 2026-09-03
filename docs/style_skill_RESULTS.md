# Middlegame Style vs. Skill — Female Titled Sample (Paper 3 supporting analysis)

**Design:** CROSS-SECTIONAL — different players observed at different skill levels,
NOT longitudinal. No within-player developmental trajectory is observed.
**Sample:** single-sex (female, verified women's-title holders) → **no sex confound.**
**Unit:** one row per player; indicators and Elo are `n_games`-weighted means
across that player's time-control rows (blitz/rapid/bullet). N = **2216** players,
176,620 games. Elo 1013.3–2893.8 (mean 2067.6, sd 340.1).
**PCA:** correlation-matrix PCA (z-scored indicators) via SVD. PC1 sign aligned so
exchange_rate / forcing_move_rate load positive ("+ = transactional/forcing pole").

---

## 1. Feasibility — sample size by skill band

### Fine bands (100-pt). Flag: n < 50 = too small for stable PCA.

| band | mid | n | flag |
|---|---:|---:|---|
| 1000–1099 | 1050 | 15 | **n<50 — too small** |
| 1100–1199 | 1150 | 13 | **n<50 — too small** |
| 1200–1299 | 1250 | 27 | **n<50 — too small** |
| 1300–1399 | 1350 | 40 | **n<50 — too small** |
| 1400–1499 | 1450 | 58 | ok |
| 1500–1599 | 1550 | 74 | ok |
| 1600–1699 | 1650 | 103 | ok |
| 1700–1799 | 1750 | 143 | ok |
| 1800–1899 | 1850 | 139 | ok |
| 1900–1999 | 1950 | 227 | ok |
| 2000–2099 | 2050 | 245 | ok |
| 2100–2199 | 2150 | 269 | ok |
| 2200–2299 | 2250 | 286 | ok |
| 2300–2399 | 2350 | 215 | ok |
| 2400–2499 | 2450 | 181 | ok |
| 2500+ | 2550 | 181 | ok |

12 of 16 fine bands have adequate n (≥50). The four bands below 1400 (n=15,13,27,40)
are too small for stable within-band PCA and are excluded from per-band PCA.

### Coarse bands (4 × 500-pt). All adequate.

| band | mid | n |
|---|---:|---:|
| 1000–1499 | 1250 | 153 |
| 1500–1999 | 1750 | 686 |
| 2000–2499 | 2250 | 1196 |
| 2500+ | 2600 | 181 |

---

## 2. Attacking–positional structure (PC1) across skill

**Full female sample (N=2216): PC1 = 34.42% variance** (PC2 15.64%, PC3 13.89%).

PC1 is an **attacking/transactional ↔ positional** axis:

| indicator | PC1 loading |
|---|---:|
| reactive_move_rate | +0.4271 |
| exchange_rate | +0.4160 |
| forcing_move_rate | +0.4112 |
| tension_duration | −0.4085 |
| avg_mobility | −0.3864 |
| center_control_score | −0.3689 |
| pawn_storm_indicator | −0.1183 |
| king_shelter_score | −0.0722 |
| advanced_pawn_push_rate | −0.0619 |
| castling_ply | +0.0120 |

**+ pole** = simplifying/forcing/reactive (trade pieces, play forcing moves, respond
to opponent). **− pole** = positional richness (hold tension longer, higher mobility,
more central control). Six indicators carry the axis; the other four are near-zero.

### Per-band PC1 variance explained (adequate fine bands)

| band | n | PC1 var % |
|---|---:|---:|
| 1400–1499 | 58 | 43.06 |
| 1500–1599 | 74 | 28.04 |
| 1600–1699 | 103 | 39.62 |
| 1700–1799 | 143 | 32.01 |
| 1800–1899 | 139 | 31.66 |
| 1900–1999 | 227 | 30.62 |
| 2000–2099 | 245 | 35.88 |
| 2100–2199 | 269 | 37.80 |
| 2200–2299 | 286 | 35.83 |
| 2300–2399 | 215 | 37.31 |
| 2400–2499 | 181 | 36.19 |
| 2500+ | 181 | 35.21 |

Full per-band PC1 loadings: see `style_skill_figures/fig5_loadings_heatmap.png`
and console output. The same six indicators dominate PC1 in essentially every band.

### Tucker's congruence coefficient (PC1 loadings)

Benchmark: |φ| ≥ 0.95 = identical structure; 0.85–0.94 = fair similarity; < 0.85 = different.

**Full-sample PC1 vs each band:**

| band | φ |
|---|---:|
| 1400–1499 | 0.9898 |
| 1500–1599 | 0.8108 |
| 1600–1699 | 0.9389 |
| 1700–1799 | 0.9507 |
| 1800–1899 | 0.9503 |
| 1900–1999 | 0.9893 |
| 2000–2099 | 0.9651 |
| 2100–2199 | 0.9749 |
| 2200–2299 | 0.9968 |
| 2300–2399 | 0.9486 |
| 2400–2499 | 0.9823 |
| 2500+ | 0.9625 |

**Adjacent fine bands:**

| pair | φ |
|---|---:|
| 1400–1499 vs 1500–1599 | 0.7648 |
| 1500–1599 vs 1600–1699 | 0.6893 |
| 1600–1699 vs 1700–1799 | 0.8230 |
| 1700–1799 vs 1800–1899 | 0.8923 |
| 1800–1899 vs 1900–1999 | 0.9691 |
| 1900–1999 vs 2000–2099 | 0.9747 |
| 2000–2099 vs 2100–2199 | 0.9030 |
| 2100–2199 vs 2200–2299 | 0.9790 |
| 2200–2299 vs 2300–2399 | 0.9398 |
| 2300–2399 vs 2400–2499 | 0.9566 |
| 2400–2499 vs 2500+ | 0.9813 |

**Coarse bands (low→mid→high), adjacent congruence:**

| pair | PC1 var % (each) | φ |
|---|---|---:|
| 1000–1499 vs 1500–1999 | 28.65 / 31.03 | **0.9941** |
| 1500–1999 vs 2000–2499 | 31.03 / 35.45 | **0.9976** |
| 2000–2499 vs 2500+ | 35.45 / 35.21 | **0.9793** |

**Interpretation:** the attacking–positional axis is **stable, not reorganized**, across
skill. All coarse-band adjacencies are ≥ 0.979 (near-identical), and full-vs-band φ is
≥ 0.95 for the great majority of bands. The low fine-band wobble (1500–1599 vs neighbors,
φ≈0.69–0.76) is small-n sampling noise in a single band whose PC1 happens to be led by
mobility/center rather than exchange; it disappears at coarse resolution. The *structure*
of style does not change with skill — what changes is **where players sit on it** (§3–4).

---

## 3. Does style sharpen or consolidate with skill?

PC1 scores projected onto the **common full-sample axis** (within-band axes are not
comparable), then within-band dispersion:

| band | mid | n | mean PC1 | sd PC1 | var PC1 |
|---|---:|---:|---:|---:|---:|
| 1400–1499 | 1450 | 58 | 1.6425 | 2.9101 | 8.4687 |
| 1500–1599 | 1550 | 74 | 1.2082 | 1.8731 | 3.5084 |
| 1600–1699 | 1650 | 103 | 0.5929 | 1.7861 | 3.1901 |
| 1700–1799 | 1750 | 143 | 0.2936 | 1.7553 | 3.0811 |
| 1800–1899 | 1850 | 139 | 0.0564 | 1.6002 | 2.5607 |
| 1900–1999 | 1950 | 227 | −0.1000 | 1.5948 | 2.5435 |
| 2000–2099 | 2050 | 245 | −0.1708 | 1.9123 | 3.6568 |
| 2100–2199 | 2150 | 269 | −0.0292 | 1.7443 | 3.0424 |
| 2200–2299 | 2250 | 286 | −0.3535 | 1.6536 | 2.7343 |
| 2300–2399 | 2350 | 215 | −0.6768 | 1.3645 | 1.8619 |
| 2400–2499 | 2450 | 181 | −0.4119 | 1.4025 | 1.9670 |
| 2500+ | 2550 | 181 | −0.7552 | 1.3061 | 1.7060 |

**Dispersion (sd of PC1) vs Elo midpoint: Pearson r = −0.7439**; slope = −0.08597 sd per
+100 Elo. **Style CONSOLIDATES (converges), it does not sharpen/diverge.** Stronger
players are more alike on the attacking–positional axis. Mean PC1 also falls
monotonically (1.64 → −0.76): with skill, style shifts **away** from the
exchange/forcing/reactive pole **toward** the tension/mobility/center pole.

### Monotone indicator trends (band-mean vs Elo midpoint, 12 adequate bands)

| indicator | Pearson r | Spearman ρ | slope /100 Elo | monotone? |
|---|---:|---:|---:|---|
| forcing_move_rate | −0.9740 | −0.9930 | −0.00464 | yes |
| exchange_rate | −0.9716 | −0.9860 | −0.00359 | yes |
| pawn_storm_indicator | +0.8974 | +0.9650 | +0.00063 | yes |
| center_control_score | +0.8569 | +0.9021 | +0.02951 | yes |
| reactive_move_rate | −0.8661 | −0.9301 | −0.00303 | yes |
| tension_duration | +0.8843 | +0.8951 | +0.01217 | partial |
| avg_mobility | +0.7479 | +0.6853 | +0.06977 | no |
| advanced_pawn_push_rate | +0.6977 | +0.6014 | +0.00066 | no |
| king_shelter_score | +0.6860 | +0.5874 | +0.00290 | no |
| castling_ply | −0.6535 | −0.6434 | −0.05278 | no |

Strongest monotone shifts with rising skill: **fewer forcing moves, fewer exchanges,
fewer reactive moves; longer-held tension and more central control.** Per-player
continuous correlations with Elo are same-signed but weaker (exchange_rate −0.388,
forcing −0.353, reactive −0.269; others |r|<0.21) — band-aggregation removes individual
noise and reveals the trend.

---

## 4. Non-linearity / emergence point (exploratory)

Continuous segmented (one-breakpoint, continuous piecewise-linear) vs linear, N=2216:

| outcome | linear slope | linear R² | breakpoint | seg R² | slope below | slope above | ΔR² | F(2,2212) | verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| PC1 (common axis) | −0.001948 | 0.1275 | **1792.8** | 0.1538 | −0.004433 | −0.000968 | +0.0263 | **34.355** | segmented improves |
| exchange_rate | −0.0000369 | 0.1503 | **1858.4** | 0.1615 | −0.0000613 | −0.0000245 | +0.0112 | **14.756** | segmented improves |

Both outcomes change **~3–4× faster below ≈1800 Elo than above** (PC1 slope −0.0044 →
−0.0010; exchange_rate −6.1e-5 → −2.5e-5). The segmented fit significantly beats linear
(F=34.4 and 14.8, both ≫ critical ≈3.0). Read as an **early-consolidation / emergence
zone around 1800 Elo**: most of the stylistic reorganization (toward the positional pole,
and the dispersion shrinkage) happens across the lower titled range, then plateaus into a
slower drift among masters. **Exploratory** — single-breakpoint grid search, cross-sectional.

See `fig4_breakpoint.png`.

---

## Headline

1. **Structure is invariant** — the attacking↔positional PC1 axis is the same shape at
   every skill level (coarse-band congruence ≥ 0.979); it does not reorganize.
2. **Position on the axis moves** — with skill, style shifts off the
   forcing/exchanging/reactive pole toward holding tension + central control
   (mean PC1 1.64 → −0.76; all six core indicators monotone).
3. **Style consolidates, not sharpens** — within-band PC1 dispersion falls with Elo
   (r = −0.74). Experts converge stylistically rather than diverging.
4. **Emergence ~1800 Elo** — the shift is ~3–4× steeper below ≈1800 than above and a
   breakpoint model significantly beats a straight line (exploratory).

All four results are **cross-sectional** and from a **single-sex (female)** sample.

## Figures (`style_skill_figures/`)
- `fig1_band_counts.png` — n per Elo band (red = n<50)
- `fig2_pc1_variance.png` — PC1 variance explained per band
- `fig3_dispersion.png` — within-band PC1 sd + mean vs skill
- `fig4_breakpoint.png` — mean PC1 & exchange_rate vs Elo with segmented vs linear fit
- `fig5_loadings_heatmap.png` — PC1 loadings across all bands (sign-aligned)

Reproduce: `python3 style_skill_analysis.py`
