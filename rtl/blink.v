// LED bring-up test for Tang Nano 20K.
// Toggles all six on-board LEDs every 0.5 s with the 27 MHz clock.
// LEDs are active low on this board, so the output is inverted.
module blink (
    input  wire       clk,
    output wire [5:0] led
);

localparam HALF_PERIOD = 27_000_000 / 2;

reg [24:0] cnt = 0;
reg [5:0]  state = 0;

always @(posedge clk) begin
    if (cnt == HALF_PERIOD - 1) begin
        cnt   <= 0;
        state <= ~state;
    end else begin
        cnt <= cnt + 1'b1;
    end
end

assign led = ~state;

endmodule
