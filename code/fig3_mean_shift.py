#!/usr/bin/env python3
"""
Paper 3 -- Figure 2 (file stem fig3_mean_shift), REPLACEMENT for fig3_dispersion.

The dispersion result (within-band SD of PC1 vs Elo) was withdrawn as a
measurement-precision artifact (see style_skill_ROBUSTNESS.txt): games-played
rises with Elo, so low-Elo player PC1 scores are noisier and appear more spread.
The surviving headline is the SHIFT IN MEAN PC1 toward the positional pole.

The SD series is omitted entirely. No r value appears anywhere in the figure.
Same data, aggregation, PCA and orientation as style_skill_analysis.py.
Writes fig3_mean_shift.png (300 DPI) + fig3_mean_shift.pdf (vector).
Leaves fig3_dispersion.png / .pdf untouched for the record.
"""
import csv, os
import numpy as np
np.seterr(divide="ignore", over="ignore", invalid="ignore")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = os.path.dirname(os.path.abspath(__file__))
FIGDIR = os.path.join(OUT, "style_skill_figures")
os.makedirs(FIGDIR, exist_ok=True)

INDICATORS = [
    "exchange_rate", "tension_duration", "avg_mobility", "center_control_score",
    "advanced_pawn_push_rate", "pawn_storm_indicator", "castling_ply",
    "king_shelter_score", "forcing_move_rate", "reactive_move_rate",
]

# ---- identical to style_skill_analysis.py -----------------------------------
def load_player_level(path):
    rows = {}
    with open(path) as f:
        for r in csv.DictReader(f):
            if r["gender"] != "female":
                continue
            pid = r["player_id"]
            try:
                w = float(r["n_games"]); elo = float(r["avg_elo"])
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
        V = np.array([rr[2] for rr in recs], float)
        if not np.all(np.isfinite(V)):
            mask = np.all(np.isfinite(V), axis=1)
            if not mask.any():
                continue
            W, e, V = W[mask], e[mask], V[mask]
        wsum = W.sum()
        players.append(pid); elos.append((W * e).sum() / wsum)
        X.append((W[:, None] * V).sum(axis=0) / wsum); ngames.append(wsum)
    return (np.array(players), np.array(elos, float),
            np.array(X, float), np.array(ngames, float))


def pca(Xsub):
    mu = Xsub.mean(axis=0)
    sd = Xsub.std(axis=0, ddof=1)
    sd_safe = np.where(sd == 0, 1.0, sd)
    Z = (Xsub - mu) / sd_safe
    U, S, Vt = np.linalg.svd(Z, full_matrices=False)
    eig = (S ** 2) / (Xsub.shape[0] - 1)
    return mu, sd_safe, eig / eig.sum(), Vt, U * S, eig


def segmented_fit(x, y, grid=None):
    if grid is None:
        grid = np.linspace(np.percentile(x, 10), np.percentile(x, 90), 81)
    best = None
    for c in grid:
        A = np.column_stack([np.ones_like(x), x, np.maximum(0.0, x - c)])
        coef, *_ = np.linalg.lstsq(A, y, rcond=None)
        r = y - A @ coef
        rss = float(r @ r)
        if best is None or rss < best["rss"]:
            best = dict(c=float(c), coef=coef, rss=rss)
    return best

players, elo, X, ngames = load_player_level(
    os.path.join(OUT, "analysis_dataset_agg.csv"))
N = len(players)
mu_f, sd_f, vr_f, load_f, scores_f, eig_f = pca(X)
pc1_full = load_f[0].copy()
ix_exch = INDICATORS.index("exchange_rate")
ix_forcing = INDICATORS.index("forcing_move_rate")
if np.sign(pc1_full[ix_exch] + pc1_full[ix_forcing]) < 0:
    pc1_full = -pc1_full
pc1_common = ((X - mu_f) / sd_f) @ pc1_full

def fine_band(e):
    lo = int(np.floor(e / 100.0) * 100)
    return 2500 if lo >= 2500 else lo

fine_lo = np.array([fine_band(e) for e in elo])
fine_edges = sorted(set(fine_lo))

# adequate bands (n >= 50) -- the same 12 bands as the published figure
disp_mid, disp_mean, disp_n = [], [], []
for lo in fine_edges:
    idx = np.where(fine_lo == lo)[0]
    if len(idx) < 50:
        continue
    disp_mid.append(lo + 50.0)
    disp_mean.append(pc1_common[idx].mean())
    disp_n.append(len(idx))
disp_mid = np.array(disp_mid); disp_mean = np.array(disp_mean)

bp = segmented_fit(elo, pc1_common)["c"]

print(f"N = {N} players; {len(disp_mid)} adequate bands (n >= 50)")
print(f"Band-mean PC1: {disp_mean[0]:+.4f} (Elo {disp_mid[0]:.0f}) -> "
      f"{disp_mean[-1]:+.4f} (Elo {disp_mid[-1]:.0f})")
print(f"Breakpoint (segmented fit on continuous Elo) = {bp:.1f}")

# ---------------------------------------------------------------- figure ----
DPI = 300
PRIMARY = "#4c72b0"          # same primary as fig1/fig2/fig4/fig5

fig, ax = plt.subplots(figsize=(8, 4.5))

# zero reference: the sign flip between the two poles of the axis
ax.axhline(0.0, color="#b0b0b0", lw=0.8, ls="-", zorder=1)

# breakpoint marker (light, dotted, behind the data)
ax.axvline(bp, color="#8c8c8c", lw=1.1, ls=":", zorder=1)
ax.annotate("breakpoint ≈ 1800", xy=(bp, 0.965), xycoords=("data", "axes fraction"),
            xytext=(6, 0), textcoords="offset points",
            ha="left", va="top", fontsize=9, color="#5c5c5c")

# main (and only) series
ax.plot(disp_mid, disp_mean, color=PRIMARY, marker="o", ls="-", lw=2.0, ms=8,
        zorder=3)

ax.set_xlabel("Player Elo (band midpoint)")
ax.set_ylabel("Within-band mean PC1  (attacking +  /  positional −)")
ax.set_title("Style shifts toward the positional pole as skill rises")

# pole cues on the y-axis, so the direction of the shift is readable unaided
ax.margins(x=0.04)
ax.set_ylim(min(disp_mean) - 0.45, max(disp_mean) + 0.45)
ax.annotate("more attacking / forcing", xy=(0.985, 0.90), xycoords="axes fraction",
            ha="right", va="top", fontsize=8.5, color="#6b6b6b", style="italic")
ax.annotate("more positional", xy=(0.985, 0.06), xycoords="axes fraction",
            ha="right", va="bottom", fontsize=8.5, color="#6b6b6b", style="italic")

plt.tight_layout()
fig.savefig(os.path.join(FIGDIR, "fig3_mean_shift.png"), dpi=DPI)
fig.savefig(os.path.join(FIGDIR, "fig3_mean_shift.pdf"))
plt.close(fig)

print("\nWrote:")
for fn in ("fig3_mean_shift.png", "fig3_mean_shift.pdf"):
    p = os.path.join(FIGDIR, fn)
    print(f"   {p}  ({os.path.getsize(p)} bytes)")
print("\nfig3_dispersion.png / .pdf left untouched.")
