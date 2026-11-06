"""Build the E/I tables (Table 9 and Table 10) from results/ei_full_sweep.csv, and check them.

Table 9: the (w_max = 10, w_inh = 1, e_max = 30) combination, one row per f_inh:
  mean rate with min-max over the 10 networks, silent share, share above 0.3 spikes per step.
Table 10: all 24 combinations, one row each: rate at f_inh = 0, 0.3 and 0.6, ceiling share
  (share of neurons above 0.3 spikes per step) at f_inh = 0 and 0.3, and whether the mean rate
  never rises with f_inh in any of the 10 networks.

The two tables are generated from the same rows. The script asserts that the Table 9 values
equal the matching Table 10 row, then writes the LaTeX rows to results/ei_tables.tex. It also
checks that every generated row appears verbatim in docs/paper/main.tex.

Run from the repository root:  python host/make_ei_tables.py
"""

import collections
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
CSV = os.path.join(ROOT, "results", "ei_full_sweep.csv")
PAPER = os.path.join(ROOT, "docs", "paper", "main.tex")
OUT = os.path.join(ROOT, "results", "ei_tables.tex")

SUBSET = (10, 1.0, 30)   # (w_max, w_inh, e_max) of Table 9
F9 = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6]


def load():
    rows = list(csv.DictReader(open(CSV)))
    for r in rows:
        r["w_max"] = int(r["w_max"])
        r["e_max"] = int(r["e_max"])
        r["w_inh"] = float(r["w_inh"])
        r["f_inh"] = round(float(r["f_inh"]), 2)
        r["mean_rate"] = float(r["mean_rate"])
        r["at_max"] = float(r["at_max"])
        r["silent"] = float(r["silent"])
    return rows


def combo_rows(rows):
    combos = collections.OrderedDict()
    for r in rows:
        combos.setdefault((r["w_max"], r["w_inh"], r["e_max"]), []).append(r)
    return combos


def mean(rs, f, col):
    v = [r[col] for r in rs if r["f_inh"] == f]
    return sum(v) / len(v)


def monotone(rs):
    nets = collections.defaultdict(dict)
    for r in rs:
        nets[r["seed"]][r["f_inh"]] = r["mean_rate"]
    return all(all(d[b] <= d[a] for a, b in zip(sorted(d), sorted(d)[1:])) for d in nets.values())


def table9_rows(rs):
    out = []
    for f in F9:
        v = [r["mean_rate"] for r in rs if r["f_inh"] == f]
        out.append(dict(f=f, mean=sum(v) / len(v), lo=min(v), hi=max(v),
                        silent=mean(rs, f, "silent"), above=mean(rs, f, "at_max")))
    return out


def fmt3(x):
    return f"{x:.3f}"


def main():
    rows = load()
    combos = combo_rows(rows)

    # Table 9 rows
    t9 = table9_rows(combos[SUBSET])
    t9_lines = []
    for d in t9:
        t9_lines.append(f"{d['f']:.1f} & {fmt3(d['mean'])} ({fmt3(d['lo'])}--{fmt3(d['hi'])}) & "
                        f"{d['silent']:.2f} & {100 * d['above']:.0f}\\% \\\\")

    # Table 10 rows
    t10_lines = []
    t10_data = {}
    for key in sorted(combos):
        rs = combos[key]
        r0, r3, r6 = mean(rs, 0.0, "mean_rate"), mean(rs, 0.3, "mean_rate"), mean(rs, 0.6, "mean_rate")
        c0, c3 = mean(rs, 0.0, "at_max"), mean(rs, 0.3, "at_max")
        mono = monotone(rs)
        t10_data[key] = (r0, r3, r6, c0, c3, mono)
        t10_lines.append(f"{key[0]} & {key[1]:.1f} & {key[2]} & {fmt3(r0)} & {fmt3(r3)} & {fmt3(r6)} & "
                         f"{100 * c0:.0f}\\% & {100 * c3:.0f}\\% & {'yes' if mono else 'no'} \\\\")

    # Cross-check: Table 9 values equal the Table 10 row for the same combination
    r0, r3, r6, c0, c3, _ = t10_data[SUBSET]
    d0, d3, d6 = t9[0], t9[3], t9[6]
    assert abs(d0["mean"] - r0) < 1e-12 and abs(d3["mean"] - r3) < 1e-12 and abs(d6["mean"] - r6) < 1e-12, \
        "Table 9 and Table 10 disagree on the mean rate"
    assert abs(d0["above"] - c0) < 1e-12 and abs(d3["above"] - c3) < 1e-12, \
        "Table 9 and Table 10 disagree on the ceiling share"
    print("cross-check: Table 9 values equal the Table 10 row for w_max=10, w_inh=1.0, e_max=30")

    body9 = (
        "\\toprule\n"
        "$f_{\\mathrm{inh}}$ & Mean rate (min--max) & Silent neurons & Above 0.3 spikes per step \\\\\n"
        "\\midrule\n" + "\n".join(t9_lines) + "\n\\bottomrule\n"
    )
    body10 = (
        "\\toprule\n"
        "$w_{\\max}$ & $w_{\\mathrm{inh}}$ & $e_{\\max}$ & $\\bar r$ at $f_{\\mathrm{inh}}{=}0$ & $\\bar r$ at $0.3$ & "
        "$\\bar r$ at $0.6$ & Ceiling at $0$ & Ceiling at $0.3$ & Monotone \\\\\n"
        "\\midrule\n" + "\n".join(t10_lines) + "\n\\bottomrule\n"
    )
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write("% Table 9 body\n" + body9 + "\n% Table 10 body\n" + body10)
    print(f"wrote {os.path.relpath(OUT, ROOT)}")

    # Every generated row must appear verbatim in the paper
    paper = open(PAPER, encoding="utf-8").read()
    missing = [l for l in t9_lines + t10_lines if l not in paper]
    if "--update-paper" in sys.argv:
        # Everything between the label and the end of its tabular is regenerated, so this is
        # idempotent: running it again gives the same paper.
        specs = {
            "tab:ei": "\\begin{tabular}{rcccc}",
            "tab:ei24": "\\footnotesize\\setlength{\\tabcolsep}{3pt}\n\\begin{tabular}{rrrrrrrrr}",
        }
        for label, body in (("tab:ei", body9), ("tab:ei24", body10)):
            start = paper.index("\\label{" + label + "}") + len("\\label{" + label + "}")
            end = paper.index("\\end{tabular}", start) + len("\\end{tabular}")
            paper = paper[:start] + "\n" + specs[label] + "\n" + body + "\\end{tabular}" + paper[end:]
        open(PAPER, "w", encoding="utf-8", newline="\n").write(paper)
        missing = [l for l in t9_lines + t10_lines if l not in paper]
        print("updated docs/paper/main.tex")
    if missing:
        print(f"NOT in paper: {len(missing)} rows, first: {missing[0]}")
        return 1
    print(f"all {len(t9_lines) + len(t10_lines)} generated rows appear in docs/paper/main.tex")
    return 0


if __name__ == "__main__":
    sys.exit(main())
