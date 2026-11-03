// Combinational next-state logic of one LIF neuron (Q8.8, signed 16-bit state).
// Bit-exact with model/fixed.py step(); see docs/DECISIONS.md D-001..D-005.
//
//   i_next = sat(sat(i + (-(i >>> k_s))) + syn_in)
//   v_next = sat(sat(v + ((v_rest - v) >>> k_m)) + i_next)
//   ref_cnt > 0     : v_out = v_reset, ref_next = ref_cnt - 1, spike = 0
//   v_next >= theta : v_out = v_reset, ref_next = refrac,  spike = 1
//   otherwise       : v_out = v_next,  ref_next = 0,       spike = 0
//
// Intermediate values use 18-bit signed arithmetic: -(i >>> 0) with
// i = -32768 is +32768, and v_rest - v needs 17 bits.
module lif_core (
    input  signed [15:0] v,
    input  signed [15:0] i,
    input         [2:0]  ref_cnt,
    input  signed [15:0] syn_in,
    input  signed [15:0] theta,
    input  signed [15:0] v_reset,
    input  signed [15:0] v_rest,
    input         [3:0]  k_m,
    input         [3:0]  k_s,
    input         [2:0]  refrac,
    output signed [15:0] v_next,
    output signed [15:0] i_next,
    output        [2:0]  ref_next,
    output               spike
);

    // Clamp an 18-bit signed value to [-32768, 32767].
    function signed [15:0] sat16;
        input signed [17:0] x;
        begin
            if (x > 18'sd32767)
                sat16 = 16'sh7FFF;
            else if (x < -18'sd32768)
                sat16 = 16'sh8000;
            else
                sat16 = x[15:0];
        end
    endfunction

    // ---- synaptic current ----
    wire signed [15:0] i_shr   = i >>> k_s;                 // arithmetic shift
    wire signed [17:0] i_decay = -$signed({{2{i_shr[15]}}, i_shr});
    wire signed [17:0] i_sum1  = $signed({{2{i[15]}}, i}) + i_decay;
    wire signed [15:0] i_s1    = sat16(i_sum1);
    wire signed [17:0] i_sum2  = $signed({{2{i_s1[15]}}, i_s1})
                               + $signed({{2{syn_in[15]}}, syn_in});
    wire signed [15:0] i_new   = sat16(i_sum2);

    // ---- membrane potential ----
    wire signed [17:0] v_diff  = $signed({{2{v_rest[15]}}, v_rest})
                               - $signed({{2{v[15]}}, v});  // 17 bits needed
    wire signed [17:0] v_leak  = v_diff >>> k_m;            // arithmetic shift
    wire signed [17:0] v_sum1  = $signed({{2{v[15]}}, v}) + v_leak;
    wire signed [15:0] v_s1    = sat16(v_sum1);
    wire signed [17:0] v_sum2  = $signed({{2{v_s1[15]}}, v_s1})
                               + $signed({{2{i_new[15]}}, i_new});
    wire signed [15:0] v_new   = sat16(v_sum2);

    // ---- refractory / threshold ----
    wire in_ref = (ref_cnt != 3'd0);
    wire fire   = ~in_ref & (v_new >= theta);

    assign i_next   = i_new;
    assign spike    = fire;
    assign v_next   = (in_ref | fire) ? v_reset : v_new;
    assign ref_next = in_ref ? (ref_cnt - 3'd1) : (fire ? refrac : 3'd0);

endmodule
