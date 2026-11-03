// Simulation wrapper for rtl/uart_tx.v and rtl/uart_rx.v (cocotb testbench top).
// loop_en = 1: rx is fed from tx (loopback).
// loop_en = 0: rx is fed from ext_rx, so cocotb can bit-bang an external sender.
module uart_tb_top (
    input  wire       clk,
    input  wire [7:0] tx_data,
    input  wire       tx_start,
    output wire       tx_busy,
    output wire       tx_line,
    input  wire       loop_en,
    input  wire       ext_rx,
    output wire [7:0] rx_data,
    output wire       rx_valid
);

wire rx_line = loop_en ? tx_line : ext_rx;

uart_tx u_tx (
    .clk   (clk),
    .data  (tx_data),
    .start (tx_start),
    .busy  (tx_busy),
    .tx    (tx_line)
);

uart_rx u_rx (
    .clk        (clk),
    .rx         (rx_line),
    .data       (rx_data),
    .data_valid (rx_valid)
);

endmodule
