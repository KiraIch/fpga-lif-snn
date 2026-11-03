"""Unit tests for the fixed-point reference model (run: python -m pytest model)."""

from fixed import Params, Q_MAX, Q_MIN, State, sadd, sat, run, step, to_q

P = Params(theta=to_q(1.0), v_reset=0, v_rest=0, k_m=4, k_s=2, refrac=2)


def test_sat_clamps_both_ends():
    assert sat(40000) == Q_MAX
    assert sat(-40000) == Q_MIN
    assert sat(123) == 123


def test_sadd_saturates_after_each_addition():
    assert sadd(32000, 1000) == Q_MAX
    assert sadd(-32000, -1000) == Q_MIN
    # Saturate after each addition: Q_MAX + 1 clamps to Q_MAX, then -1 gives Q_MAX - 1.
    assert sadd(Q_MAX, 1, -1) == Q_MAX - 1


def test_arithmetic_shift_floors_toward_minus_infinity():
    assert (-1) >> 1 == -1
    assert (-3) >> 1 == -2
    assert 3 >> 1 == 1


def test_to_q_rounds_and_saturates():
    assert to_q(1.0) == 256
    assert to_q(-0.5) == -128
    assert to_q(1000.0) == Q_MAX


def test_no_input_no_spike():
    assert run(P, [0] * 100) == [0] * 100


def test_strong_input_spikes_and_resets():
    spikes = run(P, [to_q(2.0)] * 20)
    assert spikes[0] == 1  # large input crosses threshold on the first step
    assert sum(spikes) > 0


def test_refractory_period_is_enforced():
    spikes = run(P, [to_q(4.0)] * 200)
    fire_steps = [t for t, s in enumerate(spikes) if s]
    assert len(fire_steps) > 2
    gaps = [b - a for a, b in zip(fire_steps, fire_steps[1:])]
    assert min(gaps) >= P.refrac + 1


def test_large_input_saturates_without_wrapping():
    s = State()
    for _ in range(1000):
        s, _ = step(s, P, Q_MAX)
        assert Q_MIN <= s.v <= Q_MAX
        assert Q_MIN <= s.i <= Q_MAX


def test_negative_input_saturates_without_wrapping():
    s = State()
    for _ in range(1000):
        s, _ = step(s, P, Q_MIN)
        assert Q_MIN <= s.v <= Q_MAX
        assert Q_MIN <= s.i <= Q_MAX


def test_inhibition_reduces_firing():
    excit = run(P, [to_q(0.05)] * 2000)
    balanced = run(P, [to_q(0.05) - to_q(0.03)] * 2000)
    assert sum(excit) > 0
    assert sum(balanced) < sum(excit)
