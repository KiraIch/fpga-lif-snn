"""cocotb tests for rtl/uart_tx.v and rtl/uart_rx.v (8N1, 115200 baud, 27 MHz).

Run inside WSL with the OSS CAD Suite environment loaded:
    source ~/oss-cad-suite/environment
    cd sim && make -f Makefile.uart

Tests
  test_tx_frame_timing                 bit widths on tx line are exactly CLK_DIV cycles
  test_tx_start_ignored_while_busy     start while busy is ignored (valid/ready)
  test_loopback_all_256_values         every byte value through tx -> rx
  test_loopback_10000_back_to_back     10,000 random bytes, no idle between frames
  test_loopback_10000_random_idle      2,000 random bytes with random idle between frames
  test_rx_external_baud_tolerance      rx fed by a bit-banged sender at -4 % .. +4 % bit time,
                                       random idle between frames
"""

import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, ReadOnly, RisingEdge

CLK_FRE = 27_000_000
BAUD = 115_200
CLK_DIV = (CLK_FRE + BAUD // 2) // BAUD  # must match the RTL: 234
PERIOD_PS = 37_038                        # 27 MHz (37.037 ns, rounded to an even ps count)

N_LOOPBACK = 10_000
N_IDLE = 2_000
N_EXT_PER_FACTOR = 200
SEED = 20261102


async def setup(dut, loop_en):
    Clock(dut.clk, PERIOD_PS, unit="ps").start()
    dut.tx_data.value = 0
    dut.tx_start.value = 0
    dut.loop_en.value = loop_en
    dut.ext_rx.value = 1
    await ClockCycles(dut.clk, 5)


class RxMonitor:
    """Collects every rx_data value on each rx_valid pulse."""

    def __init__(self, dut):
        self.data = []
        self.valid_cycles = 0
        self.multi_cycle_pulses = 0
        cocotb.start_soon(self._run(dut))

    async def _run(self, dut):
        prev = 0
        while True:
            await RisingEdge(dut.clk)
            await ReadOnly()
            v = int(dut.rx_valid.value)
            if v:
                self.valid_cycles += 1
                if prev:
                    self.multi_cycle_pulses += 1
                self.data.append(int(dut.rx_data.value))
            prev = v


async def tx_send(dut, values, gap_fn):
    """Send bytes through the valid/ready interface.

    gap_fn(i) returns the number of idle clock cycles inserted before byte i,
    counted from the cycle in which busy falls.
    """
    for i, value in enumerate(values):
        await ReadOnly()
        if int(dut.tx_busy.value):
            await FallingEdge(dut.tx_busy)
        await ClockCycles(dut.clk, gap_fn(i) + 1)   # now at a rising edge: writable
        dut.tx_data.value = value
        dut.tx_start.value = 1
        await RisingEdge(dut.clk)                   # DUT samples start=1 on this edge
        dut.tx_start.value = 0
    await ReadOnly()
    if int(dut.tx_busy.value):
        await FallingEdge(dut.tx_busy)


def compare(sent, received):
    errors = 0
    first = None
    for i, s in enumerate(sent):
        r = received[i] if i < len(received) else None
        if r != s:
            errors += 1
            if first is None:
                first = (i, s, r)
    extra = max(0, len(received) - len(sent))
    return errors + extra, first, extra


@cocotb.test()
async def test_tx_frame_timing(dut):
    """One frame of 0x55 (alternating bits): every bit is CLK_DIV cycles wide."""
    await setup(dut, loop_en=0)

    events = []  # (cycle, signal, value)
    cycle = 0
    prev_tx, prev_busy = 1, 0

    async def watch():
        nonlocal cycle, prev_tx, prev_busy
        while True:
            await RisingEdge(dut.clk)
            await ReadOnly()
            tx = int(dut.tx_line.value)
            busy = int(dut.tx_busy.value)
            if tx != prev_tx:
                events.append((cycle, "tx", tx))
            if busy != prev_busy:
                events.append((cycle, "busy", busy))
            prev_tx, prev_busy = tx, busy
            cycle += 1

    cocotb.start_soon(watch())
    await tx_send(dut, [0x55], lambda i: 0)
    await ClockCycles(dut.clk, 2)

    tx_edges = [c for c, sig, _ in events if sig == "tx"]
    busy_fall = [c for c, sig, v in events if sig == "busy" and v == 0]
    assert len(tx_edges) == 10, f"expected 10 tx edges for 0x55, got {len(tx_edges)}: {events}"
    diffs = [b - a for a, b in zip(tx_edges, tx_edges[1:])]
    assert all(d == CLK_DIV for d in diffs), f"bit widths {diffs}, expected all {CLK_DIV}"
    assert busy_fall and busy_fall[0] - tx_edges[-1] == CLK_DIV, "stop bit width mismatch"

    measured_baud = CLK_FRE / CLK_DIV
    err_pct = (measured_baud - BAUD) / BAUD * 100
    dut._log.info(f"frame timing OK: CLK_DIV={CLK_DIV}, baud={measured_baud:.1f}, err={err_pct:+.3f}%")


@cocotb.test()
async def test_tx_start_ignored_while_busy(dut):
    """A start pulse while busy must not queue a second frame."""
    await setup(dut, loop_en=1)
    mon = RxMonitor(dut)

    dut.tx_data.value = 0xA5
    dut.tx_start.value = 1
    await RisingEdge(dut.clk)
    dut.tx_start.value = 0
    await ClockCycles(dut.clk, 100)

    dut.tx_data.value = 0x3C
    dut.tx_start.value = 1
    await RisingEdge(dut.clk)
    dut.tx_start.value = 0
    await ClockCycles(dut.clk, 15 * CLK_DIV)

    assert mon.data == [0xA5], f"expected only 0xA5 to be sent, got {[hex(x) for x in mon.data]}"


@cocotb.test()
async def test_loopback_all_256_values(dut):
    """Every byte value 0x00..0xFF through tx -> rx, back to back."""
    await setup(dut, loop_en=1)
    mon = RxMonitor(dut)
    sent = list(range(256))
    await tx_send(dut, sent, lambda i: 0)
    await ClockCycles(dut.clk, 2 * CLK_DIV)

    errors, first, extra = compare(sent, mon.data)
    assert errors == 0, f"{errors} errors, first mismatch {first}, extra {extra}"
    assert mon.multi_cycle_pulses == 0, "data_valid was not a single-cycle pulse"


@cocotb.test()
async def test_loopback_10000_back_to_back(dut):
    """10,000 random bytes, next start right after the previous stop bit."""
    await setup(dut, loop_en=1)
    mon = RxMonitor(dut)
    rng = random.Random(SEED)
    sent = [rng.randrange(256) for _ in range(N_LOOPBACK)]

    await tx_send(dut, sent, lambda i: 0)
    await ClockCycles(dut.clk, 2 * CLK_DIV)

    errors, first, extra = compare(sent, mon.data)
    dut._log.info(f"back-to-back: sent={len(sent)} received={len(mon.data)} errors={errors}")
    assert errors == 0, f"{errors} errors, first mismatch {first}, extra {extra}"
    assert mon.multi_cycle_pulses == 0, "data_valid was not a single-cycle pulse"


@cocotb.test()
async def test_loopback_random_idle(dut):
    """2,000 random bytes with a random idle of 0..4 bit times between frames."""
    await setup(dut, loop_en=1)
    mon = RxMonitor(dut)
    rng = random.Random(SEED + 1)
    sent = [rng.randrange(256) for _ in range(N_IDLE)]

    await tx_send(dut, sent, lambda i: rng.randrange(0, 4 * CLK_DIV))
    await ClockCycles(dut.clk, 2 * CLK_DIV)

    errors, first, extra = compare(sent, mon.data)
    dut._log.info(f"random idle: sent={len(sent)} received={len(mon.data)} errors={errors}")
    assert errors == 0, f"{errors} errors, first mismatch {first}, extra {extra}"
    assert mon.multi_cycle_pulses == 0, "data_valid was not a single-cycle pulse"


@cocotb.test()
async def test_rx_external_baud_tolerance(dut):
    """rx fed by a bit-banged sender whose bit time is off by -4 % .. +4 %."""
    await setup(dut, loop_en=0)
    mon = RxMonitor(dut)
    rng = random.Random(SEED + 2)

    total_errors = 0
    for factor in (1.00, 1.02, 0.98, 1.03, 0.97, 1.04, 0.96):
        bit_cycles = round(CLK_DIV * factor)
        sent = [rng.randrange(256) for _ in range(N_EXT_PER_FACTOR)]
        before = len(mon.data)

        for value in sent:
            bits = [0] + [(value >> k) & 1 for k in range(8)] + [1]
            for b in bits:
                dut.ext_rx.value = b
                await ClockCycles(dut.clk, bit_cycles)
            idle = rng.randrange(0, 3 * CLK_DIV)
            dut.ext_rx.value = 1
            await ClockCycles(dut.clk, idle + 1)
        await ClockCycles(dut.clk, 2 * CLK_DIV)

        received = mon.data[before:]
        errors, first, extra = compare(sent, received)
        total_errors += errors
        dut._log.info(f"ext sender factor={factor:.2f} bit={bit_cycles} cycles: "
                      f"sent={len(sent)} received={len(received)} errors={errors}")
        assert errors == 0, f"factor {factor}: {errors} errors, first mismatch {first}, extra {extra}"

    assert mon.multi_cycle_pulses == 0, "data_valid was not a single-cycle pulse"
    assert total_errors == 0
