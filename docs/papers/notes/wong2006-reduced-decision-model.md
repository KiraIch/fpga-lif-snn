# A Recurrent Network Mechanism of Time Integration in Perceptual Decisions

- 作者、年份、期刊/會議：Kong-Fatt Wong、Xiao-Jing Wang，2006，The Journal of Neuroscience 26(4):1314–1328
- 連結：https://www.cns.nyu.edu/wanglab/publications/pdf/wong2006.pdf
- 全文狀態：全文已讀（依規定精讀摘要、引言、結果與討論的主要段落，未逐圖核對）
- 本地 PDF：docs/papers/pdfs/wong2006-reduced-decision-model.pdf

## 一句話重點

把生物物理的皮層決策網路簡化成兩變數模型，指出慢速的 NMDA 興奮性迴路是產生接近實驗的決策時間積分的關鍵。

## English summary

Wong and Wang reduce a biophysically detailed cortical decision network to a two-variable model. They show that slow NMDA-mediated recurrent excitation is needed to reproduce realistic reaction times, while AMPA-only recurrence falls short. The reduced model also links task difficulty and error-trial timing to the saddle-point geometry of the decision space.

## 與本專案的關係

本專案的 E/I 擾動實驗需要解讀「擾動如何改變決策時間」，此文提供 NMDA 時間常數與 winner-take-all 動力學的理論對照，適合作為 E/I 擾動（見 01）與 Brunel 網路（見 02）之間的橋樑。它不直接對應 FPGA RTL，實作仍以 `model/fixed.py` 的定點規格為準。

## 重點方法與數字（只列能從全文確認的）

- 兩變數簡化模型（興奮/抑制兩個 pool 的 firing rate 加上 NMDA gating），由數千神經元的網路經平均場近似降階而來。
- 文中 NMDA 時間常數約 100 ms；反應時間定義為決策時間加上 100 ms 的非決策潛伏期。
- 錯誤試次的反應時間比正確試次長，與猴子 LIP 實驗的定性趨勢一致。
- 論文提出可檢驗的預測：在刺激期間對某一 pool 施加興奮性擾動，會加快該選項的決策、同時減慢另一選項；作者指出此預測在其模擬中得到確認。

## 限制與注意

- 簡化模型依賴平均場與多項近似，與原始 spiking 網路之間有誤差，未考慮定點數或 FPGA 位寬限制。
- 參數針對猴子 LIP 的反應時間資料調整，移植到本專案的 E/I 實驗需重新校正。
- 圖與附錄的細節數值未逐一核對，相關數字以原文為準。
