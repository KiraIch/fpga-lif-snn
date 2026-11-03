"""Full E/I sweep on the Python model (N = 256).

Axes (all combinations, each with several random networks):
    f_inh  fraction of inhibitory sources            0.0 .. 0.6 in steps of 0.1
    w_inh  inhibitory weight scale (1.0 = same size)  0.5, 1.0, 1.5, 2.0
    w_max  largest excitatory weight magnitude        10, 20
    e_max  external input 0..e_max (Q8.8 raw)         10, 30, 60
    seed   random networks                            3 per combination

Same arithmetic as model/network.py (see host/ei_sweep.py: run() visits only the spiking
sources, and the chosen conditions are checked against the exact model on the board).
Writes build/ei_full_sweep.csv and prints a summary.
"""

import csv
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "model"))

import ei_sweep  # noqa: E402
from fixed import Params  # noqa: E402

F_INH = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
W_INH = [0.5, 1.0, 1.5, 2.0]
W_MAX = [10, 20]
E_MAX = [10, 30, 60]
SEEDS = [20261104, 20261105, 20261106]


def build(f_inh, w_max, w_inh, rng):
    """Like ei_sweep.build, but the inhibitory weights are scaled by w_inh."""
    n_exc = ei_sweep.N - round(ei_sweep.N * f_inh)
    W = [[0] * ei_sweep.N for _ in range(ei_sweep.N)]
    for j in range(ei_sweep.N):
        for i in range(ei_sweep.N):
            if rng.random() < ei_sweep.P_CONN:
                if j < n_exc:
                    W[j][i] = rng.randint(0, w_max)
                else:
                    W[j][i] = -round(rng.randint(0, w_max) * w_inh)
    return W


def main():
    os.makedirs(ei_sweep.BUILD, exist_ok=True)
    p = Params(**ei_sweep.PARAMS)
    rows = []
    total = len(F_INH) * len(W_INH) * len(W_MAX) * len(E_MAX) * len(SEEDS)
    n = 0
    for w_max in W_MAX:
        for w_inh in W_INH:
            for f_inh in F_INH:
                for seed in SEEDS:
                    W = build(f_inh, w_max, w_inh, random.Random(seed))
                    for e_max in E_MAX:
                        ext_rng = random.Random(seed * 1000 + e_max)
                        ext = [ext_rng.randint(0, e_max) for _ in range(ei_sweep.N)]
                        m = ei_sweep.measure(ei_sweep.run(W, ext, p))
                        rows.append(dict(w_max=w_max, w_inh=w_inh, f_inh=f_inh,
                                         e_max=e_max, seed=seed, **m))
                        n += 1
                    print(f"[{n}/{total}] w_max={w_max} w_inh={w_inh} f_inh={f_inh} seed={seed}",
                          flush=True)

    path = os.path.join(ei_sweep.BUILD, "ei_full_sweep.csv")
    with open(path, "w", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        wr.writeheader()
        wr.writerows(rows)
    print(f"wrote {path} ({len(rows)} runs)")


if __name__ == "__main__":
    main()
