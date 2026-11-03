# A Quarter of a Century of Neuromorphic Architectures on FPGAs - an Overview

- 作者、年份、期刊/會議：Wiktor J. Szczerek、Artur Podobas（KTH Royal Institute of Technology），2025（arXiv 首版；本檔為 v4，2026-05-18 版），arXiv 綜述
- 連結：https://arxiv.org/pdf/2502.20415
- 全文狀態：全文已讀（依規定精讀摘要、引言、分類方法與結論，未逐篇核對表格）
- 本地 PDF：docs/papers/pdfs/szczerek2025-fpga-neuromorphic-survey.pdf

## 一句話重點

綜述約 25 年來在 FPGA 上實作的數位神經形態架構，以硬體設計選擇建立八類 taxonomy，方便選擇與比較架構。

## English summary

Szczerek and Podobas survey digital neuromorphic architectures implemented on FPGAs over roughly 25 years. They read 135 papers and propose an eight-class taxonomy based on hardware design choices, such as clock-driven versus event-driven operation. The authors then compare the reported metrics and discuss future directions for FPGA neuromorphic designs.

## 與本專案的關係

本專案是 256 神經元 LIF 網路在 Tang Nano 20K 上的實作，此綜述可用來定位本專案屬於哪一類架構（同步/時脈驅動、時間多工等），並查找同規模的 FPGA 文獻作對照。結論中提到缺乏統一的設計空間探索框架，也提醒本專案的效能比較需注意條件是否一致。

## 重點方法與數字（只列能從全文確認的）

- 收錄並精讀 135 篇文獻，依提出的 taxonomy 分類，並蒐集效能指標。
- Taxonomy 共八類，主要依同步（clock-driven）與非同步（event-driven）、時間多工、記憶體配置等硬體選擇劃分。
- 文中列表顯示多數條目以 LIF 為神經元模型，神經元數與權重位寬差異很大（各表格數值未逐筆核對）。
- 結論認為各類架構差異大，建議建立可自動搜尋最佳架構的 Design Space Exploration 框架。

## 限制與注意

- 屬綜述而非實驗，效能數字取自各論文自報，實驗條件與目標平台不一致，不宜直接排名。
- 綜述時間截至 2026 年修訂版，之後的新架構未涵蓋。
- 表格中的個別數值未逐一核對，引用前請回到原文。
