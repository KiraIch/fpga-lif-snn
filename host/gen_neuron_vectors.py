"""Generate the single-neuron test vectors from the reference model (model/fixed.py).

The expected replies come from the Python model, not from the RTL. The
testbench (sim/tb_neuron_top.v) checks the board logic against them byte by byte.

Writes to sim/ (run from the repository root):
    neuron_stream.mem   bytes sent to the board
    neuron_expect.mem   bytes of the expected replies, in order
    neuron_meta.mem     two 16-bit words: length of the stream, length of the replies

Scenario: set parameters, run 40 steps at input +0.1, read the trace in two
20-sample pieces; then run 10 steps at input -0.1 from rest (checks that RUN
resets the neuron, and that negative potentials and arithmetic shifts match)
and read those 10 samples.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SIM = os.path.join(HERE, "..", "sim")
sys.path.insert(0, os.path.join(HERE, "..", "model"))

from protocol import Cmd, RESPONSE_FLAG, encode, pack_params, pack_read_record, pack_run  # noqa: E402
from fixed import Params, State, step, to_q  # noqa: E402

PARAMS = dict(theta=512, v_reset=0, v_rest=-64, k_m=4, k_s=3, refrac=2)


def model_trace(p, inputs):
    """Return [(V, spike)] per step, starting from rest, as the board should record it."""
    s = State()
    out = []
    for x in inputs:
        s, spk = step(s, p, x)
        out.append((s.v, spk))
    return out


def record_reply(trace, start, count):
    payload = bytearray()
    for v, spk in trace[start:start + count]:
        payload += (v & 0xFFFF).to_bytes(2, "little") + bytes([spk])
    return encode(Cmd.READ_RECORD | RESPONSE_FLAG, bytes(payload))


def main():
    p = Params(**PARAMS)
    x1 = to_q(0.1)
    x2 = to_q(-0.1)
    trace1 = model_trace(p, [x1] * 40)
    trace2 = model_trace(p, [x2] * 10)

    # (frame, expected reply bytes). The testbench sends each frame and waits for
    # its reply, as the host must do: a RUN or READ sent during a reply is refused.
    frames = [
        (encode(Cmd.WRITE_PARAM, pack_params(**PARAMS)), b""),
        (encode(Cmd.RUN, pack_run(x1, 40)), b""),
        (encode(Cmd.READ_RECORD, pack_read_record(0, 20)), record_reply(trace1, 0, 20)),
        (encode(Cmd.READ_RECORD, pack_read_record(20, 20)), record_reply(trace1, 20, 20)),
        (encode(Cmd.RUN, pack_run(x2, 10)), b""),
        (encode(Cmd.READ_RECORD, pack_read_record(0, 10)), record_reply(trace2, 0, 10)),
    ]
    stream = b"".join(f for f, _ in frames)
    expect = b"".join(r for _, r in frames)

    with open(os.path.join(SIM, "neuron_stream.mem"), "w") as f:
        for b in stream:
            f.write(f"{b:02x}\n")
    with open(os.path.join(SIM, "neuron_expect.mem"), "w") as f:
        for b in expect:
            f.write(f"{b:02x}\n")
    # Meta: frame count, then (frame length, reply length) per frame.
    with open(os.path.join(SIM, "neuron_meta.mem"), "w") as f:
        f.write(f"{len(frames):04x}\n")
        for frame, reply in frames:
            f.write(f"{len(frame):04x}\n{len(reply):04x}\n")

    spikes1 = sum(s for _, s in trace1)
    print(f"stream {len(stream)} bytes, expected replies {len(expect)} bytes, {len(frames)} frames")
    print(f"run 1: {spikes1} spikes in 40 steps, V range {min(v for v, _ in trace1)}..{max(v for v, _ in trace1)}")


if __name__ == "__main__":
    main()
