"""E/I parameter sweep on the Python model (N = 256), to find a regime that does not saturate.

Same arithmetic as model/network.py (D-006, D-008, D-009): syn_i = sat(sum_j (W[j][i] << 2) * s_j + ext_i),
then one single-neuron step per neuron. Only the spiking sources are visited, so a
sweep is fast. The chosen conditions are checked against model/network.py run_network
(bit exact) before they go to the board.

Sweep axes:
    f_inh  fraction of inhibitory sources (the rest are excitatory)
    w_max  largest weight magnitude (raw 8-bit value; the synapse adds w << 2 per spike)
    e_max  external input per neuron: uniform integer 0..e_max, Q8.8 raw (50 ~ 0.2)

Writes build/ei_sweep.csv and prints a table.
"""

import csv
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "..", "build")
sys.path.insert(0, os.path.join(HERE, "..", "model"))

from fixed import Params, State, sat, step  # noqa: E402

N = 256
T = 600           # steps per run
WARM = 100        # steps discarded before measuring
SEED = 20261104
PARAMS = dict(theta=384, v_reset=0, v_rest=0, k_m=4, k_s=3, refrac=2)
W_SHIFT = 2
P_CONN = 8 / N    # about 8 inputs per neuron, as in gen_net_top_vectors.py

F_INH = [0.2, 0.5]
W_MAX = [10, 20, 40, 60]
E_MAX = [10, 30]


def build(f_inh, w_max, rng):
    n_exc = N - round(N * f_inh)
    W = [[0] * N for _ in range(N)]
    for j in range(N):
        for i in range(N):
            if rng.random() < P_CONN:
                if j < n_exc:
                    W[j][i] = rng.randint(0, w_max)
                else:
                    W[j][i] = -rng.randint(0, w_max)
    return W


def run(W, ext, p):
    """Sparse version of run_network: returns spike counts per neuron after WARM steps."""
    states = [State() for _ in range(N)]
    spikes = [0] * N
    counts = [0] * N
    for t in range(T):
        acc = [0] * N
        for j in range(N):
            if spikes[j]:
                row = W[j]
                for i in range(N):
                    acc[i] += row[i] << W_SHIFT
        new = [0] * N
        for i in range(N):
            s2, spk = step(states[i], p, sat(acc[i] + ext[i]))
            states[i] = s2
            new[i] = spk
        spikes = new
        if t >= WARM:
            for i in range(N):
                counts[i] += spikes[i]
    return counts


def measure(counts):
    steps = T - WARM
    rates = [c / steps for c in counts]
    mean = sum(rates) / N
    var = sum((r - mean) ** 2 for r in rates) / N
    return dict(
        mean_rate=mean,
        rate_sd=var ** 0.5,
        silent=sum(1 for c in counts if c == 0) / N,
        at_max=sum(1 for r in rates if r > 0.3) / N,   # 1/3 is the refractory limit
    )


def main():
    os.makedirs(BUILD, exist_ok=True)
    p = Params(**PARAMS)
    rows = []
    for f_inh in F_INH:
        for w_max in W_MAX:
            rng = random.Random(SEED)
            W = build(f_inh, w_max, rng)
            for e_max in E_MAX:
                ext = [rng.randint(0, e_max) for _ in range(N)]
                m = measure(run(W, ext, p))
                row = dict(f_inh=f_inh, w_max=w_max, e_max=e_max, **m)
                rows.append(row)
                print(f"f_inh={f_inh:.1f} w_max={w_max:3d} e_max={e_max:3d}  "
                      f"rate={m['mean_rate']:.3f} sd={m['rate_sd']:.3f} "
                      f"silent={m['silent']:.2f} at_max={m['at_max']:.2f}", flush=True)
    path = os.path.join(BUILD, "ei_sweep.csv")
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {path}")


if __name__ == "__main__":
    main()
