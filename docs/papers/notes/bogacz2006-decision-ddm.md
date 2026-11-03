# 最佳決策的物理學：兩選一任務的模型分析（Bogacz et al. 2006）

- 作者、年份、期刊/會議：Rafal Bogacz, Eric Brown, Jeff Moehlis, Philip Holmes & Jonathan D. Cohen, 2006, Psychological Review 113:700–765（DOI 10.1037/0033-295X.113.4.700，依 PDF 首頁確認）
- 連結：https://sites.engineering.ucsb.edu/~moehlis/moehlis_papers/psych.pdf
- 全文狀態：僅摘要（已讀摘要與部分引言，未讀完整分析章節）
- 本地 PDF：docs/papers/pdfs/bogacz2006-decision-ddm.pdf

## 一句話重點

這篇分析六種兩選一（TAFC）決策模型，發現除一種外都能化為擴散模型（DDM），並證明速度與正確率之間存在最佳權衡。

## English summary

This paper analyzes six models of two-alternative forced-choice decisions. Five of the six reduce to the drift diffusion model, which is statistically optimal for a given speed or accuracy. The authors also show that an optimal speed-accuracy tradeoff exists for objectives such as reward rate.

## 與本專案的關係

專案若要把 SNN 的輸出轉成反應時間與正確率，需要一個行為層的評估基準，DDM 是常見的選擇。這篇說明 DDM 在最佳化意義下的地位，可作為 SNN 輸出的對照基準。建議與 Roxin & Ledberg 2008 合讀。

## 重點方法與數字（只列能從全文確認的）

- 摘要指出：六種模型中，除一種外皆可化為 DDM。
- 摘要指出：DDM 在給定速度或正確率的條件下，是統計上最佳的演算法。
- 摘要指出：存在最佳速度-正確率權衡，可最大化 reward rate 等目標函數。

## 限制與注意

- 以理論分析為主，未涉及硬體實作。
- 篇幅長，本導讀只看摘要與引言，未核對其中的實證資料分析。
