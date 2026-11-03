# 以 Posit 實作的 FPGA 脈衝神經元（Posit-based Spiking Neuron in an FPGA）

- 作者、年份、期刊/會議：Victor H. L. Silva, Jeferson F. Chaves, Rogério M. Gomes, Bruno A. Santos（CEFET-MG），2021，SBMicro（依任務描述；全文抬頭未確認會議資訊）
- 連結：https://sbmicro.org.br/sforum-eventos/sforum2021/Posit-based%20Spiking%20Neuron%20in%20an%20FPGA.pdf
- 全文狀態：全文已讀
- 本地 PDF：docs/papers/pdfs/silva-posit-spiking-neuron-fpga.pdf

## 一句話重點
以 posit 數值格式取代 IEEE 754，在 FPGA 上實作 Izhikevich 神經元，並比較 18、24、32-bit 的資源與軌跡。

## English summary
The authors implement an Izhikevich spiking neuron in FPGA hardware using posit arithmetic instead of IEEE 754 floating point. They report that the posit-based design reproduces firing patterns while using about 25% less memory than IEEE 754 designs. They also trace a software-hardware divergence to rounding differences between two posit libraries.

## 與本專案的關係
- 本專案選定點而非 posit 或浮點，這篇可作為「數值格式」的反面對照。
- 論文發現 SoftPosit 與 PACoGen 的捨入差異造成軌跡不一致，這正是本專案「逐位元一致」驗證要防範的問題：參考模型與 RTL 必須明定同一套捨入規則。
- 神經元模型是 Izhikevich，與本專案的 LIF 不同。

## 重點方法與數字（全文可確認）
- 以 Quartus 針對 Stratix V 5SEEBF45I4 合成，比較 N = 18、24、32 的 posit 資源（ALM 與 DSP）。
- 以 SoftPosit 作軟體參考，用 ModelSim 比對 v 的軌跡。
- 論文稱 24-bit posit 與 32-bit IEEE 754 的軌跡差異可忽略，記憶體節省約 25%（論文聲稱）。

## 限制與注意
- 論文自承與定點實作的比較「不公平」，因為兩者的模型與數值格式不同。
- 資源表的細部數字解析度不足，完整數據未確認。
- 會議名稱與年份以任務描述為準，全文抬頭未確認。
