import random

from fixed import Params, State, step, sat
from network import W_SHIFT, run_network, step_network, synaptic_inputs

P = Params(theta=384, v_reset=0, v_rest=0, k_m=4, k_s=3, refrac=2)


def test_zero_weights_are_independent_neurons():
    # With no synapses, each neuron must match the single-neuron model driven by ext alone.
    ext = [40, -30, 0]
    W = [[0, 0, 0] for _ in range(3)]
    trace = run_network(P, W, ext, steps=60)
    for i, x in enumerate(ext):
        s = State()
        for t in range(60):
            s, spk = step(s, P, x)
            assert trace[t][i] == (s.v, spk), (t, i)


def test_spike_arrives_one_step_later():
    # Neuron 0 is driven hard; neuron 1 has no external input.
    W = [[0, 100], [0, 0]]
    ext = [400, 0]
    states = [State(), State()]
    spikes = [0, 0]
    seen = []
    for t in range(12):
        syn = synaptic_inputs(W, spikes, ext)
        seen.append((spikes[0], syn[1]))
        states, spikes = step_network(states, spikes, W, ext, P)
    for prev_spike, syn1 in seen:
        assert syn1 == (100 << W_SHIFT if prev_spike else 0)
    assert any(s for s, _ in seen)  # the test would be vacuous if neuron 0 never spiked


def test_saturation_is_applied_once_not_per_source():
    # 300 sources each add +508 (127 << 2). The exact sum is 152400.
    # Saturating after every addition would give 32767 - 32768 = -1 with ext = -32768;
    # saturating once gives sat(152400 - 32768) = 32767.
    n = 301
    W = [[127] for _ in range(n - 1)] + [[0]]   # one target column
    ext = [-32768]
    spikes = [1] * (n - 1) + [0]
    syn = synaptic_inputs(W, spikes, ext)
    assert syn == [32767]


def test_order_of_sources_does_not_matter():
    rng = random.Random(7)
    n = 40
    W = [[rng.randint(-128, 127)] for _ in range(n)]
    ext = [rng.randint(-20000, 20000)]
    spikes = [rng.randint(0, 1) for _ in range(n)]
    base = synaptic_inputs(W, spikes, ext)
    order = list(range(n))
    rng.shuffle(order)
    permuted = synaptic_inputs([W[j] for j in order], [spikes[j] for j in order], ext)
    assert base == permuted


def test_inhibition_saturates_low():
    W = [[-128] for _ in range(300)]
    spikes = [1] * 300
    # Exact sum is -153600; one saturation gives -32768.
    assert synaptic_inputs(W, spikes, [0]) == [-32768]


def test_quiet_network_stays_quiet():
    W = [[0] * 4 for _ in range(4)]
    trace = run_network(P, W, [0, 0, 0, 0], steps=30)
    assert all(v == 0 and spk == 0 for row in trace for v, spk in row)


def test_trace_shape():
    W = [[1, 2], [3, 4]]
    trace = run_network(P, W, [10, 20], steps=7)
    assert len(trace) == 7 and all(len(row) == 2 for row in trace)
