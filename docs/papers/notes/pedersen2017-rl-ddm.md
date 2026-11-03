# The drift diffusion model as the choice rule in reinforcement learning

- 作者、年份、期刊/會議：Pedersen, Frank & Biele，2017（線上 2016-12-13），Psychonomic Bulletin & Review 24:1234–1251
- 連結：https://doi.org/10.3758/s13423-016-1199-y
- 全文狀態：全文已讀（依規則抽讀摘要、引言與結果段落，未逐頁抄錄）
- 本地 PDF：docs/papers/pdfs/pedersen2017-rl-ddm.pdf

## 一句話重點

提出 RL-DDM，把擴散模型當作強化學習的選擇規則，同時擬合學習過程、選擇與反應時間。

## English summary

This theoretical review introduces reinforcement-learning models in which the drift diffusion model serves as the choice rule. Applied to data from adults with ADHD, the best-fitting model describes learning, choices, and response times, and stimulant effects are analyzed for parameters such as boundary separation and drift rate. The authors also report a parameter recovery experiment that supports their hierarchical Bayesian estimation approach.

## 與本專案的關係

這篇屬行為層建模，與 FPGA 硬體沒有直接對應，但與 33 相關。若未來要以行為模型擬合 E/I 擾動實驗的決策資料，RL-DDM 是候選框架之一。讀它的目的，是了解如何同時估計學習與反應時間參數，以及為何需要階層貝氏估計。

## 重點方法與數字

- 最佳模型（文中 Model 6，RLDD）對學習、選擇與反應時間的描述最好（全文）
- 以 17 位成人 ADHD 病人在用藥 ON/OFF 條件下的資料分析（全文）
- 以階層貝氏估計（hierarchical Bayesian）實作，並以模擬資料做參數還原實驗（全文）
- 用藥效應分析涵蓋 boundary separation、drift rate 等參數（全文圖 5）

## 限制與注意

- 理論與方法論文，ADHD 樣本數小，結論不宜直接外推到其他族群。
- 未逐頁核對所有圖表與統計數字。
