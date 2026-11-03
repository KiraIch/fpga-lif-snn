# 簡化 SNN 的 FPGA 實作（FPGA Implementation of Simplified Spiking Neural Network）

- 作者、年份、期刊/會議：Shikhar Gupta, Arpan Vyas, Gaurav Trivedi（IIT Guwahati），2020，IEEE ICECS（27th）；arXiv:2010.01200
- 連結：https://arxiv.org/pdf/2010.01200
- 全文狀態：全文已讀
- 本地 PDF：docs/papers/pdfs/gupta2020-non-timemultiplexed-snn.pdf

## 一句話重點
以事件驅動的簡化 LIF 加上線上 STDP，在 Virtex-6 上實作 800 個神經元的全連接網路，每個輸出神經元有獨立的運算單元。

## English summary
The authors implement a simplified, event-driven LIF network with online STDP on a Virtex-6 FPGA. The network has 800 neurons and 12,544 synapses, and the design updates a neuron only when there is spiking activity. The paper reports resource usage at 100 MHz and compares against other FPGA SNN designs by time resolution and resources per neuron.

## 與本專案的關係
- 作為「不採時分多工」的對照：每個輸出神經元有專屬的電位加法與權重單元，可看出 LUT 用量與時分多工的取捨。
- 本專案 GW2AR-18 資源有限，需評估 256 神經元是否能以時分多工或類似方式實作。
- 論文的事件驅動概念與 Cheung 2009 的 activity factor 思路相近。

## 重點方法與數字（全文可確認）
- Xilinx XC6VLX240T，100 MHz；網路為 784 輸入加 16 輸出神經元，共 12,544 個突觸。
- Slice LUT 56,230（37%），FF 23,238（8%），BRAM 16（4%），DSP48E1 64（8%）。
- 依活動度動態調整時間單位，減少無 spike 時的運算。

## 限制與注意
- 論文未明確以 "non-time-multiplexed" 作為自述關鍵字，此分類來自任務描述（未確認）。
- 論文同時出現 24-bit 與 floating-point 的描述，數值表示的細節未確認。
- 結果只針對 XC6V，與 GW2A 的資源不可直接比較。
