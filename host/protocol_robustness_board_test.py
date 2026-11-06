"""Protocol robustness on the board: the cases the 682-frame flow does not send.

Run on the board with a single-neuron build (neuron_top) or a network build; both use
rtl/cmd_decoder.v. Each case reports the replies received and the change of the error counter.

Cases:
  1. bad checksum on READ_STATUS            -> refused, err + 1, no reply
  2. unknown command 0x0A                    -> refused, err + 1, no reply
  3. busy: READ_STATUS sent while the board
     is still sending a READ_RECORD reply   -> refused, err + 1, only the READ_RECORD reply arrives
  4. truncated frame [A5 06 00], then a valid READ_STATUS
                                             -> the decoder has no time-out; the valid frame is
                                                taken as the rest of the bad one: no reply, err + 1
  5. recovery: a further valid READ_STATUS   -> answered, and err is unchanged from case 4

The expected values are written out before the run. The script exits with 1 if any case differs.

Usage (repository root, after `make flash TOP=neuron_top` or a network build in fpga/):
    python3 host/protocol_robustness_board_test.py [/dev/ttyUSB1]
"""

import os
import select
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import run_trial as rt  # noqa: E402
from protocol import FrameParser, pack_read_record, pack_run  # noqa: E402
from uart_loopback import open_port  # noqa: E402

CMD_READ_STATUS = 0x06
CMD_RUN = 0x04
CMD_READ_RECORD = 0x05
CMD_REPLY = 0x80
DRAIN_S = 0.4


def frame(cmd, data=b"", checksum_delta=0):
    """[0xA5][cmd][len][data][checksum]; checksum = sum of cmd, len and data, mod 256."""
    body = bytes([cmd, len(data)]) + data
    cs = (sum(body) + checksum_delta) & 0xFF
    return bytes([0xA5]) + body + bytes([cs])


def drain(fd, parser, seconds=DRAIN_S):
    """Collect every complete frame that arrives within `seconds`."""
    frames = []
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        ready, _, _ = select.select([fd], [], [], 0.02)
        if ready:
            frames += parser.feed(os.read(fd, 4096))
    return frames


def err_of(fd):
    st = rt.read_status(fd)
    if st is None:
        raise RuntimeError("READ_STATUS got no reply")
    return st["err"]


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyUSB1"
    fd = open_port(path)
    parser = FrameParser()
    print(f"Port {path} open at 115200 8N1")
    results = []
    last_err = [None]   # error counter after the most recent case

    def case(name, expect_replies, expect_err_delta, action):
        e0 = err_of(fd)
        frames = action()
        e1 = err_of(fd)
        last_err[0] = e1
        got = [c for c, _ in frames if c & CMD_REPLY]
        ok = (sorted(got) == sorted(expect_replies)) and (e1 - e0 == expect_err_delta)
        results.append(ok)
        print(f"{name}: replies {[hex(c) for c in got] or 'none'} "
              f"(expected {[hex(c) for c in expect_replies] or 'none'}), "
              f"err {e0} -> {e1} (expected +{expect_err_delta})  {'PASS' if ok else 'FAIL'}")

    def bad_checksum():
        os.write(fd, frame(CMD_READ_STATUS, checksum_delta=1))
        return drain(fd, parser)

    def unknown_command():
        os.write(fd, frame(0x0A))
        return drain(fd, parser)

    def busy_during_reply():
        os.write(fd, frame(CMD_READ_RECORD, pack_read_record(0, 32)))
        os.write(fd, frame(CMD_READ_STATUS))   # arrives while the 96-byte reply is being sent
        return drain(fd, parser)

    def truncated_then_valid():
        os.write(fd, bytes([0xA5, CMD_READ_STATUS, 0x00]))
        time.sleep(0.05)
        os.write(fd, frame(CMD_READ_STATUS))
        return drain(fd, parser)

    # READ_RECORD is valid only inside the last run (rtl/cmd_decoder.v), so case 3 needs a
    # run of at least 32 steps first. Without it the READ_RECORD is refused, with no reply.
    os.write(fd, frame(CMD_RUN, pack_run(0, 64)))
    drain(fd, parser, 0.1)

    case("1 bad checksum", [], 1, bad_checksum)
    case("2 unknown command", [], 1, unknown_command)
    case("3 busy during reply", [CMD_READ_RECORD | CMD_REPLY], 1, busy_during_reply)
    case("4 truncated frame", [], 1, truncated_then_valid)

    # the decoder must recover: a fresh valid frame is answered, and the error counter
    # is the same as after case 4 (the valid frame itself must not count as an error)
    frames = drain(fd, parser, 0.1)
    st = rt.read_status(fd)
    answered = st is not None
    err_same = answered and st["err"] == last_err[0]
    recovered = answered and err_same
    results.append(recovered)
    print(f"5 recovery after case 4: READ_STATUS {'answered' if answered else 'NOT answered'}, "
          f"err {last_err[0]} -> {st['err'] if answered else None} "
          f"(expected unchanged)  {'PASS' if recovered else 'FAIL'}")

    os.close(fd)
    all_ok = all(results)
    print("PROTOCOL ROBUSTNESS BOARD TEST: PASS" if all_ok else "PROTOCOL ROBUSTNESS BOARD TEST: FAIL")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
