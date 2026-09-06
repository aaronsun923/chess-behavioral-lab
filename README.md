# Chess as a Behavioral Laboratory — analysis code

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.22285434.svg)](https://doi.org/10.5281/zenodo.22285434)

Analysis code, specifications, figures, and anonymized player-level data for a four-paper
research program that uses chess as a recorded decision environment.

Zenodo community: https://zenodo.org/communities/chess-behavioral-lab

## Papers

| # | Title | DOI |
|---|-------|-----|
| 1 | Conditional by Design: Sex Differences in Chess Middlegame Decision Style Emerge at the Expert Tier | https://doi.org/10.5281/zenodo.22262168 |
| 2 | Same Axis, Different Place: How Middlegame Style Shifts Across the Expertise Gradient | https://doi.org/10.5281/zenodo.22262896 |
| 3 | Opening Convention, Middlegame Freedom: What Elite Stylistic Variation Implies for Developmental Chess Pedagogy | https://doi.org/10.5281/zenodo.22265831 |
| 4 | Sharper, Not Safer: The Direction of Human Deviations from Engine Play | https://doi.org/10.5281/zenodo.22267000 |

## Layout

- `code/` — the analysis pipeline.
  - `chess_pipeline_v2.py` — core: the ten engine-independent style indicators, middlegame boundary detection, gender-verification logic. Import only.
  - `fetch_titled_players.py` — builds the titled-player roster and resolves gender from official titles and the FIDE player list.
  - `download_and_analyze.py`, `download_and_analyze_male.py`, `download_and_analyze_male_titled.py` — download rated games from the Chess.com public API and run the pipeline (female roster; male probe; quota-matched male titled sample).
  - `probe_male_titled.py` — sampling probe for the male titled frame.
  - `style_skill_analysis.py`, `style_skill_robustness.py`, `fig3_mean_shift.py` — Paper 2 analyses: per-band PCA, Tucker's congruence, segmented regression, the measurement-artifact analysis, and figures.
  - `paper4_pilot.py`, `paper4_report.py`, `paper4b_pilot.py`, `paper4b_report.py`, `paper4b_figures.py` — Paper 4: engine evaluation pipeline (Stockfish, fixed depth 15, MultiPV 5), deviation-magnitude models, punishment-steepness (ΔRISK) analyses, and figures.
- `specs/` — the locked specifications for the Paper 4 analyses: v1 (deviation structure and the complementarity test) and v2 (the risk-direction analysis).
- `docs/` — pilot reports and the Paper 2 results file.
- `figures/` — the figures embedded in the papers.
- `data/` — anonymized player-level aggregated indicators (see below).

## Data

Raw game-level data are not redistributed, in keeping with the Chess.com terms of service
and to protect individual players. The `data/` folder contains player-level aggregated
indicators with usernames replaced by stable anonymous identifiers (P00001, ...), consistent
across files so joins still work. Titles, rating bands, and per-player mean ratings are
retained because the analyses require them; players with distinctive title-rating
combinations may remain identifiable in principle.

To rebuild the dataset from scratch: download the FIDE standard player list from
https://ratings.fide.com/download.phtml, save it as `fide_players.csv` in `code/`, then run
`fetch_titled_players.py` followed by the `download_and_analyze*.py` scripts. Downloads are
rate-limited and take time.

## Environment

Python 3.10+. Install dependencies with:

    pip install -r requirements.txt

Paper 4 additionally requires a Stockfish binary on PATH (the papers used a fixed-depth-15,
MultiPV-5 configuration; any recent Stockfish release reproduces the setup).

## License

MIT (see LICENSE). The papers themselves are CC-BY 4.0 on Zenodo.
