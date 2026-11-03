# FPGA 上的快速 SNN 模擬演算法（Fast Algorithms for Spiking Neural Network Simulation with FPGAs）

- 作者、年份、期刊/會議：Björn A. Lindqvist, Artur Podobas（KTH），2024，arXiv:2405.02019（預印本）
- 連結：https://arxiv.org/pdf/2405.02019
- 全文狀態：全文已讀
- 本地 PDF：docs/papers/pdfs/lindqvist2024-energy-per-synaptic-event.pdf
- 注意：論文實際題目與任務列出的題目不同；能耗指標是論文的一部分，不是全篇主題。

## 一句話重點
以 OpenCL 高階合成在 Intel Agilex 7 上實作 Potjans-Diesmann 皮質微電路的模擬器，並報告每突觸事件的能耗上下限。

## English summary
The authors build OpenCL high-level-synthesis simulators for the Potjans-Diesmann cortical microcircuit on a single Intel Agilex 7 FPGA. Their best simulator runs about 25% faster than real time. They report energy per synaptic event with pessimistic and optimistic bounds of about 21 nJ and 9 nJ.

## 與本專案的關係
- E/I 實驗需要效能與能耗的報告指標，可借用 nJ/synaptic event 的定義，以及並列上下限的寫法。
- 論文引用 van Albada 等人（2018）的能耗定義，可作為本專案能耗指標的參考來源。
- 本專案的 GW2AR-18 能耗量測方式需另外設計，不能直接與此論文比較。

## 重點方法與數字（全文可確認）
- 能耗以板上功耗乘以模擬時間估計，依 synaptic events 換算。
- 能耗上限約 21 nJ/event，下限約 9 nJ/event。
- 最佳模擬器比即時快約 25%；作者在引言中另寫為約 1.2 倍。

## 限制與注意
- 摘要寫 21 nJ 以下，引言寫 25 nJ/event，數字不一致，需以正文表格為準。
- 平台是大型 Agilex 7，模型規模是數萬神經元級別，與本專案的 256 神經元不在同一量級。
- 能耗為上限估計，論文自承實際值可能更低。
