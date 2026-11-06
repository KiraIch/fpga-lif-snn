"""Saturation board test: one LIF neuron on the Tang Nano 20K, driven into the 16-bit limits.

host/run_trial.py checks 20 moderate inputs and never reaches the limits in the sets A and B.
This script uses two parameter sets with maximum shifts (k_m = k_s = 15), so the synaptic
current and the membrane potential hit -32768 and +32767. Inputs are -128.0, -15.625, -3.90625,
+15.625 and +127.99609375 (raw -32768, -4000, -1000, +4000, +32767).

For each run it:
  1. counts, with a traced copy of model/fixed.py, how often each saturating addition clamps
     (i1, i2: the two additions of the current update; v1, v2: the two of the voltage update;
     + upper limit, - lower limit), and checks that the traced copy equals fixed.step;
  2. runs the board for 100 steps and compares V and spike of every step with the model.

The comparison and the protocol are those of host/run_trial.py. Results go to
build/saturation_board_test.json.

Usage (repository root, after `make flash TOP=neuron_top` in fpga/):
    python3 host/saturation_board_test.py [/dev/ttyUSB1]
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "model"))
sys.path.insert(0, HERE)

import fixed  # noqa: E402
import run_trial as rt  # noqa: E402
from clamp_census import count_clamps  # noqa: E402
from protocol import FrameParser  # noqa: E402
from uart_loopback import open_port  # noqa: E402

SAT_SETS = {
    "S1": dict(theta=512, v_reset=0, v_rest=0, k_m=15, k_s=15, refrac=0),
    "S2": dict(theta=512, v_reset=-128, v_rest=0, k_m=15, k_s=15, refrac=7),
}
SAT_INPUTS = [-128.0, -15.625, -3.90625, 15.625, 127.99609375]
SAT_STEPS = 100


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyUSB1"
    fd = open_port(path)
    parser = FrameParser()
    print(f"Port {path} open at 115200 8N1")

    rt.INPUTS = SAT_INPUTS
    rt.STEPS = SAT_STEPS
    report = {}
    all_ok = True
    for name, params_kw in SAT_SETS.items():
        ok, samples, bad, failures, runs = rt.run_set(fd, parser, name, params_kw)
        all_ok = all_ok and ok
        p = fixed.Params(**params_kw)
        for run in runs:
            run["clamps"] = {f"{pos}{sign}": n for (pos, sign), n in
                             sorted(count_clamps(p, run["x_raw"], SAT_STEPS).items())}
            print(f"  set {name} raw {run['x_raw']:+6d} clamps {run['clamps'] or 'none'}")
        report[name] = dict(params=params_kw, steps=SAT_STEPS, runs=runs)
        print()

    st_end = rt.read_status(fd)
    os.close(fd)

    os.makedirs(os.path.join(ROOT, "build"), exist_ok=True)
    with open(os.path.join(ROOT, "build", "saturation_board_test.json"), "w") as f:
        json.dump(report, f)
    print(f"board counters at end: {st_end}")
    print("SATURATION BOARD TEST: PASS" if all_ok else "SATURATION BOARD TEST: FAIL")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
