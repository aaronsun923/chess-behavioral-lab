"""
==============================================================================
download_and_analyze_male.py  —  Male side, Elo-stratified (needs internet)
==============================================================================
Builds the MALE half of the study, stratified to match the female side's real
Elo distribution (computed with the same "mean game rating per player" ruler).

PIPELINE per candidate (open titles only: GM/IM/FM/CM/NM):
  1. Resolve gender via fetch_titled_players.resolve_open_player
       Chess.com real name -> FIDE FTS (exact, then prefix fallback) -> sex.
     KEEP ONLY sex == 'M'. Women (e.g. open-GM holders Hou Yifan, Lei Tingjie)
     and unverifiable players are excluded. Gender logic is NEVER loosened.
  2. For confirmed males, download the last 12 months of games, filter
       (rated, rules=='chess', time_class in {bullet,blitz,rapid}), and run the
       UNCHANGED 11-indicator pipeline (chess_pipeline_v2.analyze_game).
  3. Bin the player by MEAN game rating (mean of player_elo across analyzed
       games). effective = >=1 analyzed game.

STRATIFICATION (to female proportions, total ~1000):
       1000-1499: 69    1500-1999: 309    2000-2499: 540    2500+: 82

ENUMERATION STRATEGY:
  - Titles processed weak->strong (NM,CM,FM,IM,GM) so the sparse low band gets
    its best shot from weaker titles first, and the GM flood is deferred.
  - Router: once a band is full, a confirmed male whose FIDE rating is clearly
    too high to land in any still-open band has his (expensive) game download
    skipped. Conservative margin (400) — never skips anyone who could plausibly
    fill an open band. Saves hours; does NOT affect gender.
  - Stall guard: if STALL_LIMIT consecutive candidates add nothing to an open
    band, stop and report (graceful give-up for an unfillable band — NOT a
    reason to loosen gender or pad numbers).

OUTPUT: analysis_dataset_male_raw.csv, analysis_dataset_male_agg.csv
Etiquette: 1.0s delays, checkpoint every 200 candidates, try/except per player,
reuse fide_cache.csv.
==============================================================================
"""

import io
import time
import logging
import argparse
from collections import Counter

import requests
import chess
import chess.pgn
import pandas as pd

from chess_pipeline_v2 import analyze_game
import fetch_titled_players as FT

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

HEADERS = FT.HEADERS
REQUEST_DELAY = 1.0

# --- mirror the female-side filters EXACTLY for comparability ---
MAX_GAMES_PER_PLAYER = 100
MIN_PLAYER_RATING = 1000
MAX_PLAYER_RATING = 4000
ALLOWED_TIME_CLASSES = {'bullet', 'blitz', 'rapid'}
# Female side scanned 18 months; user specified 12 for males. With the 100-game
# cap, active titled players hit the cap well inside 12mo, so this rarely binds.
MAX_MONTHS_SCANNED = 12

# Weak -> strong: fill the sparse low band first; defer the GM flood.
TITLE_ORDER = ['NM', 'CM', 'FM', 'IM', 'GM']

BANDS = [('1000-1499', 1000, 1500), ('1500-1999', 1500, 2000),
         ('2000-2499', 2000, 2500), ('2500+', 2500, float('inf'))]
TARGETS = {'1000-1499': 69, '1500-1999': 309, '2000-2499': 540, '2500+': 82}
BAND_CEILING = {'1000-1499': 1500, '1500-1999': 2000, '2000-2499': 2500}  # exclusive
ROUTER_MARGIN = 400      # Chess.com mean assumed >= FIDE_rating - margin
STALL_LIMIT = 1500       # consecutive no-progress candidates before giving up

OUT_RAW = 'analysis_dataset_male_raw.csv'
OUT_AGG = 'analysis_dataset_male_agg.csv'

INDICATORS = ['exchange_rate', 'tension_duration', 'avg_mobility',
              'center_control_score', 'advanced_pawn_push_rate',
              'pawn_storm_indicator', 'castling_ply', 'king_shelter_score',
              'forcing_move_rate', 'reactive_move_rate']


def band_of(rating):
    for name, lo, hi in BANDS:
        if lo <= rating < hi:
            return name
    return None


def can_skip_download(fide_rating, open_bands):
    """Skip the game download ONLY if the player is clearly too strong to land
    in any still-open band (conservative). Never skips when the top band is
    open (it accepts arbitrarily high ratings)."""
    try:
        r = float(fide_rating)
    except (TypeError, ValueError):
        return False
    if r <= 0 or '2500+' in open_bands:
        return False
    open_ceilings = [BAND_CEILING[b] for b in open_bands if b in BAND_CEILING]
    if not open_ceilings:
        return False
    return (r - ROUTER_MARGIN) >= max(open_ceilings)


def get_json(url):
    resp = requests.get(url, headers=HEADERS, timeout=120)
    resp.raise_for_status()
    return resp.json()


def iter_recent_games(username):
    """Yield raw Chess.com game dicts, newest months first, politely."""
    try:
        archives = get_json(
            f"https://api.chess.com/pub/player/{username}/games/archives"
        ).get('archives', [])
    except Exception as e:
        logging.warning(f"archives fetch failed for {username}: {e}")
        return
    for url in reversed(archives[-MAX_MONTHS_SCANNED:]):
        time.sleep(REQUEST_DELAY)
        try:
            games = get_json(url).get('games', [])
        except Exception as e:
            logging.warning(f"month fetch failed ({url}): {e}")
            continue
        for g in reversed(games):
            yield g


def process_player(username, title):
    """Download + filter + analyze one male's games. Returns (records, mean_elo,
    band). Records are annotated with player_mean_elo and elo_band."""
    records = []
    for g in iter_recent_games(username):
        if len(records) >= MAX_GAMES_PER_PLAYER:
            break
        if not g.get('rated'):
            continue
        if g.get('rules') != 'chess':
            continue
        time_class = g.get('time_class')
        if time_class not in ALLOWED_TIME_CLASSES:
            continue

        wu = (g.get('white', {}).get('username') or '').lower()
        bu = (g.get('black', {}).get('username') or '').lower()
        if username.lower() == wu:
            color, side = chess.WHITE, 'white'
        elif username.lower() == bu:
            color, side = chess.BLACK, 'black'
        else:
            continue

        player_rating = g.get(side, {}).get('rating')
        if player_rating is None or not (MIN_PLAYER_RATING <= player_rating <= MAX_PLAYER_RATING):
            continue

        pgn = g.get('pgn')
        if not pgn:
            continue
        game = chess.pgn.read_game(io.StringIO(pgn))
        if game is None:
            continue
        metrics = analyze_game(game, color)
        if metrics is None:
            continue

        records.append({
            'player_id': username,
            'gender': 'male',
            'title': title,
            'player_elo': player_rating,
            'time_category': time_class,
            'eco': game.headers.get('ECO', ''),
            'color': side,
            'url': g.get('url', ''),
            **metrics,
        })

    if not records:
        return [], None, None
    mean_elo = sum(r['player_elo'] for r in records) / len(records)
    band = band_of(mean_elo)
    for r in records:
        r['player_mean_elo'] = round(mean_elo, 1)
        r['elo_band'] = band
    return records, mean_elo, band


def write_outputs(all_records):
    if not all_records:
        return
    df = pd.DataFrame(all_records)
    df.to_csv(OUT_RAW, index=False)
    agg = df.groupby(['player_id', 'gender', 'elo_band', 'player_mean_elo',
                      'time_category']).agg(
        n_games=('player_id', 'size'),
        avg_elo=('player_elo', 'mean'),
        **{ind: (ind, 'mean') for ind in INDICATORS}
    ).reset_index()
    agg.to_csv(OUT_AGG, index=False)


def log_progress(tag, processed, band_counts, funnel):
    bands = "  ".join(f"{b}:{band_counts[b]}/{TARGETS[b]}"
                      f"{'✓' if band_counts[b] >= TARGETS[b] else ''}" for b in TARGETS)
    logging.info(f"[{tag}] processed={processed}  bands[ {bands} ]  "
                 f"funnel={dict(funnel)}")


def final_report(processed, band_counts, funnel, stop_reason):
    print("\n=== MALE COLLECTION REPORT ===")
    print(f"Stop reason: {stop_reason}")
    print(f"Total candidates processed: {processed}")
    eff = funnel.get('male_effective', 0)
    print("\nGender funnel (of processed candidates):")
    for k in ['male_effective', 'male_no_games', 'male_skipped_full_band',
              'female', 'unknown', 'error']:
        v = funnel.get(k, 0)
        print(f"  {k:24s}: {v}")
    resolved_male = (funnel.get('male_effective', 0) + funnel.get('male_no_games', 0)
                     + funnel.get('male_skipped_full_band', 0))
    if processed:
        print(f"\n  resolved-male rate: {resolved_male}/{processed} = {resolved_male/processed:.1%}")
        print(f"  effective-male rate (≥1 game / processed): {eff}/{processed} = {eff/processed:.1%}")
    print("\nPer-band effective males vs target:")
    print(f"  {'band':<12}{'effective':>10}{'target':>8}{'status':>10}")
    for b in TARGETS:
        c = band_counts[b]
        status = 'FULL' if c >= TARGETS[b] else 'SHORT'
        print(f"  {b:<12}{c:>10}{TARGETS[b]:>8}{status:>10}")
    short = [b for b in TARGETS if band_counts[b] < TARGETS[b]]
    if short:
        print(f"\n*** SHORT bands (your call — accept fewer, or merge bands): {short}")
        print("*** Gender determination was NOT loosened to chase targets.")


def main():
    global REQUEST_DELAY, MAX_GAMES_PER_PLAYER, MAX_MONTHS_SCANNED
    ap = argparse.ArgumentParser(description="Male-side Elo-stratified collection")
    ap.add_argument('--delay', type=float, default=REQUEST_DELAY)
    ap.add_argument('--max-games-per-player', type=int, default=MAX_GAMES_PER_PLAYER)
    ap.add_argument('--max-months', type=int, default=MAX_MONTHS_SCANNED)
    ap.add_argument('--max-candidates', type=int, default=None,
                    help="Smoke-test cap on candidates processed.")
    ap.add_argument('--titles', nargs='+', default=TITLE_ORDER)
    args = ap.parse_args()
    REQUEST_DELAY = args.delay
    MAX_GAMES_PER_PLAYER = args.max_games_per_player
    MAX_MONTHS_SCANNED = args.max_months
    FT.REQUEST_DELAY = args.delay   # keep fetch_titled_players' Chess.com calls in sync

    cache = FT.load_fide_cache(FT.FIDE_CACHE)
    band_counts = {b: 0 for b in TARGETS}
    funnel = Counter()
    all_records = []
    seen = set()
    processed = 0
    stall = 0
    stop_reason = "all title lists exhausted"
    stop = False

    for title in args.titles:
        if stop:
            break
        usernames = FT.fetch_title_usernames(title)
        time.sleep(REQUEST_DELAY)
        for u in usernames:
            if stop:
                break
            if u in seen:
                continue
            seen.add(u)

            if all(band_counts[b] >= TARGETS[b] for b in TARGETS):
                stop, stop_reason = True, "all bands met"
                break
            if args.max_candidates and processed >= args.max_candidates:
                stop, stop_reason = True, "max-candidates cap (smoke test)"
                break

            processed += 1
            open_bands = [b for b in TARGETS if band_counts[b] < TARGETS[b]]

            # ---- gender resolution (cached) ----
            try:
                r = FT.resolve_open_player(u, title, cache)
            except Exception as e:
                logging.warning(f"  resolve error {u}: {e}")
                funnel['error'] += 1
                stall += 1
                continue

            if r['gender'] != 'male':
                funnel[r['gender']] += 1          # 'female' or 'unknown'
                stall += 1
            else:
                # router: skip download if clearly too strong for any open band
                if can_skip_download(r.get('fide_rating'), open_bands):
                    funnel['male_skipped_full_band'] += 1
                    stall += 1
                else:
                    try:
                        recs, mean_elo, band = process_player(u, title)
                    except Exception as e:
                        logging.warning(f"  download/analyze error {u}: {e}")
                        recs, band = [], None
                    if not recs:
                        funnel['male_no_games'] += 1
                        stall += 1
                    else:
                        all_records.extend(recs)
                        band_counts[band] += 1
                        funnel['male_effective'] += 1
                        logging.info(f"  + {u} ({title}) mean_elo={mean_elo:.0f} "
                                     f"band={band} games={len(recs)}")
                        stall = 0 if band in open_bands else stall + 1
                    time.sleep(REQUEST_DELAY)

            if processed % 200 == 0:
                write_outputs(all_records)
                log_progress(f"checkpoint after {processed}", processed, band_counts, funnel)

            if stall >= STALL_LIMIT:
                stop, stop_reason = True, f"stall guard ({STALL_LIMIT} no-progress candidates)"
                break

    write_outputs(all_records)
    log_progress("FINAL", processed, band_counts, funnel)
    final_report(processed, band_counts, funnel, stop_reason)
    if all_records:
        print(f"\nWrote {len(all_records)} game records "
              f"({funnel.get('male_effective',0)} effective males) to {OUT_RAW} / {OUT_AGG}")


if __name__ == "__main__":
    main()
