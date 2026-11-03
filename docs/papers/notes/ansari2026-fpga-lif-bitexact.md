# A Time-Multiplexed Spiking Neural Network Accelerator with Pipelined Readout for FPGA Inference

- 作者、年份、期刊/會議：Reza Ansari、Maciej Wielgosz（AGH University of Science and Technology），2026，arXiv:2608.00595v1（2026-08-01，未經同儕審查的預印本）
- 連結：https://arxiv.org/pdf/2608.00595
- 全文狀態：全文已讀（依規定精讀摘要、引言、架構與結論章節，未逐頁抄錄）
- 本地 PDF：docs/papers/pdfs/ansari2026-fpga-lif-bitexact.pdf

> 注意：清單題目「FPGA 整數 LIF 與逐位元驗證」與文件實際題目不符，以上列文件題目為準。

## 一句話重點

以時間多工與流水線 argmax 讀出設計一個 MNIST 推論用的 SNN 加速器，使用整數 LIF 神經元並與軟體參考模型逐位元比對。

## English summary

Ansari and Wielgosz present a time-multiplexed, inference-only SNN accelerator for MNIST on an Artix-7 FPGA. Their integer LIF neurons are checked against a bit-accurate software reference model, and a pipelined argmax readout raises Fmax from 13.3 MHz to 167 MHz. The target is a 784-64-10 classification network, so it is not a recurrent E/I design.

## 與本專案的關係

本專案 M1 的核心要求是 RTL 與 Python 定點模型逐位元一致，此文的「整數 LIF + 軟體參考模型比對 + VHDL testbench」流程可作為驗證做法的參考。其 LIF 更新式以位移取代乘法（leak 為 shift 運算），與本專案「位移代替乘法」的數值規則相近。流水線 argmax 的做法可供日後讀出層參考。

## 重點方法與數字（只列能從全文確認的）

- 時間多工的 1-bit spike feeding，由 FSM 控制，權重分散存放於各區域記憶體，以降低布線壓力。
- LIF 更新式：V[t+1] = V[t] − (V >> leak_shift) + I_syn[t]，並以暫存器寬度避免溢位。
- 以 10,000 筆 MNIST 測試集與五組隨機種子，對照 bit-accurate 軟體 SNN 參考模型，並以 VHDL testbench 驗證結構等價性。
- 在 Artix-7 XC7A200T 上 Fmax 由 13.3 MHz 提升至 167 MHz；單張影像延遲約 82 µs；功耗為 Vivado 估計的 0.336 W，能效約 36,300 samples/J（估計值）。

## 限制與注意

- 只在 MNIST 上驗證，無遞迴連接與 E/I 抑制，不能直接對應本專案的 256 神經元 E/I 實驗。
- 目標板為 Artix-7（AC701 評估板），與本專案的 Tang Nano 20K（GW2AR-18）資源與時脈不同，效能數字不可直接套用。
- 功耗與能效為估計值，且為未經同儕審查的 arXiv 預印本。
