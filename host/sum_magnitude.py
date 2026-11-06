"""Largest exact synaptic sums in the networks run on the board.

For each network, the exact sum over sources plus the external input (before any saturation)
is recorded at every step and neuron. This is the value the 24-bit accumulator of rtl/network.v
carries. The script reports the largest magnitude and how many samples leave the 16-bit range.

The networks are rebuilt here with the same generators and seeds as the board runs, without
importing the board scripts (they import the UART code):
  - command flow: host/gen_net_top_vectors.py (SEED, N = 256, T = 200)
  - E/I board conditions: host/ei_full_sweep.py (seed 20261104, 600 steps, five conditions)

Run from the repository root:  python host/sum_magnitude.py
"""

import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "model"))

from fixed import Params, State, sat, step  # noqa: E402
from network import W_SHIFT  # noqa: E402

with open(os.path.join(HERE, "gen_net_top_vectors.py"), encoding="utf-8") as f:
    SEED = int(re.search(r"^SEED\s*=\s*(\d+)", f.read(), re.M).group(1))

PARAMS = dict(theta=384, v_reset=0, v_rest=0, k_m=4, k_s=3, refrac=2)


def flow_network(N=256):
    rng = random.Random(SEED)
    n_exc = int(N * 0.8)
    W = [[0] * N for _ in range(N)]
    for j in range(N):
        for i in range(N):
            if rng.random() < min(0.5, 8 / N):
                W[j][i] = rng.randint(0, 60) if j < n_exc else -rng.randint(0, 60)
    ext = [rng.randint(0, 50) for _ in range(N)]
    return W, ext


def ei_network(f_inh, w_max, w_inh, seed, e_max, N=256, p_conn=8 / 256):
    n_exc = N - round(N * f_inh)
    rng = random.Random(seed)
    W = [[0] * N for _ in range(N)]
    for j in range(N):
        for i in range(N):
            if rng.random() < p_conn:
                if j < n_exc:
                    W[j][i] = rng.randint(0, w_max)
                else:
                    W[j][i] = -round(rng.randint(0, w_max) * w_inh)
    ext_rng = random.Random(seed * 1000 + e_max)
    ext = [ext_rng.randint(0, e_max) for _ in range(N)]
    return W, ext


def measure(W, ext, steps):
    """Run from rest; return (largest |exact sum|, samples outside 16 bits, samples)."""
    N = len(ext)
    p = Params(**PARAMS)
    states = [State() for _ in range(N)]
    spikes = [0] * N
    worst = 0
    outside = 0
    total = 0
    for _ in range(steps):
        syn = []
        for i in range(N):
            acc = 0
            for j in range(N):
                if spikes[j]:
                    acc += W[j][i] << W_SHIFT
            exact = acc + ext[i]
            worst = max(worst, abs(exact))
            outside += abs(exact) > 32767
            total += 1
            syn.append(sat(exact))
        new_states, new_spikes = [], []
        for s, x in zip(states, syn):
            s2, spk = step(s, p, x)
            new_states.append(s2)
            new_spikes.append(spk)
        states, spikes = new_states, new_spikes
    return worst, outside, total


def main():
    W, ext = flow_network()
    worst, outside, total = measure(W, ext, 200)
    print(f"command flow (N=256, T=200, SEED={SEED}): largest |exact sum| = {worst}, "
          f"samples outside 16 bits = {outside} of {total}")
    conditions = [(0.2, 1.0, 10, 30), (0.5, 1.0, 10, 30), (0.5, 0.5, 10, 30),
                  (0.5, 2.0, 10, 30), (0.3, 1.5, 20, 10)]
    for f_inh, w_inh, w_max, e_max in conditions:
        W, ext = ei_network(f_inh, w_max, w_inh, 20261104, e_max)
        worst, outside, total = measure(W, ext, 600)
        print(f"E/I f_inh={f_inh} w_inh={w_inh} w_max={w_max} e_max={e_max}: "
              f"largest |exact sum| = {worst}, samples outside 16 bits = {outside} of {total}")


if __name__ == "__main__":
    main()
