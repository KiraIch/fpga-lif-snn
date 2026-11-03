"""E/I perturbation experiment on the Python model (N = 256).

Baseline network: w_max = 10, e_max = 30 (chosen with host/ei_sweep.py: no saturation).
Perturbation: the fraction of inhibitory sources f_inh, from 0 (all excitatory) to 0.6.
Each f_inh is run on several random networks (different seeds), so the spread is visible.

Writes build/ei_experiment.csv and prints a table. The per-run numbers come from
ei_sweep.run (same arithmetic as model/network.py; see that file).
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

W_MAX = 10
E_MAX = 30
F_INH = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
SEEDS = [20261104, 20261105, 20261106]


def main():
    os.makedirs(ei_sweep.BUILD, exist_ok=True)
    p = Params(**ei_sweep.PARAMS)
    rows = []
    for f_inh in F_INH:
        for seed in SEEDS:
            rng = random.Random(seed)
            W = ei_sweep.build(f_inh, W_MAX, rng)
            ext = [rng.randint(0, E_MAX) for _ in range(ei_sweep.N)]
            m = ei_sweep.measure(ei_sweep.run(W, ext, p))
            rows.append(dict(f_inh=f_inh, seed=seed, **m))
            print(f"f_inh={f_inh:.1f} seed={seed}  rate={m['mean_rate']:.3f} "
                  f"sd={m['rate_sd']:.3f} silent={m['silent']:.2f} at_max={m['at_max']:.2f}",
                  flush=True)

    path = os.path.join(ei_sweep.BUILD, "ei_experiment.csv")
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    print("\nmean over seeds:")
    print("f_inh  rate   (min-max)        silent")
    for f_inh in F_INH:
        rs = [r for r in rows if r["f_inh"] == f_inh]
        rates = [r["mean_rate"] for r in rs]
        sil = sum(r["silent"] for r in rs) / len(rs)
        print(f"{f_inh:.1f}   {sum(rates)/len(rates):.3f}  ({min(rates):.3f}-{max(rates):.3f})   {sil:.2f}")
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
