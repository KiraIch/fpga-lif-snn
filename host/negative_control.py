"""Negative control for the board checker, on the traces the board actually returned.

The board comparison (host/run_trial.py run_set, host/sweep.py run_one, host/saturation_board_test.py)
counts the steps where the board trace differs from the model trace: `a != b` on (V, spike) pairs.
This script takes the board traces saved in build/saturation_board_test.json and checks that the
same comparison
  1. reports 0 differences for the unmodified traces (the board matched), and
  2. reports a difference for each deliberately injected error:
       - one membrane-potential bit flipped in the middle of one trace (V XOR 1),
       - one spike removed (a spike at the first step with a spike is cleared),
       - the model trace shifted by one step,
       - one whole trace replaced by the trace of another input.
If any injected error is not reported, the script fails.

Run from the repository root after host/saturation_board_test.py has written its JSON:
    python host/negative_control.py
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")


def mismatches(hw, ref):
    """Same comparison as host/run_trial.py run_set and host/sweep.py run_one."""
    return sum(1 for a, b in zip(hw, ref) if a != b)


def main():
    with open(os.path.join(ROOT, "build", "saturation_board_test.json")) as f:
        report = json.load(f)
    runs = [run for name in sorted(report) for run in report[name]["runs"]]
    print(f"board traces loaded: {len(runs)} runs, {sum(len(r['hw']) for r in runs)} steps")

    base_bad = sum(mismatches(r["hw"], r["ref"]) for r in runs)
    print(f"unmodified: differences {base_bad}  ({'PASS' if base_bad == 0 else 'FAIL'})")
    ok = base_bad == 0

    # a run whose trace changes under a one-step shift and that has spikes
    run = next(r for r in runs if r["ref"][1:] + r["ref"][:1] != r["ref"]
               and any(s for _, s in r["ref"]))
    hw, ref = run["hw"], run["ref"]
    mid = len(ref) // 2

    # 1. one V bit flipped in the model trace
    bad_ref = list(ref)
    v, s = bad_ref[mid]
    bad_ref[mid] = (v ^ 1, s)
    n1 = mismatches(hw, bad_ref)
    print(f"injected: one V bit flipped at step {mid}: differences {n1}  "
          f"({'detected' if n1 > 0 else 'MISSED'})")
    ok = ok and n1 > 0

    # 2. one spike removed from the model trace (if the run has a spike)
    spike_steps = [i for i, (_, s) in enumerate(ref) if s]
    if spike_steps:
        i = spike_steps[0]
        bad_ref = list(ref)
        bad_ref[i] = (bad_ref[i][0], 0)
        n2 = mismatches(hw, bad_ref)
        print(f"injected: spike at step {i} removed: differences {n2}  "
              f"({'detected' if n2 > 0 else 'MISSED'})")
        ok = ok and n2 > 0
    else:
        print("injected: spike removal skipped (no spikes in the chosen run)")

    # 3. model trace shifted by one step
    n3 = mismatches(hw, ref[1:] + ref[:1])
    print(f"injected: model trace shifted by one step: differences {n3}  "
          f"({'detected' if n3 > 0 else 'MISSED'})")
    ok = ok and n3 > 0

    # 4. a whole trace replaced by another run's model trace
    other = next(r for r in runs if r["ref"] != ref)
    n4 = mismatches(hw, other["ref"])
    print(f"injected: whole trace replaced by another input's model trace: differences {n4}  "
          f"({'detected' if n4 > 0 else 'MISSED'})")
    ok = ok and n4 > 0

    print("NEGATIVE CONTROL: PASS" if ok else "NEGATIVE CONTROL: FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
