#!/usr/bin/env python3
"""
p5_A1_counts.py — SPEC v5 Amendment A1.6/A1.7: depth-20 and depth-25 evaluation
counts and the cost estimate at the sustained (throttled) rate. No engine.
Writes data/spec_v5/A1_tasks.parquet and reports/spec_v5_A1_counts.md.
"""
import os, sys, json

import numpy as np
import pandas as pd
import chess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p5_common as C
import p5_evals as EV

SHALLOW = [2, 4, 8, 12, 15]
f = lambda x: f'{x:,.0f}'


def terminal(fen, uci):
    b = chess.Board(fen); b.push_uci(uci)
    return b.is_checkmate() or b.is_stalemate() or b.is_insufficient_material() or \
        b.is_seventyfive_moves() or b.is_fivefold_repetition()


def main():
    r = pd.read_parquet(os.path.join(C.OUT_DIR, 'root_choices.parquet'))
    r['h'] = [chess.Board(fn).parse_san(s).uci() for fn, s in zip(r.fen, r.move_played)]
    r['b15'] = r['best_15_singlepv']
    col = {2: 'best_2', 4: 'best_4', 8: 'best_8', 12: 'best_12', 15: 'b15'}
    N = len(r)
    st = EV.load_store()
    have20 = set(zip(st[st.depth == 20].row_id, st[st.depth == 20].move_uci))

    # ---------- depth-20 evaluations, all rows (A1.1, A1.2)
    items = [('h', r, 'h')]
    items.append(('best_20', r[r.best_20 != r.h], 'best_20'))
    for d in SHALLOW:
        c = col[d]
        items.append((f'best_{d}', r[(r[c] != r.h) & (r[c] != r.best_20)], c))
    t = []
    for name, rows, c in items:
        for x in rows.itertuples():
            u = getattr(x, c)
            t.append((name, x.row_id, x.game_id, x.ply, x.fen, u, 20))
    t = pd.DataFrame(t, columns=['item', 'row_id', 'game_id', 'ply', 'fen', 'move_uci', 'depth'])
    t['terminal'] = [terminal(fn, u) for fn, u in zip(t.fen, t.move_uci)]
    t['in_store'] = [(a, b) in have20 for a, b in zip(t.row_id, t.move_uci)]

    # ---------- depth-25 check: first 1,000 subsample rows in draw order (A1.4)
    sub = pd.read_csv(os.path.join(C.OUT_DIR, 'subsample_ids.csv')).sort_values('draw_order').head(1000)
    rs = r.set_index('row_id').loc[sub.row_id].reset_index()
    t25 = []
    for x in rs.itertuples():
        seen = set()
        for name, c in [('h', 'h'), ('best_20', 'best_20')] + [(f'best_{d}', col[d]) for d in SHALLOW]:
            u = getattr(x, c)
            if u in seen:
                continue
            seen.add(u)
            t25.append((name, x.row_id, x.game_id, x.ply, x.fen, u, 25))
    t25 = pd.DataFrame(t25, columns=['item', 'row_id', 'game_id', 'ply', 'fen', 'move_uci', 'depth'])
    t25['terminal'] = [terminal(fn, u) for fn, u in zip(t25.fen, t25.move_uci)]
    t25['in_store'] = False
    pd.concat([t, t25], ignore_index=True).to_parquet(os.path.join(C.OUT_DIR, 'A1_tasks.parquet'), index=False)

    new20 = t[~t.terminal & ~t.in_store].drop_duplicates(['row_id', 'move_uci'])
    n20 = len(new20)
    n25 = int((~t25.terminal).sum())

    # ---------- rates
    th = json.load(open(os.path.join(C.OUT_DIR, 'checks', 'throttle_check.json')))
    fast = th['faster_nproc']
    w20 = th['runs'][fast]['wall_s_per_eval']
    s15 = st[(st.depth == 15) & (st.terminal == '')][['row_id', 'move_uci', 'seconds']]
    s20 = st[(st.depth == 20) & (st.terminal == '')][['row_id', 'move_uci', 'seconds']]
    pair = s15.merge(s20, on=['row_id', 'move_uci'], suffixes=('_15', '_20'))
    ratio = pair.seconds_20.mean() / pair.seconds_15.mean()
    w25 = w20 * ratio
    h20 = n20 * w20 / 3600
    h25 = n25 * w25 / 3600

    # ---------- report
    elog = json.load(open(os.path.join(C.OUT_DIR, 'root_choices_engine_log.json')))
    L = []; P = L.append
    P('# SPEC v5 Amendment A1: depth-20 and depth-25 counts and cost\n')
    P('Spec: `specs/paper4_spec_v5.md`, Amendment A1 at 880423e. A1.7 steps run: depth-2 root search, depth-20 root search, '
      'throttling check. Engine, settings and root input as the pre-run count §1 (Stockfish 18, SHA-256 '
      f"`{elog['engine_sha256'][:16]}…`, Threads 1, Hash 128, ucinewgame per search). The depth-25 check and the depth-20 evaluations have not been run.\n")

    P('## 1. Root searches (single-PV, all 50,021 positions)\n')
    P('| Depth | Searches | Wall time (min, 8 processes) | Engine time, mean per search (s) | Rows with best_d = best_20 |\n|---|---|---|---|---|')
    for d in [2, 20]:
        p = elog['passes'][str(d)]
        eq = '—' if d == 20 else f"{int((r.best_2 == r.best_20).sum()):,} ({(r.best_2 == r.best_20).mean():.4f})"
        P(f"| {d} | {p['searches']:,} | {p['wall_seconds'] / 60:.1f} | {p['engine_seconds_sum'] / p['searches']:.4f} | {eq} |")
    for d in [4, 8, 12, 15]:
        c = col[d]
        P(f"| {d} (from the pre-run count) | | | | {int((r[c] == r.best_20).sum()):,} ({(r[c] == r.best_20).mean():.4f}) |")
    P(f"\nColumns best_2 and best_20 added to `data/spec_v5/root_choices.parquet` (earlier columns unchanged; previous file kept as `root_choices_preA1.parquet`). "
      f"best_15 here is best_15_singlepv. Rows with best_20 = h: {int((r.best_20 == r.h).sum()):,}.\n")

    P('## 2. Throttling check (A1.6)\n')
    P(f"{th['positions']} depth-20 positions from the study store ({th['source']}), re-run at nproc = 6 and then nproc = 8, back to back; "
      'results in `data/spec_v5/checks/`, not in the study store.\n')
    P('| nproc | Batch wall (s) | Wall s per evaluation | Evaluations per hour | Engine s per evaluation, mean | median | Positions differing from store (5 WP values, 5 moves, nodes) |\n|---|---|---|---|---|---|---|')
    for k in ['6', '8']:
        x = th['runs'][k]
        P(f"| {k} | {x['wall_s']:.1f} | {x['wall_s_per_eval']:.3f} | {x['evals_per_hour']:,.0f} | {x['engine_s_mean']:.3f} | {x['engine_s_median']:.3f} | {x['positions_differing_from_store']} |")
    P(f'\nFaster: nproc = {fast}.\n')

    P('## 3. Evaluation counts\n')
    P('"In store" = already evaluated at depth 20 in the pilot (subsample: after h, best_15, best_4). Terminal = checkmate or draw after the move; no engine call.\n')
    P('| Item | Definition | Rows | In store | Terminal | Engine evaluations |\n|---|---|---|---|---|---|')
    defs = {'h': 'position after h, all rows', 'best_20': 'best_20 ≠ h'}
    for name, _, _ in items:
        s = t[t['item'] == name]
        dd = defs.get(name, f'{name} ≠ h and {name} ≠ best_20')
        P(f"| depth 20: {name} | {dd} | {len(s):,} | {int(s.in_store.sum()):,} | {int(s.terminal.sum()):,} | {int((~s.in_store & ~s.terminal).sum()):,} |")
    P(f"| depth 20: total | distinct (row, move), not in store, non-terminal | | | | {n20:,} |")
    for name in ['h', 'best_20'] + [f'best_{d}' for d in SHALLOW]:
        s = t25[t25['item'] == name]
        P(f"| depth 25: first counted as {name} | first 1,000 subsample rows in draw order, distinct positions | {len(s):,} | | {int(s.terminal.sum()):,} | {int((~s.terminal).sum()):,} |")
    P(f"| depth 25: total | | {len(t25):,} | | {int(t25.terminal.sum()):,} | {n25:,} |")
    P('\nPer-item list: `data/spec_v5/A1_tasks.parquet`.\n')

    P('## 4. Cost at the sustained rate\n')
    P(f'| Run | Engine evaluations | Wall s per evaluation (nproc = {fast}) | Hours |\n|---|---|---|---|')
    P(f'| Depth-20 evaluations | {n20:,} | {w20:.3f} (throttling check) | {h20:.1f} |')
    P(f'| Depth-25 check | {n25:,} | {w25:.3f} (extrapolated) | {h25:.1f} |')
    P(f'\nDepth-25 rate: no depth-25 search has been run (A1.7). It is the throttled depth-20 rate × {ratio:.2f}, the ratio of mean engine seconds at depth 20 to depth 15 '
      f'on the {len(pair):,} positions evaluated at both depths in the pilot (depth-15 mean {pair.seconds_15.mean():.3f} s, depth-20 mean {pair.seconds_20.mean():.3f} s), '
      'i.e. the same growth per five plies from 20 to 25 as from 15 to 20.\n')

    p = os.path.join(C.REPO, 'reports', 'spec_v5_A1_counts.md')
    open(p, 'w').write('\n'.join(L))
    print(open(p).read())


if __name__ == '__main__':
    main()
