#!/usr/bin/env python3
"""
Paper 3 ROBUSTNESS CHECK: measurement-precision confound on the dispersion result.

Question: is the observed decline in within-band PC1 dispersion with Elo
(r = -0.744) partly an artifact of low-Elo players having FEWER GAMES, hence
noisier player-level PC1 estimates, hence more apparent spread?

Reuses the PCA/orientation/aggregation of style_skill_analysis.py verbatim.
Does NOT modify any existing analysis or output file.
"""
import csv, os
import numpy as np
from scipy import stats

np.seterr(divide="ignore", over="ignore", invalid="ignore")
OUT = os.path.dirname(os.path.abspath(__file__))

INDICATORS = [
    "exchange_rate", "tension_duration", "avg_mobility", "center_control_score",
    "advanced_pawn_push_rate", "pawn_storm_indicator", "castling_ply",
    "king_shelter_score", "forcing_move_rate", "reactive_move_rate",
]

# ======================================================================
# 0. REPRODUCE the player-level dataset + PCA of style_skill_analysis.py
# ======================================================================
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


players, elo, X, ngames = load_player_level(os.path.join(OUT, "analysis_dataset_agg.csv"))
N = len(players)
mu_f, sd_f, vr_f, load_f, scores_f, eig_f = pca(X)
pc1_full = load_f[0].copy()
ix_exch = INDICATORS.index("exchange_rate")
ix_forcing = INDICATORS.index("forcing_move_rate")
if np.sign(pc1_full[ix_exch] + pc1_full[ix_forcing]) < 0:
    pc1_full = -pc1_full
pc1_common = ((X - mu_f) / sd_f) @ pc1_full     # identical to main analysis

def fine_band(e):
    lo = int(np.floor(e / 100.0) * 100)
    return 2500 if lo >= 2500 else lo

fine_lo = np.array([fine_band(e) for e in elo])
fine_edges = sorted(set(fine_lo))
fine_counts = {lo: int((fine_lo == lo).sum()) for lo in fine_edges}
adequate = [lo for lo in fine_edges if fine_counts[lo] >= 50]
blab = lambda lo: "2500+" if lo == 2500 else f"{lo}-{lo+99}"
bmid = lambda lo: lo + 50.0

pidx = {p: i for i, p in enumerate(players)}

print("=" * 78)
print("PAPER 3 ROBUSTNESS: MEASUREMENT-PRECISION CONFOUND ON THE DISPERSION RESULT")
print("=" * 78)
print(f"\nReproduced base analysis: N = {N} female players, "
      f"{int(ngames.sum())} games, PC1 var = {vr_f[0]*100:.2f}%")
print("PC1 loadings reused verbatim from style_skill_analysis.py "
      "(exchange_rate/forcing = + pole).")

# ======================================================================
# 1. GAMES PER PLAYER BY ELO BAND
# ======================================================================
print("\n\n" + "=" * 78)
print("1.  GAMES PER PLAYER BY ELO BAND")
print("=" * 78)
print("""
Table 1a. Distribution of n_games by 100-pt Elo band (all 16 bands, N=2216).
""".rstrip())
print(f"{'band':>10} {'mid':>6} {'n_play':>7} {'mean':>7} {'median':>7} "
      f"{'min':>5} {'p25':>6} {'p75':>6} {'%<100':>7} {'%<=10':>7}")
print("-" * 78)
for lo in fine_edges:
    g = ngames[fine_lo == lo]
    print(f"{blab(lo):>10} {bmid(lo):>6.0f} {len(g):>7d} {g.mean():>7.1f} "
          f"{np.median(g):>7.1f} {g.min():>5.0f} {np.percentile(g,25):>6.1f} "
          f"{np.percentile(g,75):>6.1f} {100*(g<100).mean():>6.1f}% "
          f"{100*(g<=10).mean():>6.1f}%")
print("-" * 78)
print(f"{'ALL':>10} {'':>6} {N:>7d} {ngames.mean():>7.1f} "
      f"{np.median(ngames):>7.1f} {ngames.min():>5.0f} "
      f"{np.percentile(ngames,25):>6.1f} {np.percentile(ngames,75):>6.1f} "
      f"{100*(ngames<100).mean():>6.1f}% {100*(ngames<=10).mean():>6.1f}%")
print("\nNote: n_games is capped at 100 by the download script, so the upper tail")
print("is censored; all variation is in how far BELOW 100 a player falls.")

log_ng = np.log(ngames)
r_lg_elo = stats.pearsonr(log_ng, elo)
rho_lg_elo = stats.spearmanr(log_ng, elo)
r_raw = stats.pearsonr(ngames, elo)
print("\n\nTable 1b. Association of games-per-player with Elo (player level, N=2216).")
print(f"{'pair':>38} {'r':>9} {'95% CI':>20} {'p':>11}")
print("-" * 78)
ci = r_lg_elo.confidence_interval(0.95)
print(f"{'log(n_games)  vs  Elo  (Pearson)':>38} {r_lg_elo.statistic:>9.4f} "
      f"[{ci.low:>+.4f},{ci.high:>+.4f}] {r_lg_elo.pvalue:>11.3e}")
ci2 = r_raw.confidence_interval(0.95)
print(f"{'n_games       vs  Elo  (Pearson)':>38} {r_raw.statistic:>9.4f} "
      f"[{ci2.low:>+.4f},{ci2.high:>+.4f}] {r_raw.pvalue:>11.3e}")
print(f"{'log(n_games)  vs  Elo  (Spearman)':>38} {rho_lg_elo.statistic:>9.4f} "
      f"{'--':>20} {rho_lg_elo.pvalue:>11.3e}")
print("-" * 78)

# band-level: mean log n_games vs band midpoint
mids_adq = np.array([bmid(lo) for lo in adequate])
mean_logng_adq = np.array([log_ng[fine_lo == lo].mean() for lo in adequate])
r_band_ng = stats.pearsonr(mids_adq, mean_logng_adq)
print(f"\nBand level (12 adequate bands): mean log(n_games) vs band midpoint "
      f"r = {r_band_ng.statistic:+.4f} (p = {r_band_ng.pvalue:.4f})")

# ======================================================================
# 2. MEASUREMENT-ERROR-CORRECTED DISPERSION
# ======================================================================
print("\n\n" + "=" * 78)
print("2.  MEASUREMENT-ERROR-CORRECTED DISPERSION")
print("=" * 78)
print("""
Method. A player's PC1 score is a linear map of their indicator means:
    PC1_i = sum_j w_j * (Xbar_ij - mu_j) / sd_j,   w = full-sample PC1 loadings.
So each game can be projected onto the SAME axis, giving per-game PC1 scores
g_i1..g_in. The sampling variance of the player's PC1 estimate is then
    s2e_i = Var(g_i) / n_i
which is exactly a' S_i a / n_i with S_i the full within-player 10x10 covariance
matrix -- i.e. it keeps the within-player COVARIANCES between indicators, not
just the diagonal variances. (A diagonal-only variant is reported as a
sensitivity below; it understates the noise because the indicators covary.)

Observed between-player variance in a band decomposes as
    var_obs = var_true + mean(s2e)      =>   var_true = var_obs - mean(s2e).
""".rstrip())

# ---- per-game PC1 scores from the raw game-level file ----
# Mirror the original pipeline EXACTLY (download_and_analyze.py):
#   n_games = groupby(player, time_category).size()      -> counts ALL games
#   indicator = groupby(...).mean()                      -> pandas mean SKIPS NaN
# so castling_ply (the only indicator with missing values, 10.4% of games:
# player never castled) is averaged over fewer games than the other nine.
# style_skill_analysis.py then DROPS any player x time_category row with a
# non-finite indicator, i.e. any time-category in which castling_ply was NaN
# for every game. We replicate that structure so per-game PC1 scores average
# back to exactly the published player PC1 score.
IDX_CAST = INDICATORS.index("castling_ply")
cells = {}          # (player, time_category) -> list of 10-vectors
n_bad_other = 0
with open(os.path.join(OUT, "analysis_dataset_raw.csv")) as f:
    for r in csv.DictReader(f):
        if r["gender"] != "female":
            continue
        pid = r["player_id"]
        if pid not in pidx:
            continue
        v, bad = [], False
        for c in INDICATORS:
            try:
                x = float(r[c])
            except (ValueError, KeyError):
                x = np.nan
            if not np.isfinite(x):
                x = np.nan
                if c != "castling_ply":
                    bad = True
            v.append(x)
        if bad:
            n_bad_other += 1
            continue
        cells.setdefault((pid, r["time_category"]), []).append(v)

print(f"\nGame-level rows loaded (dropped {n_bad_other} rows for "
      f"non-castling missingness).")

n_cast_imp = n_cell_drop = 0
per_game_pc1, n_used = {}, np.zeros(N)
a_vec = pc1_full / sd_f      # weights on raw (unstandardised) indicators
by_player = {}
for (pid, tc), lst in cells.items():
    G = np.array(lst, float)
    miss = ~np.isfinite(G[:, IDX_CAST])
    if miss.all():
        n_cell_drop += 1          # this time-category row was dropped upstream
        continue
    if miss.any():
        n_cast_imp += int(miss.sum())
        # impute with the time-category's own observed castling mean -- this is
        # precisely the value the NaN-skipping pipeline mean already used
        G[miss, IDX_CAST] = G[~miss, IDX_CAST].mean()
    by_player.setdefault(pid, []).append(G)

for pid, blocks in by_player.items():
    G = np.vstack(blocks)
    per_game_pc1[pid] = (G - mu_f) @ a_vec
    n_used[pidx[pid]] = len(G)

print(f"castling_ply imputed from its own time-category mean in {n_cast_imp} "
      f"games (10.4% of games); PC1 loading = {pc1_full[IDX_CAST]:+.4f}.")
print(f"Dropped {n_cell_drop} player x time-category cells where castling_ply "
      f"was missing in every game (matches style_skill_analysis.py).")

# validation: mean of per-game PC1 must equal the published player PC1 score
chk = np.array([per_game_pc1[p].mean() - pc1_common[pidx[p]] for p in per_game_pc1])
print(f"Validation, |mean(per-game PC1) - published player PC1|: "
      f"max = {np.abs(chk).max():.2e}, mean = {np.abs(chk).mean():.2e}  "
      f"(0 = exact reconstruction of the published scores)")
ndiff = int((n_used != ngames).sum())
print(f"Games used per player vs published n_games: {N-ndiff}/{N} exact matches.")

# ---- per-player sampling variance ----
s2_within = np.full(N, np.nan)     # within-player variance of per-game PC1
for pid, g in per_game_pc1.items():
    if len(g) >= 2:
        s2_within[pidx[pid]] = g.var(ddof=1)
have = np.isfinite(s2_within)
print(f"\nPlayers with >=2 usable games (own within-player variance): {have.sum()} of {N}")
print(f"Players with <2 usable games (pooled band variance imputed): {(~have).sum()}")

# band-pooled within-player variance, used for imputation + as sensitivity
pooled_band = {}
for lo in fine_edges:
    m = (fine_lo == lo) & have
    num = np.sum((n_used[m] - 1) * s2_within[m])
    den = np.sum(n_used[m] - 1)
    pooled_band[lo] = num / den if den > 0 else np.nan
s2_player = s2_within.copy()
for i in range(N):
    if not have[i]:
        s2_player[i] = pooled_band[fine_lo[i]]

n_eff = np.where(n_used >= 1, n_used, 1.0)
s2e_full = s2_player / n_eff                       # PRIMARY: full covariance
s2e_pool = np.array([pooled_band[fine_lo[i]] for i in range(N)]) / n_eff  # sensitivity A

# sensitivity B: diagonal-only (variances only, no within-player covariances)
s2e_diag = np.full(N, np.nan)
for pid, blocks in by_player.items():
    G = np.vstack(blocks)
    if len(G) >= 2:
        s2e_diag[pidx[pid]] = np.sum((a_vec ** 2) * G.var(axis=0, ddof=1)) / len(G)
s2e_diag = np.where(np.isfinite(s2e_diag), s2e_diag, s2e_full)

print("""
Table 2a. Observed vs corrected within-band dispersion of PC1
          (common full-sample axis; adequate bands, n >= 50).
   var_obs  = observed between-player variance of PC1 in the band
   mean_s2e = mean sampling (measurement) variance of the player PC1 estimates
   var_true = var_obs - mean_s2e   (measurement-error-corrected)
   %noise   = 100 * mean_s2e / var_obs
""".rstrip())
hdr = (f"{'band':>10} {'mid':>6} {'n':>5} {'var_obs':>9} {'sd_obs':>7} "
       f"{'mean_s2e':>9} {'var_true':>9} {'sd_true':>8} {'%noise':>7}")
print(hdr); print("-" * len(hdr))
rows2 = []
for lo in adequate:
    m = fine_lo == lo
    s = pc1_common[m]
    vobs = s.var(ddof=1)
    ms2e = s2e_full[m].mean()
    vtrue = vobs - ms2e
    sdtrue = np.sqrt(vtrue) if vtrue > 0 else np.nan
    rows2.append((lo, bmid(lo), int(m.sum()), vobs, np.sqrt(vobs), ms2e, vtrue, sdtrue))
    print(f"{blab(lo):>10} {bmid(lo):>6.0f} {int(m.sum()):>5d} {vobs:>9.4f} "
          f"{np.sqrt(vobs):>7.4f} {ms2e:>9.4f} {vtrue:>9.4f} {sdtrue:>8.4f} "
          f"{100*ms2e/vobs:>6.1f}%")
print("-" * len(hdr))

mids2 = np.array([r[1] for r in rows2])
sd_obs2 = np.array([r[4] for r in rows2])
sd_true2 = np.array([r[7] for r in rows2])
var_obs2 = np.array([r[3] for r in rows2])
var_true2 = np.array([r[6] for r in rows2])

def rline(name, y, x=mids2):
    ok = np.isfinite(y)
    res = stats.pearsonr(x[ok], y[ok])
    ci = res.confidence_interval(0.95)
    sl = np.polyfit(x[ok], y[ok], 1)[0] * 100
    return (f"{name:>44} {res.statistic:>8.4f} "
            f"[{ci.low:>+.3f},{ci.high:>+.3f}] {res.pvalue:>9.4f} {sl:>+11.5f}")

print("""
Table 2b. Dispersion-vs-skill correlation, uncorrected vs corrected
          (12 adequate band midpoints).
""".rstrip())
h2 = f"{'dispersion measure':>44} {'r':>8} {'95% CI':>17} {'p':>9} {'slope/100':>11}"
print(h2); print("-" * len(h2))
print(rline("sd_obs   (UNCORRECTED -- published r = -0.744)", sd_obs2))
print(rline("sd_true  (CORRECTED, full within-player cov)", sd_true2))
# sensitivities
sd_true_pool, sd_true_diag = [], []
for lo in adequate:
    m = fine_lo == lo
    vobs = pc1_common[m].var(ddof=1)
    for acc, s2e in ((sd_true_pool, s2e_pool), (sd_true_diag, s2e_diag)):
        vt = vobs - s2e[m].mean()
        acc.append(np.sqrt(vt) if vt > 0 else np.nan)
print(rline("sd_true  (sens. A: band-pooled within-player var)",
            np.array(sd_true_pool)))
print(rline("sd_true  (sens. B: diagonal-only, no covariances)",
            np.array(sd_true_diag)))
print("-" * len(h2))
print(rline("var_obs  (variance scale, uncorrected)", var_obs2))
print(rline("var_true (variance scale, corrected)", var_true2))
print("-" * len(h2))

# Spearman as a rank-robust check
for nm, y in (("sd_obs", sd_obs2), ("sd_true", sd_true2)):
    ok = np.isfinite(y)
    sp = stats.spearmanr(mids2[ok], y[ok])
    print(f"  Spearman rho, {nm:>8} vs midpoint: {sp.statistic:+.4f} (p={sp.pvalue:.4f})")

print("""
Table 2c. How much of the observed dispersion decline is measurement noise?
""".rstrip())
print(f"{'quantity':>44} {'lowest band':>13} {'highest band':>14} {'change':>10}")
print("-" * 84)
print(f"{'sd_obs (uncorrected)':>44} {sd_obs2[0]:>13.4f} {sd_obs2[-1]:>14.4f} "
      f"{sd_obs2[-1]-sd_obs2[0]:>+10.4f}")
print(f"{'sd_true (corrected)':>44} {sd_true2[0]:>13.4f} {sd_true2[-1]:>14.4f} "
      f"{sd_true2[-1]-sd_true2[0]:>+10.4f}")
print(f"{'mean sampling variance s2e':>44} "
      f"{s2e_full[fine_lo==adequate[0]].mean():>13.4f} "
      f"{s2e_full[fine_lo==adequate[-1]].mean():>14.4f} "
      f"{s2e_full[fine_lo==adequate[-1]].mean()-s2e_full[fine_lo==adequate[0]].mean():>+10.4f}")
drop_obs = sd_obs2[0] - sd_obs2[-1]
drop_true = sd_true2[0] - sd_true2[-1]
print("-" * 84)
print(f"Share of the observed top-to-bottom SD drop that survives correction: "
      f"{100*drop_true/drop_obs:.1f}%")

# ======================================================================
# 3. PLAYER-LEVEL DISPERSION TEST
# ======================================================================
print("\n\n" + "=" * 78)
print("3.  PLAYER-LEVEL DISPERSION TEST  (N = 2216)")
print("=" * 78)

band_mean = np.zeros(N)
for lo in fine_edges:
    m = fine_lo == lo
    band_mean[m] = pc1_common[m].mean()
absdev = np.abs(pc1_common - band_mean)
print("""
Outcome: |PC1_i - mean(PC1) in i's own 100-pt Elo band|  (absolute deviation
from band mean = player-level dispersion contribution). All 16 fine bands are
used so every player has a band mean; N = 2216.
Predictors are on their natural scale: Elo coefficients are PER 100 ELO POINTS.
""".rstrip())

def ols(y, Xd, names):
    n, k = Xd.shape
    beta, *_ = np.linalg.lstsq(Xd, y, rcond=None)
    resid = y - Xd @ beta
    dof = n - k
    s2 = resid @ resid / dof
    XtXi = np.linalg.inv(Xd.T @ Xd)
    se = np.sqrt(np.diag(s2 * XtXi))
    t = beta / se
    p = 2 * stats.t.sf(np.abs(t), dof)
    crit = stats.t.ppf(0.975, dof)
    lo_, hi_ = beta - crit * se, beta + crit * se
    sst = np.sum((y - y.mean()) ** 2)
    r2 = 1 - (resid @ resid) / sst
    return dict(names=names, beta=beta, se=se, t=t, p=p, lo=lo_, hi=hi_,
                r2=r2, dof=dof, rss=float(resid @ resid), k=k, n=n)

def show(fit, title):
    print(f"\n{title}")
    h = f"{'term':>22} {'coef':>12} {'SE':>10} {'t':>8} {'p':>11} {'95% CI':>26}"
    print(h); print("-" * len(h))
    for i, nm in enumerate(fit["names"]):
        print(f"{nm:>22} {fit['beta'][i]:>12.5f} {fit['se'][i]:>10.5f} "
              f"{fit['t'][i]:>8.3f} {fit['p'][i]:>11.3e} "
              f"[{fit['lo'][i]:>+9.5f}, {fit['hi'][i]:>+9.5f}]")
    print("-" * len(h))
    print(f"  N = {fit['n']}   R^2 = {fit['r2']:.5f}   df resid = {fit['dof']}")

elo100 = elo / 100.0
one = np.ones(N)
m1 = ols(absdev, np.column_stack([one, elo100]), ["intercept", "Elo (per 100)"])
m2 = ols(absdev, np.column_stack([one, elo100, log_ng]),
         ["intercept", "Elo (per 100)", "log(n_games)"])
show(m1, "Model 1  |PC1 - band mean| ~ Elo")
show(m2, "Model 2  |PC1 - band mean| ~ Elo + log(n_games)")

print("\nTable 3. Elo coefficient, before vs after adjusting for log(n_games).")
h3 = f"{'model':>34} {'Elo coef /100':>14} {'SE':>9} {'95% CI':>26} {'p':>11}"
print(h3); print("-" * len(h3))
print(f"{'1. Elo only':>34} {m1['beta'][1]:>14.5f} {m1['se'][1]:>9.5f} "
      f"[{m1['lo'][1]:>+9.5f}, {m1['hi'][1]:>+9.5f}] {m1['p'][1]:>11.3e}")
print(f"{'2. + log(n_games)':>34} {m2['beta'][1]:>14.5f} {m2['se'][1]:>9.5f} "
      f"[{m2['lo'][1]:>+9.5f}, {m2['hi'][1]:>+9.5f}] {m2['p'][1]:>11.3e}")
print("-" * len(h3))
att = 100 * (1 - m2["beta"][1] / m1["beta"][1])
print(f"Attenuation of the Elo coefficient after adjustment: {att:+.1f}%")
print(f"log(n_games) coefficient: {m2['beta'][2]:+.5f} "
      f"[{m2['lo'][2]:+.5f}, {m2['hi'][2]:+.5f}], p = {m2['p'][2]:.3e}")

# extra: restrict to well-measured players only (n_games >= 50 and == 100)
print("\nTable 3b. Same regression restricted to well-measured players")
print("          (removes the precision gradient by construction).")
h4 = (f"{'subset':>34} {'N':>6} {'Elo coef /100':>14} {'95% CI':>26} {'p':>11}")
print(h4); print("-" * len(h4))
for lab, msk in (("all players", np.ones(N, bool)),
                 ("n_games >= 30", ngames >= 30),
                 ("n_games >= 50", ngames >= 50),
                 ("n_games == 100 (fully sampled)", ngames >= 100)):
    yy = np.abs(pc1_common[msk] - band_mean[msk])
    f_ = ols(yy, np.column_stack([np.ones(msk.sum()), elo100[msk]]),
             ["intercept", "Elo"])
    print(f"{lab:>34} {int(msk.sum()):>6d} {f_['beta'][1]:>14.5f} "
          f"[{f_['lo'][1]:>+9.5f}, {f_['hi'][1]:>+9.5f}] {f_['p'][1]:>11.3e}")
print("-" * len(h4))

print("""
Table 3c. Within-band dispersion among EQUALLY-MEASURED players only
          (n_games == 100, N = 1394). No precision gradient can exist here,
          so any surviving decline is a real style effect.
""".rstrip())
msk100 = ngames >= 100
h3c = (f"{'band':>10} {'mid':>6} {'n':>5} {'sd_obs(all)':>12} {'sd_obs(n=100)':>14} "
       f"{'mean_s2e(n=100)':>16} {'sd_true(n=100)':>15}")
print(h3c); print("-" * len(h3c))
m100_mid, m100_sd, m100_sdtrue = [], [], []
for lo in fine_edges:
    m = (fine_lo == lo) & msk100
    if m.sum() < 30:
        continue
    s_ = pc1_common[m]
    v = s_.var(ddof=1); e_ = s2e_full[m].mean()
    vt = v - e_
    m100_mid.append(bmid(lo)); m100_sd.append(np.sqrt(v))
    m100_sdtrue.append(np.sqrt(vt) if vt > 0 else np.nan)
    print(f"{blab(lo):>10} {bmid(lo):>6.0f} {int(m.sum()):>5d} "
          f"{pc1_common[fine_lo==lo].std(ddof=1):>12.4f} {np.sqrt(v):>14.4f} "
          f"{e_:>16.4f} {(np.sqrt(vt) if vt>0 else float('nan')):>15.4f}")
print("-" * len(h3c))
m100_mid = np.array(m100_mid); m100_sd = np.array(m100_sd)
m100_sdtrue = np.array(m100_sdtrue)
if len(m100_mid) >= 3:
    rr = stats.pearsonr(m100_mid, m100_sd); ci = rr.confidence_interval(0.95)
    print(f"  sd_obs  vs Elo midpoint (n_games==100 only, {len(m100_mid)} bands): "
          f"r = {rr.statistic:+.4f} [{ci.low:+.3f},{ci.high:+.3f}], p = {rr.pvalue:.4f}")
    ok = np.isfinite(m100_sdtrue)
    rr2 = stats.pearsonr(m100_mid[ok], m100_sdtrue[ok])
    print(f"  sd_true vs Elo midpoint (n_games==100 only): "
          f"r = {rr2.statistic:+.4f}, p = {rr2.pvalue:.4f}")

print("""
Table 3d. Leverage check -- the 1400-1499 band is a large outlier
          (var_obs 8.47 vs 1.7-3.7 elsewhere). Refit dropping it.
""".rstrip())
h3d = f"{'series':>44} {'r (12 bands)':>13} {'r (drop 1400s)':>15} {'p (drop)':>10}"
print(h3d); print("-" * len(h3d))
for nm, y in (("sd_obs  (uncorrected)", sd_obs2), ("sd_true (corrected)", sd_true2)):
    ok = np.isfinite(y)
    full_r = stats.pearsonr(mids2[ok], y[ok]).statistic
    k = ok & (mids2 > 1500)
    rr = stats.pearsonr(mids2[k], y[k])
    print(f"{nm:>44} {full_r:>13.4f} {rr.statistic:>15.4f} {rr.pvalue:>10.4f}")
print("-" * len(h3d))

# ======================================================================
# 4. DOES THE ~1800 BREAKPOINT SURVIVE log(n_games)?
# ======================================================================
print("\n\n" + "=" * 78)
print("4.  SEGMENTED REGRESSION WITH log(n_games) ADDED")
print("=" * 78)

def linear_fit_cov(x, y, Z=None):
    A = np.column_stack([np.ones_like(x), x] + ([Z] if Z is not None else []))
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    r = y - A @ coef
    rss = float(r @ r); sst = float(np.sum((y - y.mean()) ** 2))
    return dict(coef=coef, rss=rss, r2=1 - rss / sst, k=A.shape[1])

def segmented_fit_cov(x, y, Z=None, grid=None):
    if grid is None:
        grid = np.linspace(np.percentile(x, 10), np.percentile(x, 90), 81)
    best = None
    for c in grid:
        hinge = np.maximum(0.0, x - c)
        cols = [np.ones_like(x), x, hinge] + ([Z] if Z is not None else [])
        A = np.column_stack(cols)
        coef, *_ = np.linalg.lstsq(A, y, rcond=None)
        r = y - A @ coef
        rss = float(r @ r)
        if best is None or rss < best["rss"]:
            best = dict(c=float(c), coef=coef, rss=rss, A=A)
    sst = float(np.sum((y - y.mean()) ** 2))
    best["r2"] = 1 - best["rss"] / sst
    best["k"] = best["A"].shape[1] + 1          # +1 for the estimated breakpoint
    best["slope_low"] = float(best["coef"][1])
    best["slope_high"] = float(best["coef"][1] + best["coef"][2])
    best["grid"] = grid
    return best

def prof_ci(x, y, Z, best, alpha=0.05):
    """Profile-likelihood CI for the breakpoint: all c whose RSS is within the
    F-based threshold of the optimum."""
    n = len(x); k = best["A"].shape[1]
    thr = best["rss"] * (1 + stats.f.ppf(1 - alpha, 1, n - k - 1) / (n - k - 1))
    keep = []
    for c in best["grid"]:
        hinge = np.maximum(0.0, x - c)
        cols = [np.ones_like(x), x, hinge] + ([Z] if Z is not None else [])
        A = np.column_stack(cols)
        coef, *_ = np.linalg.lstsq(A, y, rcond=None)
        r = y - A @ coef
        if float(r @ r) <= thr:
            keep.append(c)
    return (min(keep), max(keep)) if keep else (np.nan, np.nan)

def f_test(lin, seg, n):
    df1 = seg["k"] - lin["k"]; df2 = n - seg["k"]
    F = ((lin["rss"] - seg["rss"]) / df1) / (seg["rss"] / df2)
    return F, df1, df2, stats.f.sf(F, df1, df2)

for label, yv, published in [("PC1 (common-axis score)", pc1_common, 1792.8),
                             ("exchange_rate", X[:, ix_exch], 1858.4)]:
    print(f"\n--- outcome: {label}  (published breakpoint = {published:.1f} Elo) ---")
    h5 = (f"{'model':>28} {'breakpoint':>11} {'95% CI (bp)':>18} {'slope<bp':>12} "
          f"{'slope>bp':>12} {'R2':>8} {'F':>9} {'p':>10}")
    print(h5); print("-" * len(h5))
    for mlab, Z in (("no covariate (as published)", None),
                    ("+ log(n_games)", log_ng)):
        lin = linear_fit_cov(elo, yv, Z)
        seg = segmented_fit_cov(elo, yv, Z)
        F, df1, df2, pF = f_test(lin, seg, N)
        clo, chi = prof_ci(elo, yv, Z, seg)
        print(f"{mlab:>28} {seg['c']:>11.1f} [{clo:>7.1f},{chi:>7.1f}] "
              f"{seg['slope_low']:>+12.6f} {seg['slope_high']:>+12.6f} "
              f"{seg['r2']:>8.4f} {F:>9.3f} {pF:>10.3e}")
        print(f"{'   (linear counterpart)':>28} {'--':>11} {'--':>18} "
              f"{lin['coef'][1]:>+12.6f} {'--':>12} {lin['r2']:>8.4f} "
              f"{'--':>9} {'--':>10}")
        if Z is not None:
            print(f"{'   log(n_games) coef':>28} {seg['coef'][3]:>+11.5f}")
    print("-" * len(h5))

# also: does the breakpoint survive among fully-sampled players only?
print("\nTable 4b. Breakpoint in the fully-sampled subsample (n_games == 100),")
print("          where measurement precision is constant by construction.")
h6 = (f"{'outcome':>28} {'N':>6} {'breakpoint':>11} {'95% CI (bp)':>18} "
      f"{'slope<bp':>12} {'slope>bp':>12} {'F':>9} {'p':>10}")
print(h6); print("-" * len(h6))
msk = ngames >= 100
for label, yv in (("PC1 (common axis)", pc1_common), ("exchange_rate", X[:, ix_exch])):
    xs, ys = elo[msk], yv[msk]
    lin = linear_fit_cov(xs, ys); seg = segmented_fit_cov(xs, ys)
    F, df1, df2, pF = f_test(lin, seg, msk.sum())
    clo, chi = prof_ci(xs, ys, None, seg)
    print(f"{label:>28} {int(msk.sum()):>6d} {seg['c']:>11.1f} "
          f"[{clo:>7.1f},{chi:>7.1f}] {seg['slope_low']:>+12.6f} "
          f"{seg['slope_high']:>+12.6f} {F:>9.3f} {pF:>10.3e}")
print("-" * len(h6))
print("\nDone. No existing analysis file was modified.")
