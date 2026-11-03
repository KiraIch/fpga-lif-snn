"""M2 board comparison: one LIF neuron on the Tang Nano 20K against model/fixed.py.

For each parameter set and each of 20 constant input currents:
  1. WRITE_PARAM, then READ_STATUS to confirm the board has the parameters.
  2. RUN 1000 steps on the board (the neuron starts at rest).
  3. READ_RECORD the trace in 32-sample pieces.
  4. Compare V and spike of every step with the Python model, bit for bit.

Parameter sets:
  A  typical values                     (k_m=4, k_s=3, refrac=2, V_rest<0)
  B  zero shifts and a positive V_rest  (k_m=0, k_s=0: the shift leaves the value unchanged;
                                         v_reset<0, refrac=0; theta is low enough to spike)
  C  maximum shifts and refractory      (k_m=15, k_s=15: the shift floors small negatives
                                         to -1; refrac=7; v_reset<0)

Results go to build/m2_trial_<set>.json. Set A is also written to build/m2_trial.json,
which host/plot_trial.py reads.

Usage (repository root, after `make flash TOP=neuron_top` in fpga/):
    python3 host/run_trial.py [/dev/ttyUSB1]
"""

import json
import os
import select
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
sys.path.insert(0, os.path.join(ROOT, "model"))
sys.path.insert(0, HERE)

from fixed import Params, State, step, to_q  # noqa: E402
from protocol import (  # noqa: E402
    Cmd,
    FrameParser,
    encode,
    pack_params,
    pack_read_record,
    pack_run,
    unpack_q88,
    unpack_records,
)
from uart_loopback import open_port  # noqa: E402

PARAM_SETS = {
    "A": dict(theta=512, v_reset=0, v_rest=-64, k_m=4, k_s=3, refrac=2),
    "B": dict(theta=128, v_reset=-128, v_rest=64, k_m=0, k_s=0, refrac=0),
    "C": dict(theta=512, v_reset=-128, v_rest=0, k_m=15, k_s=15, refrac=7),
}
STEPS = 1000
CHUNK = 32
INPUTS = [round(-0.1 + 0.025 * k, 4) for k in range(20)]   # -0.1 .. 0.375, real units
TIMEOUT_S = 3.0


def send(fd, frame):
    os.write(fd, frame)
    time.sleep(0.02)


def read_frame(fd, parser, want_cmd):
    """Return the data of the next frame with cmd == want_cmd, or None on timeout."""
    deadline = time.monotonic() + TIMEOUT_S
    while time.monotonic() < deadline:
        ready, _, _ = select.select([fd], [], [], 0.05)
        if ready:
            for cmd, data in parser.feed(os.read(fd, 4096)):
                if cmd == want_cmd:
                    return data
    return None


def read_status(fd):
    parser = FrameParser()
    send(fd, encode(Cmd.READ_STATUS))
    data = read_frame(fd, parser, Cmd.READ_STATUS | 0x80)
    if data is None or len(data) != 11:
        return None
    theta, v_reset, v_rest = unpack_q88(data[0:6])
    return dict(theta=theta, v_reset=v_reset, v_rest=v_rest, k_m=data[6], k_s=data[7],
                refrac=data[8], ok=data[9], err=data[10])


def model_trace(p, x_raw, steps):
    s = State()
    out = []
    for _ in range(steps):
        s, spk = step(s, p, x_raw)
        out.append((s.v, spk))
    return out


def board_trace(fd, parser, steps):
    """Read the whole record of the last run, in CHUNK-sized requests. None if any request fails."""
    trace = []
    for start in range(0, steps, CHUNK):
        count = min(CHUNK, steps - start)
        send(fd, encode(Cmd.READ_RECORD, pack_read_record(start, count)))
        data = read_frame(fd, parser, Cmd.READ_RECORD | 0x80)
        if data is None or len(data) != 3 * count:
            return None
        trace += unpack_records(data)
    return trace


def run_set(fd, parser, name, params_kw):
    """Run one parameter set. Returns (all_ok, samples, mismatches, failures, runs)."""
    send(fd, encode(Cmd.WRITE_PARAM, pack_params(**params_kw)))
    st = read_status(fd)
    if st is None or any(st[k] != v for k, v in params_kw.items()):
        print(f"set {name}: FAIL parameters not confirmed by the board: {st}")
        return False, 0, 0, 1, []
    print(f"set {name}: parameters confirmed: {params_kw}")

    p = Params(**params_kw)
    runs = []
    samples = 0
    bad_total = 0
    failures = 0

    for x in INPUTS:
        x_raw = to_q(x)
        send(fd, encode(Cmd.RUN, pack_run(x_raw, STEPS)))
        hw = board_trace(fd, parser, STEPS)
        if hw is None:
            failures += 1
            print(f"  input {x:+.4f}: FAIL no complete record from the board")
            continue
        ref = model_trace(p, x_raw, STEPS)
        bad = sum(1 for a, b in zip(hw, ref) if a != b)
        bad_total += bad
        samples += len(ref)
        hw_spikes = sum(s for _, s in hw)
        ref_spikes = sum(s for _, s in ref)
        status = "PASS" if bad == 0 else "FAIL"
        print(f"  input {x:+.4f} (raw {x_raw:+5d}): {status}  mismatches {bad}/{len(ref)}  "
              f"spikes hw {hw_spikes} model {ref_spikes}  "
              f"V range {min(v for v, _ in hw)}..{max(v for v, _ in hw)}")
        runs.append(dict(x=x, x_raw=x_raw, hw=hw, ref=ref, mismatches=bad))

    ok = bad_total == 0 and failures == 0 and len(runs) == len(INPUTS)
    print(f"set {name}: samples {samples}, mismatches {bad_total}, failed reads {failures}  "
          f"-> {'PASS' if ok else 'FAIL'}")
    return ok, samples, bad_total, failures, runs


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyUSB1"
    fd = open_port(path)
    parser = FrameParser()
    print(f"Port {path} open at 115200 8N1")

    os.makedirs(os.path.join(ROOT, "build"), exist_ok=True)
    all_ok = True
    total_samples = 0
    total_bad = 0
    for name, params_kw in PARAM_SETS.items():
        ok, samples, bad, failures, runs = run_set(fd, parser, name, params_kw)
        all_ok = all_ok and ok
        total_samples += samples
        total_bad += bad
        out = os.path.join(ROOT, "build", f"m2_trial_{name}.json")
        with open(out, "w") as f:
            json.dump(dict(params=params_kw, steps=STEPS, runs=runs), f)
        if name == "A":
            with open(os.path.join(ROOT, "build", "m2_trial.json"), "w") as f:
                json.dump(dict(params=params_kw, steps=STEPS, runs=runs), f)
        print()

    st_end = read_status(fd)
    os.close(fd)

    print(f"all sets: samples compared {total_samples}, mismatches {total_bad}")
    print(f"board counters at end: {st_end}")
    print("M2 BOARD COMPARE: PASS" if all_ok else "M2 BOARD COMPARE: FAIL")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
