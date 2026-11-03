# Learning and Choice in Mood Disorders: Searching for the Computational Parameters of Anhedonia

- 作者、年份、期刊/會議：Robinson & Chase，2017，Computational Psychiatry 1:208–233
- 連結：https://doi.org/10.1162/cpsy_a_00009
- 全文狀態：全文已讀（依規則抽讀摘要、結論與 DDM 相關段落，未逐頁抄錄）
- 本地 PDF：docs/papers/pdfs/robinson2017-depression-ddm.pdf

## 一句話重點

這是一篇綜述，主張憂鬱的快感缺失（anhedonia）可用強化學習參數解釋，其中以 choice temperature 最關鍵，但文獻結果異質性大。

## English summary

This review examines which reinforcement-learning parameters may explain anhedonia in major depression. It emphasizes choice variability ("temperature") as a parameter that can account for the heterogeneity in prior findings. The authors close with five unresolved questions for the field.

## 與本專案的關係

這篇與本專案 FPGA 硬體沒有直接對應，屬行為層建模的背景參考。它的價值在於說明參數之間的權衡（例如 temperature 與價值參數會互相抵消），這與 33、34 的參數估計議題相通。若未來要用行為模型解讀 E/I 擾動後的決策變化，需要先理解這類可識別性問題。

## 重點方法與數字

- 認為 anhedonia 與強化學習參數有關，但文獻結果異質（全文）
- temperature 與價值參數會互相抵消，使單一指標的解讀困難；文中以 10,000 次模擬示範（全文）
- 神經影像研究指出腹側紋狀體（ventral striatum）反應減弱與快感缺失有關（全文）
- 文末提出五個未解問題（全文）
- 文中討論 anhedonia 是否只降低 DDM 的 drift rate，此為提出的問題，並非定論（全文）

## 限制與注意

- DDM 不是本文主軸，只佔一段討論。給定題目「憂鬱症的擴散模型研究」與實際文件不符，應改描述為強化學習參數綜述。
- PDF 來源為期刊網站的 proof 版本連結，與最終出版版本的差異未確認。
