# FPGA 上的 SNN 加速器綜述（A Survey of Spiking Neural Network Accelerator on FPGA）

- 作者、年份、期刊/會議：Murat Isik，2023，arXiv:2307.03910（預印本）
- 連結：https://arxiv.org/pdf/2307.03910
- 全文狀態：全文已讀
- 本地 PDF：docs/papers/pdfs/isik2023-neuron-models-fpga.pdf
- 注意：論文實際題目為綜述，任務列出的「各種神經元模型的 FPGA 實作比較」與內容不符。

## 一句話重點
綜述 FPGA 上的 SNN 加速器，整理神經元模型、編碼格式與硬體設計技術，並討論發展趨勢。

## English summary
This survey reviews FPGA-based spiking neural network accelerators, covering neuron models, spike coding formats, and hardware design techniques. It categorizes neuron models such as Hodgkin-Huxley, Izhikevich, and LIF and discusses their hardware trade-offs. The author outlines trends and optimization directions rather than running a new head-to-head experiment.

## 與本專案的關係
- 可作為 M1 階段的文獻入門，以及 LIF 與 Izhikevich、Hodgkin-Huxley 在複雜度與硬體實作上的選型背景。
- 本專案選 LIF 的理由可引用其分類，但綜述不提供本專案所需的 bit-exact 規格。

## 重點方法與數字
- 綜述本身沒有新的實驗數字，表格內的文獻數字未逐項核對（未確認）。
- 將神經元模型依複雜度與硬體可實作性排序。
- 列舉 FPGA SNN 的應用實例，如語音、生醫與自駕。

## 限制與注意
- 不是實作比較，不能用來比較不同神經元模型在 FPGA 上的效能。
- 綜述截至 2023 年，之後的研究未涵蓋。
