# 論文索引與導讀

本資料夾收錄 neuro-fpga 計畫的 36 篇參考文獻。每篇都有一份導讀（`notes/`），能取得的全文放在 `pdfs/`。

- **PDF 不納入 git**（已加入 `.gitignore`），只保留在本機。
- **全文狀態**有三種：全文已讀、僅摘要、未取得全文。「全文已讀」在多數情況下是抽讀摘要、引言、方法與結論，不是逐頁精讀；導讀內容以文件實際內容為準，計畫裡的描述若不符，已標在下方「需要修正的資訊」。
- **導讀內容**：每篇包含一句話重點、3 句英文摘要、與本專案的關係、重點方法與限制。

若你能用機構權限取得未取得全文的論文，請把 PDF 放進 `pdfs/`，檔名與下表相同，之後再請 Claude 重寫對應導讀。

## 統計

| 全文狀態 | 篇數 |
| --- | --- |
| 全文已讀 | 14 |
| 僅摘要 | 12 |
| 未取得全文 | 10 |

## 第一組：先讀 8 篇（計畫指定）

| 編號 | 論文（原文題目） | 年份 | 全文狀態 | 導讀 | 備註 |
| --- | --- | --- | --- | --- | --- |
| 01 | Lam et al., *J Neurosci*（E/I 擾動與脈衝決策） | 2022（DOI 含 2021，未核對） | 未取得全文 | [導讀](notes/lam2022-ei-perturbation-decision.md) | **計畫中最重要的一篇，優先取得** |
| 02 | Brunel, *Dynamics of Sparsely Connected Networks of Excitatory and Inhibitory Spiking Neurons* | 2000 | 未取得全文 | [導讀](notes/brunel2000-ei-network.md) | 只取得 meta 資訊 |
| 03 | Wong & Wang, *A Recurrent Network Mechanism of Time Integration in Perceptual Decisions* | 2006 | 全文已讀 | [導讀](notes/wong2006-reduced-decision-model.md) | [PDF](pdfs/wong2006-reduced-decision-model.pdf) |
| 04 | Murray et al., *Cereb Cortex*（NMDA 去抑制與工作記憶） | 2014 | 未取得全文 | [導讀](notes/murray2014-nmda-working-memory.md) | 原題未確認 |
| 05 | Ansari & Wielgosz, *A Time-Multiplexed Spiking Neural Network Accelerator with Pipelined Readout for FPGA Inference* | 2026（arXiv:2608.00595） | 全文已讀 | [導讀](notes/ansari2026-fpga-lif-bitexact.md) | [PDF](pdfs/ansari2026-fpga-lif-bitexact.pdf)；**與計畫描述不符** |
| 06 | Mitchell, Schuman & Potok, ICONS（低價 FPGA 256 神經元 SNN） | 2020 | 未取得全文 | [導讀](notes/mitchell2020-low-cost-fpga-snn.md) | OSTI 連線失敗，原題未確認 |
| 07 | Szczerek & Podobas, *A Quarter of a Century of Neuromorphic Architectures on FPGAs - an Overview* | 2025 | 全文已讀 | [導讀](notes/szczerek2025-fpga-neuromorphic-survey.md) | [PDF](pdfs/szczerek2025-fpga-neuromorphic-survey.pdf) |
| 08 | Huys, Maia & Frank, *Computational psychiatry as a bridge from neuroscience to clinical applications* | 2016 | 僅摘要 | [導讀](notes/huys2016-computational-psychiatry.md) | 無 PDF |

## 第二組：FPGA 上的 SNN 與模擬

| 編號 | 論文（原文題目） | 年份 | 全文狀態 | 導讀 | 備註 |
| --- | --- | --- | --- | --- | --- |
| 09 | Gautam et al., *NeuroCoreX*（開源 FPGA 脈衝網路模擬器，含 STDP） | 2025 | 全文已讀 | [導讀](notes/gautam2025-neurocorex.md) | [PDF](pdfs/gautam2025-neurocorex.pdf) |
| 10 | Cheung, Schultz & Leong, *A Parallel Spiking Neural Network Simulator* | 2009 | 全文已讀 | [導讀](notes/cheung2009-izhikevich-fixed-point-fpga.md) | [PDF](pdfs/cheung2009-izhikevich-fixed-point-fpga.pdf)；**與計畫描述不符** |
| 11 | Fan & Levy, *A Robust, Open-Source Framework for Spiking Neural Networks on Low-End FPGAs* | 2025 | 全文已讀 | [導讀](notes/fan2025-low-end-fpga-snn.md) | [PDF](pdfs/fan2025-low-end-fpga-snn.pdf)；摘要與 LUT 數字不一致 |
| 12 | Gupta, Vyas & Trivedi, *FPGA Implementation of Simplified Spiking Neural Network* | 2020 | 全文已讀 | [導讀](notes/gupta2020-non-timemultiplexed-snn.md) | [PDF](pdfs/gupta2020-non-timemultiplexed-snn.pdf)；「非分時多工」是任務分類，論文未明說 |
| 13 | Matinizadeh et al., *QUANTISENC* | 2024 | 全文已讀 | [導讀](notes/matinizadeh2024-quantisenc.md) | [PDF](pdfs/matinizadeh2024-quantisenc.pdf)；單神經元 LUT 在文字與表格間不一致 |
| 14 | *Posit-based Spiking Neuron in an FPGA* | 未確認 | 全文已讀 | [導讀](notes/silva-posit-spiking-neuron-fpga.md) | [PDF](pdfs/silva-posit-spiking-neuron-fpga.pdf)；會議名稱未確認 |
| 15 | Lindqvist & Podobas, *Fast Algorithms for Spiking Neural Network Simulation with FPGAs* | 2024 | 全文已讀 | [導讀](notes/lindqvist2024-energy-per-synaptic-event.md) | [PDF](pdfs/lindqvist2024-energy-per-synaptic-event.pdf)；**與計畫描述不符**；每突觸能耗摘要 21 nJ、引言 25 nJ |
| 16 | Stimberg, Goodman & Nowotny, *Brian2GeNN*（GPU 加速 SNN 模擬） | 2020 | 未取得全文 | [導讀](notes/stimberg2020-brian2genn.md) | PMC 只回傳 HTML |
| 17 | Isik, *A Survey of Spiking Neural Network Accelerator on FPGA* | 2023 | 全文已讀 | [導讀](notes/isik2023-neuron-models-fpga.md) | [PDF](pdfs/isik2023-neuron-models-fpga.pdf)；**與計畫描述不符**（實為加速器綜述，非神經元模型比較） |

## 第三組：網路理論與認知模型

| 編號 | 論文（原文題目） | 年份 | 全文狀態 | 導讀 | 備註 |
| --- | --- | --- | --- | --- | --- |
| 18 | van Vreeswijk & Sompolinsky, *Science*（平衡網路的不規則發放） | 1996 | 未取得全文 | [導讀](notes/vanvreeswijk1996-balanced-network.md) | DOI 回傳 403 |
| 19 | Wang, *Neuron*（慢速迴響與機率式決策） | 2002 | 僅摘要 | [導讀](notes/wang2002-decision-spiking-network.md) | [PDF](pdfs/wang2002-decision-spiking-network.pdf) |
| 20 | Compte et al., *Cereb Cortex*（空間工作記憶的突觸機制） | 2000 | 僅摘要 | [導讀](notes/compte2000-synaptic-wm.md) | [PDF](pdfs/compte2000-synaptic-wm.pdf) |
| 21 | Amit & Brunel, *Cereb Cortex*（記憶吸引子與背景活動） | 1997 | 未取得全文 | [導讀](notes/amit1997-attractor-memory.md) | OUP 回傳 403 |
| 22 | Lim & Goldman, *Nat Neurosci*（平衡迴路中的記憶保存） | 2013 | 未取得全文 | [導讀](notes/lim2013-balanced-memory.md) | 給定連結與 eScholarship 都回傳 403 |
| 23 | Bogacz et al., *Psychol Rev*（最佳決策的物理學：兩選一任務） | 2006 | 僅摘要 | [導讀](notes/bogacz2006-decision-ddm.md) | [PDF](pdfs/bogacz2006-decision-ddm.pdf) |
| 24 | Roxin & Ledberg, *PLoS Comput Biol*（兩選一決策網路化簡為一維擴散方程） | 2008 | 僅摘要 | [導讀](notes/roxin2008-network-to-ddm.md) | [PDF](pdfs/roxin2008-network-to-ddm.pdf)；計畫的 econpapers 連結是書目頁 |
| 25 | Ratcliff & McKoon, *Neural Computation* | 2008 | 未取得全文 | [導讀](notes/ratcliff2008-ddm-review.md) | **題目未確認**；依記憶可能是 DDM 理論與資料的綜述，不是參數擬合論文 |

## 第四組：計算精神醫學、DDM 與 RL

| 編號 | 論文（原文題目） | 年份 | 全文狀態 | 導讀 | 備註 |
| --- | --- | --- | --- | --- | --- |
| 26 | Wang & Krystal, *Computational Psychiatry*（*Neuron*） | 2014 | 僅摘要 | [導讀](notes/wang2014-circuit-perturbation.md) | PMC 需 bot 驗證；計畫中的描述需對照 |
| 27 | Montague et al., *Computational psychiatry*（*Trends Cogn Sci*） | 2012 | 僅摘要 | [導讀](notes/montague2012-computational-psychiatry-start.md) | 無 PDF |
| 28 | Rubenstein & Merzenich, *Model of autism: increased ratio of excitation/inhibition in key neural systems* | 2003 | 僅摘要 | [導讀](notes/rubenstein2003-autism-ei.md) | **計畫中的 DOI 錯誤**；正確 DOI 為 10.1034/j.1601-183x.2003.00037.x，卷頁未核對 |
| 29 | Sohal & Rubenstein, *Excitation-inhibition balance as a framework for investigating mechanisms in neuropsychiatric disorders* | 2019 | 僅摘要 | [導讀](notes/sohal2019-ei-framework.md) | 無 PDF |
| 30 | Antoine et al., *Increased Excitation-Inhibition Ratio Stabilizes Synapse and Circuit Excitability in Four Autism Mouse Models* | 2019 | 僅摘要 | [導讀](notes/antoine2019-ei-compensation.md) | 無 PDF |
| 31 | *NMDA receptor function in large-scale anticorrelated neural systems with implications for cognition and schizophrenia*（Anticevic et al.） | 2012 | 僅摘要 | [導讀](notes/anticevic2012-ketamine-wm.md) | **與計畫描述不符**（計畫寫「ketamine 工作記憶」，「工作記憶」未確認） |
| 32 | Robinson & Chase, *Learning and Choice in Mood Disorders: Searching for the Computational Parameters of Anhedonia* | 2017 | 全文已讀（抽讀） | [導讀](notes/robinson2017-depression-ddm.md) | [PDF](pdfs/robinson2017-depression-ddm.pdf)；**與計畫描述不符**（主要是 RL 參數綜述，DDM 只佔一段） |
| 33 | Boehm et al., *Estimating across-trial variability parameters of the Diffusion Decision Model: Expert advice and recommendations* | 2018 | 未取得全文 | [導讀](notes/boehm2018-parameter-recovery.md) | **與計畫描述不符**（實為變異參數估計的專家建議，非參數還原實作） |
| 34 | Pedersen, Frank & Biele, *The drift diffusion model as the choice rule in reinforcement learning* | 2017（線上 2016-12） | 全文已讀（抽讀） | [導讀](notes/pedersen2017-rl-ddm.md) | [PDF](pdfs/pedersen2017-rl-ddm.pdf) |
| 35 | Izhikevich, *Solving the distal reward problem through linkage of STDP and dopamine signaling* | 2007 | 僅摘要 | [導讀](notes/izhikevich2007-dopamine-stdp.md) | **計畫中的 DOI 錯誤**；正確 DOI 為 10.1093/cercor/bhl152，無 PDF |
| 36 | Frémaux & Gerstner, *Neuromodulated Spike-Timing-Dependent Plasticity, and Theory of Three-Factor Learning Rules* | 2016 | 全文已讀（抽讀） | [導讀](notes/fremaux2016-three-factor-rules.md) | [PDF](pdfs/fremaux2016-three-factor-rules.pdf) |

## 需要修正的資訊

以下是計畫文件與原文不符的地方，建議你在引用前核對，或由你決定是否更新計畫文件：

1. **05 Ansari & Wielgosz 2026**：計畫寫它是「整數 LIF 與逐位元驗證」，實際主題是分時多工 SNN 加速器與管線讀出。計畫中「和你的流程最像」的理由需要重新評估。
2. **07 Szczerek & Podobas 2025**：實際題目與計畫寫法不同（見上表）。
3. **10 Cheung 2009**：實際是平行 SNN 模擬器，計畫寫的「Izhikevich 18-bit 定點 FPGA 實作」需要核對。
4. **15 Lindqvist 2024**：實際題目是 FPGA 上的快速 SNN 模擬演算法；摘要與引言的能耗數字不一致（21 nJ 與 25 nJ）。
5. **17 Isik 2023**：實際是 FPGA SNN 加速器綜述，不是神經元模型比較。
6. **25 Ratcliff & McKoon 2008**：題目與內容未經原文確認，計畫中的「參數擬合」描述可能不準。
7. **28 Rubenstein & Merzenich 2003**：計畫的 DOI 無法解析，正確 DOI 為 10.1034/j.1601-183x.2003.00037.x。
8. **31 Anticevic 2012**：計畫寫的「ketamine 工作記憶」與實際題目不符。
9. **32 Robinson & Chase 2017**：主要是 RL 參數綜述，DDM 只佔一段，計畫寫的「憂鬱症 DDM 研究」需要修正。
10. **33 Boehm 2018**：實際是 DDM 變異參數估計的專家建議，不是參數還原的實作研究，計畫中用來支持「參數還原」的引用需要重新評估。
11. **35 Izhikevich 2007**：計畫的 DOI 指向無關論文，正確 DOI 為 10.1093/cercor/bhl152。
12. **01 Lam et al. 2022**：年份與 DOI 字串（含 2021）不一致，原題未確認。這是計畫中最重要的一篇，需要優先取得原文。
