# 開發日誌（LOG）

## 2026-11-02（第 1 週第 1 天）

**完成**

- 建立 repo 骨架（`model/ rtl/ sim/ fpga/ host/ experiments/ docs/`），本機 `git init`，尚未 commit、尚未建立 GitHub repo。
- `model/fixed.py`：Q8.8 定點 LIF，規格見 `docs/DECISIONS.md` D-001 至 D-006。
- `model/lif.py`：浮點版 LIF，用於形狀比較。
- `model/test_fixed.py`：10 個單元測試，全部通過（`python -m pytest model`）。
- `model/fi_curve.py`：產生 `docs/fi_curve.png`，浮點與定點的最大發放率差為 0.027（每步），曲線形狀一致。

**觀察**

- f-I 曲線呈階梯狀，主要來自不反應期（D-005）與 `>>` 造成的死區（D-001）。
- 定點在閾值附近偏離浮點最多，原因是量化；之後要用 `10,000` 組隨機輸入的逐位元比對取代「形狀一致」的目視判斷。

**尚未做（需要使用者）**

- 板子：LED 閃爍、BSRAM 測試、UART 回傳（硬體，需要 Tang Nano 20K 與 USB-C 線）。
- 開源 FPGA 工具鏈（OSS CAD Suite）只能在 WSL2 或 Linux 安裝，本機目前沒有 `yosys`、`nextpnr`、`iverilog`。
- `CLAUDE.md` 的板子事實（腳位、時脈、LED）需要你對照 Sipeed 官方文件填寫，AI 不代填。

**下一步**

- 確認 WSL2 是否可用，安裝 OSS CAD Suite。
- 填寫 `CLAUDE.md` 的板子區塊。

## 2026-11-02（工具鏈與板子偵測）

**完成**

- WSL Ubuntu 24.04 安裝 OSS CAD Suite 2026-11-02（`~/oss-cad-suite`）。yosys 0.70、nextpnr-himbaechel 0.11.1（gowin uarch）、gowin_pack、openFPGALoader 1.2.0（板子清單含 tangnano20k，介面 ft2232）、Icarus 14、Verilator、cocotb 2.1.0.dev0 皆可執行。
- 端到端測試：一個計數器 Verilog 經 `synth_gowin` → nextpnr-himbaechel（GW2AR-LV18QN88C8/I7）→ `gowin_pack` 成功產生 bitstream。測試用的 CST 腳位（clk 4、led 16）是**佔位用**，只為了驗證流程，不是板子腳位，**不可燒錄**。

**板子**

- Windows 偵測到 VID 0403 / PID 6010（FTDI 系列）裝置，出現兩個序列埠 COM3、COM4，板子亮燈，使用附贈線材。
- 較早的檢查沒有偵測到，推測當時連線不完整；之後正常。
- 兩個 channel 的用途（JTAG 或 UART）與板子腳位，尚未對照 Sipeed 官方文件核對。

**待辦**

- WSL 讀不到 USB 裝置，需安裝 usbipd-win（Windows 系統管理員權限）後才能用 openFPGALoader 在 WSL 內燒錄。
- 核對官方文件後，填寫 CLAUDE.md 的板子區塊與正式 CST。
- WSL home 內另有 `oss-cad-suite-linux-x64-20261102.tgz`（約 714 MB），解壓後可刪除，尚未刪。

## 2026-11-02（板子透過 JTAG 讀到晶片）

- usbipd-win 安裝後，以系統管理員 bind 板子（BUSID 7-2，0403:6010），attach 到 WSL Ubuntu。
- 新增 udev 規則 `/etc/udev/rules.d/99-tang-nano-20k.rules`（MODE=0666，僅限 0403:6010），之後 openFPGALoader 不需 root 即可連線。
- `openFPGALoader --detect`（唯讀，未燒錄）回報：idcode 0x81b，Gowin GW2A(R)-18(C)，irlength 8。**晶片型號已由硬體確認**，與計畫的 GW2AR-18 一致。
- 只做了偵測，**沒有燒錄**。腳位、時脈、LED 仍待核對 Sipeed 官方文件。

## 2026-11-02（對照官方範例的板子腳位）

- 官方 wiki 頁面（wiki.sipeed.com）的腳位表是圖片，文字中沒有腳位號碼，無法直接讀取。
- 改查 Sipeed 官方範例 repo（sipeed/TangNano-20K-example）的約束檔與原始碼，取得：clk pin 4（27 MHz）、LED pin 15–20（低電位點亮）、UART rx 70 / tx 69（115200 baud）、reset pin 88（高電位有效）。
- 已寫入 CLAUDE.md 的板子區塊，並標明來源與尚未核對的部分。
- 尚未核對：原理圖或 wiki 腳位圖、USB 兩個通道的用途、pin 88 是否為 S1 按鍵、wiki 寫 BL616 與實際看到的 FTDI VID/PID 的對應。

## 2026-11-02（LED 閃爍上板成功）

- 新增 `rtl/blink.v`（六顆 LED 每 0.5 秒整組亮滅）與 `fpga/blink.cst`（clk pin 4，LED pin 15–20，取自官方範例）。
- `make blink` 在 WSL 編譯成功，`make flash-blink` 透過 JTAG 寫入 SRAM，openFPGALoader 回報 DONE。
- **使用者確認六顆 LED 有閃爍。** 表示 clk 腳位、27 MHz 時脈、LED 腳位與低電位點亮的極性都正確。
- 程式只寫入 SRAM，斷電後消失。
- 尚未核對：兩個 USB 序列埠的用途（JTAG 或 UART）、pin 88 是否為 S1。

## 2026-11-02（BSRAM 自我測試上板）

- `rtl/bsram_test.v`：寫入 256 × 16 的圖樣，逐一讀回比對，結果顯示在 LED。
- 模擬（Icarus）：通過（256 組，515 時脈）。故意把第 100 個字寫錯，測試正確回報 FAIL。
- 合成（yosys）：記憶體映射為 1 個 `SPX9`（BSRAM 原語）。nextpnr 最高 173.58 MHz，27 MHz 通過。
- 上板（SRAM，DONE）：使用者回報 LED 為**同側兩顆亮、其餘暗**，符合 PASS 的預期狀態（led[0]=done、led[1]=pass）。
- 尚未做：用 UART 回傳測試結果，與逐字的讀回值比對；目前只有 PASS/FAIL 的 LED 指示。

## 2026-11-02（M2 第一部分：單顆 LIF 的 RTL 與 bit-exact 模擬）

- `rtl/lif_core.v`：純組合邏輯的單步更新，與 `model/fixed.py` 的 `step()` 一致。中間運算用 18-bit，因為 `-(i >>> 0)` 在 i = -32768 時會超出 16-bit，`v_rest - v` 需要 17-bit。
- 模擬（Icarus 14，cocotb 2.1.0.dev0）：隨機 10,000 組 10,000/10,000 一致；定向 110 組全部一致（飽和、閾值 ±1、不反應期輸入、k_s=0、k_m=0、k=0..15、refrac=0/7、syn_in=-32768）；多步 15 組 × 500 步，發放序列與狀態全部一致。
- 變異測試：把洩漏的 `>>>` 改成 `>>` 後，測試立即抓到不一致，確認比對有效。
- 合成：`synth_gowin` 成功，274 LUT、136 ALU、100 MUX，無 DSP、無 FF（純組合）。
- 命名：輸入埠 `ref` 改為 `ref_cnt`，因為 `ref` 是 SystemVerilog 關鍵字。
- 模型：`fixed.Params` 新增 k_m、k_s 必須在 0..15 的檢查（RTL 的 shift 欄位是 4-bit）。
- 尚未做：board 上的單顆神經元比對，需要 UART 與頂層整合。`sim/lif_core_reg.v` 只用於模擬。

## 2026-11-02（UART 收發器，M1 模擬部分）

- `rtl/uart_tx.v`、`rtl/uart_rx.v`：8N1，分頻 round(27 MHz / 115200) = 234，實際鮑率 115384.6（誤差 +0.16%）。
- 模擬（Icarus 14，cocotb 2.1.0.dev0，`make -f Makefile.uart`）：6/6 通過。包括 10,000 位元組背靠背回送、2,000 位元組隨機空閒、全部 256 個值、外部傳送 0.96–1.04 位元時間的容忍度、發送 start 在忙碌時被忽略。
- 我自己重跑並核對了結果；RTL 的取樣位置與移位方向也已人工檢查。
- 合成：uart_tx 37 LUT / 22 FF；uart_rx 53 LUT / 32 FF。
- 尚未做：板上回送測試（M1 的 UART 驗收項目）。
- 注意：`sim/Makefile` 曾被 UART agent 覆寫，原內容無法復原；神經元測試改用 `Makefile.lif`。

## 2026-11-03（M3 開始：N = 16 網路模擬，論文準備）

**完成**

- D-008（網路更新順序、突觸輸入單次飽和）與 D-009（w_shift 全域常數 = 2）寫入 DECISIONS.md（草稿）。
- `model/network.py` + `model/test_network.py`：7 個新測試，模型測試共 17/17 通過。測試中發現 `synaptic_inputs` 把來源數錯當成目標數，已修正。
- `rtl/network.v`：時間多工排程器，三個階段（神經元更新、事件驅動突觸、交換）。
- `host/gen_net_vectors.py` + `sim/tb_network.v`：3,200 筆紀錄（200 步 × 16 顆）與模型**全部一致**。
- 變異測試：W_SHIFT = 3（440 處不一致）、少算最後一個目標（541）、突觸不傳遞（2158）。三個都被抓到。
- 「同一步延遲」的變異被發現實際上等價於原設計，所以把 `acc_nxt` 的清零從階段 A 移到階段 C，讓設計不再依賴那個順序。
- yosys（N = 16）：約 8,500 cells。這個結構放不下 N = 256，需要改用 BSRAM 與同步讀取。
- 論文準備：`docs/paper/outline.md`（主張、證據檔、章節計畫、圖表清單、參考文獻狀態、待作者決定的事項、不能寫進論文的事項）、`docs/paper/main.tex`（骨架，未編譯，本機沒有 LaTeX）、`docs/paper/references.bib`（只放需要核對的條目，標註 check）。

**尚未做**

- 網路上板（M3 的板上步驟）。
- N = 256（BSRAM 狀態與權重）。
- `WRITE_WEIGHTS` 指令、每顆神經元各自的參數、LFSR 雜訊、板上 raster。
- 論文內文，以及論文的圖（網路 raster、架構圖、掃描摘要）。

## 2026-11-03（M2：完整參數掃描與 README）

**完成**

- `host/sweep.py`：格點（k_m 0–15 × k_s 0–15 × refrac 0–7，2048 組，θ/V_reset/V_rest 固定）與隨機（200 組，固定種子）。每組 3 個輸入 × 300 步，逐步比對模型，並檢查每組前後的 err 計數。
- **板上結果：兩個掃描全部 PASS。** 格點 2048/2048、隨機 200/200。合計 2,023,200 個採樣點，0 不一致，0 次讀取失敗，err 計數器沒有變化。
- 覆蓋：格點 2024 組有發放、24 組沒有；隨機 195 組有發放、5 組沒有。沒有發放的組也被比對。
- 格點約 25 分鐘（1489 秒），隨機約 2 分鐘。
- README 重寫為英文：狀態表、神經元模型與定點格式、驗證方法、M2 板上結果、掃描結果、目錄、執行方式、限制。

**觀察**

- 掃描中 err 計數器沒有變化，所有請求都是有效的。
- 格點掃描中 θ/V_reset/V_rest 固定，它們只由隨機掃描覆蓋。

**尚未做**

- 30 秒上板錄影（使用者操作）。
- M3：256 顆網路。

## 2026-11-03（M2：三組參數比對）

**完成**

- `host/run_trial.py` 改為依序跑三組參數，每組 20 個輸入 × 1000 步，結果存成 `build/m2_trial_<組>.json`（A 組另存為 `m2_trial.json`，供 `plot_trial.py` 使用）。
- 三組參數：A 典型值；B 位移為 0、V_rest > 0、低閾值（會發放）；C 位移為最大值 15、refrac = 7、負輸入使 V 飽和。
- **板上結果：三組皆 PASS，共 60,000 個採樣點，0 不一致，0 次讀取失敗。** 掃描期間 err 沒有增加。
- B 組第一次跑時 θ = 2.0 太高，整組都沒有發放，等於沒有測到發放路徑。改成 θ = 0.5 後，B 組在輸入 ≥ 0.25 時每步都發放，發放路徑有被覆蓋。

**觀察**

- ok 計數器是 8-bit，超過 255 會繞回（這次的 ok 從 93 變成 32）。err 沒有變化。
- 每組只抽樣三組，不是完整掃描。

**尚未做**

- 完整參數掃描；README 第一節；30 秒錄影。

## 2026-11-03（M2：單顆神經元上板比對）

**完成**

- `rtl/neuron_top.v`：uart_rx → cmd_decoder → lif_core（一步一個時脈）→ 記錄記憶體 → 回覆排程器 → uart_tx。記錄記憶體映射為一個 `DPX9B`（BSRAM）。
- `cmd_decoder.v`：新增 RUN（0x04）與 READ_RECORD（0x05），含範圍檢查；新增 `busy` 輸入，回覆傳送中拒絕 STATUS/RUN/READ。
- `protocol.py`：`pack_run`、`pack_read_record`、`unpack_records`。測試 26/26 通過。
- `host/gen_neuron_vectors.py`：期望回覆由 Python 模型（`model/fixed.py`）產生。
- `sim/tb_neuron_top.v`：位元層級模擬，6 個封包、162 個回覆 bytes **全部一致**。變異版（記錄寫入前一步的 V）→ FAIL（56 處不一致）。
- 模擬過程中發現設計缺陷：RUN 在前一次回覆傳送期間開始，會覆寫記錄記憶體。修正：`busy` 拒絕機制；測試台改為一次送一個封包、等回覆再送下一個。
- yosys 合成 `neuron_top`：約 918 cells，記錄記憶體為 1 個 `DPX9B`。
- `make TOP=neuron_top` 建置，`make flash TOP=neuron_top` 燒錄 SRAM。decoder 最高 49 MHz（27 MHz 通過）。
- **板上比對（`host/run_trial.py`）：PASS。** θ = 2.0、V_rest = −0.25、k_m = 4、k_s = 3、refrac = 2。20 個輸入（−0.1 到 0.375），每個跑 1000 步：**20,000 個採樣點的 V 與 spike 與模型逐位元一致，0 個不一致，0 次讀取失敗**，板上 err = 0。
- 板上邊界測試：READ 超出範圍、RUN 0 步、RUN 1025 步、READ 超出 1 步紀錄，四個都被拒絕（err 0 → 4，沒有回覆）。
- `host/plot_trial.py`：產生 `docs/m2_trace_board_vs_model.png`（前 100 步膜電位與 spike 比對）與 `docs/m2_fi_board.png`（20 點 f-I，板上與模型）。

**觀察**

- 發放率在 0.25 之後飽和於 332/1000，符合 refrac = 2 的理論上限（約 1000/3）。
- 目前只比對了一組參數。

**尚未做**

- M2 驗收的文件項目：README 第一節（仍是 stub）。
- 30 秒上板錄影（使用者操作）。
- 其他參數組合的比對。

## 2026-11-03（上板命令鏈測試）

**完成**

- `rtl/cmd_decoder.v` 新增 READ_STATUS（cmd 0x06，len 0）：有效時 ok +1，並送出 `status_req` 脈衝。
- `rtl/cmd_test.v`（頂層）：uart_rx → cmd_decoder → 回覆產生器 → uart_tx。READ_STATUS 時回覆 15 bytes 的狀態封包（cmd 0x86），內容為參數與計數器。LED 顯示 ok 與 err 的低 3 位。
- `fpga/cmd_test.cst`、`fpga/Makefile` 的 `cmd_test_deps`。`make TOP=cmd_test` 建置成功，decoder 最高 139 MHz（27 MHz 通過）。
- `sim/tb_cmd_test.v`（Icarus，位元級串列輸入與輸出）：**PASS**，15-byte 回覆與 Python 產生的期望逐 byte 相同。變異版（回覆 checksum +1）→ FAIL，抓到。
- `sim/tb_cmd_decoder.v` 重跑：PASS（ok=2、err=3）。未知命令的測試改用 0x7E，因為 READ_STATUS 已實作。
- **上板**：`make flash TOP=cmd_test`，`host/board_cmd_test.py` 在 `/dev/ttyUSB1` 上 **5/5 PASS**：有效寫入後參數更新；checksum 錯、k_m = 16、未知命令都被拒絕且參數不變；第二次有效寫入更新參數。

**觀察**

- 第一次跑板上測試時，腳本的計數期望值錯了：READ_STATUS 本身也是有效封包，ok 會因為讀取而加 1。硬體的行為是對的，錯在腳本。修正後全部通過。
- 參數與計數器存在 SRAM，斷電後歸零。
- LED 的顯示沒有被腳本驗證，只能用眼睛確認。

**尚未做**

- 其他命令（WRITE_WEIGHTS、SET_INPUT、RUN、READ_RECORD）的回應與實作。
- 逾時機制（見 4.12）。橋接晶片的分段停頓使得逾時會誤判，目前沒有處理。

## 2026-11-03（FPGA 端命令解碼器與解釋文件）

**完成**

- `rtl/cmd_decoder.v`：byte 串流解析狀態機（SYNC → CMD → LEN → DATA → CSUM），先驗 checksum 再提交。已實作 WRITE_PARAM（9 bytes），提交前檢查 k_m ≤ 15、k_s ≤ 15、refrac ≤ 7。錯誤與成功的封包各有計數器。
- `host/gen_cmd_vectors.py`：用 `protocol.py` 產生 59 bytes 的測試串流（有效、checksum 錯、未知命令、k_m 超出範圍、前置垃圾、有效）與期望值，寫入 `sim/cmd_stream.mem`、`sim/cmd_expect.mem`。
- `sim/tb_cmd_decoder.v`：Icarus 模擬 **PASS**（ok=2、err=3，參數等於第二個有效封包）。
- 變異測試：關掉 checksum 檢查 → FAIL（ok/err 計數不符）；拿掉 k_m 範圍檢查 → FAIL。兩者都被抓到。
- yosys 合成 `cmd_decoder`：約 210 cells，182 FF。緩衝區 16×8 bit 沒有用 BSRAM（太小）。
- `host/protocol.py` 新增 `pack_params`，`host/test_protocol.py` 增至 20 個測試，全部通過。
- `docs/EXPLAIN.md`：解釋專案的理論（LIF、定點數、飽和、算術位移、驗證思想）、硬體與工具鏈、各模組的實作原理，以及還不確定的地方。之後每寫一段程式會同步更新它。

**觀察 / 設計決定**

- 解碼器**沒有逾時**。UART 橋接晶片的分段送出會在封包中間停頓約 2 ms，逾時太短會誤判正常封包。長度欄位損壞時，解碼器會錯位，PC 端要用已知起點重新同步。
- 參數只在 checksum 通過後才寫入，損壞的封包不會改變運作中的參數。
- 測試台有一個無害的警告（`not enough words`），因為記憶體陣列比實際檔案大，只使用前 59 個位元組。

**尚未做**

- 解碼器尚未上板，也沒有回應封包（cmd | 0x80）。
- WRITE_WEIGHTS、SET_INPUT、RUN、READ_RECORD、READ_STATUS 還沒有實作，目前會被計為錯誤。
- checksum、位元組序、命令代碼仍是草稿（D-007）。

## 2026-11-03（host 協定層：protocol.py）

**完成**

- `host/protocol.py`：封包編碼與解碼（`[0xA5][cmd][len][data][checksum]`）、增量解析器（可跨多次收到的資料拼接，遇到壞封包會跳過並重新同步）、Q8.8 與 int8 的打包與解包、指令代碼（寫參數、寫權重、設定輸入、執行、讀紀錄、讀狀態）。
- `host/test_protocol.py`：18 個 pytest 測試（已知向量、長度邊界 0 到 255、壞 checksum、長度不符、壞 sync、逐位元組餵入、前置垃圾、資料中含 0xA5、壞封包後重新同步、數值範圍檢查）。**18/18 通過**（`python -m pytest test_protocol.py`，在 `host/` 目錄執行）。
- 決定與理由記在 DECISIONS.md D-007（草稿）。checksum、位元組序與指令代碼都是我選的，計畫書沒有指定。

**尚未做**

- 協定還沒有接到板子上：目前的 RTL 只有回送，沒有指令解碼。M2 的參數寫入與上板比對需要先實作 FPGA 端的解碼器。
- 指令代碼與回應格式尚未實際驗證。

## 2026-11-03（板上 UART 回送）

**完成**

- `rtl/uart_echo.v`：rx 收到的 byte 原樣送回 tx，中間有 1-byte 暫存。`fpga/uart_echo.cst`：clk 4、rx 70、tx 69。
- `sim/tb_uart_echo.v`（Icarus）：4 個 byte 背靠背回送，4/4 PASS。把暫存改成固定 0 的變異版，測試正確報 FAIL。
- `fpga/Makefile` 新增 `uart_echo_deps`，讓 yosys 同時讀入 `uart_rx.v`、`uart_tx.v`。`make TOP=uart_echo` 建置成功，最高頻率 266 MHz（u_rx），27 MHz 通過。
- `make flash TOP=uart_echo` 寫入 SRAM，DONE。
- 使用 `/dev/ttyUSB1`（FTDI 通道 B）：回送成功，因此 **ttyUSB1 是 UART 通道**。`host/uart_loopback.py` 在這個埠上跑出 4/4 PASS，連跑兩次結果一致。

**觀察：USB-UART 橋接的緩衝限制**

- 一次寫入 96 或 128 bytes：只回來 66 bytes。
- 64-byte 分段、每段間隔 5 ms：回來 232/256。64 bytes 在 115200 下需要 5.6 ms，5 ms 不夠排空。
- 32-byte 分段（5 ms 間隔）與 16-byte 分段（2 ms 間隔）：256/256 全部通過。
- 因此 host 測試改為：短突發（≤64 bytes）一次寫入，長資料按 16-byte 分段、依線速節流寫入。

判斷：這是主機到 BL616 之間的緩衝限制（沒有 RTS/CTS 流控），不是 RTL 的問題。依據是 FPGA 端按線速接收的分段測試全部通過。**但我沒有直接觀察 FPGA 的接收計數**，「丟失發生在橋接晶片」仍是推論。

**M1 UART 驗收（10,000 bytes）**

- `host/uart_loopback.py`：10,000 bytes 隨機資料，按 16-byte 分段節流送出，回送逐位元比對，**0 錯誤**（10,000/10,000）。整次執行約 1.6 秒。
- 這是主機節流下的結果，不是連續背靠背。一次送出超過約 64 bytes 仍會在橋接晶片丟資料，見上方觀察。
- **使用者確認：節流版本算通過 M1 的 UART 驗收。** 背靠背傳輸仍未解決，列為已知限制。

**尚未做**

- 原理圖與 wiki 腳位圖的對照（rx 70 / tx 69 目前只由回送結果確認，沒有與原理圖對照）。
- pin 88 是否為 S1 按鍵。
- M2 的板上單顆神經元比對與 UART 協定（`host/protocol.py` 尚未開始）。
- 「空閒位元」的解讀仍待使用者確認。

## 2026-11-03（M3：網路改為 BSRAM 風格，N = 256 模擬通過）

**完成**

- `rtl/network.v` 重寫：每塊記憶體單寫埠、單同步讀埠（狀態 `smem`、外部輸入 `emem`、權重 `wmem`、發放 `spk`、累加器 `amem`）。突觸累加器改為兩塊交替（`par`），階段 A 與 B 做成流水線。
- 模擬（`sim/tb_network.v`）：N = 16 為 3,200 筆 PASS；N = 64 為 12,800 筆 PASS；N = 256 為 51,200 筆 PASS，全部逐位元一致。
- 變異測試：W_SHIFT = 3、少算最後一個目標、突觸不傳遞、寫到錯誤的累加器緩衝，四個全部 FAIL。
- 綜合（yosys `synth_gowin`）：N = 256 從 45,418 cells 降到 1,457 cells，記憶體改由區塊記憶體承擔（32 DPB、2 SDPX9B、1 DPX9B）。N = 16 與 64 分別為 1,382 與 1,343 cells。
- `sim/tb_network.v` 的逾時從 50 ms 改為 2 s，因為 N = 256 需要約 147 ms 的模擬時間。
- 更新 `docs/EXPLAIN.md` 4.17、`docs/DECISIONS.md` D-010（草稿）、`docs/paper/outline.md`（C7、C8）、`CLAUDE.md` 階段說明。

**觀察**

- 舊版 45,000 cells 來自陣列寫法造成的正反器記憶體，不是演算法本身的成本。
- 隨機網路的發放率偏高，接近不反應期上限（每顆最多 66 次，200 步）。做 E/I 實驗前要調整外部輸入或權重。

**尚未做**

- place-and-route（nextpnr）與 GW2AR-18 的資源確認，目前只有綜合數字。
- 板上網路執行、`WRITE_WEIGHTS` 指令、每顆神經元各自的參數、LFSR 雜訊。

## 2026-11-03（M3：N = 256 place-and-route）

**完成**

- 用測試外殼 `build/pnr/net_pnr_top.v`（不是板上設計）包住 N = 256 網路：輸入接計數器、輸出縮成一個腳位。nextpnr-himbaechel（GW2AR-18）布線成功，`gowin_pack` 產生 `build/pnr/net_pnr.fs`。
- 資源：區塊記憶體 35 / 46（76%），LUT4 785 / 20,736，DFF 392 / 15,552，IOB 2 / 384。
- 最高頻率 47.39 MHz，目標 27 MHz，通過。
- 外殼的綜合數字 1,014 cells，比單獨網路的 1,457 cells 少，原因是計數器輸入讓 yosys 化簡了一部分邏輯。

**尚未做**

- 完整設計（加入 `WRITE_WEIGHTS` 指令解碼與 UART）的 place-and-route。
- 板上網路執行。
- 燒錄 `net_pnr.fs`：沒有燒，這個檔案只用來確認流程。

## 2026-11-03（M3：完整設計，網路接上 UART 命令）

**完成**

- 協定擴充（`host/protocol.py`，草稿 D-011）：WRITE_WEIGHTS 0x02、SET_INPUT 0x03、READ_COUNTS 0x07、READ_SNAPSHOT 0x08；STATUS 網路版回覆 4 bytes（ok、err、已完成步數）。新增測試 31 項全部通過。
- `rtl/cmd_decoder.v`：payload 緩衝從 16 增加到 255 bytes，新增四個命令與範圍檢查；`busy` 現在也擋 WRITE_PARAM。原有的解碼器、命令測試、單顆神經元上板版模擬都重跑，仍然通過。`neuron_top` 與 `cmd_test` 補上 `buf_addr` 的 tie-off。
- `rtl/network_top.v`：完整設計。UART → decoder → 複製 FSM（權重與輸入）→ 網路；執行控制清計數器；每筆紀錄更新計數器與快照；回覆排程器送 STATUS、COUNTS、SNAPSHOT。
- `host/gen_net_top_vectors.py` 與 `sim/tb_network_top.v`：位元組層級測試。N = 16：14 個封包、112 bytes 回覆，全部一致（err = 3，對應三個壞封包）。N = 64：52 個封包、352 bytes，全部一致。N = 256：675 個封包、1,336 bytes 回覆，全部一致（ok = 672、err = 3）。N = 256 的第一次執行因為測試台的 stream 陣列太小而失敗，已修正。
- 變異測試：輸入位元組對調、範圍檢查差一、計數器時序錯誤，三個都 FAIL。
- `make TOP=network_top`（`fpga/Makefile` 新增 `network_top_deps`，`fpga/network_top.cst` 與 `neuron_top.cst` 相同腳位）：布線成功，產生 `fpga/build/network_top.fs`。LUT4 2,355（11%）、DFF 1,264（8%）、區塊記憶體 37 / 46（80%），最高頻率 42.9 MHz，目標 27 MHz 通過。

**觀察**

- yosys 對 `wmem` 的 BSRAM 映射發出 12 條 `brams_map.v` 警告（填補為 undef 的位元）。映射實例是 1-bit 寬度的條塊，推論是填補位元，但**沒有用網表模擬證明**。我寫的網表比對工具連 DFF 映射的記憶體也讀到 `x`，所以目前不能用來判斷，要先除錯。
- decoder 的 ok、err 計數器是 8-bit，超過 255 會繞回。第一版的 host 期望值沒有繞回，N = 256 的測試生成器因此出錯，已修正。

**尚未做**

- 網表層級的記憶體驗證（見上）。
- 板上網路執行：已燒錄，見下一筆。
- READ_RECORD 在網路版沒有回覆，但仍被計為 ok。host 不應送。
- 每顆神經元各自的參數、LFSR 雜訊。

## 2026-11-03（完整網路上板：N = 256 流程測試通過）

**完成**

- `make flash TOP=network_top`：`network_top.fs` 燒進 SRAM，完成。
- `host/board_network_test.py`（新增）：讀 `sim/nt_*.mem`，經 `/dev/ttyUSB1` 送出 675 個封包（16 bytes 分段，按線速節流），每個有回覆的封包讀完整回覆後與模型比對。
- **板上結果：PASS。** 1,336 bytes 回覆全部一致，最後 ok = 672、err = 3，耗時 45.5 秒。

**觀察**

- 第一次模擬超時是測試台的陣列太小，不是設計的錯；修正後模擬與板上都通過。
- 板上通過的是整條路徑（命令、權重與輸入載入、執行、讀回）。它不是逐步軌跡比對，也不包含 E/I 實驗。

**尚未做**

- 網表層級的記憶體映射驗證（`wmem` 的 12 條 `brams_map.v` 警告，仍未證實）。
- E/I 實驗與逐步的板上軌跡比對。
- READ_RECORD 在網路版沒有回覆，但仍被計為 ok，host 不應送。

## 2026-11-04（網表比對工具停止；E/I 擾動實驗）

**決定**

- 網表模擬停止追查。原因：安裝的 Gowin 區塊記憶體模擬模型是空的，這個工具鏈無法做網表模擬。使用者選擇以上板結果作為功能驗證。

**完成**

- `host/ei_sweep.py`：N = 256 的 E/I 參數掃描（f_inh、w_max、e_max）。第一次掃描（w_max = 60）網路不是沉默就是飽和，改掃 w_max 後找到 `w_max = 10`、`e_max = 30` 的不飽和區間。
- `host/ei_experiment.py`：f_inh 從 0 到 0.6，每個 3 個隨機網路。發放率從 0.316 單調降到 0.123，沉默神經元從 0 增加到 0.26。
- `host/ei_board_test.py`：f_inh = 0.2 與 0.5 兩個條件上板，各 662 個封包，所有回覆與完整模型（`run_network`）逐位元一致，PASS。
- `host/plot_ei.py` → `docs/ei_rate_vs_finh.png`。
- 文件：EXPLAIN 4.19（E/I 實驗）與 4.18（網表決定）、DECISIONS D-012（草稿）。

**觀察**

- 在 `w_max = 60` 時，網路由遞迴連線主導。單一輸入約 0.94，就能把電位推到閾值 1.5 附近，外部輸入的影響幾乎消失。這是擾動實驗選 `w_max = 10` 的原因。
- 掃描的 f_inh = 0 時發放率 0.316，接近不反應期上限 0.333，所以有意義的範圍約為 0.2 到 0.5。

**尚未做**

- 只掃了 f_inh。抑制權重、e_max、連線機率都還沒有掃。
- 論文正文、README 的網路段落。
- 30 秒上板錄影（你操作）。

## 2026-11-04（E/I 完整掃描）

**完成**

- `host/ei_full_sweep.py`：f_inh 0 到 0.6（每 0.1）× w_inh 0.5 / 1.0 / 1.5 / 2.0 × w_max 10 / 20 × e_max 10 / 30 / 60 × 3 個隨機網路，共 504 次模型執行（約 4 分鐘）。
- `host/ei_full_summary.py`：每組合（24 組）的平均，寫入 `build/ei_full_summary.csv`。
- 結果：24 組在 f_inh 增加時全部單調不增（容許誤差 0.005）。抑制權重 w_inh 的效果明顯，w_max = 10、e_max = 30、f_inh = 0.6 時，w_inh 從 0.5 到 2.0，發放率從 0.160 降到 0.085。

**觀察**

- 修正先前的說法：f_inh 小於 0.2 時，大部分神經元已在不反應期上限附近（w_max = 10、e_max = 30、f_inh = 0 時 79% 超過 0.3）。有效的擾動範圍是 f_inh 約 0.2 到 0.6。
- w_max = 20 時 f_inh = 0 幾乎全部飽和，不適合做擾動。
- e_max = 60 時即使 f_inh = 0 也有 91% 飽和，e_max = 30 比較乾淨。

**尚未做**

- 上板（`host/ei_board_test.py`，已加入 `--w-inh`，網路與完整掃描相同）：共 5 個條件，每個 662 個封包，所有回覆（計數與快照）都與完整模型逐位元一致。條件是 w_inh = 1、w_max = 10、e_max = 30 的 f_inh = 0.2 與 0.5；f_inh = 0.5 的 w_inh = 0.5 與 2.0；f_inh = 0.3、w_inh = 1.5、w_max = 20、e_max = 10。其他組合只在模型中。
- 沒有掃連線機率與每顆神經元不同的參數。
- 論文正文、README 的網路段落。
- 30 秒上板錄影（你操作）。

## 2026-11-04（README 網路段落）

**完成**

- `README.md`：狀態改為 2026-11-04，M3 列為完成（模擬與上板 N = 256 流程），E/I 列為模型掃描與 5 個上板條件。新增第 4 節「256-neuron network (M3)」：模型式子、硬體結構、板上命令與讀回方式、N = 256 資源數字、驗證表、網表模擬的限制、E/I 實驗設定與結果。
- 目錄與執行指令：補上網路相關的檔案，以及板上與 E/I 模型的執行指令。限制段加入網路版的限制。
- 文件只改敘述，沒有改程式。數字都取自 `docs/EXPLAIN.md` 4.17 到 4.19 與 `build/ei_experiment.csv`（3 個網路的平均）。

**觀察**

- 修正先前的說法：上板的 5 個條件涵蓋 24 組參數中的 4 組（不是 5 組）。README 已改成「5 個條件、4 組參數」。
- README 的 E/I 發放率表使用 `build/ei_experiment.csv` 的 3 網路平均（w_inh = 1）。板上 f_inh = 0.2、0.5 的模型平均率 0.238、0.144 是單一網路（種子 20261104），兩者不同，README 沒有混用。

**下一步**

- 論文正文（`docs/paper/`）與錄影仍待做。
- 若要板上做逐步的軌跡比對，需要先決定是否加入軌跡讀回命令。

## 2026-11-04（逐步 spike 軌跡：READ_TRACE）

**完成**

- `rtl/network_top.v`：spike 軌跡記憶體（8 bit 寬，512 步 × N/8）。每筆紀錄收進 8 bit 移位暫存器，湊滿一個 byte 就寫入，位址是 `{steps_done, 神經元 k 的高位}`。只保留一次 RUN 的前 512 步。讀回時 7 步一個回覆。
- `rtl/cmd_decoder.v`：新命令 READ_TRACE（0x09），起始步 2 bytes、步數 1 byte（1..7）。範圍檢查用 `min(run_len, 512)`，讀不到上一次較長 RUN 的舊資料。
- `host/protocol.py`：`Cmd.READ_TRACE`、`pack_read_trace`、`unpack_trace`，以及兩個測試（`host/test_protocol.py`，33 個測試通過）。
- `host/gen_net_top_vectors.py`：加入軌跡的讀取與壞封包（超出範圍、步數 0、步數 8）；可以指定 T。
- `host/ei_board_test.py`：每個條件在最後讀回前 min(steps, 512) 步的 spike，與 `run_network` 逐位元比對。

**驗證**

- 模擬（位元組層級）：N = 16、T = 200 PASS；N = 16、T = 600 PASS（測 512 上限的 off-by-one）；N = 64、T = 200 PASS；N = 256、T = 200 PASS（682 個封包，1,892 bytes）。
- 變異測試：bit 順序、步位址加 1、上限 513、數量上限 8，四個都 FAIL。
- 既有的 decoder 與 neuron_top 測試（`tb_cmd_decoder`、`tb_cmd_test`、`tb_neuron_top`）：PASS。
- place-and-route：BSRAM 45 / 46，LUT4 2,536，DFF 1,315，最高 41.38 MHz，通過。
- 板上：五個 E/I 條件，每個 736 個封包（計數、快照、前 512 步的軌跡），全部與 `run_network` 逐位元一致。

**觀察**

- 重跑時 w_inh = 1 的兩個條件得到的模型發放率是 0.246（f_inh 0.2）與 0.138（f_inh 0.5），與先前文件寫的 0.238 與 0.144 不同。網路生成與比對對象相同，板上比對仍然通過。舊數字的來源沒有查明；`docs/EXPLAIN.md` 4.19 已改為重跑的數字，並註明。
- WSL 的 Python 沒有 pytest，測試改用 Windows 的 Python 執行。
- 板上的 N = 256 命令流程測試第一次跑時 FAIL：3 個狀態回覆不符。原因是 E/I 五個條件之後，板上的 ok/err 計數與步數沒有歸零，而這個測試假設剛燒完的板子。重新燒錄（SRAM 重設）後再跑：682 個封包、1,892 bytes，全部 PASS。

**下一步**

- 論文正文與 30 秒錄影（你操作）。

## 2026-11-04（全面檢查與修正）

**完成**

- 飽和規則的文字：程式與測試都是「精確求和，加上外部輸入後只飽和一次」，但四份文件寫成兩次飽和。已改為一次：`model/network.py` 的 docstring、`README.md` 第 4 節、`docs/DECISIONS.md` D-008、`docs/EXPLAIN.md` 4.17。
- E/I 板上腳本的封包數：每個條件 745 個封包（1 個開始的 READ_STATUS、1 個 WRITE_PARAM、656 個 WRITE_WEIGHTS、3 個 SET_INPUT、1 個 RUN、1 個 READ_STATUS、4 個 READ_COUNTS、4 個 READ_SNAPSHOT、74 個 READ_TRACE）。先前寫的 736 是腳本列印的總數，漏了開始的狀態讀取與 8 個計數／快照封包。README、CLAUDE.md、DECISIONS D-013、EXPLAIN 4.19、4.20 已改為 745。舊的 LOG 條目保留不改，更正寫在這裡。
- 發放率差異：板上腳本 `ei_board_test.py` 的 W 與 `ei_sweep.py`、`ei_experiment.py` 相同，但 ext 的抽取順序不同。w_inh = 1 時 W 一樣，所以只有 ext 造成發放率不同。板上腳本的數字是全部 600 步，`ei_sweep.measure` 與 `ei_experiment.py` 扣掉前 100 步。EXPLAIN 4.19 與 DECISIONS D-012 已寫明。舊的 662 個封包執行沒有用舊的 ext 抽取方式重跑，所以不能說舊網路已重現。
- 過時數字：README（675 改為 682、70,168 bytes、1,892 bytes；E/I 736 改為 745）、CLAUDE.md 的目前階段與常用指令、DECISIONS D-010 與 D-011 的狀態、`docs/paper/outline.md` 的 C8 與第 6 節。
- 新行為的說明：`host/pytest.ini`；`pack_read_trace` 拒絕「起始 + 數量 > 512」，`unpack_trace` 拒絕 n ≤ 0；板上腳本的 RUN 等待改為依步數計算（固定 2 秒對 N = 256、1024 步不夠）；腳本 FAIL 時結束碼為 1；`ei_board_test.py` 同時印出全部步與扣除暖機後的發放率；新增 `sim/tb_decoder_busy.v`（忙碌時所有命令都被拒絕）；`sim/Makefile` 統一入口；`cmd_decoder.v` 註解修正（READ_RECORD 在忙碌時也被拒絕）；網路版要求 N 為 2 的次方且 N ≥ 16；READ_TRACE 每封包 7 步的上限只在 N ≤ 256 成立；`gen_net_top_vectors.py` 要求 7 ≤ T ≤ 1024。以上寫入 EXPLAIN 4.11、4.18、4.20 與 README 的驗證表與執行指令。

**驗證**

- busy 拒絕測試（`sim/tb_decoder_busy.v`）：PASS，9 種命令在忙碌時都被拒絕（err +9、沒有任何 req 脈衝、theta 不變），忙碌解除後 WRITE_PARAM 與 RUN 被接受。變異測試：讓 READ_STATUS 不檢查 busy，測試台 FAIL（3 項不符），所以這個測試抓得到錯誤。
- 模擬重跑（`sim/Makefile`）：decoder_busy、decoder、cmd_test、neuron_top、uart_echo、bsram、network（N = 16，3,200 筆）、network_top（N = 16，21 個封包）全部 PASS。檢查前另以手動指令跑過 cocotb lif_core（2 + 1）、cocotb UART（6/6）、network 與 network_top N = 64（12,800 筆；59 個封包），全部 PASS。N = 256 的位元組層級模擬這次沒有重跑（RTL 只改了註解）。
- 板上重跑：沒有做。RTL 只改註解，位元流不變；上板腳本的改動（等待時間、結束碼、封包計數）還沒在板上跑過。
- host 的 pytest（`host/` 下 `python -m pytest`）：35 passed，沒有 collection error。model 的 pytest：17 passed。`gen_net_top_vectors.py 16 5` 會以錯誤訊息結束（結束碼 1）。

**觀察**

- 飽和文字的錯誤存在四份文件中，程式與測試一直是正確的。這次修的是文件，不是程式。
- 板上計數器跨 session 保留，沒有 reset 命令，所以 `board_network_test.py` 仍然需要剛燒完的板子。這個問題沒有修。
- E/I 發放率的解釋已用兩種抽樣方式各跑一次模型確認：目前的抽法得到 0.246 / 0.138（全部 600 步），舊抽法得到 0.238 / 0.144，與兩組舊數字完全相同（見 EXPLAIN 4.19）。
- STATUS 回覆的「4 bytes」與「8 bytes」並不矛盾：資料是 4 bytes（ok、err、步數 2 bytes），加上 sync、cmd、len、checksum，整個封包是 8 bytes。

**下一步**

- 下次上板時用新版腳本重跑 `board_network_test.py` 與一個 E/I 條件，確認等待時間與 745 個封包的計數。
- 決定網路的 Icarus 測試（用 Python 產生的 .mem，不是 cocotb）是否符合 CLAUDE.md 的 cocotb 鐵則。
- 可選：加入 reset 命令。
- 原理圖與腳位核對（rx 70、tx 69、pin 88）。
- 論文正文（`docs/paper/`）與錄影。

## 2026-11-04（論文正文初稿）

**完成**

- `docs/paper/main.tex`：寫完全文初稿（摘要、引言、模型、硬體、驗證、結果、資源、限制、可用性、AI 聲明）。所有數字取自 `outline.md` 的證據檔，並重新核對：`build/sweep_grid.csv`、`build/sweep_random.csv`（2,048 + 200 組，mismatch、failures、err_delta 全為 0；有發放的組 2,024 + 195）、`build/ei_experiment.csv`（各 f_inh 的平均與範圍）、README 與 EXPLAIN 的板上數字。
- `docs/paper/references.bib`：新增 szczerek2025、ansari2026、cheung2009、fan2025，每筆都標了待核對的欄位。
- `docs/paper/outline.md`：各節狀態改為 first draft；第 6 節「不能寫的內容」改為涵蓋已有的板上證據。

**驗證**

- 沒有 LaTeX 編譯器，所以沒有編譯。靜態檢查：所有引用鍵都在 bib 中、所有 `\ref` 都有對應的 label、環境與大括號平衡、兩個圖檔存在。
- 初稿中有三處不準確的句子，自查後已改：摘要把 2,023,200 個採樣點算在三組手選參數上（其實 60,000 個在三組、2,023,200 個在掃描）；把「測試台抓到覆寫錯誤」寫成變異測試抓到；對文獻的概括太廣，改為只涵蓋已讀的論文。

**觀察**

- 論文只寫「硬體對模型」的一致性，沒有生物學結論。E/I 示範只用模型數據，板上只有五個條件。
- 文獻：Brunel 2000 沒有全文，只在引言用於「這類網路」的描述；Lam 2022 未引用，因為沒有全文。

**下一步**

- 作者改寫成自己的文字（標題、作者、摘要、引言的缺口陳述）。
- 安裝 LaTeX 後編譯；補 E/I 圖（`docs/ei_rate_vs_finh.png`）與架構圖。
- 核對每筆參考文獻的 DOI 或網址；取得 Lam 2022 全文。
- 重新上板驗證新腳本後，再確認論文中板上流程的數字。

## 2026-11-04（論文標題、作者、摘要與引言）

**完成**

- 論文初稿已 commit（`bee7a64`）。
- `docs/paper/main.tex`：標題改為 Bit-Exact Verification of a 256-Neuron Fixed-Point Spiking Network on a Low-Cost FPGA；作者 ChiaAn Lin（ntuhibiki@gmail.com，通訊作者）；單位保留 TODO。摘要與引言重寫：摘要涵蓋問題、方法、單顆神經元與網路的板上結果、資源、E/I 模型掃描、限制與「無生物學主張」；引言有動機、位元精確的標準、相關工作、缺口陳述、三項貢獻與全文架構。
- `docs/paper/references.bib`：新增 gautam2025（標題為意譯，標了待核對）。

**驗證**

- 沒有編譯（沒有 LaTeX）。靜態檢查：引用鍵、`\ref`、環境與大括號、圖檔都通過。
- 摘要與引言中的數字重新對過：60,000 + 2,023,200 = 2,083,200 個單顆神經元採樣；2,248 組掃描；682 個封包；5 個 E/I 條件；512 步；2,536 LUT4（12%）、45/46 BSRAM（97%）、41.38 MHz；504 次模型執行、24 個組合全部單調。
- 寫的過程中自查改掉兩處：「FPGA 比通用處理器更快更便宜」沒有證據，已刪除；把 Cheung 2009 寫成「位元精確比對」的例子，其實它是速度導向的模擬器，已分開寫。

**觀察**

- 引言的缺口陳述（「在我們回顧的設計中，沒有找到同時具備遞迴抑制網路、逐步位元精確比對、變異測試的設計」）只涵蓋我們讀過的論文，不是整個文獻。檔案裡標了 CHECK，由作者決定保留、放軟或刪除。
- 引言引用 Fan 2025 與 Gautam 2025 的方式，以導讀的內容為準（Fan：MNIST 準確度；Gautam：推論的功能一致）。

**下一步**

- 作者核對摘要與引言，改寫成自己的文字；補單位；決定缺口陳述。
- 在有 LaTeX 的環境編譯；補 E/I 圖與架構圖。
- 核對 bib 每筆的 DOI 與網址，特別是 gautam2025 的完整標題。
- 更新：作者要求刪掉引言的缺口陳述（「在我們回顧的設計中沒有找到…」）。已刪除，並把前後句改為「本文把這個嚴格標準套用到有抑制連線的遞迴網路」，不再主張新穎性。


## 2026-11-04（安裝 LaTeX 並編譯論文）

**完成**

- 用 winget 安裝 MiKTeX 25.12（使用者範圍，不需系統管理員）。`pdflatex`、`bibtex` 都能執行。
- 開啟 MiKTeX 按需安裝（`[MPM]AutoInstall=1`），讓 natbib、booktabs、hyperref 等套件第一次用到時自動下載。
- 編譯 `docs/paper/main.tex`（pdflatex、bibtex、pdflatex 兩次）。輸出放在暫存資料夾，沒有寫進 repo。結果：11 頁，0 個錯誤，0 個未定義的引用，7 筆參考文獻全部解析。
- 修正 `references.bib`：cheung2009 的 `note` 欄位含有底線的網址，BibTeX 會把它原樣輸出到參考文獻，造成 `Missing $` 錯誤。改為標準的 `url` 欄位。

**觀察**

- 目前的 `note` 欄位（例如 `check: ...`）會印在 PDF 的參考文獻裡。這是草稿用的提醒，投稿前要移除。
- 有兩個 overfull hbox（約 11 pt、22 pt），只是排版上的小問題，之後再調。
- 沒有檢視 PDF 的版面（環境沒有 pdftoppm），只用 log 驗證。

**下一步**

- 作者用 PDF 檢查版面與標題、作者的顯示。
- 投稿前移除 `note` 裡的 check 提醒。
