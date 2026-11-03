"""Generate the command-decoder test stream from host/protocol.py.

Writes two files for sim/tb_cmd_decoder.v (run from the sim/ directory):

    sim/cmd_stream.mem   one byte per line, the raw bytes sent to the board
    sim/cmd_expect.mem   nine 16-bit words: theta, v_reset, v_rest, k_m, k_s,
                         refrac, ok_count, err_count, then the stream length

The stream holds one accepted frame, then four rejected ones (bad checksum,
unknown command, out-of-range k_m, and junk before a frame), then a second
accepted frame. Only the second accepted frame's parameters should remain.

Usage (from the repository root):
    python3 host/gen_cmd_vectors.py
"""

import os

from protocol import RESPONSE_FLAG, Cmd, encode, pack_params, pack_q88

HERE = os.path.dirname(os.path.abspath(__file__))
SIM = os.path.join(HERE, "..", "sim")


def write_param_frame(theta, v_reset, v_rest, k_m, k_s, refrac):
    return encode(Cmd.WRITE_PARAM, pack_params(theta, v_reset, v_rest, k_m, k_s, refrac))


def main():
    good1 = write_param_frame(0x0180, -256, 0, 4, 3, 5)
    good2 = write_param_frame(0x0200, 0x0040, -0x0100, 2, 7, 7)

    bad_checksum = bytearray(write_param_frame(0x0300, 0, 0, 1, 1, 1))
    bad_checksum[-1] ^= 0x01

    unknown_cmd = encode(0x7E)  # not implemented: must be counted as an error

    # Same layout as pack_params, but k_m = 16 is out of range, so the decoder must reject it.
    out_of_range = encode(Cmd.WRITE_PARAM, pack_q88([0x0100, 0, 0]) + bytes([16, 3, 5]))

    junk = bytes([0x00, 0x11, 0x22])

    stream = good1 + bytes(bad_checksum) + unknown_cmd + out_of_range + junk + good2

    # Expected register values come from good2's payload, not from the decoder.
    payload = pack_params(0x0200, 0x0040, -0x0100, 2, 7, 7)
    theta = int.from_bytes(payload[0:2], "little", signed=True)
    v_reset = int.from_bytes(payload[2:4], "little", signed=True)
    v_rest = int.from_bytes(payload[4:6], "little", signed=True)
    k_m, k_s, refrac = payload[6], payload[7], payload[8]
    ok_count, err_count = 2, 3

    values = [theta, v_reset, v_rest, k_m, k_s, refrac, ok_count, err_count, len(stream)]

    # Top-level test (sim/tb_cmd_test.v): one WRITE_PARAM, then READ_STATUS.
    # The reply must be a STATUS frame with the parameters and the counters.
    top_stream = write_param_frame(0x0180, -256, 0, 4, 3, 5) + encode(Cmd.READ_STATUS)
    top_payload = pack_q88([0x0180, -256, 0]) + bytes([4, 3, 5, 2, 0])  # ok=2 (both frames), err=0
    top_reply = encode(Cmd.READ_STATUS | RESPONSE_FLAG, top_payload)

    with open(os.path.join(SIM, "cmd_stream.mem"), "w") as f:
        for b in stream:
            f.write(f"{b:02x}\n")
    with open(os.path.join(SIM, "cmd_expect.mem"), "w") as f:
        for v in values:
            f.write(f"{v & 0xFFFF:04x}\n")
    with open(os.path.join(SIM, "top_stream.mem"), "w") as f:
        for b in top_stream:
            f.write(f"{b:02x}\n")
    with open(os.path.join(SIM, "top_expect.mem"), "w") as f:
        for b in top_reply:
            f.write(f"{b:02x}\n")

    print(f"stream: {len(stream)} bytes; top stream: {len(top_stream)} bytes; reply: {len(top_reply)} bytes")
    print("expect (theta, v_reset, v_rest, k_m, k_s, refrac, ok, err, len):", values)


if __name__ == "__main__":
    main()
