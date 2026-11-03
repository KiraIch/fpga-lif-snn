"""Plot the E/I perturbation: mean firing rate and silent fraction against the inhibitory fraction.

Reads build/ei_experiment.csv (from host/ei_experiment.py) and writes docs/ei_rate_vs_finh.png.
Each point is the mean over the seeds; the bars show the min to max over the seeds.
"""

import csv
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "..", "build", "ei_experiment.csv")
OUT = os.path.join(HERE, "..", "docs", "ei_rate_vs_finh.png")


def main():
    with open(SRC) as f:
        rows = list(csv.DictReader(f))
    f_inh = sorted({float(r["f_inh"]) for r in rows})
    rate, lo, hi, silent = [], [], [], []
    for x in f_inh:
        rs = [float(r["mean_rate"]) for r in rows if float(r["f_inh"]) == x]
        ss = [float(r["silent"]) for r in rows if float(r["f_inh"]) == x]
        rate.append(sum(rs) / len(rs))
        lo.append(min(rs))
        hi.append(max(rs))
        silent.append(sum(ss) / len(ss))

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9, 3.6))
    ax1.errorbar(f_inh, rate, yerr=[[r - l for r, l in zip(rate, lo)], [h - r for r, h in zip(rate, hi)]],
                 marker="o", capsize=3)
    ax1.axhline(1 / 3, color="grey", linestyle="--", linewidth=1)
    ax1.text(f_inh[0], 1 / 3 + 0.005, "refractory limit (1/3)", color="grey", fontsize=8)
    ax1.set_xlabel("inhibitory fraction f_inh")
    ax1.set_ylabel("mean rate (spikes per neuron per step)")
    ax1.set_title("firing rate, N = 256")

    ax2.plot(f_inh, silent, marker="o")
    ax2.set_xlabel("inhibitory fraction f_inh")
    ax2.set_ylabel("fraction of silent neurons")
    ax2.set_title("silent neurons")

    fig.tight_layout()
    fig.savefig(OUT, dpi=150)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
