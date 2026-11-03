// Icarus testbench for rtl/cmd_decoder.v.
// Feeds the byte stream written by host/gen_cmd_vectors.py and checks the
// final parameter registers and frame counters against sim/cmd_expect.mem.
// Run from the sim/ directory after generating the vectors.
`timescale 1ns/100ps
module tb_cmd_decoder;

reg         clk = 1'b0;
reg  [7:0]  byte_in = 8'd0;
reg         byte_valid = 1'b0;

wire signed [15:0] theta, v_reset, v_rest;
wire        [3:0]  k_m, k_s;
wire        [2:0]  refrac;
wire        [7:0]  ok_count, err_count;

always #18.5 clk = ~clk;

cmd_decoder dut (
    .clk        (clk),
    .byte_in    (byte_in),
    .byte_valid (byte_valid),
    .busy       (1'b0),
    .theta      (theta),
    .v_reset    (v_reset),
    .v_rest     (v_rest),
    .k_m        (k_m),
    .k_s        (k_s),
    .refrac     (refrac),
    .ok_count   (ok_count),
    .err_count  (err_count),
    .buf_addr   (8'd0)
);

reg [7:0]  stream [0:4095];
reg [15:0] exp_mem [0:8];
integer    n;
integer    i;
integer    errors = 0;

task check16(input [15:0] got, input [15:0] want, input [8*12-1:0] name);
    begin
        if (got !== want) begin
            errors = errors + 1;
            $display("FAIL %0s: got %h, want %h", name, got, want);
        end
    end
endtask

initial begin
    $readmemh("cmd_stream.mem", stream);
    $readmemh("cmd_expect.mem", exp_mem);
    n = exp_mem[8];

    // One byte per clock, with idle clocks between bytes.
    for (i = 0; i < n; i = i + 1) begin
        @(posedge clk);
        byte_in    <= stream[i];
        byte_valid <= 1'b1;
        @(posedge clk);
        byte_valid <= 1'b0;
        repeat (2) @(posedge clk);
    end
    repeat (10) @(posedge clk);

    check16(theta,              exp_mem[0], "theta");
    check16(v_reset,            exp_mem[1], "v_reset");
    check16(v_rest,             exp_mem[2], "v_rest");
    check16({12'd0, k_m},       exp_mem[3], "k_m");
    check16({12'd0, k_s},       exp_mem[4], "k_s");
    check16({13'd0, refrac},    exp_mem[5], "refrac");
    check16({8'd0, ok_count},   exp_mem[6], "ok_count");
    check16({8'd0, err_count},  exp_mem[7], "err_count");

    if (errors == 0)
        $display("PASS: %0d bytes, ok=%0d err=%0d", n, ok_count, err_count);
    else
        $display("FAIL: %0d mismatches", errors);
    $finish;
end

initial begin
    #1000000;
    $display("FAIL: timeout");
    $finish;
end

endmodule
