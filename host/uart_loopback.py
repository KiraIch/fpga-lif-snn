"""Loopback test for rtl/uart_echo.v on the Tang Nano 20K.

Sends byte patterns to the FPGA UART and checks that every byte comes back
unchanged and in order. Uses only the standard library (termios), so it runs
under WSL without extra packages.

Usage:
    python3 host/uart_loopback.py [/dev/ttyUSB1]
"""

import os
import random
import select
import sys
import termios
import time

BAUD = termios.B115200
BAUD_RATE = 115200
TIMEOUT_S = 3.0


def open_port(path):
    """Open a serial port as raw 8N1 at 115200 baud."""
    fd = os.open(path, os.O_RDWR | os.O_NOCTTY)
    attrs = termios.tcgetattr(fd)
    attrs[0] = 0                                             # iflag: no translation
    attrs[1] = 0                                             # oflag: raw output
    attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL  # cflag: 8N1
    attrs[3] = 0                                             # lflag: non-canonical, no echo
    attrs[4] = BAUD                                          # ispeed
    attrs[5] = BAUD                                          # ospeed
    attrs[6][termios.VMIN] = 0
    attrs[6][termios.VTIME] = 0
    termios.tcsetattr(fd, termios.TCSANOW, attrs)
    termios.tcflush(fd, termios.TCIOFLUSH)
    return fd


def loopback(fd, data, chunk=0):
    """Send data and return the bytes read back (up to len(data) or timeout).

    chunk=0 writes everything at once. Otherwise the host writes `chunk` bytes
    and waits about one line time for them before the next write. The USB-UART
    bridge has no hardware flow control and a small buffer, so a burst faster
    than 115200 baud loses bytes before they reach the FPGA.
    """
    if chunk == 0:
        os.write(fd, data)
    else:
        pause_s = chunk * 10 / BAUD_RATE * 1.5
        for k in range(0, len(data), chunk):
            os.write(fd, data[k:k + chunk])
            time.sleep(pause_s)

    got = bytearray()
    deadline = time.monotonic() + TIMEOUT_S
    while len(got) < len(data) and time.monotonic() < deadline:
        ready, _, _ = select.select([fd], [], [], 0.05)
        if ready:
            got += os.read(fd, 4096)
    return bytes(got)


def check(name, fd, data, chunk=0):
    """Run one loopback case, print the result, and return True on a full match."""
    got = loopback(fd, data, chunk)
    if got == data:
        print(f"PASS {name}: {len(data)} bytes echoed")
        return True

    first = next((i for i in range(min(len(got), len(data))) if got[i] != data[i]), None)
    if first is None:
        first = min(len(got), len(data))
    print(f"FAIL {name}: sent {len(data)} bytes, got {len(got)}; first mismatch at index {first}")
    print(f"     sent: {data[first:first + 8].hex()}")
    print(f"     got:  {got[first:first + 8].hex()}")
    return False


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyUSB1"
    fd = open_port(path)
    print(f"Port {path} open at 115200 8N1")

    rng = random.Random(20261103)
    # Bursts up to 64 bytes go out in one write. Longer runs are paced in
    # 16-byte chunks; a single 96+ byte burst loses bytes at the USB-UART bridge.
    cases = [
        ("16 ascending, one write", bytes(range(16)), 0),
        ("64 x 0x55, one write", bytes([0x55]) * 64, 0),
        ("all 256 values, paced", bytes(range(256)), 16),
        ("1000 random bytes, paced", bytes(rng.randrange(256) for _ in range(1000)), 16),
        ("10,000 random bytes, paced", bytes(rng.randrange(256) for _ in range(10000)), 16),
    ]

    results = [check(name, fd, data, chunk) for name, data, chunk in cases]
    os.close(fd)

    passed = sum(results)
    print(f"\n{passed}/{len(results)} cases passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
