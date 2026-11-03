// UART transmitter, 8N1 (1 start bit, 8 data bits LSB first, 1 stop bit).
//
// Handshake: valid/ready style. `start` is a valid strobe that is accepted
// when `busy` is low (ready = !busy). Hold `data` stable when `start` is
// asserted; it is latched on the accepting clock edge. Assertions of `start`
// while `busy` is high are ignored. Drive `start` high for one cycle.
//
// Baud divisor: CLK_DIV = round(CLK_FRE / BAUD).
//   27 MHz / 115200 = 234.375 -> 234
//   Actual baud = 27 MHz / 234 = 115384.6 Hz, error = +0.16 %.
//   A 1-bit-time frame error budget of about 2 % is comfortable for 10 bits.
//
// `busy` covers the full frame including the stop bit. It falls on the clock
// edge that ends the stop bit, so a new `start` can follow with only the
// one-cycle gap of the handshake (back-to-back).
module uart_tx #(
    parameter CLK_FRE = 27000000,
    parameter BAUD    = 115200
)(
    input  wire       clk,
    input  wire [7:0] data,
    input  wire       start,
    output wire       busy,
    output reg        tx = 1'b1
);

localparam CLK_DIV = (CLK_FRE + BAUD / 2) / BAUD;
localparam CNT_W   = $clog2(CLK_DIV);

reg               active = 1'b0;
reg [9:0]         shreg  = 10'h3FF;   // {stop, data[7:0], start}, shifted out LSB first
reg [3:0]         nbits  = 4'd0;      // number of bit-time boundaries passed in this frame
reg [CNT_W-1:0]   cnt    = 0;

assign busy = active;

always @(posedge clk) begin
    if (!active) begin
        tx <= 1'b1;
        if (start) begin
            active <= 1'b1;
            shreg  <= {1'b1, data, 1'b0};
            nbits  <= 4'd0;
            cnt    <= 0;
            tx     <= 1'b0;                 // start bit begins
        end
    end else if (cnt == CLK_DIV - 1) begin
        cnt   <= 0;
        shreg <= {1'b1, shreg[9:1]};
        if (nbits == 4'd9) begin            // stop bit has lasted one full bit time
            active <= 1'b0;
            tx     <= 1'b1;
        end else begin
            nbits <= nbits + 1'b1;
            tx    <= shreg[1];              // next bit: data[0..7] then stop
        end
    end else begin
        cnt <= cnt + 1'b1;
    end
end

endmodule
