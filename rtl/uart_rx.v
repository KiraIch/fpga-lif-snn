// UART receiver, 8N1 (1 start bit, 8 data bits LSB first, 1 stop bit).
//
// The rx input is synchronised with two flip-flops. A falling edge starts the
// start-bit check. Each bit is sampled at its centre: the start bit after half
// a bit time, then each data bit and the stop bit at full bit-time intervals.
// A start bit that is high at its centre is treated as a glitch and ignored.
// A frame whose stop bit is low (framing error) is dropped.
//
// `data_valid` is a one-cycle pulse that marks `data` as valid for that frame.
// Baud divisor: CLK_DIV = round(CLK_FRE / BAUD), the same as uart_tx.
module uart_rx #(
    parameter CLK_FRE = 27000000,
    parameter BAUD    = 115200
)(
    input  wire       clk,
    input  wire       rx,
    output reg  [7:0] data = 8'd0,
    output reg        data_valid = 1'b0
);

localparam CLK_DIV = (CLK_FRE + BAUD / 2) / BAUD;
localparam HALF    = CLK_DIV / 2;
localparam CNT_W   = $clog2(CLK_DIV);

localparam S_IDLE  = 2'd0;
localparam S_START = 2'd1;
localparam S_DATA  = 2'd2;
localparam S_STOP  = 2'd3;

reg [1:0]       rx_sync = 2'b11;
reg [1:0]       state   = S_IDLE;
reg [CNT_W-1:0] cnt     = 0;
reg [2:0]       bit_idx = 3'd0;
reg [7:0]       shreg   = 8'd0;

wire rxd = rx_sync[1];

always @(posedge clk) begin
    rx_sync <= {rx_sync[0], rx};
end

always @(posedge clk) begin
    data_valid <= 1'b0;

    case (state)
        S_IDLE: begin
            if (!rxd) begin                 // falling edge: start bit candidate
                state <= S_START;
                cnt   <= 0;
            end
        end

        S_START: begin
            if (cnt == HALF - 1) begin      // centre of start bit
                cnt <= 0;
                if (!rxd) begin
                    state   <= S_DATA;
                    bit_idx <= 3'd0;
                end else begin
                    state <= S_IDLE;        // glitch, not a start bit
                end
            end else begin
                cnt <= cnt + 1'b1;
            end
        end

        S_DATA: begin
            if (cnt == CLK_DIV - 1) begin   // centre of each data bit
                cnt   <= 0;
                shreg <= {rxd, shreg[7:1]}; // LSB first
                bit_idx <= bit_idx + 1'b1;
                if (bit_idx == 3'd7)
                    state <= S_STOP;
            end else begin
                cnt <= cnt + 1'b1;
            end
        end

        S_STOP: begin
            if (cnt == CLK_DIV - 1) begin   // centre of stop bit
                cnt <= 0;
                state <= S_IDLE;
                if (rxd) begin              // valid stop bit
                    data       <= shreg;
                    data_valid <= 1'b1;
                end
            end else begin
                cnt <= cnt + 1'b1;
            end
        end
    endcase
end

endmodule
