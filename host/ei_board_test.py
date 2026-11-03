"""Run one E/I condition on the Tang Nano 20K and check every reply against model/network.py.

The network is built the same way as in host/ei_sweep.py (same seed, same draws), so the
board sees the same weights and inputs as the sweep. The expected replies come from the
exact model, run_network, not from the sparse sweep. So this also checks the sweep.

Usage (from host/, with the N = 256 bitstream loaded):
    python ei_board_test.py /dev/ttyUSB1 --f-inh 0.2 --w-max 10 --e-max 30 --steps 600

Frames (host/protocol.py): WRITE_PARAM, WRITE_WEIGHTS, SET_INPUT, RUN, READ_STATUS,
READ_COUNTS, READ_SNAPSHOT, READ_TRACE (the spikes of the first min(steps, 512) steps, 7 per
frame). The board keeps its counters across sessions, so the first
READ_STATUS gives the starting ok and err counts, and the expected values are relative to it.
"""

import argparse
import os
import random
import select
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "model"))

import ei_full_sweep  # noqa: E402
import ei_sweep  # noqa: E402
from fixed import Params  # noqa: E402
from network import run_network  # noqa: E402
from protocol import (  # noqa: E402
    TRACE_MAX_STEPS,
    TRACE_STEPS,
    Cmd,
    encode,
    pack_params,
    pack_read_block,
    pack_read_trace,
    pack_run,
    pack_set_input,
    pack_write_weights,
)
from uart_loopback import BAUD_RATE, open_port  # noqa: E402

N = ei_sweep.N
CHUNK = 16            # bytes per paced write (the USB-UART bridge drops bytes above ~64 back to back)
RUN_WAIT_S = 2.0
REPLY_TIMEOUT_S = 10.0
CMD_STATUS_REPLY = 0x86
CMD_COUNTS_REPLY = 0x87
CMD_SNAPSHOT_REPLY = 0x88
CMD_TRACE_REPLY = 0x89


def trace_data(trace, start, count):
    """Expected READ_TRACE reply: N/8 bytes per step, bit j of byte b is neuron 8b+j."""
    out = bytearray()
    for t in range(start, start + count):
        for b in range(N // 8):
            out.append(sum(trace[t][8 * b + j][1] << j for j in range(8)))
    return bytes(out)


def build_frames(W, ext, steps, ok0, err0):
    """Return a list of (frame bytes, expected reply bytes or None), and the expected final counts."""
    frames = []
    ok = ok0
    err = err0

    def valid(cmd, payload, reply=None):
        nonlocal ok
        ok = (ok + 1) & 0xFF
        frames.append((encode(cmd, payload), reply))

    w_flat = [W[j][i] for j in range(N) for i in range(N)]
    valid(Cmd.WRITE_PARAM, pack_params(**ei_sweep.PARAMS))
    for start in range(0, N * N, 100):
        valid(Cmd.WRITE_WEIGHTS, pack_write_weights(start, w_flat[start:start + 100]))
    for start in range(0, N, 120):
        valid(Cmd.SET_INPUT, pack_set_input(start, ext[start:start + 120]))
    valid(Cmd.RUN, pack_run(0, steps))
    return frames, ok, err


def status_reply(ok, err, steps):
    return encode(CMD_STATUS_REPLY, bytes([ok & 0xFF, err & 0xFF, steps & 0xFF, steps >> 8]))


def send_paced(fd, data):
    pause = CHUNK * 10 / BAUD_RATE * 1.5
    for i in range(0, len(data), CHUNK):
        os.write(fd, bytes(data[i:i + CHUNK]))
        time.sleep(pause)


def read_exact(fd, n, timeout):
    out = bytearray()
    deadline = time.monotonic() + timeout
    while len(out) < n:
        left = deadline - time.monotonic()
        if left <= 0:
            break
        ready, _, _ = select.select([fd], [], [], left)
        if ready:
            out += os.read(fd, n - len(out))
    return bytes(out)


def exchange(fd, frame, expect):
    """Send one frame, read its reply (if any) and return (ok, got)."""
    send_paced(fd, frame)
    if expect is None:
        return True, None
    got = read_exact(fd, len(expect), REPLY_TIMEOUT_S)
    return got == expect, got


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("port")
    ap.add_argument("--f-inh", type=float, required=True)
    ap.add_argument("--w-inh", type=float, default=1.0)
    ap.add_argument("--w-max", type=int, default=10)
    ap.add_argument("--e-max", type=int, default=30)
    ap.add_argument("--steps", type=int, default=600)
    ap.add_argument("--seed", type=int, default=ei_sweep.SEED)
    args = ap.parse_args()

    # the same network and input as host/ei_full_sweep.py for this seed and parameters
    W = ei_full_sweep.build(args.f_inh, args.w_max, args.w_inh, random.Random(args.seed))
    ext_rng = random.Random(args.seed * 1000 + args.e_max)
    ext = [ext_rng.randint(0, args.e_max) for _ in range(N)]

    print(f"model: f_inh={args.f_inh} w_inh={args.w_inh} w_max={args.w_max} "
          f"e_max={args.e_max} steps={args.steps} seed={args.seed}")
    trace = run_network(Params(**ei_sweep.PARAMS), W, ext, args.steps)
    counts = [sum(trace[t][i][1] for t in range(args.steps)) for i in range(N)]
    last = trace[-1]
    print(f"model: mean rate {sum(counts) / (N * args.steps):.3f}, "
          f"silent {sum(1 for c in counts if c == 0) / N:.2f}")

    fd = open_port(args.port)
    try:
        # starting counters, from a status request (replies are checked after this)
        send_paced(fd, encode(Cmd.READ_STATUS))
        head = read_exact(fd, 8, REPLY_TIMEOUT_S)
        if len(head) != 8:
            print("FAIL: no reply to the starting READ_STATUS")
            return
        ok0, err0 = head[3], head[4]
        print(f"board starting counters: ok={ok0} err={err0}")

        # the starting READ_STATUS already counted itself, so ok0 is the count to continue from
        frames, ok, err = build_frames(W, ext, args.steps, ok0, err0)
        bad = 0
        n_frames = 0
        for frame, reply in frames:
            n_frames += 1
            good, _ = exchange(fd, frame, reply)
            if not good:
                bad += 1
                print(f"frame {n_frames}: unexpected reply")
            if frame[1] == Cmd.RUN:
                time.sleep(RUN_WAIT_S)

        # READ_STATUS after the run
        ok = (ok + 1) & 0xFF
        good, got = exchange(fd, encode(Cmd.READ_STATUS), status_reply(ok, err, args.steps))
        if not good:
            bad += 1
            print(f"status after run differs: got {got.hex() if got else None}")

        # READ_COUNTS and READ_SNAPSHOT, in blocks of 64 neurons
        for start in range(0, N, 64):
            n = min(64, N - start)
            data = b"".join(c.to_bytes(2, "little") for c in counts[start:start + n])
            ok = (ok + 1) & 0xFF
            good, got = exchange(fd, encode(Cmd.READ_COUNTS, pack_read_block(start, n)),
                                 encode(CMD_COUNTS_REPLY, data))
            if not good:
                bad += 1
                print(f"counts block at {start}: differs")
        for start in range(0, N, 64):
            n = min(64, N - start)
            data = b""
            for i in range(start, start + n):
                v, spk = last[i]
                data += (v & 0xFFFF).to_bytes(2, "little") + bytes([spk])
            ok = (ok + 1) & 0xFF
            good, got = exchange(fd, encode(Cmd.READ_SNAPSHOT, pack_read_block(start, n)),
                                 encode(CMD_SNAPSHOT_REPLY, data))
            if not good:
                bad += 1
                print(f"snapshot block at {start}: differs")

        # spike trace, 7 steps per frame, for the steps the board keeps (the first 512)
        kept = min(args.steps, TRACE_STEPS)
        trace_frames = 0
        for start in range(0, kept, TRACE_MAX_STEPS):
            n = min(TRACE_MAX_STEPS, kept - start)
            data = trace_data(trace, start, n)
            ok = (ok + 1) & 0xFF
            trace_frames += 1
            good, got = exchange(fd, encode(Cmd.READ_TRACE, pack_read_trace(start, n)),
                                 encode(CMD_TRACE_REPLY, data))
            if not good:
                bad += 1
                print(f"trace at step {start}: differs")
        print(f"trace: steps 0..{kept - 1} in {trace_frames} frames")
    finally:
        os.close(fd)

    if bad == 0:
        print(f"PASS: {n_frames + 1 + trace_frames} frames, counts, snapshot and trace match the model")
    else:
        print(f"FAIL: {bad} replies differ")


if __name__ == "__main__":
    main()
