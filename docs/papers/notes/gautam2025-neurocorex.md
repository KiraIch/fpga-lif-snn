# NeuroCoreX：開源 FPGA 脈衝網路模擬器（含 STDP）

- 作者、年份、期刊/會議：Gautam, Date, Kulkarni, Patton, Potok（ORNL），2025，arXiv:2506.14138（預印本）
- 連結：https://arxiv.org/pdf/2506.14138
- 全文狀態：全文已讀
- 本地 PDF：docs/papers/pdfs/gautam2025-neurocorex.pdf

## 一句話重點
以單一時分多工的 LIF 神經元電路，搭配 UART 與 Python 主機介面，在 Artix-7 上做可配置、含 STDP 的開源 SNN 模擬器。

## English summary
NeuroCoreX is an open-source FPGA emulator that time-multiplexes one physical LIF neuron circuit across 100 neurons with all-to-all synapses. A Python host configures weights and parameters over UART, and on-chip pair-based STDP with a rectangular window is supported. The authors report functional agreement with a software simulator for inference, but divergence once STDP is enabled.

## 與本專案的關係
- 與本專案最接近：時分多工 LIF、UART 配置、Python 主機流程，以及 18-bit 膜電位定點格式（1 符號位、7 整數位、10 小數位）的實例。
- 可借鏡：PC 端 Python 介面的設計，以及 spike 依時間戳注入網路的做法。
- 差異：本專案用 Q8.8 16-bit、目標為 GW2AR-18，且要求與 Python 模型逐位元一致。論文只報告推論的功能一致性，學習部分有偏差，不能當作比對標準。

## 重點方法與數字（全文可確認）
- 100 個神經元，10,000 條遞迴突觸加 10,000 條輸入突觸；權重為 signed 8-bit。
- 神經元更新時脈 100 kHz，UART 時脈 100 MHz；論文稱以 1 MHz 更新可約 10 倍加速。
- 估計總功耗 305 mW，以 MMCM 與 BRAM 為主。
- 以 DIGITS 分類與 Citeseer 子圖（90 個神經元）驗證。

## 限制與注意
- 全連接結構的記憶體隨 N² 成長，作者自承擴展性有限。
- STDP 採矩形窗與 8-bit 權重，與指數窗參考實作不同，學習結果不一致。
- 硬體為 VHDL 與 Artix-7，與本專案不同；UART 協定不可直接沿用。
