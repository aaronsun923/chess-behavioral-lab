"""
==============================================================================
probe_male_titled.py  —  Stage 0 PROBE (needs internet)
==============================================================================
Diagnostic ONLY. Does NOT write the analysis dataset. Purpose: before the real
Stage-1 collection of real-FIDE-titled males (GM/IM/FM/CM), measure where each
title's players actually land on the Chess.com Elo ladder, so the user can
approve the Stage-1 plan.

Per title in {GM, IM, FM, CM}:
  1. Enumerate the full Chess.com title list, randomly sample SAMPLE players
     (fixed seed -> reproducible).
  2. Resolve sex via FIDE (fetch_titled_players.resolve_open_player): Chess.com
     real name -> FIDE FTS -> sex. FIDE-confirmed FEMALES ARE EXCLUDED (the same
     hard ethical line as the main study, e.g. Lei Tingjie). 'unknown' (no real
     name / no FIDE match / ambiguous) is also set aside (would be excluded in
     the real study).
  3. For confirmed males only, download the last MONTHS months of games, filter
     to rated standard chess in {bullet,blitz,rapid} (daily EXCLUDED), and take
     the MEAN game rating = the binning ruler agreed for this study.
  4. Bin into 1000-1499 / 1500-1999 / 2000-2499 / 2500+.

OUTPUT: a per-title band table + a resolution funnel, printed to stdout and
written to probe_male_titled_results.csv (per-player rows, for audit).
==============================================================================
"""

import csv
import time
import random
import logging
from collections import Counter, defaultdict

import requests

import fetch_titled_players as FT

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

HEADERS = FT.HEADERS
REQUEST_DELAY = 1.0
ALLOWED_TIME_CLASSES = {'bullet', 'blitz', 'rapid'}   # daily EXCLUDED
MONTHS = 3
SAMPLE = 20
TITLES = ['GM', 'IM', 'FM', 'CM']
SEED = 42

BANDS = [('1000-1499', 1000, 1500), ('1500-1999', 1500, 2000),
         ('2000-2499', 2000, 2500), ('2500+', 2500, float('inf'))]
BAND_NAMES = [b[0] for b in BANDS]

OUT_CSV = 'probe_male_titled_results.csv'


def band_of(rating):
    for name, lo, hi in BANDS:
        if lo <= rating < hi:
            return name
    return None


def get_json(url):
    resp = requests.get(url, headers=HEADERS, timeout=120)
    resp.raise_for_status()
    return resp.json()


def mean_rating_last_months(username, months=MONTHS):
    """Mean Chess.com rating over the last `months` of rated standard
    blitz/bullet/rapid games. Returns (mean, n_games)."""
    try:
        archives = get_json(
            f"https://api.chess.com/pub/player/{username}/games/archives"
        ).get('archives', [])
    except Exception as e:
        logging.warning(f"  archives fetch failed for {username}: {e}")
        return None, 0
    ratings = []
    for url in reversed(archives[-months:]):
        time.sleep(REQUEST_DELAY)
        try:
            games = get_json(url).get('games', [])
        except Exception as e:
            logging.warning(f"  month fetch failed ({url}): {e}")
            continue
        for g in games:
            if not g.get('rated'):
                continue
            if g.get('rules') != 'chess':
                continue
            if g.get('time_class') not in ALLOWED_TIME_CLASSES:
                continue
            wu = (g.get('white', {}).get('username') or '').lower()
            bu = (g.get('black', {}).get('username') or '').lower()
            if username.lower() == wu:
                side = 'white'
            elif username.lower() == bu:
                side = 'black'
            else:
                continue
            rt = g.get(side, {}).get('rating')
            if rt:
                ratings.append(rt)
    if not ratings:
        return None, 0
    return sum(ratings) / len(ratings), len(ratings)


def main():
    random.seed(SEED)
    cache = FT.load_fide_cache(FT.FIDE_CACHE)
    FT.REQUEST_DELAY = REQUEST_DELAY

    band_table = {t: Counter() for t in TITLES}     # title -> band -> n (males)
    funnel = {t: Counter() for t in TITLES}          # title -> outcome -> n
    rows = []

    for title in TITLES:
        usernames = FT.fetch_title_usernames(title)
        time.sleep(REQUEST_DELAY)
        if not usernames:
            logging.error(f"no usernames for {title}; skipping")
            continue
        sample = random.sample(usernames, min(SAMPLE, len(usernames)))
        logging.info(f"=== {title}: sampled {len(sample)} of {len(usernames)} ===")

        for i, u in enumerate(sample):
            try:
                r = FT.resolve_open_player(u, title, cache)
            except Exception as e:
                logging.warning(f"  resolve error {u}: {e}")
                funnel[title]['error'] += 1
                rows.append([title, u, '', 'error', '', '', 0])
                continue

            g = r['gender']
            name = r['name']

            if g == 'female':
                funnel[title]['female_excluded'] += 1
                logging.info(f"  [{i+1}/{len(sample)}] {u} '{name}' -> FEMALE (EXCLUDED)")
                rows.append([title, u, name, 'female_excluded', '', '', 0])
                continue
            if g == 'unknown':
                funnel[title]['unknown'] += 1
                logging.info(f"  [{i+1}/{len(sample)}] {u} '{name}' -> unknown (set aside)")
                rows.append([title, u, name, 'unknown', '', '', 0])
                continue

            # confirmed male -> measure Elo
            mean, n = mean_rating_last_months(u)
            time.sleep(REQUEST_DELAY)
            if mean is None:
                funnel[title]['male_no_games'] += 1
                logging.info(f"  [{i+1}/{len(sample)}] {u} '{name}' -> MALE, no games")
                rows.append([title, u, name, 'male_no_games', '', '', 0])
                continue
            b = band_of(mean)
            band_table[title][b] += 1
            funnel[title]['male_effective'] += 1
            logging.info(f"  [{i+1}/{len(sample)}] {u} '{name}' -> MALE "
                         f"mean={mean:.0f} band={b} ({n} games)")
            rows.append([title, u, name, 'male', b, round(mean, 1), n])

    # ---- write per-player audit csv ----
    with open(OUT_CSV, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['title', 'username', 'name', 'outcome', 'band', 'mean_elo', 'n_games'])
        w.writerows(rows)

    # ---- report ----
    print("\n" + "=" * 70)
    print("STAGE 0 PROBE RESULTS  (sample=%d per title, last %d months, seed=%d)"
          % (SAMPLE, MONTHS, SEED))
    print("=" * 70)
    print("\nBand distribution of FIDE-CONFIRMED MALES:")
    print(f"  {'':4s} {'1000-1499':>12} {'1500-1999':>12} {'2000-2499':>12} {'2500+':>10}")
    for t in TITLES:
        bt = band_table[t]
        print(f"  {t:4s} "
              f"{bt['1000-1499']:>12} {bt['1500-1999']:>12} "
              f"{bt['2000-2499']:>12} {bt['2500+']:>10}")

    print("\nCompact form:")
    for t in TITLES:
        bt = band_table[t]
        print(f"  {t}: 1000-1499 [{bt['1000-1499']}] | 1500-1999 [{bt['1500-1999']}] "
              f"| 2000-2499 [{bt['2000-2499']}] | 2500+ [{bt['2500+']}]")

    print("\nResolution funnel (of %d sampled per title):" % SAMPLE)
    keys = ['male_effective', 'male_no_games', 'female_excluded', 'unknown', 'error']
    print(f"  {'':4s} " + " ".join(f"{k:>16}" for k in keys))
    for t in TITLES:
        fn = funnel[t]
        print(f"  {t:4s} " + " ".join(f"{fn[k]:>16}" for k in keys))

    print(f"\nPer-player audit written to {OUT_CSV}")
    print("\n>>> PROBE COMPLETE — awaiting user review before Stage 1. <<<")


if __name__ == "__main__":
    main()
