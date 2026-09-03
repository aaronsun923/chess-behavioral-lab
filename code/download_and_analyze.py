"""
==============================================================================
download_and_analyze.py  —  Chess.com edition (needs internet)
==============================================================================
Given the verified-gender roster, downloads each player's games from Chess.com
and runs the UNCHANGED 11-indicator pipeline, producing the analysis dataset.

INPUT:  titled_players_roster.csv  (from fetch_titled_players.py)
OUTPUT: analysis_dataset_raw.csv   (one row per player-game)
        analysis_dataset_agg.csv   (one row per player x time_category)

KEY ADAPTATIONS vs the old Lichess version:
  - Games come from Chess.com monthly archives:
        GET /pub/player/{u}/games/archives          -> list of month URLs
        GET /pub/player/{u}/games/{YYYY}/{MM}        -> {"games":[{...}]}
  - Filtering uses the archive JSON fields directly:
        rated == True      (drop unrated)
        rules == 'chess'   (drop variants: chess960, bughouse, etc.)
  - time_category comes STRAIGHT FROM Chess.com's per-game `time_class`
    field (bullet/blitz/rapid/daily). We do NOT parse the TimeControl
    string — the pipeline's categorize_time_control assumes Lichess's
    always-present "base+inc" format and returns 'unknown' for Chess.com's
    no-increment games (e.g. "180", "60").
  - The 11 indicators are computed by chess_pipeline_v2.analyze_game, which is
    imported untouched.

Only players with gender in {female, male} are processed (others excluded).
Run serial + polite; Chess.com requires a descriptive User-Agent.
==============================================================================
"""

import requests
import chess
import chess.pgn
import pandas as pd
import io
import time
import logging
import argparse
from pathlib import Path

# 11-indicator logic imported UNCHANGED. We deliberately do NOT import
# categorize_time_control — time_category comes from Chess.com's time_class.
from chess_pipeline_v2 import analyze_game

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

ROSTER_CSV = "titled_players_roster.csv"
OUTPUT_RAW = "analysis_dataset_raw.csv"
OUTPUT_AGG = "analysis_dataset_agg.csv"

# Chess.com etiquette
USER_AGENT = "chess-gender-study/1.0 (research; contact aaronsun923@gmail.com)"
HEADERS = {"User-Agent": USER_AGENT}
REQUEST_DELAY = 1.0          # polite delay between requests

MAX_GAMES_PER_PLAYER = 100   # cap on ANALYZED games kept per player
MAX_MONTHS_SCANNED = 18      # how many recent monthly archives to walk back

# --- METHODOLOGY KNOBS (adjustable; flagged in the adaptation notes) ---
# Original Lichess script used MIN_ELO=1200, MAX_ELO=2400. That band is
# calibrated for a general population and would discard nearly all titled
# players (whose blitz/bullet ratings routinely exceed 2400). We relax it:
# keep a low floor to drop provisional/garbage ratings, no restrictive cap.
MIN_PLAYER_RATING = 1000
MAX_PLAYER_RATING = 4000
# Chess.com 'daily' = correspondence chess (days per move); the original study
# excluded correspondence. We keep real-time classes only.
ALLOWED_TIME_CLASSES = {'bullet', 'blitz', 'rapid'}


def get_json(url):
    resp = requests.get(url, headers=HEADERS, timeout=120)
    resp.raise_for_status()
    return resp.json()


def get_archive_urls(username):
    """Return monthly archive URLs (oldest -> newest)."""
    try:
        return get_json(f"https://api.chess.com/pub/player/{username}/games/archives").get('archives', [])
    except Exception as e:
        logging.warning(f"archives fetch failed for {username}: {e}")
        return []


def iter_recent_games(username):
    """Yield raw Chess.com game dicts, newest months first, politely."""
    archives = get_archive_urls(username)
    for url in reversed(archives[-MAX_MONTHS_SCANNED:]):
        time.sleep(REQUEST_DELAY)
        try:
            games = get_json(url).get('games', [])
        except Exception as e:
            logging.warning(f"month fetch failed ({url}): {e}")
            continue
        # within a month, process most recent first
        for g in reversed(games):
            yield g


def process_player(username, gender, title):
    """Download + filter + analyze one player's games. Returns list of records."""
    records = []
    for g in iter_recent_games(username):
        if len(records) >= MAX_GAMES_PER_PLAYER:
            break

        # ---- filters straight from archive JSON ----
        if not g.get('rated'):
            continue
        if g.get('rules') != 'chess':            # drop variants
            continue
        time_class = g.get('time_class')
        if time_class not in ALLOWED_TIME_CLASSES:   # drop daily/correspondence
            continue

        # which color is our player?
        wu = (g.get('white', {}).get('username') or '').lower()
        bu = (g.get('black', {}).get('username') or '').lower()
        if username.lower() == wu:
            color, side = chess.WHITE, 'white'
        elif username.lower() == bu:
            color, side = chess.BLACK, 'black'
        else:
            continue

        # player's own rating this game (from JSON, not from PGN header)
        player_rating = g.get(side, {}).get('rating')
        if player_rating is None or not (MIN_PLAYER_RATING <= player_rating <= MAX_PLAYER_RATING):
            continue

        pgn = g.get('pgn')
        if not pgn:
            continue
        game = chess.pgn.read_game(io.StringIO(pgn))
        if game is None:
            continue

        metrics = analyze_game(game, color)   # 11 indicators, UNCHANGED logic
        if metrics is None:
            continue

        records.append({
            'player_id': username,
            'gender': gender,
            'title': title,
            'player_elo': player_rating,
            'time_category': time_class,        # <-- straight from Chess.com
            'eco': game.headers.get('ECO', ''),
            'color': side,
            'url': g.get('url', ''),
            **metrics,
        })
    return records


def main():
    global REQUEST_DELAY, MAX_GAMES_PER_PLAYER, MAX_MONTHS_SCANNED
    ap = argparse.ArgumentParser(description="Download Chess.com games + run 11-indicator pipeline")
    ap.add_argument('--roster', default=ROSTER_CSV)
    ap.add_argument('--gender', choices=['female', 'male'], default=None,
                    help="Restrict to one gender (pilot use).")
    ap.add_argument('--max-players', type=int, default=None,
                    help="Process at most N usable players (pilot use).")
    ap.add_argument('--out-raw', default=OUTPUT_RAW)
    ap.add_argument('--out-agg', default=OUTPUT_AGG)
    ap.add_argument('--delay', type=float, default=REQUEST_DELAY,
                    help="Seconds between requests (default 1.0).")
    ap.add_argument('--max-games-per-player', type=int, default=MAX_GAMES_PER_PLAYER)
    ap.add_argument('--max-months', type=int, default=MAX_MONTHS_SCANNED)
    args = ap.parse_args()

    # apply CLI overrides to the module-level knobs used by the fetch helpers
    REQUEST_DELAY = args.delay
    MAX_GAMES_PER_PLAYER = args.max_games_per_player
    MAX_MONTHS_SCANNED = args.max_months

    if not Path(args.roster).exists():
        logging.error(f"{args.roster} not found. Run fetch_titled_players.py first.")
        return

    roster = pd.read_csv(args.roster)
    usable = roster[roster['gender'].isin(['female', 'male'])]
    if args.gender:
        usable = usable[usable['gender'] == args.gender]
    if args.max_players:
        usable = usable.head(args.max_players)
    usable = usable.reset_index(drop=True)
    logging.info(f"Processing {len(usable)} players "
                 f"({(usable['gender']=='female').sum()} F, "
                 f"{(usable['gender']=='male').sum()} M)")

    all_records = []
    for idx, row in usable.iterrows():
        username = row['username']
        logging.info(f"[{idx+1}/{len(usable)}] {username} ({row['gender']})")
        try:
            recs = process_player(username, row['gender'], row['title'])
        except Exception as e:
            logging.warning(f"  skipped {username}: unexpected error {e}")
            recs = []
        all_records.extend(recs)
        logging.info(f"  -> {len(recs)} games analyzed")
        time.sleep(REQUEST_DELAY)

        # checkpoint: persist raw records periodically so a long run isn't lost
        if (idx + 1) % 200 == 0 and all_records:
            pd.DataFrame(all_records).to_csv(args.out_raw, index=False)
            logging.info(f"  [checkpoint] wrote {len(all_records)} records "
                         f"after {idx+1} players")

    if not all_records:
        logging.error("No games analyzed.")
        return

    df = pd.DataFrame(all_records)
    df.to_csv(args.out_raw, index=False)
    logging.info(f"Wrote {len(df)} player-game records to {args.out_raw}")

    indicators = ['exchange_rate', 'tension_duration', 'avg_mobility',
                  'center_control_score', 'advanced_pawn_push_rate',
                  'pawn_storm_indicator', 'castling_ply', 'king_shelter_score',
                  'forcing_move_rate', 'reactive_move_rate']

    agg = df.groupby(['player_id', 'gender', 'time_category']).agg(
        n_games=('player_id', 'size'),
        avg_elo=('player_elo', 'mean'),
        **{ind: (ind, 'mean') for ind in indicators}
    ).reset_index()
    agg.to_csv(args.out_agg, index=False)
    logging.info(f"Wrote aggregated dataset to {args.out_agg}")

    print("\n=== DATASET SUMMARY ===")
    print(f"Player-game records: {len(df)}")
    print(f"Unique players: {df['player_id'].nunique()}")
    print(f"Gender (unique players): {df.groupby('gender')['player_id'].nunique().to_dict()}")
    print(f"Time categories: {df['time_category'].value_counts().to_dict()}")
    print(f"Position types: {df['position_type'].value_counts().to_dict()}")


if __name__ == "__main__":
    main()
