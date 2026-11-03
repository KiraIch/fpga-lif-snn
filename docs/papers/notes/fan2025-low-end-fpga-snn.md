# 低階 FPGA 上的開源 SNN 框架（A Robust, Open-Source Framework for Spiking Neural Networks on Low-End FPGAs）

- 作者、年份、期刊/會議：Andrew Fan, Simon D. Levy，2025，arXiv:2507.07284（v2，2025 年 7 月）
- 連結：https://arxiv.org/pdf/2507.07284
- 全文狀態：全文已讀
- 本地 PDF：docs/papers/pdfs/fan2025-low-end-fpga-snn.pdf

## 一句話重點
在低階 Artix-7 上以分塊的 any-to-any 突觸陣列傳遞 spike，並以 PyTorch 編譯器部署 8-bit 量化的 LIF 網路。

## English summary
The paper presents an open-source framework that pairs a tiled, any-to-any synaptic array on a low-end Artix-7 FPGA with a PyTorch-based model compiler. Membrane potentials and weights are quantized to 8 bits, and the authors report 0.52 ms per MNIST image at 100 MHz. The abstract lists about 6,358 LUTs and 40.5 BRAM blocks for the architecture.

## 與本專案的關係
- 與 GW2AR-18 同屬小型 FPGA，資源與 BRAM 限制相近，可作為資源規劃的參考。
- 8-bit 量化「足以維持精度」的論點，可與本專案 Q8.8 16-bit 的選擇做對照。
- PyTorch 到硬體的編譯流程，可作為本專案未來 Python 模型與 RTL 之間介面的參考。

## 重點方法與數字（全文可確認）
- LIF 以 Euler 離散化：U(t) = αU(t−1) + I(t)，spike 以 Heaviside 閾值判定。
- 突觸陣列分塊（tile）傳播 spike，支援全連接與任意連接的網路。
- 權重與膜電位量化為 8-bit 後寫入 BRAM。
- MNIST 推論 0.52 ms/img，100 MHz，Artix-7。

## 限制與注意
- 摘要的 LUT 數字與全文表格不一致，需以原表為準（未確認）。
- 結果以 MNIST 推論為主，未探討與參考模型的逐位元一致性。
- 作者開源的程式碼未檢查。
