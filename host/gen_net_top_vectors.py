"""Generate the byte-level test for rtl/network_top.v (sim/tb_network_top.v).

The frames are the ones the host sends in a real session: parameters, weights in
blocks, inputs, one run, then reads of the status, the spike counts and the
snapshot. A few bad frames are included; each must be counted as an error and
change nothing. The expected replies come from model/network.py.

Usage (from host/):  python gen_net_top_vectors.py [N] [T]    (defaults N = 16, T = 200)

T above 512 tests the trace limit: the board keeps the spikes of the first 512 steps only.

Writes to sim/ (the testbench's N must match):
    nt_stream.mem   every byte sent on rx, one hex byte per line
    nt_frames.mem   number of bytes in each frame, 16-bit hex per line
    nt_expect.mem   every byte the board must reply with, one hex byte per line
    nt_meta.mem     N, number of frames, number of reply bytes (16-bit hex each)
"""

import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SIM = os.path.join(HERE, "..", "sim")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "model"))

from fixed import Params  # noqa: E402
from network import run_network  # noqa: E402
from protocol import (  # noqa: E402
    Cmd,
    encode,
    pack_params,
    pack_read_block,
    pack_read_trace,
    pack_run,
    pack_set_input,
    pack_write_weights,
)

N = int(sys.argv[1]) if len(sys.argv) > 1 else 16
T = int(sys.argv[2]) if len(sys.argv) > 2 else 200
TRACE_STEPS = 512      # steps kept on the board (rtl/network_top.v TR_STEPS)
SEED = 20261103
PARAMS = dict(theta=384, v_reset=0, v_rest=0, k_m=4, k_s=3, refrac=2)
WEIGHT_CHUNK = 100     # weights per WRITE_WEIGHTS frame (any value up to 253)
INPUT_CHUNK = 120      # inputs per SET_INPUT frame (up to 126)
BLOCK_CHUNK = 64       # neurons per READ_COUNTS / READ_SNAPSHOT frame
CMD_READ_COUNTS = 0x07
CMD_READ_SNAPSHOT = 0x08
CMD_STATUS_REPLY = 0x86
CMD_COUNTS_REPLY = 0x87
CMD_SNAPSHOT_REPLY = 0x88
CMD_READ_TRACE = 0x09
CMD_TRACE_REPLY = 0x89


def trace_bytes(trace, start, count):
    """Spike trace for steps start..start+count-1: N/8 bytes per step, bit j of byte b is neuron 8b+j."""
    out = b""
    for t in range(start, start + count):
        for b in range(N // 8):
            out += bytes([sum(trace[t][8 * b + j][1] << j for j in range(8))])
    return out


def build_network(rng):
    """Same random E/I network as gen_net_vectors.py, for any N."""
    n_exc = int(N * 0.8)
    W = [[0] * N for _ in range(N)]
    for j in range(N):
        for i in range(N):
            if rng.random() < min(0.5, 8 / N):
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
    w_flat = [W[j][i] for j in range(N) for i in range(N)]

    frames = []        # (bytes of the frame, bytes of its reply)
    ok = 0
    err = 0

    def send(cmd, payload, reply=b"", reply_cmd=None):
        nonlocal ok
        frames.append((encode(cmd, payload), encode(reply_cmd, reply) if reply_cmd else b""))
        ok += 1

    def send_bad(frame):
        nonlocal err
        frames.append((frame, b""))
        err += 1

    send(Cmd.WRITE_PARAM, pack_params(**PARAMS))
    for start in range(0, N * N, WEIGHT_CHUNK):
        send(Cmd.WRITE_WEIGHTS, pack_write_weights(start, w_flat[start:start + WEIGHT_CHUNK]))
    send_bad(encode(Cmd.WRITE_WEIGHTS, bytes([N * N - 1 & 0xFF, (N * N - 1) >> 8, 1, 2])))   # runs past the end
    bad_param = bytearray(encode(Cmd.WRITE_PARAM, pack_params(theta=1024, v_reset=0, v_rest=0,
                                                              k_m=0, k_s=0, refrac=0)))
    bad_param[-1] ^= 0x10
    send_bad(bytes(bad_param))                                                                # checksum
    for start in range(0, N, INPUT_CHUNK):
        send(Cmd.SET_INPUT, pack_set_input(start, ext[start:start + INPUT_CHUNK]))

    # the board's counters wrap at 255
    ok_now = ok + 1
    send(Cmd.READ_STATUS, b"", bytes([ok_now & 0xFF, err & 0xFF, 0, 0]), CMD_STATUS_REPLY)
    send(Cmd.RUN, pack_run(0, T))

    steps = T
    send(Cmd.READ_STATUS, b"", bytes([(ok + 1) & 0xFF, err & 0xFF, steps & 0xFF, steps >> 8]),
         CMD_STATUS_REPLY)

    counts = [sum(trace[t][i][1] for t in range(T)) for i in range(N)]
    for start in range(0, N, BLOCK_CHUNK):
        n = min(BLOCK_CHUNK, N - start)
        data = b"".join(c.to_bytes(2, "little") for c in counts[start:start + n])
        send(Cmd.READ_COUNTS, pack_read_block(start, n), data, CMD_COUNTS_REPLY)

    last = trace[-1]
    for start in range(0, N, BLOCK_CHUNK):
        n = min(BLOCK_CHUNK, N - start)
        data = b""
        for i in range(start, start + n):
            v, spk = last[i]
            data += (v & 0xFFFF).to_bytes(2, "little") + bytes([spk])
        send(Cmd.READ_SNAPSHOT, pack_read_block(start, n), data, CMD_SNAPSHOT_REPLY)

    # spike trace: 7 steps from the start, the last steps of the run, and reads that
    # end exactly at the end of the trace or pass it by one step
    kept = min(T, TRACE_STEPS)
    send(Cmd.READ_TRACE, pack_read_trace(0, 7), trace_bytes(trace, 0, 7), CMD_TRACE_REPLY)
    send(Cmd.READ_TRACE, pack_read_trace(kept - 3, 3), trace_bytes(trace, kept - 3, 3), CMD_TRACE_REPLY)
    send(Cmd.READ_TRACE, pack_read_trace(kept - 7, 7), trace_bytes(trace, kept - 7, 7), CMD_TRACE_REPLY)
    send_bad(encode(Cmd.READ_TRACE, pack_read_trace(kept - 2, 3)))                 # ends one step past the trace
    send_bad(encode(Cmd.READ_TRACE, bytes([kept & 0xFF, kept >> 8, 1])))            # starts past the trace
    send_bad(encode(Cmd.READ_TRACE, bytes([0, 0, 0])))                              # count 0
    send_bad(encode(Cmd.READ_TRACE, bytes([0, 0, 8])))                              # count 8

    # a read that runs past the last neuron is an error
    send_bad(encode(Cmd.READ_COUNTS, bytes([(N - 1) & 0xFF, (N - 1) >> 8, 2])))

    ok_final = ok + 1
    send(Cmd.READ_STATUS, b"", bytes([ok_final & 0xFF, err & 0xFF, steps & 0xFF, steps >> 8]),
         CMD_STATUS_REPLY)

    stream = b"".join(f for f, _ in frames)
    replies = b"".join(r for _, r in frames)

    os.makedirs(SIM, exist_ok=True)
    with open(os.path.join(SIM, "nt_stream.mem"), "w") as f:
        for b in stream:
            f.write(f"{b:02x}\n")
    with open(os.path.join(SIM, "nt_frames.mem"), "w") as f:
        for fr, _ in frames:
            f.write(f"{len(fr):04x}\n")
    with open(os.path.join(SIM, "nt_expect.mem"), "w") as f:
        for b in replies:
            f.write(f"{b:02x}\n")
    with open(os.path.join(SIM, "nt_meta.mem"), "w") as f:
        for v in (N, len(frames), len(replies)):
            f.write(f"{v:04x}\n")

    print(f"N={N} T={T}: {len(frames)} frames, {len(stream)} bytes in, {len(replies)} bytes out")
    print(f"expected counters: ok={ok_final} err={err}; spikes total {sum(counts)}")


if __name__ == "__main__":
    main()
