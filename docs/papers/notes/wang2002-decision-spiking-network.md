# 皮質迴路中的慢速迴響與機率式決策（Wang 2002）

- 作者、年份、期刊/會議：Xiao-Jing Wang, 2002, Neuron 36:955–968（依 PDF 首頁確認）
- 連結：https://cenl.ucsd.edu/Jclub/Wang02.pdf
- 全文狀態：僅摘要（已讀摘要與部分引言，未讀完整結論與圖表）
- 本地 PDF：docs/papers/pdfs/wang2002-decision-spiking-network.pdf

## 一句話重點

用含 NMDA 循環興奮與回饋抑制的脈衝神經網路，示範兩個競爭輸入會被吸引子動態放大成二選一的決策，並能重現決策相關神經活動與心理測量曲線。

## English summary

This paper models a visual discrimination decision with a biophysically detailed spiking network. Slow NMDA-mediated recurrent excitation and feedback inhibition form attractor dynamics that amplify differences between competing inputs. The authors report that the model reproduces decision-correlated activity, psychometric functions, and reaction times.

## 與本專案的關係

本專案是 256 神經元 LIF 網路，這篇提供「用脈衝網路實作決策吸引子」的參考架構。NMDA 慢速興奮與抑制回饋的相對強度，直接決定吸引子是否穩定，因此與 E/I 擾動實驗高度相關。可用來規劃 E/I 掃描的對照組。

## 重點方法與數字（只列能從全文確認的）

- 模擬網路為 N = 2000 神經元，其中興奮性 1600、抑制性 400（依 PDF 方法與模擬段落）。
- 兩組輸入的平均值依 coherence 而定，並每 50 ms 重新抽樣一次（依圖 1 說明與方法段）。
- 摘要指出模型能解釋心理測量函數與反應時間，但具體曲線數值未確認。

## 限制與注意

- 模型是 biophysical 模型，參數多，直接搬到 Q8.8 定點硬體需大幅簡化。
- 本導讀未核對圖 2 之後的數值與完整結論。
