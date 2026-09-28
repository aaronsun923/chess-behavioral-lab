#!/usr/bin/env python3
"""
p5_throttle_check.py — SPEC v5 Amendment A1.6 throttling check.

200 depth-20 positions already in the study store (pilot subsample batch, non-terminal;
drawn with the SPEC v5 seed) are re-run at nproc = 6 and then at nproc = 8, back to
back, with the same successor configuration. Results are kept out of the study store
(data/spec_v5/checks/) and compared with the stored values as a determinism check.

    python3 code/p5_throttle_check.py
"""
import os, sys, json, time
import multiprocessing as mp

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import p5_common as C
import p5_evals as EV

CHK_DIR = os.path.join(C.OUT_DIR, 'checks')
N = 200


def main():
    os.makedirs(CHK_DIR, exist_ok=True)
    out = os.path.join(CHK_DIR, 'throttle_check.json')
    if os.path.exists(out):
        raise SystemExit('throttling check already done')
    st = EV.load_store()
    pool20 = st[(st.depth == 20) & (st.terminal == '') & (st.batch == 'pilot_sub_d20')] \
        .sort_values(['row_id', 'move_uci']).reset_index(drop=True)
    pick = pool20.sample(N, random_state=C.SEED).reset_index(drop=True)
    einfo = C.engine_info()
    jobs = [({'row_id': int(x.row_id), 'game_id': x.game_id, 'ply': int(x.ply), 'item': 'throttle'},
             x.fen, x.move_uci, 20) for x in pick.itertuples()]
    res = {'positions': N, 'source': 'study store, batch pilot_sub_d20, non-terminal, sample(seed 20261001)',
           'engine_sha256': einfo['engine_sha256'], 'runs': {}}
    cols = [f'wp_self_{k}' for k in range(1, 6)] + [f'mv_{k}' for k in range(1, 6)] + ['nodes']
    for nproc in [6, 8]:
        t0 = time.time()
        with mp.Pool(nproc, initializer=EV._init) as p:
            rows = p.map(EV._run, jobs, chunksize=1)
        wall = time.time() - t0
        df = pd.DataFrame(rows)
        df['nproc'] = nproc
        df.to_parquet(os.path.join(CHK_DIR, f'throttle_nproc{nproc}.parquet'), index=False)
        m = df.merge(pick[['row_id', 'move_uci'] + cols], on=['row_id', 'move_uci'], suffixes=('', '_store'))
        n_diff = int((~np.logical_and.reduce([((m[c] == m[c + '_store']) | (m[c].isna() & m[c + '_store'].isna())).values
                                              for c in cols])).sum())
        res['runs'][str(nproc)] = {'wall_s': wall, 'wall_s_per_eval': wall / N,
                                   'evals_per_hour': N / wall * 3600,
                                   'engine_s_mean': float(df.seconds.mean()),
                                   'engine_s_median': float(df.seconds.median()),
                                   'positions_differing_from_store': n_diff,
                                   'finished_utc': pd.Timestamp.utcnow().isoformat()}
        print(nproc, res['runs'][str(nproc)], flush=True)
    res['faster_nproc'] = min(res['runs'], key=lambda k: res['runs'][k]['wall_s_per_eval'])
    json.dump(res, open(out, 'w'), indent=2)
    print(json.dumps(res, indent=2))


if __name__ == '__main__':
    main()
