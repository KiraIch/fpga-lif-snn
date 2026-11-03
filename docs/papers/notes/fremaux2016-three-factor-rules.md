# Neuromodulated Spike-Timing-Dependent Plasticity, and Theory of Three-Factor Learning Rules

- 作者、年份、期刊/會議：Frémaux & Gerstner，2016，Frontiers in Neural Circuits 9:85
- 連結：https://doi.org/10.3389/fncir.2015.00085
- 全文狀態：全文已讀（依規則抽讀摘要、引言與理論段落，未逐頁抄錄）
- 本地 PDF：docs/papers/pdfs/fremaux2016-three-factor-rules.pdf

## 一句話重點

綜述神經調質如何改寫 STDP，並建立三因子學習規則的分類框架，說明資格跡（eligibility trace）如何銜接毫秒級的配對與秒級的調質訊號。

## English summary

This review examines how neuromodulators change spike-timing-dependent plasticity and why timing matters. It develops a framework for three-factor learning rules that combine presynaptic activity, postsynaptic variables, and a neuromodulatory signal. The authors use eligibility traces to bridge the delay between synaptic activity and the modulator, and they present the framework as a way to categorize existing models.

## 與本專案的關係

這篇與 35 同屬學習規則的背景文獻。若本專案未來要加入可學習突觸或獎勵驅動的權重更新，三因子框架可用來規劃規則的結構（突觸前、突觸後活動，加上神經調質與資格跡）。在目前的定點 LIF 與 E/I 擾動階段，屬於背景參考。

## 重點方法與數字

- 三因子規則框架：突觸前活動、突觸後變數與神經調質（全文）
- 資格跡可把毫秒級的配對與秒級的調質訊號連起來（全文）
- 文中指出 60 次 20 Hz 的前後配對只需數秒（全文）
- 神經調質會改變 STDP 視窗，部分情況下會變成 LTD（全文）

## 限制與注意

- 綜述，多數論點為理論與概念模型；文中引用的實驗細節與圖表未逐一核對。
