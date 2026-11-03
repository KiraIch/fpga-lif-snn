# 兩選一決策的神經模型可化簡為一維非線性擴散方程（Roxin & Ledberg 2008）

- 作者、年份、期刊/會議：Alex Roxin & Anders Ledberg, 2008, PLoS Computational Biology 4(3): e1000046（DOI 10.1371/journal.pcbi.1000046，依 PDF 首頁確認）
- 連結：給定的 econpapers 連結為書目頁，已改用同一出版社的全文 https://journals.plos.org/ploscompbiol/article/file?id=10.1371/journal.pcbi.1000046&type=printable
- 全文狀態：僅摘要（已讀摘要與引言前段，另查看模型段落的部分句子，未逐段讀完）
- 本地 PDF：docs/papers/pdfs/roxin2008-network-to-ddm.pdf

## 一句話重點

兩群勝者全拿（winner-take-all）網路的行為輸出（正確率與反應時間），可以化為一維非線性擴散方程，而且與網路細節無關。

## English summary

This paper shows that winner-take-all network models of two-choice decisions can be reduced to a one-dimensional nonlinear diffusion equation. The reduction gives how performance and reaction time depend on external inputs, largely independent of network details. The authors illustrate it with coupled rate equations and a network of integrate-and-fire neurons.

## 與本專案的關係

這篇是「SNN 網路參數 → 行為層 DDM 參數」的理論橋樑。若本專案的 E/I 擾動能用 WTA 型讀出，這篇可以提供把網路結果轉成反應時間與正確率的方法。與 Bogacz 2006 合讀，可以建立行為層的評估框架。

## 重點方法與數字（只列能從全文確認的）

- 摘要指出：WTA 網路可化為一維非線性擴散方程，且對某些系統可解析推導係數。
- 摘要指出：以外部輸入調整擴散方程，可擬合兩選一任務的行為資料。
- 文中範例包含耦合速率方程，以及由三群積分發放神經元組成的網路（依 PDF 模型段落）。

## 限制與注意

- 只讀摘要與部分段落，擴散方程的推導細節與係數對應未逐項核對。
- 若要用於本專案，需確認 WTA 假設是否符合 E/I 網路的實際讀出方式。
