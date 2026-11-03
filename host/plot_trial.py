"""Plot the M2 board comparison (run host/run_trial.py first).

Reads build/m2_trial.json and writes two figures to docs/:
  m2_trace_board_vs_model.png   membrane trace and spikes, board and model, one input
  m2_fi_board.png               f-I points from the board and the model

Usage (repository root, Windows Python with matplotlib):
    python host/plot_trial.py [input_value]     default input: 0.1
"""

import json
import os
import pathlib
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "build" / "m2_trial.json"
DOCS = ROOT / "docs"


def main():
    show_input = float(sys.argv[1]) if len(sys.argv) > 1 else 0.1
    d = json.loads(DATA.read_text())
    runs = d["runs"]
    steps = d["steps"]
    t = list(range(steps))

    run = min(runs, key=lambda r: abs(r["x"] - show_input))

    zoom = min(100, steps)   # the full run is too dense to read; the comparison covers all steps
    t = t[:zoom]
    hw_v = [v for v, _ in run["hw"][:zoom]]
    ref_v = [v for v, _ in run["ref"][:zoom]]
    hw_s = [i for i, (_, s) in enumerate(run["hw"][:zoom]) if s]
    ref_s = [i for i, (_, s) in enumerate(run["ref"][:zoom]) if s]
    v_theta = d["params"]["theta"]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(8, 5), sharex=True,
                                   gridspec_kw={"height_ratios": [3, 1]})
    ax1.plot(t, [v / 256 for v in ref_v], color="#1f77b4", lw=2.5, alpha=0.5, label="model (fixed.py)")
    ax1.plot(t, [v / 256 for v in hw_v], color="#d62728", lw=1, ls="--", label="board (FPGA)")
    ax1.axhline(v_theta / 256, color="grey", lw=0.8, ls=":", label="threshold θ")
    ax1.set_ylabel("membrane V (real units)")
    ax1.set_title(f"Board vs model, input {run['x']:+.4f}, first {zoom} of {steps} steps "
                  f"(all {steps}: {run['mismatches']} mismatches)")
    ax1.legend(loc="upper right", fontsize=8)

    ax2.eventplot([ref_s, hw_s], colors=["#1f77b4", "#d62728"], lineoffsets=[1, 0], linelengths=0.8)
    ax2.set_yticks([0, 1])
    ax2.set_yticklabels(["board", "model"])
    ax2.set_xlabel("time step")

    fig.tight_layout()
    DOCS.mkdir(exist_ok=True)
    out1 = DOCS / "m2_trace_board_vs_model.png"
    fig.savefig(out1, dpi=150)
    plt.close(fig)

    xs = [r["x"] for r in runs]
    hw_rate = [sum(s for _, s in r["hw"]) / steps for r in runs]
    ref_rate = [sum(s for _, s in r["ref"]) / steps for r in runs]
    fig, ax = plt.subplots(figsize=(7, 4.5))
    ax.plot(xs, ref_rate, color="#1f77b4", lw=2.5, alpha=0.5, label="model (fixed.py)")
    ax.plot(xs, hw_rate, "o", color="#d62728", ms=5, label="board (FPGA)")
    ax.set_xlabel("constant input current (real units, Q8.8)")
    ax.set_ylabel(f"firing rate (spikes per step, {steps} steps)")
    ax.set_title("f-I curve: board vs model")
    ax.legend(fontsize=9)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    out2 = DOCS / "m2_fi_board.png"
    fig.savefig(out2, dpi=150)
    plt.close(fig)

    print(f"written: {out1}")
    print(f"written: {out2}")


if __name__ == "__main__":
    main()
