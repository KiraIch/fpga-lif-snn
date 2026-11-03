// N-neuron network, time-multiplexed on one lif_core (M3).
// Bit-exact with model/network.py (rules in docs/DECISIONS.md D-006, D-008, D-009).
//
// Every memory has one write port and one read port, with synchronous read, so
// yosys can map them to block RAM. Each read address is presented in one cycle
// and the data arrives in the next cycle, where the pipeline stage uses it.
//
// One time step:
//   A  for k = 0..N-1 (pipelined, one neuron per cycle):
//        issue k: read state[k], ext[k], acc_cur[k]
//        next cycle: syn_in = sat16(acc_cur[k] + ext[k]); lif_core; write state[k],
//        spike[k], acc_nxt[k] = 0; send the record (V, spike).
//   B  synapse, event driven: for each source k that spiked, for each target i:
//        issue: read acc_nxt[i] and W[k][i]; next cycle: acc_nxt[i] += W << W_SHIFT
//   Then the two accumulators swap roles (ping-pong). No copy is needed.
// A spike at step t reaches the targets at step t+1 (D-006).
//
// Constraints: N is a power of two and N >= 2.
//
// Loading: set load_w_* and load_e_* while idle. Weight address = {source, target}.
// Then pulse start with steps >= 1.
module network #(
    parameter N       = 16,
    parameter W_SHIFT = 2,
    parameter IW      = $clog2(N)
)(
    input  wire                  clk,
    input  wire                  start,
    input  wire [15:0]           steps,
    input  wire signed [15:0]    theta,
    input  wire signed [15:0]    v_reset,
    input  wire signed [15:0]    v_rest,
    input  wire [3:0]            k_m,
    input  wire [3:0]            k_s,
    input  wire [2:0]            refrac,
    input  wire                  load_w_we,
    input  wire [2*IW-1:0]       load_w_addr,
    input  wire signed [7:0]     load_w_data,
    input  wire                  load_e_we,
    input  wire [IW-1:0]         load_e_addr,
    input  wire signed [15:0]    load_e_data,
    output reg                   rec_we = 1'b0,
    output reg  [IW-1:0]         rec_k = 0,
    output reg signed [15:0]     rec_v = 16'sd0,
    output reg                   rec_spk = 1'b0,
    output reg                   busy = 1'b0,
    output reg                   done = 1'b0
);

localparam S_IDLE = 3'd0;
localparam S_INIT = 3'd1;
localparam S_A    = 3'd2;
localparam S_B    = 3'd3;
localparam S_END  = 3'd4;

// ---- control state ----
reg [2:0]  st = S_IDLE;
reg        par = 1'b0;        // which accumulator buffer is the current input
reg [IW:0] ci = 0;            // init counter (covers both buffers)
reg [IW:0] ck = 0;            // phase A: index issued
reg [IW:0] pk = 0;            // phase B: source
reg [IW:0] pi = 0;            // phase B: target
reg [15:0] t = 0;
reg [15:0] tot = 0;

wire init = (st == S_INIT);

// Accumulator buffers: buffer 0 is amem[0..N-1], buffer 1 is amem[N..2N-1].
wire [IW:0] n_val    = N;
wire [IW:0] cur_base = par ? n_val : {(IW+1){1'b0}};
wire [IW:0] nxt_base = par ? {(IW+1){1'b0}} : n_val;

// ---- pipeline registers ----
reg               a_v = 1'b0;     // phase A: a record for a_idx is due in the next cycle
reg [IW-1:0]      a_idx = 0;
reg               b_v = 1'b0;     // phase B: a sum for (b_dst_base, b_idx) is due next cycle
reg [IW-1:0]      b_idx = 0;
reg [IW:0]        b_dst_base = 0;

// ---- memories ----
reg [34:0]        smem [0:N-1];       // {V[15:0], I[15:0], refractory[2:0]}
reg signed [15:0] emem [0:N-1];       // external input
reg signed [23:0] amem [0:2*N-1];     // two accumulator buffers
reg signed [7:0]  wmem [0:N*N-1];     // W[source][target]
reg               spk  [0:N-1];       // spikes of the current step

// read data (valid one cycle after the address is presented)
reg [34:0]        s_rd;
reg signed [15:0] e_rd;
reg signed [23:0] acc_rd;
reg signed [7:0]  w_rd;

// ---- stage A logic: uses s_rd, e_rd, acc_rd ----
wire signed [23:0] a_syn_wide = acc_rd + {{8{e_rd[15]}}, e_rd};
wire signed [15:0] a_syn_in;
assign a_syn_in = (a_syn_wide > 24'sd32767)  ? 16'sh7FFF :
                  (a_syn_wide < -24'sd32768) ? 16'sh8000 : a_syn_wide[15:0];

wire signed [15:0] lv_next, li_next;
wire        [2:0]  lref_next;
wire               lspike;

lif_core u_lif (
    .v       (s_rd[34:19]),
    .i       (s_rd[18:3]),
    .ref_cnt (s_rd[2:0]),
    .syn_in  (a_syn_in),
    .theta   (theta),
    .v_reset (v_reset),
    .v_rest  (v_rest),
    .k_m     (k_m),
    .k_s     (k_s),
    .refrac  (refrac),
    .v_next  (lv_next),
    .i_next  (li_next),
    .ref_next(lref_next),
    .spike   (lspike)
);

// ---- stage B logic: uses acc_rd, w_rd ----
wire signed [23:0] b_sum = acc_rd + ({{16{w_rd[7]}}, w_rd} <<< W_SHIFT);

// ---- single write port per memory ----
wire              smem_we = init | a_v;
wire [IW-1:0]     smem_wa = init ? ci[IW-1:0] : a_idx;
wire [34:0]       smem_wd = init ? 35'd0 : {lv_next, li_next, lref_next};

wire              amem_we = init | a_v | b_v;
wire [IW:0]       amem_wa = init ? ci : (a_v ? (nxt_base + a_idx) : (b_dst_base + b_idx));
wire signed [23:0] amem_wd = b_v ? b_sum : 24'sd0;

wire              spk_we = init | a_v;
wire [IW-1:0]     spk_wa = init ? ci[IW-1:0] : a_idx;
wire              spk_wd = init ? 1'b0 : lspike;

// read addresses: phase A reads at ck, phase B reads at (nxt, pi)
wire [IW:0] amem_ra = (st == S_B) ? (nxt_base + pi[IW-1:0]) : (cur_base + ck[IW-1:0]);

// ---- memory processes ----
always @(posedge clk) begin
    if (load_w_we) wmem[load_w_addr] <= load_w_data;
    w_rd <= wmem[{pk[IW-1:0], pi[IW-1:0]}];
end

always @(posedge clk) begin
    if (load_e_we) emem[load_e_addr] <= load_e_data;
    e_rd <= emem[ck[IW-1:0]];
end

always @(posedge clk) begin
    if (smem_we) smem[smem_wa] <= smem_wd;
    s_rd <= smem[ck[IW-1:0]];
end

always @(posedge clk) begin
    if (amem_we) amem[amem_wa] <= amem_wd;
    acc_rd <= amem[amem_ra];
end

always @(posedge clk) begin
    if (spk_we) spk[spk_wa] <= spk_wd;
end

// ---- control ----
always @(posedge clk) begin
    rec_we <= 1'b0;
    done   <= 1'b0;

    // phase A stage 2: record and write-back for a_idx
    if (a_v) begin
        rec_we  <= 1'b1;
        rec_k   <= a_idx;
        rec_v   <= lv_next;
        rec_spk <= lspike;
    end

    case (st)
        S_IDLE: begin
            a_v <= 1'b0;
            b_v <= 1'b0;
            if (start) begin
                ci   <= 0;
                t    <= 16'd0;
                tot  <= steps;
                par  <= 1'b0;
                busy <= 1'b1;
                st   <= S_INIT;
            end
        end

        S_INIT: begin
            // clears state, spikes and both accumulator buffers, one entry per cycle
            if (ci == 2*N - 1) begin
                ck  <= 0;
                a_v <= 1'b0;
                b_v <= 1'b0;
                st  <= S_A;
            end
            ci <= ci + 1'b1;
        end

        S_A: begin
            // phase A issue
            if (ck < N) begin
                a_idx <= ck[IW-1:0];
                a_v   <= 1'b1;
                ck    <= ck + 1'b1;
            end else begin
                a_v   <= 1'b0;
                pk    <= 0;
                pi    <= 0;
                b_v   <= 1'b0;
                st    <= S_B;
            end
        end

        S_B: begin
            b_v <= 1'b0;
            if (pk == N) begin
                st <= S_END;
            end else if (spk[pk[IW-1:0]]) begin
                // phase B issue (pk, pi); the read is presented this cycle
                b_idx      <= pi[IW-1:0];
                b_dst_base <= nxt_base;
                b_v        <= 1'b1;
                if (pi == N - 1) begin
                    pi <= 0;
                    pk <= pk + 1'b1;
                end else begin
                    pi <= pi + 1'b1;
                end
            end else begin
                pi <= 0;
                pk <= pk + 1'b1;
            end
        end

        S_END: begin
            // the last phase B write committed in the previous cycle
            par <= ~par;
            t   <= t + 16'd1;
            if (t + 16'd1 == tot) begin
                busy <= 1'b0;
                done <= 1'b1;
                st   <= S_IDLE;
            end else begin
                ck <= 0;
                st <= S_A;
            end
        end

        default: st <= S_IDLE;
    endcase
end

endmodule
