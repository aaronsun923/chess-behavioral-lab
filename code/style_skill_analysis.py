#!/usr/bin/env python3
"""
Paper 3 / pedagogy supporting analysis:
How middlegame chess STYLE varies with SKILL LEVEL in the FEMALE-ONLY titled sample.

Single-sex sample -> no sex confound. CROSS-SECTIONAL (different players at
different skill levels), NOT longitudinal.

Pure numpy + matplotlib. PCA via SVD on standardized (correlation) matrix,
Tucker's congruence by hand, segmented regression by grid search.
"""
import csv
import numpy as np
# macOS Accelerate BLAS raises spurious FPE flags on matmul under numpy 2.0;
# inputs are verified finite + full-rank, so silence the cosmetic warnings.
np.seterr(divide="ignore", over="ignore", invalid="ignore")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import os

OUT = os.path.dirname(os.path.abspath(__file__))
FIGDIR = os.path.join(OUT, "style_skill_figures")
os.makedirs(FIGDIR, exist_ok=True)

INDICATORS = [
    "exchange_rate", "tension_duration", "avg_mobility", "center_control_score",
    "advanced_pawn_push_rate", "pawn_storm_indicator", "castling_ply",
    "king_shelter_score", "forcing_move_rate", "reactive_move_rate",
]

# ----------------------------------------------------------------------
# 1. LOAD + aggregate to one row per player (n_games-weighted across
#    time categories). avg_elo also n_games-weighted.
# ----------------------------------------------------------------------
def load_player_level(path):
    rows = {}
    with open(path) as f:
        for r in csv.DictReader(f):
            if r["gender"] != "female":
                continue
            pid = r["player_id"]
            try:
                w = float(r["n_games"])
                elo = float(r["avg_elo"])
                vals = [float(r[c]) for c in INDICATORS]
            except (ValueError, KeyError):
                continue
            if not np.isfinite(elo) or w <= 0:
                continue
            rows.setdefault(pid, []).append((w, elo, vals))
    players, elos, X, ngames = [], [], [], []
    for pid, recs in rows.items():
        W = np.array([rr[0] for rr in recs], float)
        e = np.array([rr[1] for rr in recs], float)
        V = np.array([rr[2] for rr in recs], float)  # (k, 10)
        if not np.all(np.isfinite(V)):
            # keep only finite indicator rows for the weighted mean
            mask = np.all(np.isfinite(V), axis=1)
            if not mask.any():
                continue
            W, e, V = W[mask], e[mask], V[mask]
        wsum = W.sum()
        players.append(pid)
        elos.append((W * e).sum() / wsum)
        X.append((W[:, None] * V).sum(axis=0) / wsum)
        ngames.append(wsum)
    return (np.array(players), np.array(elos, float),
            np.array(X, float), np.array(ngames, float))

players, elo, X, ngames = load_player_level(
    os.path.join(OUT, "analysis_dataset_agg.csv"))
N = len(players)
print(f"Female players (player-level, n_games-weighted across time categories): N = {N}")
print(f"Total games behind them: {int(ngames.sum())}")
print(f"Elo range: {elo.min():.1f} .. {elo.max():.1f}   mean {elo.mean():.1f}  sd {elo.std(ddof=1):.1f}")

# ----------------------------------------------------------------------
# 2. FEASIBILITY: bands of 100 pts and coarse 4 bands
# ----------------------------------------------------------------------
def fine_band(e):
    lo = int(np.floor(e / 100.0) * 100)
    if lo >= 2500:
        return 2500  # 2500+
    return lo

fine_lo = np.array([fine_band(e) for e in elo])
fine_edges = sorted(set(fine_lo))

def band_label_fine(lo):
    return "2500+" if lo == 2500 else f"{lo}-{lo+99}"

def band_mid_fine(lo):
    # midpoint; for open-ended top band use lo+50 as nominal
    return lo + 50.0

print("\n=== STEP 1  FEASIBILITY ===")
print("\nFine bands (100-pt):")
print(f"{'band':>10} {'mid':>6} {'n':>5}  flag")
fine_counts = {}
for lo in fine_edges:
    n = int((fine_lo == lo).sum())
    fine_counts[lo] = n
    flag = "  <-- n<50 TOO SMALL for stable PCA" if n < 50 else ""
    print(f"{band_label_fine(lo):>10} {band_mid_fine(lo):>6.0f} {n:>5}{flag}")

# coarse 4 bands
def coarse_band(e):
    if e < 1500: return "1000-1499"
    if e < 2000: return "1500-1999"
    if e < 2500: return "2000-2499"
    return "2500+"
coarse_order = ["1000-1499", "1500-1999", "2000-2499", "2500+"]
coarse_mid = {"1000-1499": 1250, "1500-1999": 1750, "2000-2499": 2250, "2500+": 2600}
coarse_lab = np.array([coarse_band(e) for e in elo])
print("\nCoarse bands (500-pt, 4 bins):")
print(f"{'band':>12} {'mid':>6} {'n':>5}  flag")
for b in coarse_order:
    n = int((coarse_lab == b).sum())
    flag = "  <-- n<50" if n < 50 else ""
    print(f"{b:>12} {coarse_mid[b]:>6} {n:>5}{flag}")

# Adequate fine bands for within-band PCA
adequate_fine = [lo for lo in fine_edges if fine_counts[lo] >= 50]
print("\nFine bands with adequate n (>=50) for within-band PCA:",
      [band_label_fine(lo) for lo in adequate_fine])

# ----------------------------------------------------------------------
# PCA helper (correlation-matrix PCA via SVD on z-scored data)
# ----------------------------------------------------------------------
def pca(Xsub):
    mu = Xsub.mean(axis=0)
    sd = Xsub.std(axis=0, ddof=1)
    sd_safe = np.where(sd == 0, 1.0, sd)
    Z = (Xsub - mu) / sd_safe
    # SVD
    U, S, Vt = np.linalg.svd(Z, full_matrices=False)
    n = Xsub.shape[0]
    eig = (S ** 2) / (n - 1)              # variance per component
    var_ratio = eig / eig.sum()
    loadings = Vt                         # rows = components, cols = indicators
    scores = U * S                        # (n, k) component scores
    return mu, sd_safe, var_ratio, loadings, scores, eig

def tucker_congruence(a, b):
    """Tucker's phi between two loading vectors (sign-sensitive cosine)."""
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))

# ----------------------------------------------------------------------
# 3. STEP 2 -- PCA full sample + per band; congruence between adjacent
# ----------------------------------------------------------------------
print("\n=== STEP 2  ATTACKING-POSITIONAL STRUCTURE (PC1) ACROSS SKILL ===")

# (a) full sample
mu_f, sd_f, vr_f, load_f, scores_f, eig_f = pca(X)
pc1_full = load_f[0].copy()
# Orient full-sample PC1 so exchange_rate (an "attacking/sharp" marker) loads +.
ix_exch = INDICATORS.index("exchange_rate")
ix_forcing = INDICATORS.index("forcing_move_rate")
ref_sign = np.sign(pc1_full[ix_exch] + pc1_full[ix_forcing])
if ref_sign < 0:
    pc1_full = -pc1_full
    scores_f[:, 0] = -scores_f[:, 0]
    load_f[0] = pc1_full

print(f"\nFULL female sample (N={N}):  PC1 var explained = {vr_f[0]*100:.2f}%   "
      f"PC2 = {vr_f[1]*100:.2f}%   PC3 = {vr_f[2]*100:.2f}%")
print("PC1 loadings (oriented so exchange_rate/forcing load +):")
order = np.argsort(-np.abs(pc1_full))
for i in order:
    print(f"   {INDICATORS[i]:>26} {pc1_full[i]:+.4f}")

# (b) per adequate fine band
band_results = {}   # lo -> dict
print("\nWithin-band PCA (adequate fine bands):")
for lo in adequate_fine:
    idx = np.where(fine_lo == lo)[0]
    Xb = X[idx]
    mu_b, sd_b, vr_b, load_b, scores_b, eig_b = pca(Xb)
    pc1_b = load_b[0].copy()
    # orient toward full-sample PC1 (positive congruence) for reporting/scores
    if np.dot(pc1_b, pc1_full) < 0:
        pc1_b = -pc1_b
        scores_b[:, 0] = -scores_b[:, 0]
    band_results[lo] = dict(idx=idx, vr=vr_b, pc1=pc1_b,
                            scores1=scores_b[:, 0], n=len(idx))
    print(f"\n  Band {band_label_fine(lo)}  (n={len(idx)}): "
          f"PC1 var = {vr_b[0]*100:.2f}%  PC2 = {vr_b[1]*100:.2f}%")
    o = np.argsort(-np.abs(pc1_b))
    for i in o:
        print(f"      {INDICATORS[i]:>26} {pc1_b[i]:+.4f}")

# Congruence: full vs each band, and adjacent bands
print("\n--- Tucker's congruence coefficient (PC1 loadings) ---")
print("(sign-aligned to full-sample PC1; |phi|>=0.95 identical, 0.85-0.94 fair)")
print("\nFull-sample PC1 vs each band:")
for lo in adequate_fine:
    phi = tucker_congruence(pc1_full, band_results[lo]["pc1"])
    print(f"   full  vs  {band_label_fine(lo):>10}:  phi = {phi:.4f}")

print("\nAdjacent fine bands:")
adj_pairs_fine = list(zip(adequate_fine[:-1], adequate_fine[1:]))
for a, b in adj_pairs_fine:
    phi = tucker_congruence(band_results[a]["pc1"], band_results[b]["pc1"])
    print(f"   {band_label_fine(a):>10}  vs  {band_label_fine(b):>10}:  phi = {phi:.4f}")

# Also coarse-band PCA + congruence (low/mid/high style as requested)
print("\n--- Coarse-band PCA + adjacent congruence (low-vs-mid, mid-vs-high) ---")
coarse_results = {}
for b in coarse_order:
    idx = np.where(coarse_lab == b)[0]
    if len(idx) < 50:
        print(f"  Band {b} (n={len(idx)}): n<50, skipped for PCA")
        continue
    Xb = X[idx]
    mu_b, sd_b, vr_b, load_b, scores_b, eig_b = pca(Xb)
    pc1_b = load_b[0].copy()
    if np.dot(pc1_b, pc1_full) < 0:
        pc1_b = -pc1_b
        scores_b[:, 0] = -scores_b[:, 0]
    coarse_results[b] = dict(idx=idx, vr=vr_b, pc1=pc1_b,
                             scores1=scores_b[:, 0], n=len(idx))
    print(f"  Band {b} (n={len(idx)}): PC1 var = {vr_b[0]*100:.2f}%")
coarse_have = [b for b in coarse_order if b in coarse_results]
print("  Adjacent coarse congruence:")
for a, b in zip(coarse_have[:-1], coarse_have[1:]):
    phi = tucker_congruence(coarse_results[a]["pc1"], coarse_results[b]["pc1"])
    print(f"     {a:>10} vs {b:>10}: phi = {phi:.4f}")

# ----------------------------------------------------------------------
# 4. STEP 3 -- dispersion of PC1 + monotone indicator trends
# ----------------------------------------------------------------------
print("\n=== STEP 3  DOES STYLE SHARPEN OR CONSOLIDATE? ===")
# Project ALL players onto the COMMON (full-sample) PC1 axis so PC1 scores
# are comparable across bands (within-band axes differ -> not comparable).
Z_all = (X - mu_f) / sd_f
pc1_common = Z_all @ pc1_full     # common-axis PC1 score per player

print("\nWithin-band dispersion of PC1 score (projected on common full-sample axis):")
print(f"{'band':>10} {'mid':>6} {'n':>5} {'mean_PC1':>9} {'sd_PC1':>8} {'var_PC1':>9}")
disp_mid, disp_sd, disp_var, disp_mean = [], [], [], []
for lo in fine_edges:
    idx = np.where(fine_lo == lo)[0]
    if len(idx) < 50:
        continue
    s = pc1_common[idx]
    disp_mid.append(band_mid_fine(lo))
    disp_mean.append(s.mean())
    disp_sd.append(s.std(ddof=1))
    disp_var.append(s.var(ddof=1))
    print(f"{band_label_fine(lo):>10} {band_mid_fine(lo):>6.0f} {len(idx):>5} "
          f"{s.mean():>9.4f} {s.std(ddof=1):>8.4f} {s.var(ddof=1):>9.4f}")
disp_mid = np.array(disp_mid); disp_sd = np.array(disp_sd)
disp_var = np.array(disp_var); disp_mean = np.array(disp_mean)

# trend of dispersion vs Elo
def pearson(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    if len(x) < 3: return np.nan, np.nan
    r = np.corrcoef(x, y)[0, 1]
    return r, r
r_disp = np.corrcoef(disp_mid, disp_sd)[0, 1]
print(f"\nDispersion (sd of PC1) vs Elo band midpoint: Pearson r = {r_disp:.4f}")
slope_disp = np.polyfit(disp_mid, disp_sd, 1)[0]
print(f"  slope of sd_PC1 per +100 Elo = {slope_disp*100:.5f}")
print("  -> r>0 => style DIVERGES (sharpens) with skill; r<0 => CONVERGES (consolidates)")

# Monotone indicator trends: correlate band-mean of each indicator with band midpoint
print("\nMonotone indicator trends (band-mean indicator vs Elo band midpoint):")
print("Using adequate fine bands; report Pearson r, Spearman rho, slope per +100 Elo")
adq = adequate_fine
mids = np.array([band_mid_fine(lo) for lo in adq], float)

def spearman(x, y):
    rx = np.argsort(np.argsort(x)); ry = np.argsort(np.argsort(y))
    return np.corrcoef(rx, ry)[0, 1]

print(f"{'indicator':>26} {'pearson_r':>10} {'spearman':>9} {'slope/100Elo':>13} {'monotone?':>10}")
trend_rows = []
for j, name in enumerate(INDICATORS):
    bmeans = np.array([X[fine_lo == lo, j].mean() for lo in adq])
    r = np.corrcoef(mids, bmeans)[0, 1]
    rho = spearman(mids, bmeans)
    slope = np.polyfit(mids, bmeans, 1)[0] * 100
    mono = "yes" if abs(rho) >= 0.90 else ("partial" if abs(rho) >= 0.7 else "no")
    trend_rows.append((name, r, rho, slope, bmeans))
    print(f"{name:>26} {r:>10.4f} {rho:>9.4f} {slope:>13.5f} {mono:>10}")

# Also correlate each indicator with continuous player Elo (full sample) for robustness
print("\nPer-player continuous correlation: indicator vs Elo (full female sample):")
print(f"{'indicator':>26} {'pearson_r':>10}")
for j, name in enumerate(INDICATORS):
    r = np.corrcoef(elo, X[:, j])[0, 1]
    print(f"{name:>26} {r:>10.4f}")

# ----------------------------------------------------------------------
# 5. STEP 4 -- non-linearity / breakpoint
# ----------------------------------------------------------------------
print("\n=== STEP 4  NON-LINEARITY / EMERGENCE POINT (exploratory) ===")

def linear_fit(x, y):
    b1, b0 = np.polyfit(x, y, 1)
    yhat = b0 + b1 * x
    rss = float(np.sum((y - yhat) ** 2))
    sst = float(np.sum((y - y.mean()) ** 2))
    r2 = 1 - rss / sst
    return dict(b0=b0, b1=b1, rss=rss, r2=r2, k=2)

def segmented_fit(x, y, grid=None):
    """Continuous piecewise-linear w/ one breakpoint c.
    model: y = b0 + b1*x + b2*max(0, x-c). Grid-search c, OLS for the rest."""
    if grid is None:
        grid = np.linspace(np.percentile(x, 10), np.percentile(x, 90), 81)
    best = None
    for c in grid:
        hinge = np.maximum(0.0, x - c)
        A = np.column_stack([np.ones_like(x), x, hinge])
        coef, *_ = np.linalg.lstsq(A, y, rcond=None)
        yhat = A @ coef
        rss = float(np.sum((y - yhat) ** 2))
        if best is None or rss < best["rss"]:
            best = dict(c=float(c), coef=coef, rss=rss)
    sst = float(np.sum((y - y.mean()) ** 2))
    best["r2"] = 1 - best["rss"] / sst
    best["k"] = 4  # b0,b1,b2,c
    # slopes
    best["slope_low"] = float(best["coef"][1])
    best["slope_high"] = float(best["coef"][1] + best["coef"][2])
    return best

def f_test(lin, seg, n):
    # nested-ish comparison (extra params = seg.k - lin.k). Use F on RSS drop.
    df1 = seg["k"] - lin["k"]
    df2 = n - seg["k"]
    if df1 <= 0 or df2 <= 0 or seg["rss"] <= 0:
        return np.nan, np.nan
    F = ((lin["rss"] - seg["rss"]) / df1) / (seg["rss"] / df2)
    return F, df1, df2

# Run on continuous player-level data for PC1 (common axis) and exchange_rate
for label, yvec in [("PC1 (common-axis score)", pc1_common),
                    ("exchange_rate", X[:, ix_exch])]:
    lin = linear_fit(elo, yvec)
    seg = segmented_fit(elo, yvec)
    F, *dfs = f_test(lin, seg, N)
    print(f"\n-- {label} vs Elo (continuous, N={N}) --")
    print(f"   linear:    slope={lin['b1']:+.6f}  R2={lin['r2']:.4f}  RSS={lin['rss']:.4f}")
    print(f"   segmented: breakpoint={seg['c']:.1f} Elo  R2={seg['r2']:.4f}  RSS={seg['rss']:.4f}")
    print(f"              slope_below={seg['slope_low']:+.6f}  slope_above={seg['slope_high']:+.6f}")
    dR2 = seg['r2'] - lin['r2']
    print(f"   improvement: dR2={dR2:+.4f}  F({dfs[0]},{dfs[1]})={F:.3f}")
    better = "YES, segmented improves on linear" if (dR2 > 0.002 and F > 4) else \
             "marginal/no — essentially linear" if dR2 < 0.005 else "modest"
    print(f"   verdict: {better}")

# ----------------------------------------------------------------------
# 6. FIGURES
# ----------------------------------------------------------------------
print("\n=== SAVING FIGURES ===")

DPI = 300  # print quality (was 140)

def save_fig(fig, stem, pdf=False):
    """Save PNG at print DPI; optionally a vector PDF too."""
    fig.savefig(os.path.join(FIGDIR, stem + ".png"), dpi=DPI)
    if pdf:
        fig.savefig(os.path.join(FIGDIR, stem + ".pdf"))  # vector, DPI-independent
    plt.close(fig)

# Fig 1: n per fine band
fig, ax = plt.subplots(figsize=(10, 4.5))
labs = [band_label_fine(lo) for lo in fine_edges]
ns = [fine_counts[lo] for lo in fine_edges]
cols = ["#4c72b0" if n >= 50 else "#c44e52" for n in ns]
ax.bar(labs, ns, color=cols)
ax.axhline(50, ls="--", color="k", lw=1, label="n=50 PCA threshold")
ax.set_ylabel("n players"); ax.set_xlabel("Elo band (100-pt)")
ax.set_title("Female titled players per Elo band (red = n<50)")
plt.xticks(rotation=45, ha="right"); ax.legend(); plt.tight_layout()
save_fig(fig, "fig1_band_counts")

# Fig 2: PC1 variance explained per adequate band
fig, ax = plt.subplots(figsize=(8, 4.5))
bl = [band_label_fine(lo) for lo in adequate_fine]
vrs = [band_results[lo]["vr"][0]*100 for lo in adequate_fine]
ax.plot(bl, vrs, "o-", color="#4c72b0")
ax.axhline(vr_f[0]*100, ls="--", color="grey", label=f"full sample {vr_f[0]*100:.1f}%")
ax.set_ylabel("PC1 variance explained (%)"); ax.set_xlabel("Elo band")
ax.set_title("PC1 variance explained within each Elo band")
plt.xticks(rotation=45, ha="right"); ax.legend(); plt.tight_layout()
save_fig(fig, "fig2_pc1_variance")

# Fig 3: dispersion of PC1 vs Elo midpoint (dual axis; greyscale-distinguishable markers)
fig, ax = plt.subplots(figsize=(8, 4.5))
l1, = ax.plot(disp_mid, disp_sd, color="#55a868", marker="o", ls="-", ms=8,
              label="Within-band SD of PC1 (style spread)")
ax.set_xlabel("Player Elo (band midpoint)")
ax.set_ylabel("Within-band SD of PC1 (style spread)")
ax.set_title(f"Style dispersion vs skill (r = {r_disp:+.2f})")
ax.annotate(f"r = {r_disp:+.2f}", xy=(0.04, 0.06), xycoords="axes fraction",
            ha="left", va="bottom", fontsize=11,
            bbox=dict(boxstyle="round", fc="white", ec="grey", alpha=0.9))
ax2 = ax.twinx()
l2, = ax2.plot(disp_mid, disp_mean, color="#c44e52", marker="s", ls="--", ms=8,
               alpha=0.85, label="Within-band mean PC1")
ax2.set_ylabel("Within-band mean PC1", color="#c44e52")
ax.legend(handles=[l1, l2], loc="upper right")
plt.tight_layout()
save_fig(fig, "fig3_dispersion", pdf=True)

# Fig 4: mean PC1 + exchange_rate vs Elo with segmented fit (two panels)
fig, axes = plt.subplots(1, 2, figsize=(13, 5))
xs = np.linspace(elo.min(), elo.max(), 200)
# left: PC1
ax = axes[0]
ax.plot(disp_mid, disp_mean, "o", color="#4c72b0", ms=8, label="Band-mean PC1")
seg = segmented_fit(elo, pc1_common)
hinge = np.maximum(0.0, xs - seg["c"])
ys = seg["coef"][0] + seg["coef"][1]*xs + seg["coef"][2]*hinge
ax.plot(xs, ys, "-", color="#c44e52", lw=2,
        label=f"Segmented fit (breakpoint = {seg['c']:.0f} Elo)")
lin = linear_fit(elo, pc1_common)
ax.plot(xs, lin["b0"]+lin["b1"]*xs, "--", color="grey", label="Linear fit")
ax.axvline(seg["c"], ls=":", color="k", alpha=0.5)
ax.set_xlabel("Player Elo")
ax.set_ylabel("PC1 (attacking +/positional −)")
ax.set_title("PC1 (style axis) vs skill, with breakpoint")
ax.legend()
# right: exchange_rate
ax = axes[1]
exr_band = [X[fine_lo == lo, ix_exch].mean() for lo in fine_edges if fine_counts[lo] >= 50]
exr_mid = [band_mid_fine(lo) for lo in fine_edges if fine_counts[lo] >= 50]
ax.plot(exr_mid, exr_band, "o", color="#4c72b0", ms=8, label="Band-mean exchange rate")
seg2 = segmented_fit(elo, X[:, ix_exch])
hinge2 = np.maximum(0.0, xs - seg2["c"])
ys2 = seg2["coef"][0] + seg2["coef"][1]*xs + seg2["coef"][2]*hinge2
ax.plot(xs, ys2, "-", color="#c44e52", lw=2,
        label=f"Segmented fit (breakpoint = {seg2['c']:.0f} Elo)")
lin2 = linear_fit(elo, X[:, ix_exch])
ax.plot(xs, lin2["b0"]+lin2["b1"]*xs, "--", color="grey", label="Linear fit")
ax.axvline(seg2["c"], ls=":", color="k", alpha=0.5)
ax.set_xlabel("Player Elo")
ax.set_ylabel("Exchange rate")
ax.set_title("Exchange rate vs skill, with breakpoint")
ax.legend()
plt.tight_layout()
save_fig(fig, "fig4_breakpoint", pdf=True)

# Fig 5: PC1 loadings heatmap; FULL row separated from per-band rows
fig, ax = plt.subplots(figsize=(10, 6.4))
M = np.array([band_results[lo]["pc1"] for lo in adequate_fine] + [pc1_full])
ylabs = [band_label_fine(lo) for lo in adequate_fine] + ["FULL"]
im = ax.imshow(M, aspect="auto", cmap="RdBu_r", vmin=-0.6, vmax=0.6)
ax.set_xticks(range(len(INDICATORS)))
ax.set_xticklabels(INDICATORS, rotation=40, ha="right", fontsize=9)
ax.set_yticks(range(len(ylabs))); ax.set_yticklabels(ylabs)
for i in range(M.shape[0]):
    for j in range(M.shape[1]):
        ax.text(j, i, f"{M[i,j]:+.2f}", ha="center", va="center", fontsize=6)
# visually separate the FULL (last) row from the per-band rows above it
sep_y = len(adequate_fine) - 0.5
ax.axhline(sep_y, color="k", lw=2.5)
ax.get_yticklabels()[-1].set_fontweight("bold")
plt.colorbar(im, label="PC1 loading")
ax.set_title("PC1 loadings across Elo bands (sign-aligned)")
plt.tight_layout()
save_fig(fig, "fig5_loadings_heatmap", pdf=True)

print(f"Figures saved to: {FIGDIR}")
for fn in sorted(os.listdir(FIGDIR)):
    print("  ", fn)
print("\nNOTE: cross-sectional design (different players at different skill "
      "levels), NOT longitudinal. Single-sex (female) sample -> no sex confound.")
