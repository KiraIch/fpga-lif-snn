"""Plot f-I curves for the float and fixed-point LIF models.

Output: docs/fi_curve.png (M1 acceptance: the two curves have the same shape).
Run from the model/ directory: python fi_curve.py
"""

import pathlib

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

import fixed  # noqa: E402
import lif  # noqa: E402

STEPS = 2000
CURRENTS = np.linspace(0.0, 0.1, 41)
OUT = pathlib.Path(__file__).resolve().parent.parent / "docs" / "fi_curve.png"


def rate_float(c: float, p: lif.Params) -> float:
    v, i, ref, count = p.v_rest, 0.0, 0, 0
    for _ in range(STEPS):
        v, i, ref, spk = lif.step(v, i, ref, p, c)
        count += spk
    return count / STEPS


def rate_fixed(c: float, p: fixed.Params) -> float:
    spikes = fixed.run(p, [fixed.to_q(c)] * STEPS)
    return sum(spikes) / STEPS


def main() -> None:
    fp = lif.Params()
    qp = fixed.Params(
        theta=fixed.to_q(fp.theta),
        v_reset=fixed.to_q(fp.v_reset),
        v_rest=fixed.to_q(fp.v_rest),
        k_m=fp.k_m,
        k_s=fp.k_s,
        refrac=fp.refrac,
    )
    r_float = np.array([rate_float(c, fp) for c in CURRENTS])
    r_fixed = np.array([rate_fixed(c, qp) for c in CURRENTS])

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(CURRENTS, r_float, "-", label="float (lif.py)")
    ax.plot(CURRENTS, r_fixed, "o", ms=3, label="Q8.8 fixed (fixed.py)")
    ax.set_xlabel("input current per step (real units)")
    ax.set_ylabel("firing rate (spikes per step)")
    ax.set_title("LIF f-I curve, float vs fixed-point")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT, dpi=150)
    print(f"saved {OUT}")
    print(f"max |float - fixed| rate difference: {np.max(np.abs(r_float - r_fixed)):.4f}")


if __name__ == "__main__":
    main()
