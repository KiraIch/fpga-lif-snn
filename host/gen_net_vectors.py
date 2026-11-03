"""Generate network test vectors from model/network.py for sim/tb_network.v.

A small random E/I network (80% excitatory sources, 20% inhibitory, connection
probability min(0.5, 8/N): about 8 inputs per neuron), constant external drive, run from rest for T steps.
The expected output is the model's V after each step and the spike of that step,
for every neuron, in step-major order.

Writes to sim/ (run from the repository root):
    net_w.mem       W[j][i] at address j*N + i, 8-bit hex
    net_ext.mem     ext[i], 16-bit hex (Q8.8 raw)
    net_expect.mem  per (step, neuron): {spike, V} as 5 hex digits, step-major
    net_meta.mem    N, T, theta, v_reset, v_rest, k_m, k_s, refrac (16-bit hex each)
"""

import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SIM = os.path.join(HERE, "..", "sim")
sys.path.insert(0, os.path.join(HERE, "..", "model"))

from fixed import Params  # noqa: E402
from network import run_network  # noqa: E402

N = int(sys.argv[1]) if len(sys.argv) > 1 else 16
T = 200
SEED = 20261103
PARAMS = dict(theta=384, v_reset=0, v_rest=0, k_m=4, k_s=3, refrac=2)


def build_network(rng):
    n_exc = int(N * 0.8)
    W = [[0] * N for _ in range(N)]
    for j in range(N):
        for i in range(N):
            if rng.random() < min(0.5, 8 / N):   # about 8 inputs per neuron
                if j < n_exc:
                    W[j][i] = rng.randint(0, 60)
                else:
                    W[j][i] = -rng.randint(0, 60)
    ext = [rng.randint(0, 50) for _ in range(N)]
    return W, ext


def main():
    rng = random.Random(SEED)
    W, ext = build_network(rng)
    p = Params(**PARAMS)
    trace = run_network(p, W, ext, T)

    os.makedirs(SIM, exist_ok=True)
    with open(os.path.join(SIM, "net_w.mem"), "w") as f:
        for j in range(N):
            for i in range(N):
                f.write(f"{W[j][i] & 0xFF:02x}\n")
    with open(os.path.join(SIM, "net_ext.mem"), "w") as f:
        for x in ext:
            f.write(f"{x & 0xFFFF:04x}\n")
    with open(os.path.join(SIM, "net_expect.mem"), "w") as f:
        for row in trace:
            for v, spk in row:
                f.write(f"{(spk << 16) | (v & 0xFFFF):05x}\n")
    with open(os.path.join(SIM, "net_meta.mem"), "w") as f:
        values = [N, T, PARAMS["theta"], PARAMS["v_reset"], PARAMS["v_rest"],
                  PARAMS["k_m"], PARAMS["k_s"], PARAMS["refrac"]]
        for v in values:
            f.write(f"{v & 0xFFFF:04x}\n")

    total_spikes = sum(spk for row in trace for _, spk in row)
    per_neuron = [sum(trace[t][i][1] for t in range(T)) for i in range(N)]
    print(f"N={N} T={T} spikes total {total_spikes}, per neuron min {min(per_neuron)} max {max(per_neuron)}")
    print(f"connections {sum(1 for r in W for w in r if w)}, excitatory weights up to {max(max(r) for r in W)}")


if __name__ == "__main__":
    main()
