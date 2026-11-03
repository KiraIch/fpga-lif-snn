// Icarus testbench for rtl/network.v (N = 16).
// Loads weights, ext and parameters from sim/net_*.mem (written by
// host/gen_net_vectors.py), runs T steps, and compares every (step, neuron)
// record with the model's V and spike.
// Run from the sim/ directory.
`timescale 1ns/100ps
module tb_network;

parameter N = 16;             // override with iverilog -P tb_network.N=<value>
localparam IW = $clog2(N);

reg                  clk = 1'b0;
reg                  start = 1'b0;
reg  [15:0]          steps = 16'd0;
reg  signed [15:0]   theta = 16'sd0, v_reset = 16'sd0, v_rest = 16'sd0;
reg  [3:0]           k_m = 4'd0, k_s = 4'd0;
reg  [2:0]           refrac = 3'd0;
reg                  load_w_we = 1'b0;
reg  [2*IW-1:0]      load_w_addr = 0;
reg  signed [7:0]    load_w_data = 8'sd0;
reg                  load_e_we = 1'b0;
reg  [IW-1:0]        load_e_addr = 0;
reg  signed [15:0]   load_e_data = 16'sd0;

wire                 rec_we;
wire [IW-1:0]        rec_k;
wire signed [15:0]   rec_v;
wire                 rec_spk;
wire                 busy;
wire                 done;

always #18.5 clk = ~clk;

network #(.N(N), .W_SHIFT(2), .IW(IW)) dut (
    .clk        (clk),
    .start      (start),
    .steps      (steps),
    .theta      (theta),
    .v_reset    (v_reset),
    .v_rest     (v_rest),
    .k_m        (k_m),
    .k_s        (k_s),
    .refrac     (refrac),
    .load_w_we  (load_w_we),
    .load_w_addr(load_w_addr),
    .load_w_data(load_w_data),
    .load_e_we  (load_e_we),
    .load_e_addr(load_e_addr),
    .load_e_data(load_e_data),
    .rec_we     (rec_we),
    .rec_k      (rec_k),
    .rec_v      (rec_v),
    .rec_spk    (rec_spk),
    .busy       (busy),
    .done       (done)
);

reg [7:0]  wmem  [0:N*N-1];
reg [15:0] emem  [0:N-1];
reg [16:0] exp_mem [0:N*4096-1];   // {spike, V}
reg [15:0] meta  [0:7];

integer a, errors = 0, checked = 0, total, T;
integer idx = 0;

initial begin
    $readmemh("net_w.mem", wmem);
    $readmemh("net_ext.mem", emem);
    $readmemh("net_expect.mem", exp_mem);
    $readmemh("net_meta.mem", meta);
    T = meta[1];
    total = T * N;
    theta   = meta[2];
    v_reset = meta[3];
    v_rest  = meta[4];
    k_m     = meta[5];
    k_s     = meta[6];
    refrac  = meta[7];
    steps   = T;

    // Load weights and external input (one write per clock).
    for (a = 0; a < N*N; a = a + 1) begin
        @(posedge clk);
        load_w_we   <= 1'b1;
        load_w_addr <= a;
        load_w_data <= wmem[a];
    end
    @(posedge clk);
    load_w_we <= 1'b0;
    for (a = 0; a < N; a = a + 1) begin
        @(posedge clk);
        load_e_we   <= 1'b1;
        load_e_addr <= a;
        load_e_data <= emem[a];
    end
    @(posedge clk);
    load_e_we <= 1'b0;

    @(posedge clk);
    start <= 1'b1;
    @(posedge clk);
    start <= 1'b0;
end

// Check every record as it is produced.
always @(posedge clk) begin
    if (rec_we) begin
        if (idx >= total) begin
            errors = errors + 1;
            $display("FAIL: more records than expected");
        end else begin
            checked = checked + 1;
            if ({rec_spk, rec_v} !== exp_mem[idx]) begin
                errors = errors + 1;
                if (errors <= 10)
                    $display("FAIL: step %0d neuron %0d: board V=%0d spk=%0d, model %h",
                             idx / N, rec_k, rec_v, rec_spk, exp_mem[idx]);
            end
        end
        idx = idx + 1;
    end
    if (done) begin
        if (errors == 0 && checked == total)
            $display("PASS: %0d records (%0d steps x %0d neurons) match the model", checked, T, N);
        else
            $display("FAIL: %0d mismatches in %0d of %0d records", errors, checked, total);
        $finish;
    end
end

initial begin
    #2000000000;
    $display("FAIL: timeout after %0d records", checked);
    $finish;
end

endmodule
