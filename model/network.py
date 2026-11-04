"""Reference model of an N-neuron network (M3). The RTL must match this bit for bit.

Rules (see docs/DECISIONS.md D-006, D-008, D-009):

- All neurons share one parameter set `Params` (per-neuron parameters come later).
- A spike at step t enters the synaptic input at step t+1 (D-006).
- Synaptic input of neuron i at step t:
      syn_in_i = sat( sum_j (W[j][i] << w_shift) * s_j[t-1]  +  ext_i )
  The sum over sources is exact (wide). The external input is added to that
  exact sum, and the total is saturated once (D-008). The result does not
  depend on the order in which sources are added.
- Each neuron then takes one single-neuron step (model/fixed.py `step`) with
  its syn_in. All neurons use the state at t, so the update order does not matter.

W[j][i] is the weight from source j to target i, signed 8-bit. ext[i] is a
constant external input per neuron, Q8.8 raw.
"""

from fixed import Params, State, sat, step

W_SHIFT = 2   # D-009: global weight scale, contribution = W << W_SHIFT


def synaptic_inputs(W, spikes_prev, ext, w_shift=W_SHIFT):
    """Return syn_in (Q8.8 raw, saturated) for every target neuron.

    Sources are indexed by spikes_prev, targets by ext. W[j][i] connects source j to target i.
    """
    n_src = len(spikes_prev)
    out = []
    for i in range(len(ext)):
        acc = 0
        for j in range(n_src):
            if spikes_prev[j]:
                acc += W[j][i] << w_shift
        out.append(sat(acc + ext[i]))
    return out


def step_network(states, spikes_prev, W, ext, p, w_shift=W_SHIFT):
    """Advance all neurons one step. Returns (new states, spikes)."""
    syn = synaptic_inputs(W, spikes_prev, ext, w_shift)
    new_states = []
    spikes = []
    for s, x in zip(states, syn):
        s2, spk = step(s, p, x)
        new_states.append(s2)
        spikes.append(spk)
    return new_states, spikes


def run_network(p, W, ext, steps, w_shift=W_SHIFT):
    """Run from rest. Returns trace[t][i] = (V after step t, spike of step t)."""
    n = len(ext)
    states = [State() for _ in range(n)]
    spikes = [0] * n
    trace = []
    for _ in range(steps):
        states, spikes = step_network(states, spikes, W, ext, p, w_shift)
        trace.append([(s.v, spk) for s, spk in zip(states, spikes)])
    return trace
