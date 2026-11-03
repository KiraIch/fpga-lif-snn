// Simulation-only wrapper: lif_core plus a state register (v, i, ref).
// Used by the multi-step cocotb test. Not part of the synthesizable design.
module lif_core_reg (
    input                clk,
    input                rst,      // synchronous, clears v, i, ref to 0
    input  signed [15:0] syn_in,
    input  signed [15:0] theta,
    input  signed [15:0] v_reset,
    input  signed [15:0] v_rest,
    input         [3:0]  k_m,
    input         [3:0]  k_s,
    input         [2:0]  refrac,
    output reg signed [15:0] v,
    output reg signed [15:0] i,
    output reg        [2:0]  ref_r,
    output               spike
);
    wire signed [15:0] v_n, i_n;
    wire        [2:0]  r_n;

    lif_core u (
        .v(v), .i(i), .ref_cnt(ref_r), .syn_in(syn_in),
        .theta(theta), .v_reset(v_reset), .v_rest(v_rest),
        .k_m(k_m), .k_s(k_s), .refrac(refrac),
        .v_next(v_n), .i_next(i_n), .ref_next(r_n), .spike(spike)
    );

    always @(posedge clk) begin
        if (rst) begin
            v <= 16'sd0; i <= 16'sd0; ref_r <= 3'd0;
        end else begin
            v <= v_n; i <= i_n; ref_r <= r_n;
        end
    end
endmodule
