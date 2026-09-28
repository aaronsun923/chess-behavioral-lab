#!/usr/bin/env python3
"""
p5_precount.py — SPEC v5 §4 evaluation counts (pre-run count, step 3). No engine.

Uses data/spec_v5/root_choices.parquet (best_15 := best_15_singlepv), the v1 rows,
the v2/v3 successor evaluations and data/spec_v5/subsample_ids.csv. A successor
position "has a depth-15 evaluation" when the same (game_id, ply, move) was
evaluated in v2/v3 (identical engine input: root FEN + move). Writes
data/spec_v5/precount.json and data/spec_v5/precount_tasks.parquet (the list of
(row_id, move, depth) evaluations each count refers to).

    python3 code/p5_precount.py
"""
import os, sys, json

import pandas as pd
import chess

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p5_common as C

SHALLOW = [4, 8, 12]


def san2uci(fen, san):
    b = chess.Board(fen)
    return b.parse_san(san).uci()


def terminal(fen, uci):
    b = chess.Board(fen); b.push(chess.Move.from_uci(uci))
    return b.is_checkmate() or b.is_stalemate() or b.is_insufficient_material() or \
        b.is_seventyfive_moves() or b.is_fivefold_repetition()


def main():
    r = pd.read_parquet(os.path.join(C.OUT_DIR, 'root_choices.parquet'))
    r['h'] = [san2uci(f, s) for f, s in zip(r.fen, r.move_played)]
    r['best_15_mpv'] = [san2uci(f, s) for f, s in zip(r.fen, r.move_engine_best)]
    r['b15'] = r['best_15_singlepv']
    N = len(r)

    s = C.load_existing_successors()
    fen_of = dict(zip(zip(r.game_id, r.ply), r.fen))
    have = set()
    for g, p, san in zip(s.game_id, s.ply, s.move_san):
        have.add((g, int(p), san2uci(fen_of[(g, int(p))], san)))
    evald = lambda g, p, u: (g, int(p), u) in have

    out = {'N_rows': N, 'existing_v2v3_successor_evals': len(have)}
    tasks = []   # (item, row_id, game_id, ply, fen, move_uci, eval_depth, already_evaluated, terminal)

    def add(item, rows, col, depth):
        for x in rows.itertuples():
            u = getattr(x, col)
            tasks.append((item, x.row_id, x.game_id, x.ply, x.fen, u, depth,
                          evald(x.game_id, x.ply, u), terminal(x.fen, u)))

    # depth-15 agreement: single-PV vs MultiPV
    agree = (r.b15 == r.best_15_mpv)
    out['agree_15_singlepv_multipv'] = int(agree.sum())

    # (a) non-deviation rows (v1: played == MultiPV best) whose post-h position has no depth-15 evaluation
    nondev = r[r.h == r.best_15_mpv]
    out['nondeviation_rows'] = len(nondev)
    add('a', nondev, 'h', 15)

    # (b) per shallow depth: best_d differs from both h and best_15
    for d in SHALLOW:
        c = f'best_{d}'
        out[f'eq_best15_{d}'] = int((r[c] == r.b15).sum())
        out[f'ne_best15_{d}'] = int((r[c] != r.b15).sum())
        add(f'b{d}', r[(r[c] != r.h) & (r[c] != r.b15)], c, 15)
    # (c) single-PV best_15 differs from MultiPV best_15
    add('c', r[~agree], 'b15', 15)

    t = pd.DataFrame(tasks, columns=['item', 'row_id', 'game_id', 'ply', 'fen', 'move_uci',
                                     'eval_depth', 'already_evaluated', 'terminal'])

    # (d) depth-20 on the subsample: h, best_15, best_4, best_8, best_12; each distinct position once
    sub = pd.read_csv(os.path.join(C.OUT_DIR, 'subsample_ids.csv'))
    rs = r.set_index('row_id').loc[sub.row_id].reset_index()
    d20 = []
    for x in rs.itertuples():
        seen = set()
        for typ, u in [('h', x.h), ('best_15', x.b15), ('best_4', x.best_4),
                       ('best_8', x.best_8), ('best_12', x.best_12)]:
            if u in seen:
                continue
            seen.add(u)
            d20.append(('d', x.row_id, x.game_id, x.ply, x.fen, u, 20, False,
                        terminal(x.fen, u), typ))
    t20 = pd.DataFrame(d20, columns=list(t.columns) + ['first_type'])
    t = pd.concat([t.assign(first_type=None), t20], ignore_index=True)

    # distinct depth-15 engine evaluations across (a), (b), (c): same row and move = same engine input
    t15 = t[t.eval_depth == 15]
    new15 = t15[~t15.already_evaluated].drop_duplicates(['row_id', 'move_uci'])
    out['distinct_new_d15_positions'] = len(new15)
    out['distinct_new_d15_nonterminal'] = int((~new15.terminal).sum())
    out['d20_nonterminal'] = int((~t20.terminal).sum())

    # not a §4 count: best_d != best_15 positions evaluated in v2/v3, whose PV was not stored
    for d in SHALLOW:
        c = f'best_{d}'
        m = r[r[c] != r.b15]
        out[f'pv_not_stored_{d}'] = int(sum(evald(g, p, u) and not terminal(f, u)
                                            for g, p, f, u in zip(m.game_id, m.ply, m.fen, m[c])))

    t.to_parquet(os.path.join(C.OUT_DIR, 'precount_tasks.parquet'), index=False)
    json.dump(out, open(os.path.join(C.OUT_DIR, 'precount.json'), 'w'), indent=2)
    print(json.dumps(out, indent=2))
    print(t.groupby('item').agg(rows=('row_id', 'size'), already=('already_evaluated', 'sum'),
                                terminal=('terminal', 'sum')))


if __name__ == '__main__':
    main()
