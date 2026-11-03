"""cocotb bit-exact tests: rtl/lif_core.v vs model/fixed.py (the spec).

Run with `make -C sim` (PYTHONPATH must include model/; the Makefile sets it).
"""

import random

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer

from fixed import Q_MAX, Q_MIN, Params, State, run, step

N_RANDOM = 10_000
SEED = 20261102


def u16(x):
    return x & 0xFFFF


def s16(h):
    return h.value.to_signed()


# --------------------------------------------------------------------------
# combinational lif_core
# --------------------------------------------------------------------------

def drive(dut, st, p, syn):
    dut.v.value = u16(st.v)
    dut.i.value = u16(st.i)
    dut.ref_cnt.value = st.ref
    dut.syn_in.value = u16(syn)
    dut.theta.value = u16(p.theta)
    dut.v_reset.value = u16(p.v_reset)
    dut.v_rest.value = u16(p.v_rest)
    dut.k_m.value = p.k_m
    dut.k_s.value = p.k_s
    dut.refrac.value = p.refrac


async def check(dut, st, p, syn, tag=""):
    """Apply one input vector, compare all four outputs. Returns True if equal."""
    drive(dut, st, p, syn)
    await Timer(1, "ns")
    exp_s, exp_spk = step(st, p, syn)
    got = (s16(dut.v_next), s16(dut.i_next), int(dut.ref_next.value),
           int(dut.spike.value))
    exp = (exp_s.v, exp_s.i, exp_s.ref, exp_spk)
    if got != exp:
        dut._log.error(
            f"MISMATCH {tag}: in state={st} params={p} syn_in={syn}\n"
            f"  got (v_next,i_next,ref_next,spike)      = {got}\n"
            f"  expected (v_next,i_next,ref_next,spike) = {exp}")
        return False
    return True


def rand_q(rng):
    """Random Q8.8 value, biased toward saturation boundaries and zero."""
    c = rng.random()
    if c < 0.35:
        return rng.randint(Q_MIN, Q_MAX)
    if c < 0.55:
        return rng.choice([Q_MIN, Q_MIN + 1, Q_MAX, Q_MAX - 1, 0, 1, -1])
    if c < 0.75:
        return max(Q_MIN, min(Q_MAX, rng.choice([Q_MIN, Q_MAX]) + rng.randint(-300, 300)))
    return rng.randint(-1024, 1024)


@cocotb.test()
async def test_comb_random(dut):
    rng = random.Random(SEED)
    fails = 0
    first = None
    for n in range(N_RANDOM):
        st = State(v=rand_q(rng), i=rand_q(rng), ref=rng.randint(0, 7))
        p = Params(theta=rand_q(rng), v_reset=rand_q(rng), v_rest=rand_q(rng),
                   k_m=rng.randint(0, 15), k_s=rng.randint(0, 15),
                   refrac=rng.randint(0, 7))
        if rng.random() < 0.3:
            st.ref = 0  # make non-refractory paths well represented
        syn = rand_q(rng)
        if not await check(dut, st, p, syn, f"random#{n}"):
            fails += 1
            if first is None:
                first = n
    dut._log.info(f"random: {N_RANDOM - fails}/{N_RANDOM} match, {fails} fail")
    assert fails == 0, f"{fails} random mismatches (first at #{first})"


@cocotb.test()
async def test_comb_directed(dut):
    P = Params
    cases = []  # (tag, state, params, syn)
    base = P(theta=256, v_reset=0, v_rest=0, k_m=4, k_s=3, refrac=2)
    # saturation: positive and negative on i and v
    cases.append(("i sat +", State(0, Q_MAX, 0), base, Q_MAX))
    cases.append(("i sat -", State(0, Q_MIN, 0), base, Q_MIN))
    cases.append(("v sat +", State(Q_MAX, 0, 0), P(Q_MAX, 0, Q_MAX, 4, 3, 2), Q_MAX))
    cases.append(("v sat - (no fire)", State(Q_MIN, 0, 0), P(Q_MAX, 0, Q_MIN, 4, 3, 2), Q_MIN))
    cases.append(("v+i sat +", State(Q_MAX - 5, Q_MAX, 0), P(Q_MAX, 0, 0, 0, 0, 1), 10))
    cases.append(("v+i sat -", State(Q_MIN + 5, Q_MIN, 0), P(Q_MAX, 0, 0, 0, 0, 1), -10))
    # intermediate saturation then pull back (order of saturation matters)
    cases.append(("sat then back", State(Q_MAX, 0, 0), P(Q_MAX, 0, Q_MAX, 15, 15, 0), Q_MIN))
    cases.append(("i: sat then add neg", State(0, Q_MAX, 0), P(0, 0, 0, 4, 0, 0), -1))
    # theta boundary: v_next == theta, theta-1, theta+1
    for th in (100, 0, -50, Q_MAX, Q_MIN):
        for d in (-1, 0, 1):
            p = P(theta=th, v_reset=-7, v_rest=0, k_m=15, k_s=15, refrac=3)
            # v=0,i=0: v_next = 0 + (0>>15) + syn = syn, so syn = th + d
            syn = max(Q_MIN, min(Q_MAX, th + d))
            cases.append((f"theta={th} d={d}", State(0, 0, 0), p, syn))
    # refractory: input present, various ref values, strong input that would fire
    for r in range(8):
        cases.append((f"refrac ref={r}", State(0, 0, r),
                      P(100, -5, 0, 2, 2, 4), 5000))
    cases.append(("refrac neg input", State(0, 0, 3), P(100, -5, 0, 2, 2, 4), -5000))
    # k=0 corners
    cases.append(("k_s=0 i=-32768", State(0, Q_MIN, 0), P(Q_MAX, 0, 0, 4, 0, 0), 0))
    cases.append(("k_s=0 i=-32768 syn=-32768", State(0, Q_MIN, 0), P(Q_MAX, 0, 0, 4, 0, 0), Q_MIN))
    cases.append(("k_s=0 i=-32768 syn=+32767", State(0, Q_MIN, 0), P(Q_MAX, 0, 0, 4, 0, 0), Q_MAX))
    cases.append(("k_s=0 i=+32767", State(0, Q_MAX, 0), P(Q_MAX, 0, 0, 4, 0, 0), 0))
    cases.append(("k_m=0 v=-32768 rest=32767", State(Q_MIN, 0, 0), P(Q_MAX, 0, Q_MAX, 0, 3, 0), 0))
    cases.append(("k_m=0 v=32767 rest=-32768", State(Q_MAX, 0, 0), P(Q_MAX, 0, Q_MIN, 0, 3, 0), 0))
    cases.append(("k_m=0 both corners + i", State(Q_MIN, Q_MAX, 0), P(Q_MAX, 0, Q_MAX, 0, 0, 0), Q_MAX))
    cases.append(("k_m=0 mid", State(1000, 0, 0), P(Q_MAX, 0, -1000, 0, 3, 0), 0))
    # 17-bit leak difference with every shift amount
    for k in range(16):
        cases.append((f"diff17 k_m={k} +", State(Q_MIN, 0, 0), P(Q_MAX, 0, Q_MAX, k, 3, 0), 0))
        cases.append((f"diff17 k_m={k} -", State(Q_MAX, 0, 0), P(Q_MAX, 0, Q_MIN, k, 3, 0), 0))
        cases.append((f"i shift k_s={k} -", State(0, Q_MIN, 0), P(Q_MAX, 0, 0, 4, k, 0), 0))
        cases.append((f"i shift k_s={k} +", State(0, Q_MAX, 0), P(Q_MAX, 0, 0, 4, k, 0), 0))
    # refrac = 0 and 7 after spike
    cases.append(("refrac=0 fire", State(0, 0, 0), P(10, 0, 0, 4, 3, 0), 500))
    cases.append(("refrac=7 fire", State(0, 0, 0), P(10, 0, 0, 4, 3, 7), 500))
    # syn_in = -32768 generally
    cases.append(("syn=-32768 mid", State(5, 5, 0), P(10, 0, 0, 4, 3, 2), Q_MIN))
    cases.append(("syn=-32768 i low", State(0, Q_MIN + 100, 0), P(10, 0, 0, 4, 3, 2), Q_MIN))
    cases.append(("syn=-32768 ref>0", State(0, 0, 1), P(10, 0, 0, 4, 3, 2), Q_MIN))
    cases.append(("ref=1", State(0, 0, 1), P(10, 3, 0, 4, 3, 2), 500))

    fails = 0
    for tag, st, p, syn in cases:
        if not await check(dut, st, p, syn, tag):
            fails += 1
    dut._log.info(f"directed: {len(cases) - fails}/{len(cases)} match, {fails} fail")
    assert fails == 0, f"{fails} directed mismatches"


# --------------------------------------------------------------------------
# multi-step: lif_core + state register (sim/lif_core_reg.v)
# --------------------------------------------------------------------------

async def run_steps(dut, p, inputs):
    """Run inputs through the registered wrapper; return (spikes, errors)."""
    dut.theta.value = u16(p.theta)
    dut.v_reset.value = u16(p.v_reset)
    dut.v_rest.value = u16(p.v_rest)
    dut.k_m.value = p.k_m
    dut.k_s.value = p.k_s
    dut.refrac.value = p.refrac
    dut.syn_in.value = 0
    dut.rst.value = 1
    await RisingEdge(dut.clk)
    await Timer(1, "ns")
    dut.rst.value = 0

    s = State()
    spikes_rtl, spikes_exp, errors = [], [], []
    for n, x in enumerate(inputs):
        dut.syn_in.value = u16(x)
        await Timer(1, "ns")
        spikes_rtl.append(int(dut.spike.value))   # combinational on current state
        s, spk = step(s, p, x)
        spikes_exp.append(spk)
        await RisingEdge(dut.clk)
        await Timer(1, "ns")
        got = (s16(dut.v), s16(dut.i), int(dut.ref_r.value))
        if got != (s.v, s.i, s.ref):
            errors.append((n, got, (s.v, s.i, s.ref)))
    return spikes_rtl, spikes_exp, errors


@cocotb.test()
async def test_multistep(dut):
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    rng = random.Random(SEED + 1)
    steps = 500
    configs = [
        (Params(theta=256, v_reset=0, v_rest=0, k_m=4, k_s=3, refrac=3),
         lambda: rng.randint(20, 120)),                       # regular spiking
        (Params(theta=256, v_reset=0, v_rest=0, k_m=4, k_s=3, refrac=0),
         lambda: rng.randint(0, 200)),                        # no refractory
        (Params(theta=128, v_reset=-64, v_rest=-32, k_m=2, k_s=1, refrac=7),
         lambda: rng.randint(-100, 300)),                     # signed mix
        (Params(theta=Q_MAX, v_reset=Q_MIN, v_rest=Q_MAX, k_m=0, k_s=0, refrac=1),
         lambda: rng.choice([Q_MIN, Q_MAX, 0, rng.randint(Q_MIN, Q_MAX)])),  # extreme
        (Params(theta=0, v_reset=-500, v_rest=0, k_m=5, k_s=2, refrac=2),
         lambda: rng.randint(Q_MIN, Q_MAX)),                  # full-range random
    ]
    for _ in range(10):
        configs.append((
            Params(theta=rng.randint(0, 2000), v_reset=rng.randint(-500, 500),
                   v_rest=rng.randint(-500, 500), k_m=rng.randint(0, 8),
                   k_s=rng.randint(0, 8), refrac=rng.randint(0, 7)),
            (lambda: rng.randint(-200, 400))))

    total_spikes = 0
    bad = 0
    for ci, (p, gen) in enumerate(configs):
        inputs = [gen() for _ in range(steps)]
        ref_spikes = run(p, inputs)                      # fixed.run is the oracle
        spikes_rtl, spikes_exp, errors = await run_steps(dut, p, inputs)
        total_spikes += sum(ref_spikes)
        ok = spikes_rtl == ref_spikes and spikes_exp == ref_spikes and not errors
        dut._log.info(f"config {ci}: spikes={sum(ref_spikes)} "
                      f"{'OK' if ok else 'FAIL'} {p}")
        if not ok:
            bad += 1
            first = next((k for k in range(steps)
                          if spikes_rtl[k] != ref_spikes[k]), None)
            dut._log.error(f"config {ci} first spike mismatch at step {first}; "
                           f"first state error: {errors[0] if errors else None}")
    assert total_spikes > 0, "test never produced a spike; stimulus too weak"
    assert bad == 0, f"{bad}/{len(configs)} multi-step configs mismatched"
