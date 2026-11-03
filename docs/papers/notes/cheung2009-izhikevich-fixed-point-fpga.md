# 平行脈衝神經網路模擬器（A Parallel Spiking Neural Network Simulator）

- 作者、年份、期刊/會議：Kit Cheung, Simon R. Schultz, Philip H.W. Leong，2009，FPT（Field-Programmable Technology）
- 連結：https://cel.eng.sydney.edu.au/wp-content/uploads/2019/01/snn_fpt09.pdf
- 全文狀態：全文已讀
- 本地 PDF：docs/papers/pdfs/cheung2009-izhikevich-fixed-point-fpga.pdf
- 注意：論文實際題目為 "A Parallel Spiking Neural Network Simulator"，與任務列出的題目不同。

## 一句話重點
利用活動度低的特性，只更新有發 spike 的神經元，在 Virtex-5 上以 18-bit 狀態與 9-bit 權重實作 Izhikevich 模擬器。

## English summary
The paper presents a systolic FPGA simulator for Izhikevich neurons that exploits sparse firing by updating only neurons that spike. Neuron states use 18-bit fixed-point values and weights use 9-bit values on a Virtex-5 device. The authors report about 1400x real-time for a fully connected 800-neuron network.

## 與本專案的關係
- 可參考「只處理有 spike 的突觸」的 activity factor 思路，用於 256 神經元的時間步排程。
- 定點位寬的選擇依據（狀態 18-bit、權重 9-bit，以 DSP 乘法器寬度為理由）可對照本專案的 Q8.8 決定。
- 差異：模型是 Izhikevich 而非 LIF；本專案 MVP 不用 DSP。

## 重點方法與數字（全文可確認）
- Virtex-5 XC5VLX155T，32 個 PE、每個 PE 負責 25 個神經元，時脈 110.47 MHz。
- 800 神經元全連接網路模擬 1 秒（1 ms 時間步），共 6107 次發放，約 97% 時間步有發放；論文稱約 1370 倍即時。
- 權重 9-bit 的理由是參照小腦突觸的估計精度（論文自述）。

## 限制與注意
- 1400 倍是低發放率條件下的結果，發放率高時效能會下降；論文亦指出 LOD 為關鍵路徑。
- 比較對象 Thomas & Luk 使用浮點數，本文為定點，比較基準不同。
- 這是模擬器架構，不是單一神經元模型的 FPGA 實作。
