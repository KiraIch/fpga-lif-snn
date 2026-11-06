# Raw results

Files behind the numbers in the paper (`docs/paper/main.tex`). Each file is produced by the script named below.

| File | Produced by | Used in |
|---|---|---|
| `sweep_grid.csv` | `host/sweep.py` (grid), board run | Table 4 (grid row) |
| `sweep_random.csv` | `host/sweep.py` (random, seed 20261103), board run | Table 4 (random row) |
| `m2_trial_A.json`, `m2_trial_B.json`, `m2_trial_C.json` | `host/run_trial.py`, board run | Table 3, Figures 1 and 2 |
| `ei_full_sweep.csv` | `host/ei_full_sweep.py` (model, 10 networks per combination) | Table 6 (E/I), monotonicity |
| `make_network_top_2026-11-04.log` | `make -B TOP=network_top` in `fpga/` (Yosys, nextpnr-himbaechel, gowin_pack) | Table 7 (resources, maximum clock after routing) |
| `clamp_census.log` | `python host/clamp_census.py` (model only, traced copy of `fixed.step`) | Table 5 (clamp counts, saturation subsection) |
| `flash_neuron_top_2026-11-06.log` | `make flash TOP=neuron_top` in `fpga/` (SRAM) | Saturation board test (bitstream used) |
| `saturation_board_test_2026-11-06.log` | `python3 host/saturation_board_test.py /dev/ttyUSB1`, board run | Saturation subsection (sets S1 to S4: 2,000 samples, 0 mismatches) |

Notes:

- The board command-flow results (682 frames, 1,892 reply bytes) and the five E/I board conditions (745 frames each) were printed to the terminal and are not saved as files. Re-run `host/board_network_test.py` and `host/ei_board_test.py` to reproduce them.
- `ei_full_sweep.csv` has one row per (w_max, w_inh, e_max, f_inh, seed). `mean_rate` is measured after the first 100 steps.
