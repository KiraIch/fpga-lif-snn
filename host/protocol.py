"""Host-side frame format for the FPGA control link (UART, 115200 8N1).

Frame layout (from docs/ plan, I/O section):

    [SYNC 0xA5][cmd][len][data ... len bytes][checksum]

- len is the number of data bytes, 0..255.
- checksum is (cmd + len + sum(data)) mod 256.
- Multi-byte values are little-endian. Q8.8 values are signed 16-bit;
  weights are signed 8-bit.
- A response uses the same frame with RESPONSE_FLAG set in cmd.

The exact command codes and checksum rule are drafts; see docs/DECISIONS.md D-007.
"""

from enum import IntEnum

SYNC = 0xA5
MAX_DATA = 255
RESPONSE_FLAG = 0x80


class Cmd(IntEnum):
    WRITE_PARAM = 0x01    # write neuron parameters (theta, v_reset, v_rest, k_m, k_s, refrac)
    WRITE_WEIGHTS = 0x02  # write one block of the synaptic weight matrix
    SET_INPUT = 0x03      # set per-neuron constant input or noise level
    RUN = 0x04            # run T steps, store the record on the board
    READ_RECORD = 0x05    # read back the stored record
    READ_STATUS = 0x06    # read run state and error flags
    READ_COUNTS = 0x07    # network: spike count of each neuron in the last run
    READ_SNAPSHOT = 0x08  # network: V and spike of each neuron in the last step
    READ_TRACE = 0x09     # network: spikes of all neurons for some steps (first TRACE_STEPS of a run)


class FrameError(ValueError):
    """A frame is malformed: bad sync, wrong length, or bad checksum."""


def checksum(cmd: int, data: bytes) -> int:
    return (cmd + len(data) + sum(data)) & 0xFF


def encode(cmd: int, data: bytes = b"") -> bytes:
    """Build one frame."""
    if len(data) > MAX_DATA:
        raise ValueError(f"data is {len(data)} bytes; a frame holds at most {MAX_DATA}")
    return bytes([SYNC, cmd, len(data)]) + bytes(data) + bytes([checksum(cmd, data)])


def decode(frame: bytes) -> tuple[int, bytes]:
    """Check one complete frame and return (cmd, data)."""
    if len(frame) < 4 or frame[0] != SYNC:
        raise FrameError("bad sync byte or frame too short")
    cmd, n = frame[1], frame[2]
    if len(frame) != n + 4:
        raise FrameError(f"length field says {n} data bytes, frame has {len(frame) - 4}")
    data = bytes(frame[3:3 + n])
    if frame[-1] != checksum(cmd, data):
        raise FrameError("checksum mismatch")
    return cmd, data


class FrameParser:
    """Incremental parser for a byte stream from the board.

    Feed it whatever bytes arrive. It returns the complete, valid frames.
    A bad frame is skipped by moving past its sync byte, so parsing resumes
    at the next 0xA5. Junk before a sync byte is discarded.
    """

    def __init__(self):
        self._buf = bytearray()

    def feed(self, data: bytes) -> list[tuple[int, bytes]]:
        self._buf += data
        frames = []
        while True:
            start = self._buf.find(SYNC)
            if start < 0:
                self._buf.clear()
                break
            del self._buf[:start]
            if len(self._buf) < 3:
                break
            total = self._buf[2] + 4
            if len(self._buf) < total:
                break
            try:
                frames.append(decode(bytes(self._buf[:total])))
                del self._buf[:total]
            except FrameError:
                del self._buf[:1]
        return frames


def pack_q88(values) -> bytes:
    """Pack Q8.8 raw integers as signed 16-bit little-endian."""
    out = bytearray()
    for v in values:
        if not -32768 <= v <= 32767:
            raise ValueError(f"Q8.8 raw value {v} is outside signed 16-bit")
        out += int(v).to_bytes(2, "little", signed=True)
    return bytes(out)


def unpack_q88(data: bytes) -> list[int]:
    """Unpack signed 16-bit little-endian Q8.8 raw integers."""
    if len(data) % 2:
        raise ValueError("Q8.8 data must be an even number of bytes")
    return [int.from_bytes(data[i:i + 2], "little", signed=True) for i in range(0, len(data), 2)]


PARAM_LEN = 9


def pack_params(theta: int, v_reset: int, v_rest: int, k_m: int, k_s: int, refrac: int) -> bytes:
    """Payload of WRITE_PARAM: theta, v_reset, v_rest (Q8.8, 2 bytes each), then k_m, k_s, refrac (1 byte each)."""
    if not (0 <= k_m <= 15 and 0 <= k_s <= 15):
        raise ValueError("k_m and k_s must be 0..15")
    if not 0 <= refrac <= 7:
        raise ValueError("refrac must be 0..7")
    return pack_q88([theta, v_reset, v_rest]) + bytes([k_m, k_s, refrac])


RUN_MAX_STEPS = 1024
REC_MAX_COUNT = 64


def pack_run(input_q88: int, steps: int) -> bytes:
    """Payload of RUN: constant input (Q8.8, 2 bytes), then steps (1..1024, 2 bytes, little-endian)."""
    if not 1 <= steps <= RUN_MAX_STEPS:
        raise ValueError(f"steps must be 1..{RUN_MAX_STEPS}")
    return pack_q88([input_q88]) + steps.to_bytes(2, "little")


def pack_read_record(start: int, count: int) -> bytes:
    """Payload of READ_RECORD: first step (2 bytes), then count (1..64 samples, 1 byte)."""
    if not 0 <= start < RUN_MAX_STEPS:
        raise ValueError(f"start must be 0..{RUN_MAX_STEPS - 1}")
    if not 1 <= count <= REC_MAX_COUNT:
        raise ValueError(f"count must be 1..{REC_MAX_COUNT}")
    return start.to_bytes(2, "little") + bytes([count])


def unpack_records(data: bytes) -> list[tuple[int, int]]:
    """Unpack a READ_RECORD reply: per step, V (signed Q8.8, 2 bytes) then spike (0 or 1)."""
    if len(data) % 3:
        raise ValueError("record data must be a multiple of 3 bytes")
    out = []
    for i in range(0, len(data), 3):
        v = int.from_bytes(data[i:i + 2], "little", signed=True)
        spike = data[i + 2]
        if spike not in (0, 1):
            raise ValueError(f"spike byte is {spike}, expected 0 or 1")
        out.append((v, spike))
    return out


def pack_int8(values) -> bytes:
    """Pack signed 8-bit integers (synaptic weights)."""
    for v in values:
        if not -128 <= v <= 127:
            raise ValueError(f"weight {v} is outside signed 8-bit")
    return bytes(int(v) & 0xFF for v in values)


def unpack_int8(data: bytes) -> list[int]:
    return [b - 256 if b >= 128 else b for b in data]


# ---- network commands (rtl/network_top.v) ----

WEIGHTS_MAX_BYTES = 253   # 255 payload bytes minus the 2-byte start address
INPUT_MAX_VALUES = 126    # 255 payload bytes minus the start address, 2 bytes per value
BLOCK_MAX_COUNT = 64      # READ_COUNTS / READ_SNAPSHOT samples per frame


def pack_write_weights(start: int, weights) -> bytes:
    """Payload of WRITE_WEIGHTS: first flat index W[j][i] = j*N + i (2 bytes), then signed 8-bit weights."""
    if not 0 <= start <= 0xFFFF:
        raise ValueError("start must fit in 16 bits")
    if not 1 <= len(weights) <= WEIGHTS_MAX_BYTES:
        raise ValueError(f"WRITE_WEIGHTS takes 1..{WEIGHTS_MAX_BYTES} weights per frame")
    return start.to_bytes(2, "little") + pack_int8(weights)


def pack_set_input(start: int, values) -> bytes:
    """Payload of SET_INPUT: first neuron index (2 bytes), then Q8.8 external inputs (2 bytes each)."""
    if not 0 <= start <= 0xFFFF:
        raise ValueError("start must fit in 16 bits")
    if not 1 <= len(values) <= INPUT_MAX_VALUES:
        raise ValueError(f"SET_INPUT takes 1..{INPUT_MAX_VALUES} values per frame")
    return start.to_bytes(2, "little") + pack_q88(values)


def pack_read_block(start: int, count: int) -> bytes:
    """Payload of READ_COUNTS and READ_SNAPSHOT: first neuron (2 bytes), then count (1..64, 1 byte)."""
    if not 0 <= start <= 0xFFFF:
        raise ValueError("start must fit in 16 bits")
    if not 1 <= count <= BLOCK_MAX_COUNT:
        raise ValueError(f"count must be 1..{BLOCK_MAX_COUNT}")
    return start.to_bytes(2, "little") + bytes([count])


TRACE_STEPS = 512         # steps kept on the board, from the start of the last run
TRACE_MAX_STEPS = 7       # steps per READ_TRACE frame (7 x N/8 bytes fit in one reply)


def pack_read_trace(start: int, count: int) -> bytes:
    """Payload of READ_TRACE: first step (2 bytes), then count (1..7 steps, 1 byte)."""
    if not 0 <= start <= 0xFFFF:
        raise ValueError("start must fit in 16 bits")
    if not 1 <= count <= TRACE_MAX_STEPS:
        raise ValueError(f"count must be 1..{TRACE_MAX_STEPS}")
    return start.to_bytes(2, "little") + bytes([count])


def unpack_trace(data: bytes, n: int) -> list[list[int]]:
    """Unpack a READ_TRACE reply for n neurons: per step, n/8 bytes; neuron i is bit i % 8 of byte i // 8."""
    per_step = n // 8
    if n % 8 or len(data) % per_step:
        raise ValueError("trace data must be a whole number of steps")
    steps = []
    for s in range(0, len(data), per_step):
        row = []
        for byte in data[s:s + per_step]:
            row.extend((byte >> j) & 1 for j in range(8))
        steps.append(row)
    return steps


def unpack_counts(data: bytes) -> list[int]:
    """Unpack a READ_COUNTS reply: unsigned 16-bit count per neuron, little-endian."""
    if len(data) % 2:
        raise ValueError("count data must be an even number of bytes")
    return [int.from_bytes(data[i:i + 2], "little") for i in range(0, len(data), 2)]


def unpack_status(data: bytes) -> tuple[int, int, int]:
    """Unpack a READ_STATUS reply of the network build: ok_count, err_count, steps done (16-bit)."""
    if len(data) != 4:
        raise ValueError("network status is 4 bytes")
    return data[0], data[1], int.from_bytes(data[2:4], "little")
