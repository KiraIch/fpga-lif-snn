// UART loopback: every byte received on rx is sent back on tx at the same baud.
//
// A one-byte holding register sits between the receiver and the transmitter.
// If a new byte arrives while the transmitter is still busy, it waits in the
// holding register instead of being lost.
module uart_echo (
    input  wire clk,
    input  wire rx,
    output wire tx
);

localparam CLK_FRE = 27000000;
localparam BAUD    = 115200;

wire [7:0] rx_data;
wire       rx_valid;
wire       tx_busy;

reg  [7:0] hold    = 8'd0;
reg        pending = 1'b0;

// Start the transmitter when a byte is waiting and the transmitter is idle.
wire launch = pending & ~tx_busy;

uart_rx #(.CLK_FRE(CLK_FRE), .BAUD(BAUD)) u_rx (
    .clk        (clk),
    .rx         (rx),
    .data       (rx_data),
    .data_valid (rx_valid)
);

// A new byte has priority over clearing `pending`: both use values from before
// this clock edge, so the transmitter sends the old byte and the new one waits.
always @(posedge clk) begin
    if (rx_valid) begin
        hold    <= rx_data;
        pending <= 1'b1;
    end else if (launch) begin
        pending <= 1'b0;
    end
end

uart_tx #(.CLK_FRE(CLK_FRE), .BAUD(BAUD)) u_tx (
    .clk   (clk),
    .data  (hold),
    .start (launch),
    .busy  (tx_busy),
    .tx    (tx)
);

endmodule
