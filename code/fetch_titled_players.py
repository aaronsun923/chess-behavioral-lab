"""
==============================================================================
fetch_titled_players.py  —  Chess.com edition (needs internet)
==============================================================================
Builds the verified-gender player roster for the study from Chess.com, and
resolves the gender of OPEN-title players against the FIDE list.

WHY CHESS.COM: Lichess removed its titled-players API (the /api/player/titled
endpoint now 404s), so all-titled enumeration is no longer possible there.
Chess.com's public Published-Data API still exposes a working per-title
enumeration endpoint, which solves the roster problem.

GENDER RESOLUTION (the ethical hard line is unchanged):
  - Women's titles (WGM/WIM/WFM/WCM/WNM) -> female, with certainty, no FIDE.
  - Open titles   (GM/IM/FM/CM/NM)       -> resolved against the FIDE list by
                    the player's REAL NAME. NEVER guessed from username/style.

FIDE source — path 1 (the online FTS API):
  We query the community FIDE mirror at fide-players.fly.dev (a Datasette
  instance wrapping the full ~1.5M-row FIDE standard list, weekly-updated,
  with a real `sex` M/F field). Lookups go through the indexed full-text
  search endpoint (?_search=...), which is the only fast path; raw
  `WHERE name=...` scans time out server-side.

  - For each open-title player we fetch their Chess.com profile to get the
    real `name` (+ ISO-2 country), then FTS-search the FIDE list.
  - DISAMBIGUATION: among same-name candidates, prefer the row that holds the
    matching open title (strong signal), with country as a tiebreaker. If the
    best-scoring candidates disagree on sex, we mark 'unknown' and EXCLUDE —
    we never guess.
  - SAFETY: only sex == 'M' enters the male queue. Open-title women (e.g.
    Hou Yifan, Judit Polgar, Ju Wenjun, Koneru Humpy all hold open GM titles)
    resolve to 'female' and are correctly kept OUT of the male group.
  - CACHE: every resolved name -> {sex, title, w_title, fideid, ...} is written
    to fide_cache.csv, both to avoid re-querying the external API and as a
    reproducible record for the paper.

OUTPUT: titled_players_roster.csv with columns
        username, title, gender, source, name, fideid, fide_sex
==============================================================================
"""

import requests
import csv
import time
import logging
import argparse
import os
import re
import unicodedata

# Gender logic + name normalization are imported, not redefined —
# chess_pipeline_v2 is untouched.
from chess_pipeline_v2 import (
    gender_from_title, normalize_name, WOMENS_TITLES, OPEN_TITLES,
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

# ---------------------------------------------------------------------------
# Endpoints / files
# ---------------------------------------------------------------------------
CHESSCOM_TITLED_URL = "https://api.chess.com/pub/titled/{title}"
CHESSCOM_PROFILE_URL = "https://api.chess.com/pub/player/{username}"
FIDE_FTS_URL = "https://fide-players.fly.dev/players/players.json"
# Raw SQL endpoint — needed for prefix (tok*) FTS, which Datasette's _search
# strips. We MATCH against the indexed FTS table, so it stays fast.
FIDE_SQL_URL = "https://fide-players.fly.dev/players/-/query.json"
_FIDE_MATCH_SQL = ("select p.fideid, p.name, p.sex, p.title, p.w_title, "
                   "p.o_title, p.country, p.rating from players p "
                   "join players_fts f on p.rowid = f.rowid "
                   "where players_fts match :q limit :lim")

OUTPUT_ROSTER = "titled_players_roster.csv"
FIDE_CACHE = "fide_cache.csv"

# Chess.com etiquette: identify yourself, go serial, be polite.
USER_AGENT = "chess-gender-study/1.0 (research; contact aaronsun923@gmail.com)"
HEADERS = {"User-Agent": USER_AGENT}
REQUEST_DELAY = 1.0   # seconds between Chess.com requests
FIDE_DELAY = 0.6      # seconds between FIDE FTS requests (be gentle on fly.dev)

# Explicit, deterministic order (sets are unordered). WGM first so that a
# pilot taking the first N females gets WGM holders.
ALL_TITLES = ['WGM', 'WIM', 'WFM', 'WCM', 'WNM', 'GM', 'IM', 'FM', 'CM', 'NM']
assert set(ALL_TITLES) == WOMENS_TITLES | OPEN_TITLES, "title list drifted from pipeline"

ROSTER_FIELDS = ['username', 'title', 'gender', 'source', 'name', 'fideid', 'fide_sex']
FIDE_CACHE_FIELDS = ['query_name', 'open_title', 'status', 'sex',
                     'fide_name', 'fide_title', 'w_title', 'o_title',
                     'fideid', 'country', 'fide_rating']

# Chess.com country codes are ISO 3166-1 alpha-2; FIDE uses 3-letter (IOC-ish)
# codes. Country is only a *tiebreaker* (a match adds score; a mismatch never
# penalizes), so partial coverage is harmless — unmapped codes just give no
# country signal.
ISO2_TO_FIDE = {
    'US': 'USA', 'NO': 'NOR', 'FR': 'FRA', 'CN': 'CHN', 'HU': 'HUN',
    'IN': 'IND', 'RU': 'RUS', 'DE': 'GER', 'ES': 'ESP', 'IT': 'ITA',
    'NL': 'NED', 'PL': 'POL', 'UA': 'UKR', 'AM': 'ARM', 'AZ': 'AZE',
    'GE': 'GEO', 'GB': 'ENG', 'SE': 'SWE', 'CZ': 'CZE', 'HR': 'CRO',
    'RS': 'SRB', 'BG': 'BUL', 'RO': 'ROU', 'GR': 'GRE', 'TR': 'TUR',
    'IR': 'IRI', 'IL': 'ISR', 'EG': 'EGY', 'PH': 'PHI', 'VN': 'VIE',
    'ID': 'INA', 'AR': 'ARG', 'BR': 'BRA', 'PE': 'PER', 'CU': 'CUB',
    'MX': 'MEX', 'CA': 'CAN', 'AU': 'AUS', 'NZ': 'NZL', 'ZA': 'RSA',
    'FI': 'FIN', 'DK': 'DEN', 'IS': 'ISL', 'BE': 'BEL', 'CH': 'SUI',
    'AT': 'AUT', 'PT': 'POR', 'SK': 'SVK', 'SI': 'SLO', 'LT': 'LTU',
    'LV': 'LAT', 'EE': 'EST', 'BY': 'BLR', 'KZ': 'KAZ', 'UZ': 'UZB',
    'MN': 'MGL', 'JP': 'JPN', 'KR': 'KOR', 'MY': 'MAS', 'SG': 'SGP',
}


# ---------------------------------------------------------------------------
# Chess.com enumeration + profiles
# ---------------------------------------------------------------------------
def fetch_title_usernames(title):
    """Return the full list of usernames holding a given title on Chess.com."""
    url = CHESSCOM_TITLED_URL.format(title=title)
    try:
        resp = requests.get(url, headers=HEADERS, timeout=60)
        resp.raise_for_status()
        players = resp.json().get('players', [])
        logging.info(f"{title}: {len(players)} players")
        return players
    except Exception as e:
        logging.error(f"Failed to fetch title {title}: {e}")
        return []


def fetch_chesscom_profile(username):
    """Fetch a Chess.com profile -> {'name', 'country'(ISO-2), 'title'}.

    The real name is user-supplied and may be absent; if so we cannot resolve
    gender and the player is excluded (never guessed)."""
    url = CHESSCOM_PROFILE_URL.format(username=username)
    for attempt in range(3):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=30)
            if resp.status_code == 429:
                time.sleep(5 * (attempt + 1))
                continue
            resp.raise_for_status()
            d = resp.json()
            cc = (d.get('country') or '').rstrip('/').split('/')[-1].upper()
            return {'name': (d.get('name') or '').strip(),
                    'country': cc,
                    'title': d.get('title', '')}
        except Exception as e:
            logging.warning(f"profile fetch failed for {username}: {e}")
            time.sleep(2 * (attempt + 1))
    return {'name': '', 'country': '', 'title': ''}


# ---------------------------------------------------------------------------
# FIDE FTS lookup + disambiguation
# ---------------------------------------------------------------------------
def _strip_diacritics(s):
    """Fold diacritics so 'Carlsén' -> 'Carlsen' (FIDE FTS index folds too)."""
    return ''.join(c for c in unicodedata.normalize('NFKD', s)
                   if not unicodedata.combining(c))


def _name_tokens(name):
    """Normalized, diacritic-folded token set for name matching."""
    return set(t for t in _strip_diacritics(normalize_name(name)).split() if t)


def _fts_tokens(name):
    """Alphanumeric, diacritic-folded tokens for building an FTS query
    (splits on hyphens/punctuation, unlike _name_tokens)."""
    folded = _strip_diacritics(name).lower()
    return [t for t in re.split(r'[^a-z0-9]+', folded) if t]


def fide_fts_search(name, size=25, prefix=False):
    """Full-text search the FIDE list by name.

    Default (prefix=False): each token is sent as a quoted phrase so
    punctuation/FTS operators in names can't break the query; FTS5 AND-combines
    them, giving precise candidate sets.

    prefix=True: each token (len>=2) becomes an FTS prefix term `tok*`, run via
    the raw SQL MATCH endpoint (Datasette's _search strips the `*`). Used ONLY
    as a fallback when the exact search found nothing, to recover name
    short-forms (e.g. Chess.com "Alex" vs FIDE "Alexandr"). It still AND-combines
    all tokens, and — crucially — the downstream disambiguator's
    'conflicting sex -> unknown' guard is unchanged, so broadening the candidate
    set can never let a woman slip into the male queue: it can only ever turn an
    'unmatched' into a confident same-sex match or leave it 'unknown'."""
    tokens = _fts_tokens(name)
    if not tokens:
        return []

    if prefix:
        parts = ['%s*' % t for t in tokens if len(t) >= 2]
        if not parts:
            return []
        return _fide_sql_match(' '.join(parts), size)

    # exact: quoted phrases via the table _search endpoint (validated path)
    params = {
        '_search': ' '.join('"%s"' % t for t in tokens),
        '_shape': 'array',
        '_size': size,
        '_col': ['fideid', 'name', 'sex', 'title', 'w_title',
                 'o_title', 'country', 'rating'],
    }
    for attempt in range(4):
        try:
            resp = requests.get(FIDE_FTS_URL, params=params, timeout=30)
            if resp.status_code == 429:
                time.sleep(5 * (attempt + 1))
                continue
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, list) else []
        except Exception as e:
            logging.warning(f"FIDE FTS error for '{name}' (try {attempt+1}): {e}")
            time.sleep(2 * (attempt + 1))
    return []


def _fide_sql_match(match_expr, size):
    """Run an FTS5 MATCH expression (supports `tok*` prefixes) via the raw SQL
    endpoint, returning candidate rows. match_expr is built only from
    alphanumeric tokens + '*', so it is a safe FTS5 expression."""
    params = {'sql': _FIDE_MATCH_SQL, 'q': match_expr, 'lim': size, '_shape': 'array'}
    for attempt in range(4):
        try:
            resp = requests.get(FIDE_SQL_URL, params=params, timeout=30)
            if resp.status_code == 429:
                time.sleep(5 * (attempt + 1))
                continue
            resp.raise_for_status()
            data = resp.json()
            return data if isinstance(data, list) else []
        except Exception as e:
            logging.warning(f"FIDE SQL MATCH error for '{match_expr}' (try {attempt+1}): {e}")
            time.sleep(2 * (attempt + 1))
    return []


def _tokens_match(qtokens, ctokens):
    """Every significant (len>=2) query token must align with some candidate
    token (equal or prefix either way, to tolerate short forms/initials).
    This re-validates FTS hits and biases toward EXCLUSION when unsure — a
    false exclude only costs sample, while a false include could mis-sex
    someone, which we must avoid."""
    for q in qtokens:
        if len(q) < 2:
            continue
        if not any(c == q or c.startswith(q) or q.startswith(c) for c in ctokens):
            return False
    return True


def _score_candidate(cand, open_title, cc_fide):
    """Higher = more likely the right person. Title match is the strong signal;
    country is a tiebreaker that only ever adds."""
    s = 0
    ct = (cand.get('title') or '')
    if ct == open_title:
        s += 4                       # holds exactly this open title
    elif ct in OPEN_TITLES:
        s += 2                       # holds some open title
    elif cand.get('w_title'):
        s += 1                       # holds a women's title (still a real titled player)
    if cc_fide and (cand.get('country') or '') == cc_fide:
        s += 2
    return s


def resolve_sex(name, open_title, cc_iso2, candidates):
    """Pick the most likely FIDE record and return its sex, or decline.

    Returns dict: {'status', 'sex'('M'/'F'/None), 'cand'(dict or None)}.
      status in {'matched', 'matched_multi_same_sex', 'ambiguous', 'unmatched'}
    Safety: if the top-scoring candidates disagree on sex -> 'ambiguous' (None).
    """
    qtokens = _name_tokens(name)
    cc_fide = ISO2_TO_FIDE.get((cc_iso2 or '').upper())
    valid = [c for c in candidates
             if _tokens_match(qtokens, _name_tokens(c.get('name', '')))]
    if not valid:
        return {'status': 'unmatched', 'sex': None, 'cand': None}

    scored = [(_score_candidate(c, open_title, cc_fide), c) for c in valid]
    max_sc = max(s for s, _ in scored)
    top = [c for s, c in scored if s == max_sc]
    sexes = set((c.get('sex') or '').upper() for c in top if c.get('sex'))

    if len(sexes) == 1:
        sex = sexes.pop()
        status = 'matched' if len(top) == 1 else 'matched_multi_same_sex'
        # Return the highest-rated top candidate for the cache record.
        cand = max(top, key=lambda c: c.get('rating') or 0)
        return {'status': status, 'sex': sex, 'cand': cand}
    return {'status': 'ambiguous', 'sex': None, 'cand': None}


# ---------------------------------------------------------------------------
# FIDE cache (reproducible record + avoids re-querying the external API)
# ---------------------------------------------------------------------------
def load_fide_cache(path):
    cache = {}
    if os.path.exists(path):
        with open(path, newline='', encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
        # Migrate older cache files to the current schema (e.g. add fide_rating),
        # so appends don't misalign columns.
        needs_migrate = any(fld not in (rows[0] if rows else {}) for fld in FIDE_CACHE_FIELDS)
        for row in rows:
            cache[row['query_name']] = row
        if rows and needs_migrate:
            with open(path, 'w', newline='', encoding='utf-8') as f:
                w = csv.DictWriter(f, fieldnames=FIDE_CACHE_FIELDS, extrasaction='ignore')
                w.writeheader()
                for row in rows:
                    w.writerow({k: row.get(k, '') for k in FIDE_CACHE_FIELDS})
            logging.info(f"Migrated {path} to current cache schema")
        logging.info(f"Loaded {len(cache)} cached FIDE lookups from {path}")
    return cache


def append_fide_cache(path, row):
    exists = os.path.exists(path)
    with open(path, 'a', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=FIDE_CACHE_FIELDS)
        if not exists:
            w.writeheader()
        w.writerow(row)


def resolve_open_player(username, open_title, cache):
    """Resolve one open-title player's gender via Chess.com name -> FIDE FTS.

    Returns dict with: gender ('male'/'female'/'unknown'), source, name,
    fideid, fide_sex. Writes a cache row on first resolution of a name.
    """
    prof = fetch_chesscom_profile(username)
    time.sleep(REQUEST_DELAY)
    name = prof['name']
    if not name:
        return {'gender': 'unknown', 'source': 'fide_api_no_realname',
                'name': '', 'fideid': '', 'fide_sex': '', 'fide_rating': ''}

    qkey = normalize_name(name)
    if qkey not in cache:
        cands = fide_fts_search(name)
        time.sleep(FIDE_DELAY)
        res = resolve_sex(name, open_title, prof['country'], cands)
        # Fallback ONLY when exact search found no name match: retry with prefix
        # terms to recover short-forms (Alex->Alexandr). All safety guards in
        # resolve_sex are unchanged, so this cannot mis-sex anyone.
        if res['status'] == 'unmatched':
            cands_p = fide_fts_search(name, prefix=True)
            time.sleep(FIDE_DELAY)
            res_p = resolve_sex(name, open_title, prof['country'], cands_p)
            if res_p['status'] != 'unmatched':
                res = res_p
                res['status'] = 'prefix_' + res['status']  # flag for audit
        cand = res['cand'] or {}
        row = {
            'query_name': qkey,
            'open_title': open_title,
            'status': res['status'],
            'sex': res['sex'] or '',
            'fide_name': cand.get('name', ''),
            'fide_title': cand.get('title') or '',
            'w_title': cand.get('w_title') or '',
            'o_title': cand.get('o_title') or '',
            'fideid': cand.get('fideid', ''),
            'country': cand.get('country') or '',
            'fide_rating': cand.get('rating') or '',
        }
        append_fide_cache(FIDE_CACHE, row)
        cache[qkey] = row

    c = cache[qkey]
    sex = (c.get('sex') or '').upper()
    gender = 'male' if sex == 'M' else ('female' if sex == 'F' else 'unknown')
    return {'gender': gender, 'source': 'fide_api_open_title', 'name': name,
            'fideid': c.get('fideid', ''), 'fide_sex': sex,
            'fide_rating': c.get('fide_rating') or ''}


# ---------------------------------------------------------------------------
# Roster build
# ---------------------------------------------------------------------------
def build_roster(titles, limit=None, resolve_open=True):
    """Enumerate titles and assign gender.

    Women's titles -> female immediately. Open titles -> resolved against FIDE
    (unless resolve_open=False, which leaves them 'needs_fide_check' for a
    later pass). `limit` caps usernames per title (testing)."""
    cache = load_fide_cache(FIDE_CACHE)
    roster = []
    for title in titles:
        usernames = fetch_title_usernames(title)
        if limit:
            usernames = usernames[:limit]
        base = gender_from_title(title)

        if base == 'female':
            for u in usernames:
                roster.append({'username': u, 'title': title, 'gender': 'female',
                               'source': 'chesscom_womens_title', 'name': '',
                               'fideid': '', 'fide_sex': ''})

        elif base == 'needs_fide_check':
            for i, u in enumerate(usernames):
                if resolve_open:
                    logging.info(f"  resolving {title} {i+1}/{len(usernames)}: {u}")
                    r = resolve_open_player(u, title, cache)
                    roster.append({'username': u, 'title': title,
                                   'gender': r['gender'], 'source': r['source'],
                                   'name': r['name'], 'fideid': r['fideid'],
                                   'fide_sex': r['fide_sex']})
                else:
                    roster.append({'username': u, 'title': title,
                                   'gender': 'needs_fide_check',
                                   'source': 'chesscom_open_title', 'name': '',
                                   'fideid': '', 'fide_sex': ''})
        else:
            for u in usernames:
                roster.append({'username': u, 'title': title, 'gender': 'unknown',
                               'source': 'no_usable_title', 'name': '',
                               'fideid': '', 'fide_sex': ''})
        time.sleep(REQUEST_DELAY)
    return roster


def write_roster(roster, path):
    with open(path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=ROSTER_FIELDS)
        writer.writeheader()
        writer.writerows(roster)
    logging.info(f"Wrote {len(roster)} players to {path}")


def print_summary(roster):
    from collections import Counter
    gender_counts = Counter(r['gender'] for r in roster)
    title_counts = Counter(r['title'] for r in roster)
    print("\n=== ROSTER SUMMARY (Chess.com + FIDE FTS) ===")
    print(f"Total titled players: {len(roster)}")
    print(f"By title: {dict(title_counts)}")
    print(f"By gender: {dict(gender_counts)}")
    print(f"\nmale   (open title, FIDE sex=M, ENTERS male queue): {gender_counts.get('male', 0)}")
    print(f"female (women's title OR open-title FIDE sex=F, EXCLUDED from male): {gender_counts.get('female', 0)}")
    print(f"unknown (no real name / no match / ambiguous, EXCLUDED): {gender_counts.get('unknown', 0)}")
    if gender_counts.get('male', 0) < 100:
        print("\n!!! NOTE: male count < 100 — small (expected for a test run).")


# ---------------------------------------------------------------------------
# Self-test of the resolver against curated ground truth (no Chess.com needed)
# ---------------------------------------------------------------------------
def run_resolver_unit_test():
    """Hit the FIDE FTS API directly with known (name, open_title, country)
    triples and verify sex resolution — especially that open-title WOMEN are
    correctly sexed 'F' (and thus excluded from the male queue)."""
    cases = [
        # name, open_title, ISO2, expected_sex
        ("Magnus Carlsen",         "GM", "NO", "M"),
        ("Hikaru Nakamura",        "GM", "US", "M"),
        ("Wesley So",              "GM", "US", "M"),
        ("Fabiano Caruana",        "GM", "US", "M"),
        ("Maxime Vachier-Lagrave", "GM", "FR", "M"),
        ("Wei Yi",                 "GM", "CN", "M"),   # short-token stress
        ("Yifan Hou",              "GM", "CN", "F"),   # open-GM woman -> exclude
        ("Judit Polgar",           "GM", "HU", "F"),   # open-GM woman -> exclude
        ("Wenjun Ju",              "GM", "CN", "F"),   # open-GM woman -> exclude
        ("Humpy Koneru",           "GM", "IN", "F"),   # open-GM woman -> exclude
    ]
    print("\n=== RESOLVER UNIT TEST (curated ground truth) ===")
    passed = 0
    for name, title, cc, expected in cases:
        cands = fide_fts_search(name)
        time.sleep(FIDE_DELAY)
        res = resolve_sex(name, title, cc, cands)
        got = res['sex']
        gender = 'male' if got == 'M' else ('female' if got == 'F' else 'unknown')
        ok = (got == expected)
        passed += ok
        fide_name = (res['cand'] or {}).get('name', '-')
        flag = "OK " if ok else "FAIL"
        excl = " [EXCLUDED from male]" if gender != 'male' else ""
        print(f"  [{flag}] {name:24s} {title} {cc} -> sex={got or '?'} "
              f"({gender}){excl}  match='{fide_name}' status={res['status']}")
    print(f"  --> {passed}/{len(cases)} correct")
    return passed == len(cases)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description="Build Chess.com titled-player roster + FIDE gender resolution")
    ap.add_argument('--titles', nargs='+', default=ALL_TITLES,
                    help="Subset of titles to enumerate (default: all 10).")
    ap.add_argument('--limit', type=int, default=None,
                    help="Cap usernames per title (testing).")
    ap.add_argument('--no-resolve', action='store_true',
                    help="Skip FIDE resolution (leave open titles as needs_fide_check).")
    ap.add_argument('--output', default=OUTPUT_ROSTER)
    ap.add_argument('--test', action='store_true',
                    help="TEST MODE: resolver unit test + small batch (20 GM + 10 FM) "
                         "to a separate file; does NOT touch the real roster.")
    args = ap.parse_args()

    if args.test:
        # 1) Deterministic resolver check (proves female exclusion).
        unit_ok = run_resolver_unit_test()
        # 2) Small end-to-end batch to a SEPARATE file (don't clobber real data).
        print("\n=== END-TO-END BATCH: first 20 GM + first 10 FM ===")
        roster = []
        for title, n in (('GM', 20), ('FM', 10)):
            usernames = fetch_title_usernames(title)[:n]
            cache = load_fide_cache(FIDE_CACHE)
            for i, u in enumerate(usernames):
                logging.info(f"  {title} {i+1}/{len(usernames)}: {u}")
                r = resolve_open_player(u, title, cache)
                roster.append({'username': u, 'title': title, 'gender': r['gender'],
                               'source': r['source'], 'name': r['name'],
                               'fideid': r['fideid'], 'fide_sex': r['fide_sex']})
            time.sleep(REQUEST_DELAY)
        write_roster(roster, "titled_players_roster_TEST.csv")
        print("\n--- per-player results ---")
        for r in roster:
            print(f"  {r['title']} {r['username']:24s} name='{r['name']}' "
                  f"-> {r['gender']} (sex={r['fide_sex'] or '?'}, fideid={r['fideid'] or '-'})")
        print_summary(roster)
        print(f"\nResolver unit test: {'PASS' if unit_ok else 'FAIL'}")
        print(f"Cache written to: {FIDE_CACHE}")
        print("Test roster written to: titled_players_roster_TEST.csv "
              "(real roster untouched)")
        return

    roster = build_roster(args.titles, limit=args.limit,
                          resolve_open=not args.no_resolve)
    if not roster:
        logging.error("No players retrieved. Check internet / Chess.com API.")
        return
    write_roster(roster, args.output)
    print_summary(roster)


if __name__ == "__main__":
    main()
