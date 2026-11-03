"""Summarise build/ei_full_sweep.csv (from host/ei_full_sweep.py).

For each (w_max, w_inh, e_max) it averages the seeds, then reports:
    rate at f_inh = 0, 0.3, 0.6      mean spikes per neuron per step
    monotone                         the mean rate never rises as f_inh grows (tolerance 0.005)
    silent@0.6                       fraction of silent neurons at f_inh = 0.6
    max_at_f0                        fraction of neurons at the refractory limit at f_inh = 0
Writes build/ei_full_summary.csv.
"""

import csv
import os

HERE = os.path.dirname(os.path.abspath(__file__))
BUILD = os.path.join(HERE, "..", "build")
SRC = os.path.join(BUILD, "ei_full_sweep.csv")
OUT = os.path.join(BUILD, "ei_full_summary.csv")
TOL = 0.005


def mean(xs):
    return sum(xs) / len(xs)


def main():
    with open(SRC) as f:
        rows = list(csv.DictReader(f))
    groups = {}
    for r in rows:
        key = (int(r["w_max"]), float(r["w_inh"]), int(r["e_max"]))
        groups.setdefault(key, []).append(r)

    out = []
    print("w_max w_inh e_max  rate@0   rate@0.3  rate@0.6  monotone  silent@0.6  at_max@0")
    for key in sorted(groups):
        rs = groups[key]
        f_vals = sorted({float(r["f_inh"]) for r in rs})
        means = {}
        silent = {}
        at_max = {}
        for x in f_vals:
            sel = [r for r in rs if float(r["f_inh"]) == x]
            means[x] = mean([float(r["mean_rate"]) for r in sel])
            silent[x] = mean([float(r["silent"]) for r in sel])
            at_max[x] = mean([float(r["at_max"]) for r in sel])
        seq = [means[x] for x in f_vals]
        monotone = all(b <= a + TOL for a, b in zip(seq, seq[1:]))
        row = dict(w_max=key[0], w_inh=key[1], e_max=key[2],
                   rate_f0=means[0.0], rate_f03=means[0.3], rate_f06=means[0.6],
                   monotone=monotone, silent_f06=silent[0.6], at_max_f0=at_max[0.0])
        out.append(row)
        print(f"{key[0]:5d} {key[1]:5.1f} {key[2]:5d}  {means[0.0]:.3f}    {means[0.3]:.3f}    "
              f"{means[0.6]:.3f}    {str(monotone):5s}     {silent[0.6]:.2f}      {at_max[0.0]:.2f}")

    n_mono = sum(1 for r in out if r["monotone"])
    print(f"\n{len(out)} combinations, {n_mono} monotone in f_inh (tolerance {TOL})")
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
