"""Clamp census: which saturating additions of model/fixed.py clamp, in the runs used in the paper.

The single-neuron step has four saturating additions:
  i1  decay of the current      I - (I >> k_s)           (first addition of the current update)
  i2  input added to the current                          (second addition of the current update)
  v1  leak of the potential     V + ((V_rest - V) >> k_m) (first addition of the voltage update)
  v2  current added to V                                  (second addition of the voltage update)
Each clamp is counted as + (upper limit) or - (lower limit).

count_clamps() runs a traced copy of fixed.step and asserts, at every step, that the copy gives the
same state as fixed.step. The census then counts clamp events for:
  - set C of host/run_trial.py with the 20 board inputs, 1000 steps (board run, per-step match);
  - the grid and random sweeps of host/sweep.py: 3 inputs, 300 steps (board runs, per-step match);
  - constant inputs that drive the current and the potential into both limits.

Output: results/clamp_census.log (run from the repository root: python host/clamp_census.py).
This file does not import the board code, so it runs on any host.
"""

import os
import random
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "model"))

import fixed  # noqa: E402

POSITIONS = ("i1", "i2", "v1", "v2")


def count_clamps(p, x_raw, steps):
    """Clamp events per saturating addition over `steps` steps from rest, as a Counter.

    Keys are (position, sign), for example ("i2", "+"). Asserts that the traced copy equals
    fixed.step (state and spike) at every step.
    """
    hits = Counter()

    def sat(x, pos):
        if x > fixed.Q_MAX:
            hits[(pos, "+")] += 1
            return fixed.Q_MAX
        if x < fixed.Q_MIN:
            hits[(pos, "-")] += 1
            return fixed.Q_MIN
        return x

    s = fixed.State()
    r = fixed.State()
    for _ in range(steps):
        i1 = sat(s.i + (-(s.i >> p.k_s)), "i1")
        i_next = sat(i1 + x_raw, "i2")
        v1 = sat(s.v + ((p.v_rest - s.v) >> p.k_m), "v1")
        v_next = sat(v1 + i_next, "v2")
        if s.ref > 0:
            s = fixed.State(v=p.v_reset, i=i_next, ref=s.ref - 1)
            spk = 0
        elif v_next >= p.theta:
            s = fixed.State(v=p.v_reset, i=i_next, ref=p.refrac)
            spk = 1
        else:
            s = fixed.State(v=v_next, i=i_next, ref=0)
            spk = 0
        r, rspk = fixed.step(r, p, x_raw)
        assert (s.v, s.i, s.ref, spk) == (r.v, r.i, r.ref, rspk), "traced copy differs from fixed.step"
    return hits


def fmt(hits):
    return ", ".join(f"{pos}{sign}: {n}" for (pos, sign), n in sorted(hits.items())) or "none"


def sweep_census(name, sets, inputs, steps):
    """Clamp events and number of sets (with at least one clamp) per position, over all sets."""
    total = Counter()
    sets_with = Counter()
    for kw in sets:
        p = fixed.Params(**kw)
        seen = set()
        for xr in inputs:
            hits = count_clamps(p, fixed.to_q(xr), steps)
            total += hits
            seen.update(hits.keys())
        for key in seen:
            sets_with[key] += 1
    print(f"== {name}: {len(sets)} sets, inputs {inputs}, {steps} steps")
    print(f"   clamp events: {fmt(total)}")
    print(f"   sets with at least one clamp: {fmt(sets_with)}")
    print()


def main():
    print("Clamp census for model/fixed.py (raw Q8.8 values; + upper limit, - lower limit)")
    print()

    setC = dict(theta=512, v_reset=-128, v_rest=0, k_m=15, k_s=15, refrac=7)
    board_inputs = [round(-0.1 + 0.025 * k, 4) for k in range(20)]
    p = fixed.Params(**setC)
    total = Counter()
    per_input = {}
    for x in board_inputs:
        hits = count_clamps(p, fixed.to_q(x), 1000)
        total += hits
        if hits:
            per_input[fixed.to_q(x)] = hits
    print("== run_trial.py set C, 20 inputs (-0.1..0.375), 1000 steps")
    print(f"   clamp events: {fmt(total)}")
    print(f"   inputs with at least one clamp: {len(per_input)} of 20")
    for x_raw in sorted(per_input):
        print(f"     x_raw {x_raw:+6d}: {fmt(per_input[x_raw])}")
    print()

    for name, kw in (("run_trial.py set A", dict(theta=512, v_reset=0, v_rest=-64, k_m=4, k_s=3, refrac=2)),
                     ("run_trial.py set B", dict(theta=128, v_reset=-128, v_rest=64, k_m=0, k_s=0, refrac=0))):
        total = Counter()
        p = fixed.Params(**kw)
        for x in board_inputs:
            total += count_clamps(p, fixed.to_q(x), 1000)
        print(f"== {name}, 20 inputs, 1000 steps")
        print(f"   clamp events: {fmt(total)}")
        print()

    grid_fixed = dict(theta=256, v_reset=-64, v_rest=32)
    grid_sets = [dict(grid_fixed, k_m=k_m, k_s=k_s, refrac=refrac)
                 for k_m in range(16) for k_s in range(16) for refrac in range(8)]
    sweep_census("sweep.py grid", grid_sets, (-0.2, 0.1, 0.4), 300)

    rng = random.Random(20261103)
    random_sets = []
    for _ in range(200):
        random_sets.append(dict(
            theta=rng.randint(64, 1024),
            v_reset=rng.randint(-512, 256),
            v_rest=rng.randint(-512, 512),
            k_m=rng.randint(0, 15),
            k_s=rng.randint(0, 15),
            refrac=rng.randint(0, 7),
        ))
    sweep_census("sweep.py random (seed 20261103)", random_sets, (-0.2, 0.1, 0.4), 300)

    print("== saturation test (host/saturation_board_test.py), constant inputs, 100 steps")
    sat_inputs = [-128.0, -15.625, -3.90625, 15.625, 127.99609375]
    for name, kw in (("S1", dict(theta=512, v_reset=0, v_rest=0, k_m=15, k_s=15, refrac=0)),
                     ("S2", dict(theta=512, v_reset=-128, v_rest=0, k_m=15, k_s=15, refrac=7))):
        p = fixed.Params(**kw)
        for x in sat_inputs:
            hits = count_clamps(p, fixed.to_q(x), 100)
            print(f"   {name} x_raw {fixed.to_q(x):+6d}: {fmt(hits)}")
    print()

    print("== single-neuron search: which positions can be reached at all (100 steps)")
    p = fixed.Params(theta=512, v_reset=0, v_rest=0, k_m=15, k_s=15, refrac=0)
    for x_raw in (-32768, -4000, -1000, 1000, 4000, 32767):
        print(f"   x_raw {x_raw:+6d}: {fmt(count_clamps(p, x_raw, 100))}")


if __name__ == "__main__":
    main()
