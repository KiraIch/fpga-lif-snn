"""Parameter sweep for the single-neuron board test (M2).

Two sweeps, each parameter set compared bit for bit with model/fixed.py:

  grid    every legal value of the shift fields and the refractory counter:
          k_m 0..15 x k_s 0..15 x refrac 0..7 = 2048 sets, with theta, v_reset,
          v_rest fixed.
  random  200 sets drawn from a fixed seed: theta, v_reset, v_rest over the
          16-bit range (limited to values that matter), shifts and refrac over
          their legal ranges, and random input currents.

Each set: WRITE_PARAM, READ_STATUS (checks the parameters and that err did not
change), then RUN and READ_RECORD for each input, then a final READ_STATUS
(err must not change: every frame is valid). Runs are short (300 steps) to keep
the sweep time down.

Writes build/sweep_<mode>.csv, one row per set, and prints a summary.

Usage (repository root, board flashed with neuron_top):
    python3 host/sweep.py grid [/dev/ttyUSB1]
    python3 host/sweep.py random [/dev/ttyUSB1]
"""

import csv
import os
import random
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "model"))
sys.path.insert(0, HERE)

from fixed import Params, to_q  # noqa: E402
from protocol import Cmd, FrameParser, encode, pack_params, pack_run  # noqa: E402
from uart_loopback import open_port  # noqa: E402
import run_trial as rt  # noqa: E402

STEPS = 300
INPUTS = [-0.2, 0.1, 0.4]
GRID_FIXED = dict(theta=256, v_reset=-64, v_rest=32)


def grid_sets():
    for k_m in range(16):
        for k_s in range(16):
            for refrac in range(8):
                yield dict(GRID_FIXED, k_m=k_m, k_s=k_s, refrac=refrac)


def random_sets(n=200, seed=20261103):
    rng = random.Random(seed)
    for _ in range(n):
        yield dict(
            theta=rng.randint(64, 1024),
            v_reset=rng.randint(-512, 256),
            v_rest=rng.randint(-512, 512),
            k_m=rng.randint(0, 15),
            k_s=rng.randint(0, 15),
            refrac=rng.randint(0, 7),
        )


def run_one(fd, parser, params_kw, inputs):
    """Run one parameter set. Returns a dict describing the result."""
    result = dict(params_kw)
    result.update(mismatches=0, failures=0, spikes=0, err_delta=None, status="PASS", detail="")

    rt.send(fd, encode(Cmd.WRITE_PARAM, pack_params(**params_kw)))
    st0 = rt.read_status(fd)
    if st0 is None or any(st0[k] != v for k, v in params_kw.items()):
        result.update(status="FAIL", detail=f"parameters not confirmed: {st0}")
        return result

    p = Params(**params_kw)
    for x in inputs:
        x_raw = to_q(x)
        rt.send(fd, encode(Cmd.RUN, pack_run(x_raw, STEPS)))
        hw = rt.board_trace(fd, parser, STEPS)
        if hw is None:
            result["failures"] += 1
            continue
        ref = rt.model_trace(p, x_raw, STEPS)
        bad = [i for i, (a, b) in enumerate(zip(hw, ref)) if a != b]
        if bad and result["mismatches"] == 0:
            i = bad[0]
            result["detail"] = f"input {x}: first mismatch at step {i}: board {hw[i]} model {ref[i]}"
        result["mismatches"] += len(bad)
        result["spikes"] += sum(s for _, s in ref)

    st1 = rt.read_status(fd)
    if st1 is None:
        result["failures"] += 1
    else:
        result["err_delta"] = st1["err"] - st0["err"]

    if result["mismatches"] or result["failures"] or (result["err_delta"] not in (0, None)):
        result["status"] = "FAIL"
    return result


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in ("grid", "random"):
        print(__doc__)
        return 2
    mode = sys.argv[1]
    path = sys.argv[2] if len(sys.argv) > 2 else "/dev/ttyUSB1"
    sets = list(grid_sets()) if mode == "grid" else list(random_sets())

    fd = open_port(path)
    parser = FrameParser()
    print(f"sweep {mode}: {len(sets)} sets, {len(INPUTS)} inputs x {STEPS} steps each, port {path}", flush=True)

    fields = ["k_m", "k_s", "refrac", "theta", "v_reset", "v_rest",
              "mismatches", "failures", "err_delta", "spikes", "status", "detail"]
    os.makedirs(os.path.join(ROOT, "build"), exist_ok=True)
    out = os.path.join(ROOT, "build", f"sweep_{mode}.csv")
    passed = 0
    t0 = time.monotonic()
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for n, kw in enumerate(sets, 1):
            res = run_one(fd, parser, kw, INPUTS)
            w.writerow(res)
            passed += res["status"] == "PASS"
            if res["status"] != "PASS" or n % 128 == 0:
                print(f"[{n}/{len(sets)}] {res['status']} {kw} mismatches={res['mismatches']} "
                      f"failures={res['failures']} err_delta={res['err_delta']} {res['detail']}", flush=True)
            if n % 128 == 0:
                print(f"  progress {n}/{len(sets)}, {passed} PASS so far, "
                      f"{time.monotonic() - t0:.0f} s elapsed", flush=True)
    os.close(fd)

    print(f"sweep {mode}: {passed}/{len(sets)} sets PASS, written {out}", flush=True)
    print(f"sweep {mode}: {'PASS' if passed == len(sets) else 'FAIL'}", flush=True)
    return 0 if passed == len(sets) else 1


if __name__ == "__main__":
    sys.exit(main())
