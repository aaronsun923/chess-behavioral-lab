"""
==============================================================================
download_and_analyze_male_titled.py  —  Male side, TITLE-QUOTA matched
==============================================================================
Rebuilds the MALE half of the study so that its FIDE-title composition mirrors
the female side's women's-title composition, tier-for-tier:

    male open title   female women's title   share   quota (N=630)
    ----------------   ---------------------  -----   -------------
    GM                 WGM                     12%       75
    IM                 WIM                     21%      130
    FM                 WFM                     41%      255
    CM                 WCM                     27%      170

Elo is now REPORTED (which band each title's players land in), not targeted.
The probe (Stage 0) showed real FIDE-titled men play online at 2000+, so the
1500-1999 band is left to fall where it may.

ONE TITLE PER INVOCATION  (a "checkpoint"):
    python download_and_analyze_male_titled.py --title GM --quota 75
Process scarcest-first (GM, IM, FM, CM), report, get approval, run the next.

PER CANDIDATE:
  1. Resolve gender (fetch_titled_players.resolve_open_player): Chess.com real
     name -> FIDE FTS -> sex. KEEP ONLY sex=='M'. FIDE-confirmed FEMALES are
     EXCLUDED with zero tolerance (e.g. Lei Tingjie). 'unknown' excluded too.
  2. For confirmed males: download last 18 months (100-game cap), filter to
     rated standard chess in {bullet,blitz,rapid} (daily EXCLUDED), run the
     UNCHANGED 11-indicator pipeline (chess_pipeline_v2.analyze_game).
  3. effective = >=1 analyzed game. Bin by MEAN game rating (same ruler as the
     female side). Stop the title when `quota` effective males are collected.

SAFETY / ETIQUETTE:
  - Incremental: every effective player's rows are appended to the raw CSV
    immediately (interruption never loses collected data).
  - Resume-safe: players already in the raw CSV are skipped; the per-title
    shuffle is seeded, so re-running a title deterministically continues.
  - 1.0s polite delays; try/except per player; reuse fide_cache.csv.
  - Gender determination is NEVER loosened to hit a quota.

OUTPUT (mirrors the female schema + title/mean_elo/band):
  analysis_dataset_male_titled_raw.csv
  analysis_dataset_male_titled_agg.csv
==============================================================================
"""

import os
import csv
import time
import random
import logging
import argparse
from collections import Counter

import pandas as pd

import download_and_analyze_male as DM   # tested process_player / band_of / BANDS
import fetch_titled_players as FT

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

SEED = 42
DEFAULT_DELAY = 1.0
MONTHS = 18                       # match the female side exactly (was 12 in prior male run)

# Title quotas matched to female women's-title proportions (N=630).
TITLE_QUOTAS = {'GM': 75, 'IM': 130, 'FM': 255, 'CM': 170}

OUT_RAW = 'analysis_dataset_male_titled_raw.csv'
OUT_AGG = 'analysis_dataset_male_titled_agg.csv'

INDICATORS = DM.INDICATORS        # the 10 averaged indicators
RAW_FIELDS = (['player_id', 'gender', 'title', 'player_elo', 'time_category',
               'eco', 'color', 'url']
              + INDICATORS
              + ['position_type', 'middlegame_moves_analyzed', 'total_moves',
                 'player_mean_elo', 'elo_band'])


def already_collected_ids():
    """player_ids already in the raw CSV (resume / no duplicates across checkpoints)."""
    if not os.path.exists(OUT_RAW):
        return set()
    try:
        df = pd.read_csv(OUT_RAW, usecols=['player_id'])
        return set(df['player_id'].astype(str).str.lower())
    except Exception as e:
        logging.warning(f"could not read existing raw CSV: {e}")
        return set()


def append_records(records):
    """Append one player's rows to the raw CSV immediately (incremental write)."""
    exists = os.path.exists(OUT_RAW)
    with open(OUT_RAW, 'a', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=RAW_FIELDS, extrasaction='ignore')
        if not exists:
            w.writeheader()
        for r in records:
            w.writerow(r)
        f.flush()


def rebuild_agg():
    """Regenerate the aggregated CSV from the full raw CSV (all titles so far)."""
    if not os.path.exists(OUT_RAW):
        return
    df = pd.read_csv(OUT_RAW)
    agg = df.groupby(['player_id', 'gender', 'title', 'elo_band',
                      'player_mean_elo', 'time_category']).agg(
        n_games=('player_id', 'size'),
        avg_elo=('player_elo', 'mean'),
        **{ind: (ind, 'mean') for ind in INDICATORS}
    ).reset_index()
    agg.to_csv(OUT_AGG, index=False)


def run_checkpoint(title, quota, delay):
    DM.MAX_MONTHS_SCANNED = MONTHS
    DM.REQUEST_DELAY = delay
    FT.REQUEST_DELAY = delay

    cache = FT.load_fide_cache(FT.FIDE_CACHE)
    done = already_collected_ids()
    logging.info(f"{len(done)} players already in {OUT_RAW} (will skip)")

    usernames = FT.fetch_title_usernames(title)
    time.sleep(delay)
    if not usernames:
        logging.error(f"no usernames for {title}; aborting")
        return
    rng = random.Random(SEED)
    rng.shuffle(usernames)        # reproducible random sampling order

    collected = 0
    band_counts = Counter()
    funnel = Counter()
    band_examples = {b[0]: [] for b in DM.BANDS}
    processed = 0

    for u in usernames:
        if collected >= quota:
            break
        if u.lower() in done:
            continue
        processed += 1

        try:
            r = FT.resolve_open_player(u, title, cache)
        except Exception as e:
            logging.warning(f"  resolve error {u}: {e}")
            funnel['error'] += 1
            continue

        g = r['gender']
        if g == 'female':
            funnel['female_excluded'] += 1
            logging.info(f"  EXCLUDE female: {u} '{r['name']}'")
            continue
        if g == 'unknown':
            funnel['unknown'] += 1
            continue

        # confirmed male -> full pipeline
        try:
            recs, mean_elo, band = DM.process_player(u, title)
        except Exception as e:
            logging.warning(f"  download/analyze error {u}: {e}")
            recs, mean_elo, band = [], None, None
        if not recs:
            funnel['male_no_games'] += 1
            continue

        append_records(recs)
        done.add(u.lower())
        collected += 1
        band_counts[band] += 1
        funnel['male_effective'] += 1
        if len(band_examples[band]) < 5:
            band_examples[band].append(f"{u}({mean_elo:.0f},{len(recs)}g)")
        logging.info(f"  + [{collected}/{quota}] {u} ({title}) '{r['name']}' "
                     f"mean={mean_elo:.0f} band={band} games={len(recs)}")
        time.sleep(delay)

    rebuild_agg()

    stop_reason = ("quota met" if collected >= quota
                   else "title list exhausted (SHORT of quota)")
    print("\n" + "=" * 68)
    print(f"CHECKPOINT REPORT — {title}  (target {quota})")
    print("=" * 68)
    print(f"Stop reason         : {stop_reason}")
    print(f"Candidates processed: {processed}")
    print(f"\n1. Effective {title} males collected: {collected} / {quota}")
    print("\n2. Elo-band distribution of those males:")
    for name, _, _ in DM.BANDS:
        c = band_counts[name]
        if c:
            ex = ", ".join(band_examples[name])
            print(f"     {name:<12} {c:>4}   e.g. {ex}")
        else:
            print(f"     {name:<12} {c:>4}")
    print("\n3. FIDE gender / yield funnel (this checkpoint):")
    for k in ['male_effective', 'male_no_games', 'female_excluded', 'unknown', 'error']:
        print(f"     {k:<18}: {funnel[k]}")
    fem = funnel['female_excluded']
    print(f"\n   -> {fem} FIDE-confirmed FEMALE candidate(s) EXCLUDED "
          f"(zero-tolerance rule).")
    if collected < quota:
        print(f"\n*** {title} came up SHORT ({collected}/{quota}). Your call on how to make up the gap.")
    print(f"\nData appended to {OUT_RAW}; agg rebuilt to {OUT_AGG}.")
    print(">>> CHECKPOINT COMPLETE — awaiting approval before the next title. <<<")


def main():
    ap = argparse.ArgumentParser(description="Male title-quota collection (one checkpoint per title)")
    ap.add_argument('--title', required=True, choices=list(TITLE_QUOTAS),
                    help="Which title to collect this checkpoint.")
    ap.add_argument('--quota', type=int, default=None,
                    help="Override the default quota for this title.")
    ap.add_argument('--delay', type=float, default=DEFAULT_DELAY)
    args = ap.parse_args()
    quota = args.quota if args.quota is not None else TITLE_QUOTAS[args.title]
    run_checkpoint(args.title, quota, args.delay)


if __name__ == "__main__":
    main()
