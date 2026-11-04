# Paper outline (working draft)

Status: first full draft of the body in `main.tex` (2026-11-04), not compiled (no LaTeX here). No text is final. The author writes the final wording; this file holds the claims, the evidence for each claim, and the open items.

**Target:** a technical preprint (Research Square). Plan date: end of December 2026, after M2 and the start of M3. **Submission is the author's action.** Nothing is posted by the assistant.

**Working title (draft, 2026-11-04):** Bit-Exact Verification of a 256-Neuron Fixed-Point Spiking Network on a Low-Cost FPGA

**Author line (draft):** ChiaAn Lin (ntuhibiki@gmail.com). Affiliation is still a TODO in `main.tex`.

## 1. Claims and the evidence for each

Only claims with evidence below may go into the paper. Numbers come from the files listed; re-check them before submission.

| # | Claim | Evidence (file) | Numbers at 2026-11-04 |
|---|---|---|---|
| C1 | The fixed-point LIF model (Q8.8, per-step saturation, arithmetic shifts) is specified exactly and tested. | `model/fixed.py`, `model/test_fixed.py`, `docs/DECISIONS.md` D-001–D-005 | 10 unit tests pass |
| C2 | The single-neuron RTL matches the model bit for bit in simulation. | `sim/test_lif_core.py` (cocotb), `sim/Makefile` target `lif` (formerly `sim/Makefile.lif`), `docs/LOG.md` 2026-11-02 | 10,110 combinational cases; 15 × 500-step traces; mutation (`>>>`→`>>`) caught |
| C3 | The same neuron matches the model bit for bit on the board. | `host/run_trial.py`, `build/m2_trial_{A,B,C}.json`, `docs/m2_*.png` | 60,000 samples in 3 parameter sets; 0 mismatches |
| C4 | The bit-exact result holds across the legal parameter space. | `host/sweep.py`, `build/sweep_grid.csv`, `build/sweep_random.csv` | 2,048 grid + 200 random sets; 2,023,200 samples; 0 mismatches; 0 refused requests |
| C5 | A command protocol with checksums and refusal rules works on the board. | `host/protocol.py`, `host/test_protocol.py` (26), `rtl/cmd_decoder.v`, `host/board_cmd_test.py` | 5/5 board checks; the decoder rejects bad checksum, out-of-range values, and requests during a reply |
| C6 | The UART link has a measurable limit: long unpaced bursts lose bytes at the USB–UART bridge. | `host/uart_loopback.py`, `docs/LOG.md` 2026-11-03 | 96 or 128 bytes in one write return 66; 16-byte paced chunks return all |
| C7 | A time-multiplexed network with event-driven synapses matches a reference model bit for bit in simulation, for 16, 64 and 256 neurons. | `model/network.py`, `model/test_network.py`, `rtl/network.v`, `sim/tb_network.v` | 3,200 / 12,800 / 51,200 records; 4 mutants caught |
| C8 | Resource use for the single neuron and the network at N = 16, 64, 256. | yosys `stat` (`build/stat_net_*.txt`, not committed); nextpnr report for N = 256 (`build/pnr/pnr.log`) | single neuron ~274 LUT; network 1,382 / 1,343 / 1,457 cells (yosys), state and weights in block RAM; full design at N = 256, place-and-route (`make TOP=network_top`, `fpga/build`): 2,536 LUT4 (12%), 1,315 DFF (8%), 45/46 BSRAM (97%), 41.38 MHz (target 27 MHz). Earlier numbers from a test harness that is not the design (35/46 BSRAM, 785 LUT4, 392 DFF, 47.4 MHz) must not be used as the design's numbers |

**Board status (2026-11-04):** the full design at N = 256 runs on the board for the command flow (682 frames, bit-exact), and five E/I conditions run on the board (each 745 frames, bit-exact, first 512 steps of spikes). These are the only board claims for the network. **Not yet claimed:** any biological result; any E/I condition on the board beyond the five; V step-by-step on the board (only spikes); gate-level simulation of the netlist (not possible with the installed toolchain). Do not write a claim before the evidence file exists and its numbers are re-checked.

## 2. Section plan

| Section | Content | Evidence | Status |
|---|---|---|---|
| Abstract | one paragraph, after C1–C4 are final | C1–C4 | draft v2 (assistant-written, author to check) |
| 1 Introduction | why a bit-exact FPGA neuron; the cost argument; what is new here (verification method, low cost) | related work (see §4) | draft v2 (assistant-written); the novelty (gap) sentence was removed at the author's request |
| 2 Model | LIF equations, shift-based time constants, Q8.8 rules, refractory period | `model/fixed.py`, D-001–D-006 | first draft |
| 3 Hardware | Tang Nano 20K, pipeline, UART link, decoder, neuron top | `rtl/neuron_top.v`, `rtl/cmd_decoder.v` | first draft (single neuron and network) |
| 4 Verification | model as spec; simulation; mutation tests; board comparison; sweep | C2, C3, C4, mutation logs | first draft |
| 5 Results | board comparison figure, f-I figure, sweep table, limits of the UART link | C3, C4, C6 | figures exist |
| 6 Resources and scaling | single neuron, network at N = 16, 64, 256 | C8 | synthesis done for N = 16, 64, 256; place-and-route of the full design at N = 256 done (45/46 BSRAM, 41.38 MHz); board: command flow at N = 256 and five E/I conditions done (see §1, board status) |
| 7 Limitations | no timeout in the decoder; bridge limit; not compared with biology; single-clock time steps; draft decisions | `docs/EXPLAIN.md` §6 | first draft |
| 8 Availability and AI statement | repository; the AI-assisted development statement (same as README) | `README.md` | first draft; repository link is a TODO |

## 3. Figures

| Figure | File | Generated by | Notes |
|---|---|---|---|
| f-I curve, float vs Q8.8 | `docs/fi_curve.png` | `model/fi_curve.py` | exists |
| Board vs model, membrane trace and spikes (first 100 of 1000 steps) | `docs/m2_trace_board_vs_model.png` | `host/plot_trial.py` (set A) | exists |
| f-I board vs model | `docs/m2_fi_board.png` | `host/plot_trial.py` | exists |
| Sweep summary (sets with spikes; mismatches) | to make | from `build/sweep_*.csv` | to do |
| Network raster (N = 16) | to make after the board run | `sim` output or board | to do |
| Architecture block diagram | to make | by hand (`docs/` or `artifact-diagramming`) | to do |

## 4. References: status

Only use references whose full text was read, or cite them as "abstract only" in the text. The index with statuses is in `docs/papers/README.md`. The notes are in `docs/papers/notes/`.

| Use in paper | Reference | Status (from the index) |
|---|---|---|
| E/I network dynamics | Brunel 2000 | 未取得全文 (metadata only) |
| E/I perturbation and decisions | Lam et al. 2022 | 未取得全文; priority to obtain |
| Decision model | Wong & Wang 2006 | 全文已讀 |
| LIF neuron, textbook | Gerstner & Kistler 2002 (*Spiking Neuron Models*) | check: not in the index yet |
| Simple neuron models | Izhikevich 2003 | check: DOI in the plan is wrong (plan §文獻) |
| FPGA spiking hardware | see index group FPGA/SNN (09–17) | check each note's status before citing |

Every citation needs its DOI or URL checked against the publisher page before submission. The plan's citation errors are listed in `docs/papers/README.md`.

## 5. Open items for the author

- Title, author list, affiliations, corresponding email.
- The wording of the central claim and of the abstract.
- Whether the preprint waits for the M3 board run or goes out on M2 results.
- The Research Square submission requirements (format, license, AI-use statement) — check the site before writing the final version.
- Obtain the full text of Lam 2022 (priority) and any other "未取得全文" paper that is cited.

## 6. What must not be in the paper

- Any sentence about the network on the board that goes beyond the command flow (682 frames) and the five E/I conditions in §1.
- The f-I hardware curve as "validated against biology": it is validated against the model only.
- Numbers that are not in a file listed above.
