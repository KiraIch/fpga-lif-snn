"""Bit-exact fixed-point LIF neuron (Q8.8, signed 16-bit state).

This file is the specification for rtl/lif_core.v: every RTL result must
match it bit for bit. Rules are recorded in docs/DECISIONS.md.

- State values are signed 16-bit integers in Q8.8 (raw = real * 256).
- Every addition saturates to [-32768, 32767]; nothing wraps.
- ">>" on Python ints is an arithmetic shift (floors toward -inf), which
  matches ">>>" on signed registers in Verilog.
"""

from dataclasses import dataclass

FRAC_BITS = 8
Q_MIN = -(1 << 15)
Q_MAX = (1 << 15) - 1


def sat(x: int) -> int:
    """Clamp to the signed 16-bit range."""
    return min(max(x, Q_MIN), Q_MAX)


def sadd(*terms: int) -> int:
    """Add left to right, saturating after each addition."""
    acc = terms[0]
    for t in terms[1:]:
        acc = sat(acc + t)
    return acc


def to_q(x: float) -> int:
    """Real value to Q8.8 raw integer: round to nearest, then saturate."""
    return sat(round(x * (1 << FRAC_BITS)))


@dataclass(frozen=True)
class Params:
    theta: int    # firing threshold, Q8.8 raw
    v_reset: int  # reset potential after a spike, Q8.8 raw
    v_rest: int   # resting potential, Q8.8 raw
    k_m: int      # membrane leak: dt/tau_m = 2**-k_m
    k_s: int      # synaptic decay: dt/tau_s = 2**-k_s
    refrac: int   # refractory steps after a spike (3-bit counter, 0..7)

    def __post_init__(self):
        if not 0 <= self.refrac <= 7:
            raise ValueError("refrac is a 3-bit counter: must be 0..7")
        if not (0 <= self.k_m <= 15 and 0 <= self.k_s <= 15):
            raise ValueError("k_m and k_s are 4-bit shift amounts: must be 0..15")


@dataclass
class State:
    v: int = 0    # membrane potential, Q8.8 raw
    i: int = 0    # synaptic current, Q8.8 raw
    ref: int = 0  # remaining refractory steps


def step(s: State, p: Params, syn_in: int) -> tuple[State, int]:
    """Advance one time step.

    syn_in is the summed synaptic and external input for this step, Q8.8 raw.
    Returns (next state, spike) where spike is 0 or 1.
    """
    # I[t+1] = I[t] - (I[t] >> k_s) + input
    i_next = sadd(s.i, -(s.i >> p.k_s), syn_in)
    # V[t+1] = V[t] + ((V_rest - V[t]) >> k_m) + I[t+1]
    # The difference V_rest - V can need 17 bits; it is exact in Python and
    # the RTL must compute it in 17 bits before shifting.
    v_next = sadd(s.v, (p.v_rest - s.v) >> p.k_m, i_next)

    if s.ref > 0:
        return State(v=p.v_reset, i=i_next, ref=s.ref - 1), 0
    if v_next >= p.theta:
        return State(v=p.v_reset, i=i_next, ref=p.refrac), 1
    return State(v=v_next, i=i_next, ref=0), 0


def run(p: Params, syn_inputs: list[int], s: State | None = None) -> list[int]:
    """Run a sequence of inputs and return the spike train."""
    if s is None:
        s = State()
    spikes = []
    for x in syn_inputs:
        s, spk = step(s, p, x)
        spikes.append(spk)
    return spikes
