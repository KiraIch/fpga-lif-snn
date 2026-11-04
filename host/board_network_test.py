"""Run the full network design on the Tang Nano 20K over the UART link.

Sends the frames that host/gen_net_top_vectors.py wrote to sim/ (nt_*.mem), in the
same order as the simulation, and checks every reply byte against the model.

The USB-UART bridge drops bytes when more than about 64 arrive back to back, so
the frames are sent in 16-byte chunks with a pause that matches the line speed.
Each frame with a reply is read in full before the next frame is sent. After a
RUN the script waits a fixed time, because RUN has no reply.

Usage (from host/, after gen_net_top_vectors.py N with the N of the bitstream):
    python board_network_test.py /dev/ttyUSB1
"""

import os
import select
import sys
import time

from uart_loopback import BAUD_RATE, open_port

HERE = os.path.dirname(os.path.abspath(__file__))
SIM = os.path.join(HERE, "..", "sim")

CHUNK = 16
CLK_HZ = 27000000     # board clock
BOARD_N = 256         # neurons in the bitstream
REPLY_TIMEOUT_S = 10.0


def run_wait_s(n, steps):
    """Time to wait after a RUN frame, since RUN has no reply.

    Worst case: every neuron spikes at every step, so the network takes about
    (N + N*N + 2*N) clocks per step. Times 1.2 for margin, plus 0.1 s.
    """
    return (n + n * n + 2 * n) * steps / CLK_HZ * 1.2 + 0.1


def load_hex(name):
    with open(os.path.join(SIM, name)) as f:
        return [int(line, 16) for line in f if line.strip()]


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


def main():
    port = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyUSB1"
    stream = load_hex("nt_stream.mem")
    frame_len = load_hex("nt_frames.mem")
    expect = load_hex("nt_expect.mem")
    n, nframes, nreply = load_hex("nt_meta.mem")
    assert len(stream) == sum(frame_len) and len(expect) == nreply
    if n != BOARD_N:
        print(f"WARNING: nt_meta.mem has N={n}, but the board bitstream is N={BOARD_N}; "
              f"run gen_net_top_vectors.py {BOARD_N} first")
    print(f"N={n}: {nframes} frames, {len(stream)} bytes in, {nreply} bytes expected back")

    fd = open_port(port)
    pos = 0          # position in the request stream
    epos = 0         # position in the expected reply stream
    bad = 0
    t0 = time.monotonic()
    try:
        for f in range(nframes):
            frame = stream[pos:pos + frame_len[f]]
            pos += frame_len[f]
            send_paced(fd, frame)

            # The reply, if any, is the next expected one, and its cmd is the request cmd + 0x80.
            has_reply = epos < nreply and expect[epos + 1] == (frame[1] | 0x80)
            if has_reply:
                rlen = expect[epos + 2] + 4          # sync, cmd, len, data, checksum
                want = bytes(expect[epos:epos + rlen])
                got = read_exact(fd, rlen, REPLY_TIMEOUT_S)
                epos += rlen
                if got != want:
                    bad += 1
                    print(f"frame {f} (cmd {frame[1]:#04x}): reply differs")
                    print(f"  want {want.hex()}")
                    print(f"  got  {got.hex()}")
            elif frame[1] == 0x04:
                # RUN payload: input (bytes 3..4), then steps (bytes 5..6, little-endian)
                steps = frame[5] | (frame[6] << 8)
                time.sleep(run_wait_s(n, steps))
            else:
                time.sleep(0.05)
    finally:
        os.close(fd)

    dt = time.monotonic() - t0
    if bad == 0 and epos == nreply:
        print(f"PASS: {nframes} frames, {nreply} reply bytes match the model ({dt:.1f} s)")
    else:
        print(f"FAIL: {bad} replies differ, {epos} of {nreply} reply bytes checked ({dt:.1f} s)")
        sys.exit(1)


if __name__ == "__main__":
    main()
