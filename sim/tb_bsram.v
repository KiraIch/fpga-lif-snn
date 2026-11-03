// Icarus testbench for rtl/bsram_test.v.
// Runs the self-test to completion and checks that no word mismatches.
`timescale 1ns / 1ps

module tb_bsram;

reg        clk = 1'b0;
wire [5:0] led;

bsram_test dut (
    .clk(clk),
    .led(led)
);

// 27 MHz clock (period about 37 ns).
always #18.5 clk = ~clk;

integer cycles;

initial begin
    cycles = 0;
    while (!dut.done && cycles < 10000) begin
        @(posedge clk);
        cycles = cycles + 1;
    end

    if (!dut.done) begin
        $display("FAIL: self-test did not finish within %0d cycles", cycles);
        $finish;
    end

    // led is active low: led[1] == 0 means pass.
    if (dut.errors == 8'd0 && led[1] == 1'b0 && led[2] == 1'b1) begin
        $display("PASS: 256 words written and read back with 0 mismatches (%0d cycles)", cycles);
    end else begin
        $display("FAIL: %0d mismatches, led = %b", dut.errors, led);
    end

    $finish;
end

endmodule
