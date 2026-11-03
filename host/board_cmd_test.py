"""Board test for the command link (rtl/cmd_test.v, flashed as TOP=cmd_test).

Sends WRITE_PARAM and READ_STATUS frames to the board, reads the STATUS reply,
and checks the parameters and counters against what was sent. Frames with a
bad checksum, an out-of-range value, or an unknown command must be counted as
errors and must not change the parameters.

Usage (from the repository root):
    python3 host/board_cmd_test.py [/dev/ttyUSB1]
"""

import os
import select
import sys
import time

from protocol import Cmd, FrameParser, encode, pack_params, pack_q88, unpack_q88
from uart_loopback import open_port

REPLY_CMD = Cmd.READ_STATUS | 0x80
TIMEOUT_S = 2.0


def send(fd, frame):
    os.write(fd, frame)
    time.sleep(0.02)  # one frame is far below the bridge limit; wait for the board to process it


def read_reply(fd, parser):
    """Return the next (cmd, data) frame from the board, or None on timeout."""
    deadline = time.monotonic() + TIMEOUT_S
    while time.monotonic() < deadline:
        ready, _, _ = select.select([fd], [], [], 0.05)
        if ready:
            frames = parser.feed(os.read(fd, 4096))
            if frames:
                return frames[0]
    return None


def read_status(fd):
    """Send READ_STATUS and return a dict of the reply fields, or None."""
    parser = FrameParser()
    send(fd, encode(Cmd.READ_STATUS))
    frame = read_reply(fd, parser)
    if frame is None:
        return None
    cmd, data = frame
    if cmd != REPLY_CMD or len(data) != 11:
        return {"bad_reply": (cmd, len(data))}
    theta, v_reset, v_rest = unpack_q88(data[0:6])
    return {
        "theta": theta, "v_reset": v_reset, "v_rest": v_rest,
        "k_m": data[6], "k_s": data[7], "refrac": data[8],
        "ok": data[9], "err": data[10],
    }


def param_fields(theta, v_reset, v_rest, k_m, k_s, refrac):
    return {"theta": theta, "v_reset": v_reset, "v_rest": v_rest,
            "k_m": k_m, "k_s": k_s, "refrac": refrac}


def check(name, cond, detail=""):
    print(("PASS " if cond else "FAIL ") + name + (f"  {detail}" if detail and not cond else ""))
    return cond


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyUSB1"
    fd = open_port(path)
    print(f"Port {path} open at 115200 8N1")

    results = []

    start = read_status(fd)
    if start is None or "bad_reply" in start:
        print(f"FAIL no STATUS reply at start: {start}")
        os.close(fd)
        return 1
    print(f"start: {start}")
    # Expected counters. The board counts every valid frame, READ_STATUS included.
    exp = {"ok": start["ok"], "err": start["err"]}
    good1 = param_fields(0x0180, -256, 0, 4, 3, 5)
    good2 = param_fields(0x0200, 0x0040, -0x0100, 2, 7, 7)

    def expect(state, want_params, label):
        """Check a STATUS reply against the expected counters and parameters.

        The caller updates exp for the frame it just sent. This READ_STATUS is
        itself a valid frame, so the expected ok count goes up by one here.
        """
        if state is None or "bad_reply" in state:
            return check(label, False, f"no valid reply: {state}")
        got = {k: state[k] for k in want_params}
        counters_ok = state["ok"] == (exp["ok"] + 1) % 256 and state["err"] == exp["err"] % 256
        exp["ok"] += 1
        return check(label, counters_ok and got == want_params, f"reply={state}")

    # 1. A valid WRITE_PARAM is accepted and the reply shows the new values.
    send(fd, encode(Cmd.WRITE_PARAM, pack_params(**good1)))
    exp["ok"] += 1
    results.append(expect(read_status(fd), good1, "valid WRITE_PARAM is applied"))

    # 2. A frame with a bad checksum is rejected and changes nothing.
    bad = bytearray(encode(Cmd.WRITE_PARAM, pack_params(**param_fields(0x0300, 0, 0, 1, 1, 1))))
    bad[-1] ^= 0x01
    send(fd, bytes(bad))
    exp["err"] += 1
    results.append(expect(read_status(fd), good1, "bad checksum is rejected"))

    # 3. k_m = 16 is out of range (4-bit field): rejected, parameters unchanged.
    out_of_range = encode(Cmd.WRITE_PARAM, pack_q88([0x0300, 0, 0]) + bytes([16, 1, 1]))
    send(fd, out_of_range)
    exp["err"] += 1
    results.append(expect(read_status(fd), good1, "k_m = 16 is rejected"))

    # 4. An unknown command is counted as an error.
    send(fd, encode(0x7E))
    exp["err"] += 1
    results.append(expect(read_status(fd), good1, "unknown command is rejected"))

    # 5. A second valid WRITE_PARAM replaces the parameters.
    send(fd, encode(Cmd.WRITE_PARAM, pack_params(**good2)))
    exp["ok"] += 1
    results.append(expect(read_status(fd), good2, "second valid WRITE_PARAM is applied"))

    os.close(fd)
    passed = sum(bool(r) for r in results)
    print(f"\n{passed}/{len(results)} checks passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
