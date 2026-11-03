# QUANTISENC：可配置的量化 SNN 核心（A Fully-Configurable Open-Source Software-Defined Digital Quantized Spiking Neural Core Architecture）

- 作者、年份、期刊/會議：Shadi Matinizadeh 等（Drexel 大學、Accenture Labs），2024，arXiv:2404.02248（預印本）
- 連結：https://arxiv.org/pdf/2404.02248
- 全文狀態：全文已讀
- 本地 PDF：docs/papers/pdfs/matinizadeh2024-quantisenc.pdf

## 一句話重點
由軟體定義層數、神經元數與 Q 格式（位元寬與小數位）產生 LIF 硬體核心，並以 PyTorch 訓練模型後評估資源與功耗。

## English summary
QUANTISENC is an open-source, software-defined digital SNN core that generates hardware from a layer configuration defined in PyTorch. Its LIF neurons use signed fixed-point arithmetic with user-selectable bit width and decimal precision. The authors sweep several Q formats and report LUT, FF, BRAM, DSP, and power for each setting.

## 與本專案的關係
- 直接對應本專案「以 Q 格式掃描選位元寬」的需求，論文的掃描方法可作為本專案定點選擇的依據。
- 可用其資源與功耗表的趨勢，估計 256 神經元在 GW2AR-18 上的資源。
- 差異：論文平台是大型 Virtex/Zynq UltraScale，且其規格與本專案的 model/fixed.py 不同，本專案仍以 model/fixed.py 為準。

## 重點方法與數字（全文可確認）
- 量化比較：16-bit（Q9.7）的 RMSE 為 0.25 mV，8-bit（Q5.3）為 0.43 mV（論文所述的資料設定未確認）。
- 基線網路為 256-128-10，8-bit（Q5.3），論文報告約 48k LUT、約 9% 資源；功耗隨位元寬上升。
- 支援 layer 間 pipeline，以分散式突觸記憶體提升吞吐量。

## 限制與注意
- 單一 LIF 神經元的 LUT 與 FF 數字，在文字與表格之間不一致，使用前需核對原表。
- 論文平台與本專案的低階 FPGA 差距大，資源數字不能直接套用。
- 論文的 LIF 採 CUBA 突觸，與本專案的突觸模型是否相同需再確認。
