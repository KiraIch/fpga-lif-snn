"""Floating-point reference LIF neuron.

Same equations as fixed.py but with real numbers and no saturation. It is
used to check the shape of the fixed-point model, not for bit-exact tests.
Parameters are in real units (threshold 1.0 = Q8.8 raw 256).
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Params:
    theta: float = 1.0
    v_reset: float = 0.0
    v_rest: float = 0.0
    k_m: int = 4
    k_s: int = 2
    refrac: int = 2


def step(v: float, i: float, ref: int, p: Params, syn_in: float) -> tuple[float, float, int, int]:
    """Advance one time step. Returns (v, i, ref, spike)."""
    i_next = i - i * 2.0 ** -p.k_s + syn_in
    v_next = v + (p.v_rest - v) * 2.0 ** -p.k_m + i_next

    if ref > 0:
        return p.v_reset, i_next, ref - 1, 0
    if v_next >= p.theta:
        return p.v_reset, i_next, p.refrac, 1
    return v_next, i_next, 0, 0
