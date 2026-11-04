# CLAUDE.md — neuro-fpga 專案規則

## 專案目標與目前階段

在 Tang Nano 20K（GW2AR-18）上實作 256 顆神經元的脈衝網路（LIF），輸出必須和 Python 參考模型逐位元一致。之後用它做興奮/抑制（E/I）擾動實驗。

**目前階段：** M3 進行中（M1 的一項待辦未完成）。

- M1 / M2 已完成：Python 定點模型與 f-I 曲線；板上 LED、BSRAM 自測、UART 回送（`rtl/uart_echo.v`）；M2 單顆神經元上板比對（`host/run_trial.py` 三組參數，`host/sweep.py` 完整掃描 2,248 組，合計逐位元一致）；README 已完成，錄影待做。
- M3 網路：
  - 網路核心（`rtl/network.v`，單埠 BSRAM 風格、雙累加器）在模擬中與模型逐位元一致，N = 16、64、256 分別為 3,200、12,800、51,200 筆紀錄。
  - 完整設計（`rtl/network_top.v`：UART 命令、權重與輸入載入、計數與快照讀回、逐步 spike 軌跡 READ_TRACE 0x09，前 512 步）：位元組層級模擬 N = 16、64、256 通過（N = 256 為 682 個封包，`docs/EXPLAIN.md` 4.18）；`make TOP=network_top` 布線通過，區塊記憶體 45/46，41.38 MHz（4.20）。網表模擬在此工具鏈無法完成（Gowin 區塊記憶體模擬模型是空的），2026-11-04 起以上板結果作為功能驗證。
  - 已燒上板（SRAM）：N = 256 流程測試（682 個封包）與模型逐位元一致，PASS。E/I 五個條件（f_inh 0.2、0.5 等）各 745 個封包，計數、快照與前 512 步 spike 軌跡都與完整模型逐位元一致，PASS。
  - E/I 擾動（f_inh 0 到 0.6）：模型完整掃描 504 次執行，24 組全部單調（`docs/EXPLAIN.md` 4.19）。
  - 論文正文還沒寫。論文準備在 `docs/paper/`（outline.md、main.tex 骨架、references.bib）。
- M1 其餘待辦：原理圖與腳位核對（rx 70、tx 69、pin 88，見下方「板子事實」）。

每完成一個階段就更新這一節。

## 數值格式（不可違反）

- 膜電位 V、突觸電流 I：有號 Q8.8（16-bit），raw = 實數 × 256。
- 所有加法飽和（clamp 到 [−32768, 32767]），不繞回。
- 右移用算術位移（RTL 用 `>>>` 且宣告 `signed`）。
- 位移代替乘法（dt/τ 取 2 的負次方）。MVP 不用 DSP。
- 權重為 8-bit 有號整數，搭配全域位移縮放。
- 規格以 `model/fixed.py` 為準，RTL 必須符合它。

## 鐵則

- 任何 RTL 修改都必須通過 cocotb 與 Python 模型的逐位元比對，才算完成。
- 不能只說「看起來對」。沒跑過的測試不算通過。
- 模型與 RTL 的規格不一致時，先改規格（`model/fixed.py` 與 `docs/DECISIONS.md`），再改 RTL。

## 常用指令

```bash
cd model && python -m pytest          # 定點模型單元測試
cd model && python fi_curve.py        # 產生 docs/fi_curve.png
cd host && python -m pytest           # PC 端協定測試（host/pytest.ini 只收 test_*.py，不會匯入板上腳本）
```

模擬（WSL，先 `source ~/oss-cad-suite/environment`）：

```bash
cd sim && make <target>               # target: all, lif, uart, bsram, decoder, decoder_busy, cmd_test, neuron_top, uart_echo, network, network_top
cd sim && make network_top N=256 T=600   # N 預設 16、T 預設 200；network_top 要求 N 為 2 的次方且 N >= 16
```

- `network` 與 `network_top` 的 target 會覆寫版本控制中的 `sim/*.mem`。上板測試需要 N = 256、T = 200 的版本：用其他 N 或 T 跑過之後，先用 `git checkout -- sim/nt_*.mem` 還原。
- `gen_net_top_vectors.py` 要求 7 <= T <= 1024。READ_TRACE「每個封包 7 步」的限制（回覆長度不超過 255 bytes）只在 N <= 256 時成立。

板子（WSL，先 `source ~/oss-cad-suite/environment`；`fpga/Makefile`）：

```bash
cd fpga && make TOP=<name>            # 合成、布線、打包
cd fpga && make flash TOP=<name>      # 燒進 SRAM（揮發性）
python3 host/board_network_test.py /dev/ttyUSB1   # N = 256 命令流程測試（需先重新燒錄，板子的計數不會歸零）
python3 host/ei_board_test.py /dev/ttyUSB1 --f-inh 0.5 --w-inh 2.0   # 單一 E/I 條件，FAIL 時結束碼為 1
```

## 板子事實

> 下列事實來自 Sipeed 官方範例（github.com/sipeed/TangNano-20K-example）的約束檔與原始碼，2026-11-02 查核。**原理圖與 wiki 的腳位圖（圖片）尚未逐一核對**，正式燒錄前仍需你對照一次。不從 Primer 20K 等其他板子推測。

- 晶片：Gowin GW2A(R)-18(C)，已由 JTAG idcode 0x81b 確認。工具鏈參數 `--device GW2AR-LV18QN88C8/I7 --vopt family=GW2A-18C` 可完成合成與 PnR。
- USB 介面：Windows 顯示 FTDI 0403:6010 兩個序列埠（COM3、COM4）。官方 wiki 說板上是 BL616 負責下載與 USB-UART，與 VID/PID 的對應**尚未確認**。哪個通道是 JTAG、哪個是 UART，也待確認。
- 時脈：clk 接 pin 4，27 MHz（官方 sdc：period 37.037 ns）。
- LED：六顆，pin 15、16、17、18、19、20，**低電位點亮**（官方範例 `assign leds = ~leds_value`）。**已於 2026-11-02 上板確認閃爍**（`rtl/blink.v`、`fpga/blink.cst`）。
- UART：官方 uart 範例使用 rx pin 70、tx pin 69，115200 baud，clk 27 MHz。
- reset：uart 範例使用 pin 88，高電位有效（`rst_n = !rst`）。是否為板上按鍵 S1，**未確認**。
- 來源檔案：`led/blink_led/src/blink_led.cst`、`led/blink_leds/src/blink_leds.cst`、`uart/src/top.cst`、`uart/src/uart_top.v`。

## 工作紀錄

- 每次工作在 `docs/LOG.md` 記一筆（日期、完成、觀察、下一步）。
- 每寫一段程式，同步更新 `docs/EXPLAIN.md`：用白話解釋理論與實作原理，讓使用者能理解我在做什麼。新增模組時補一節，改動時更新對應的段落。
- 設計決定寫進 `docs/DECISIONS.md`。
- 文件與 README 用英文；這份 CLAUDE.md 與內部紀錄用中文。
