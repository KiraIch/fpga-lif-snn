// Full network design for the Tang Nano 20K (M3 board step).
//
//   uart_rx -> cmd_decoder -> copy FSM -> network (weights and inputs are loaded here)
//                  |                          |
//                  |                  run control, per-neuron memories
//                  |                          |
//                  +-> reply sequencer <-------+
//                              |
//                           uart_tx
//
// Frames (host/protocol.py):
//   WRITE_PARAM    set theta, v_reset, v_rest, k_m, k_s, refrac
//   WRITE_WEIGHTS  set a block of the weight matrix, W[j][i] at j*N + i
//   SET_INPUT      set a block of the per-neuron external input
//   RUN            run the network for `steps` steps. No reply. The input field is
//                  ignored: the network takes its input from SET_INPUT.
//   READ_STATUS    reply (cmd 0x86): ok_count, err_count, steps done (2 bytes)
//   READ_COUNTS    reply (cmd 0x87): spike count of each neuron in the last run (2 bytes each)
//   READ_SNAPSHOT  reply (cmd 0x88): V and spike of each neuron in the last step (3 bytes each)
//   READ_TRACE     reply (cmd 0x89): spikes of all neurons for `count` steps, from step `start`
//                  (N/8 bytes per step, bit j of byte b is neuron 8b+j)
//
// Records are not stored in full. Each record from the network updates two
// per-neuron memories: the spike count (cleared when a run starts) and the last
// {spike, V}. Memory is N x 33 bits, not N x steps x 17 bits, which would not fit
// in the block RAM of the GW2AR-18.
// The spikes are also kept step by step, one bit per neuron, for the first TR_STEPS
// steps of a run (TR_STEPS x N bits of block RAM). Only the spikes are kept, not V.
//
// A reply is sent one request at a time. The decoder refuses every command while a
// reply is being sent, the copy is running, or the network is running (see busy).
module network_top #(
    parameter N = 256
)(
    input  wire       clk,
    input  wire       rx,
    output wire       tx,
    output wire [5:0] led
);

localparam IW       = $clog2(N);
localparam CLK_FRE  = 27000000;
localparam BAUD     = 115200;
localparam STAT_CMD = 8'h86;
localparam CNT_CMD  = 8'h87;
localparam SNAP_CMD = 8'h88;
localparam TRACE_CMD = 8'h89;
localparam TR_STEPS = 512;        // steps kept in the spike trace (block RAM limit)
localparam TR_BYTES = N / 8;      // bytes per step in the trace

localparam R_IDLE = 2'd0;   // run control
localparam R_CLR  = 2'd1;   // clear the spike counts
localparam R_GO   = 2'd2;   // network running

localparam C_IDLE = 1'b0;   // copy of a WRITE_WEIGHTS / SET_INPUT payload
localparam C_RUN  = 1'b1;

localparam Q_IDLE   = 4'd0; // reply sequencer
localparam Q_STAT   = 4'd1;
localparam Q_H0     = 4'd2;
localparam Q_H1     = 4'd3;
localparam Q_H2     = 4'd4;
localparam Q_FETCH  = 4'd5;
localparam Q_FETCH2 = 4'd6;
localparam Q_B0     = 4'd7;
localparam Q_B1     = 4'd8;
localparam Q_B2     = 4'd9;
localparam Q_NEXT   = 4'd10;
localparam Q_CSUM   = 4'd11;
localparam Q_TWAIT  = 4'd12;      // trace: one clock for the memory to follow the byte address
localparam Q_TB     = 4'd13;
localparam Q_TNEXT  = 4'd14;

// ---- state ----
reg [1:0]  rs = R_IDLE;
reg [IW:0] ci = 0;               // clear counter
reg        net_start = 1'b0;
reg [10:0] run_steps_r = 11'd0;
reg [15:0] steps_done = 16'd0;

reg        cp_state = C_IDLE;
reg        cp_is_input = 1'b0;
reg [15:0] cp_start = 16'd0;
reg [7:0]  cp_n = 8'd0;
reg [7:0]  cp_i = 8'd0;
reg        cp_phase = 1'b0;
reg [7:0]  cp_lo = 8'd0;
reg        ld_w_we = 1'b0;
reg        ld_e_we = 1'b0;
reg [2*IW-1:0]     ld_w_addr = 0;
reg signed [7:0]   ld_w_data = 8'sd0;
reg [IW-1:0]       ld_e_addr = 0;
reg signed [15:0]  ld_e_data = 16'sd0;

reg        rec_we_d = 1'b0;
reg [IW-1:0] rec_k_d = 0;
reg        rec_spk_d = 1'b0;

reg [3:0]  seq = Q_IDLE;
reg [2:0]  sidx = 3'd0;
reg [7:0]  stat [0:7];
reg [IW-1:0] rptr = 0;
reg [6:0]  rleft = 7'd0;
reg        rsnap = 1'b0;
reg        rtrace = 1'b0;
reg [8:0]  tptr = 9'd0;          // trace: first step of the reply, then the step being sent
reg [IW-4:0] tbyte = 0;          // trace: byte within the step
reg [7:0]  rcmd = 8'd0;
reg [7:0]  total = 8'd0;
reg [7:0]  csum = 8'd0;

reg        tx_start = 1'b0;
reg [7:0]  tx_data = 8'd0;

reg [15:0] cnt_mem  [0:N-1];     // spike count of the current run
reg [16:0] snap_mem [0:N-1];     // {spike, V} of the last step
reg [15:0] cnt_rd  = 16'd0;
reg [16:0] snap_rd = 17'd0;

reg [7:0]  tsh = 8'd0;                              // spikes of the current byte, being collected
reg [7:0]  tmem [0:TR_STEPS*TR_BYTES-1];            // spike trace, {step, byte}
reg [7:0]  tr_rd = 8'd0;

// ---- wires ----
wire [7:0] rx_data;
wire       rx_valid;
wire       tx_busy;
wire       tx_free = ~tx_busy & ~tx_start;

wire signed [15:0] theta, v_reset, v_rest, run_input;
wire [3:0]  k_m, k_s;
wire [2:0]  refrac;
wire [7:0]  ok_count, err_count;
wire        status_req, run_req, rec_req;
wire [10:0] run_len;
wire [9:0]  rec_start;
wire [6:0]  rec_count;
wire        wr_req, wr_is_input, rd_req, rd_is_snap, rd_is_trace;
wire [15:0] wr_start, rd_start;
wire [7:0]  wr_count;
wire [6:0]  rd_count;
wire [7:0]  buf_addr, buf_dout;

wire        reply_busy = (seq != Q_IDLE);
wire        copy_busy  = (cp_state == C_RUN);
wire        run_busy   = (rs != R_IDLE);
wire        busy       = reply_busy | copy_busy | run_busy;

wire        rec_we;
wire [IW-1:0] rec_k;
wire signed [15:0] rec_v;
wire        rec_spk;
wire        net_done;

// Memory read address: the record path reads the neuron being recorded;
// the reply path reads the neuron being sent.
wire [IW-1:0] mem_ra = (seq == Q_IDLE) ? rec_k : rptr;

wire [7:0] stat_sum = STAT_CMD + 8'd4 + ok_count + err_count
                    + steps_done[7:0] + steps_done[15:8];

uart_rx #(.CLK_FRE(CLK_FRE), .BAUD(BAUD)) u_rx (
    .clk        (clk),
    .rx         (rx),
    .data       (rx_data),
    .data_valid (rx_valid)
);

cmd_decoder #(.NET_N(N)) u_dec (
    .clk        (clk),
    .byte_in    (rx_data),
    .byte_valid (rx_valid),
    .busy       (busy),
    .theta      (theta),
    .v_reset    (v_reset),
    .v_rest     (v_rest),
    .k_m        (k_m),
    .k_s        (k_s),
    .refrac     (refrac),
    .ok_count   (ok_count),
    .err_count  (err_count),
    .status_req (status_req),
    .run_req    (run_req),
    .run_input  (run_input),
    .run_len    (run_len),
    .rec_req    (rec_req),
    .rec_start  (rec_start),
    .rec_count  (rec_count),
    .wr_req     (wr_req),
    .wr_is_input(wr_is_input),
    .wr_start   (wr_start),
    .wr_count   (wr_count),
    .rd_req     (rd_req),
    .rd_is_snap (rd_is_snap),
    .rd_is_trace(rd_is_trace),
    .rd_start   (rd_start),
    .rd_count   (rd_count),
    .buf_addr   (buf_addr),
    .buf_dout   (buf_dout)
);

// ---- copy of a WRITE_WEIGHTS or SET_INPUT payload into the network ----
// The payload is in the decoder's buffer: start at bytes 0..1, data from byte 2.
// Weights take one byte each. Inputs take two bytes each, low byte first.
// A payload is at most 253 bytes, and the next frame cannot arrive before the
// copy ends (a frame takes more than 2000 clocks per byte at 115200 baud).
assign buf_addr = cp_is_input ? (8'd2 + {cp_i[6:0], 1'b0} + {7'd0, cp_phase})
                              : (8'd2 + cp_i);

always @(posedge clk) begin
    ld_w_we <= 1'b0;
    ld_e_we <= 1'b0;
    case (cp_state)
        C_IDLE: if (wr_req) begin
            cp_state    <= C_RUN;
            cp_is_input <= wr_is_input;
            cp_start    <= wr_start;
            cp_n        <= wr_count;
            cp_i        <= 8'd0;
            cp_phase    <= 1'b0;
        end

        C_RUN: begin
            if (cp_i == cp_n) begin
                cp_state <= C_IDLE;
            end else if (!cp_is_input) begin
                ld_w_we   <= 1'b1;
                ld_w_addr <= cp_start + cp_i;
                ld_w_data <= buf_dout;
                cp_i      <= cp_i + 8'd1;
            end else if (!cp_phase) begin
                cp_lo    <= buf_dout;
                cp_phase <= 1'b1;
            end else begin
                ld_e_we   <= 1'b1;
                ld_e_addr <= cp_start + cp_i;
                ld_e_data <= {buf_dout, cp_lo};
                cp_phase  <= 1'b0;
                cp_i      <= cp_i + 8'd1;
            end
        end
    endcase
end

// ---- run control ----
// A RUN request clears the spike counts (N clocks), starts the network, and
// waits for it to finish. Each record updates the counts and the snapshot.
always @(posedge clk) begin
    net_start <= 1'b0;
    case (rs)
        R_IDLE: if (run_req) begin
            run_steps_r <= run_len;
            steps_done  <= 16'd0;
            ci          <= 0;
            rs          <= R_CLR;
        end

        R_CLR: begin
            ci <= ci + 1'b1;
            if (ci == N - 1) begin
                net_start <= 1'b1;
                rs        <= R_GO;
            end
        end

        R_GO: begin
            if (rec_we && rec_k == N - 1)
                steps_done <= steps_done + 16'd1;
            if (net_done)
                rs <= R_IDLE;
        end

        default: rs <= R_IDLE;
    endcase
end

// ---- per-neuron memories ----
// The count update is a read-modify-write over two clocks. Consecutive records
// are for different neurons, so the read of one neuron never sees a write
// that is still in flight.
wire        cnt_we = (rs == R_CLR) | rec_we_d;
wire [IW-1:0] cnt_wa = (rs == R_CLR) ? ci[IW-1:0] : rec_k_d;
wire [15:0] cnt_wd = (rs == R_CLR) ? 16'd0 : cnt_rd + {15'd0, rec_spk_d};

always @(posedge clk) begin
    if (cnt_we)
        cnt_mem[cnt_wa] <= cnt_wd;
    cnt_rd <= cnt_mem[mem_ra];

    if (rec_we)
        snap_mem[rec_k] <= {rec_spk, rec_v};
    snap_rd <= snap_mem[mem_ra];

    // spike trace: records come in neuron order, so the byte is complete at k = 8b+7.
    // steps_done is the step of this record (it is incremented at the last record).
    if (rec_we)
        tsh <= {rec_spk, tsh[7:1]};
    if (rec_we && rec_k[2:0] == 3'd7 && steps_done < TR_STEPS)
        tmem[{steps_done[8:0], rec_k[IW-1:3]}] <= {rec_spk, tsh[7:1]};
    tr_rd <= tmem[{tptr, tbyte}];

    rec_we_d  <= rec_we;
    rec_k_d   <= rec_k;
    rec_spk_d <= rec_spk;
end

network #(.N(N), .W_SHIFT(2), .IW(IW)) u_net (
    .clk        (clk),
    .start      (net_start),
    .steps      ({5'd0, run_steps_r}),
    .theta      (theta),
    .v_reset    (v_reset),
    .v_rest     (v_rest),
    .k_m        (k_m),
    .k_s        (k_s),
    .refrac     (refrac),
    .load_w_we  (ld_w_we),
    .load_w_addr(ld_w_addr),
    .load_w_data(ld_w_data),
    .load_e_we  (ld_e_we),
    .load_e_addr(ld_e_addr),
    .load_e_data(ld_e_data),
    .rec_we     (rec_we),
    .rec_k      (rec_k),
    .rec_v      (rec_v),
    .rec_spk    (rec_spk),
    .busy       (),
    .done       (net_done)
);

// ---- reply sequencer ----
// STATUS: 8 bytes from a copy taken when the request arrives.
// COUNTS and SNAPSHOT: header, then one entry per neuron, then the checksum.
// The memories are read with a registered address, so each entry waits one clock
// (Q_FETCH2) before its bytes are sent.
always @(posedge clk) begin
    tx_start <= 1'b0;
    case (seq)
        Q_IDLE: begin
            if (status_req) begin
                stat[0] <= 8'hA5;
                stat[1] <= STAT_CMD;
                stat[2] <= 8'd4;
                stat[3] <= ok_count;
                stat[4] <= err_count;
                stat[5] <= steps_done[7:0];
                stat[6] <= steps_done[15:8];
                stat[7] <= stat_sum;
                sidx    <= 3'd0;
                seq     <= Q_STAT;
            end else if (rd_req) begin
                rptr   <= rd_start[IW-1:0];
                tptr   <= rd_start[8:0];
                tbyte  <= 0;
                rleft  <= rd_count;
                rsnap  <= rd_is_snap;
                rtrace <= rd_is_trace;
                rcmd   <= rd_is_trace ? TRACE_CMD : (rd_is_snap ? SNAP_CMD : CNT_CMD);
                total  <= rd_is_trace ? (rd_count << (IW-3))
                        : rd_is_snap ? ({rd_count, 1'b0} + {1'b0, rd_count}) : {rd_count, 1'b0};
                seq    <= Q_H0;
            end
        end

        Q_STAT: if (tx_free) begin
            tx_data  <= stat[sidx];
            tx_start <= 1'b1;
            sidx     <= sidx + 3'd1;
            if (sidx == 3'd7)
                seq <= Q_IDLE;
        end

        Q_H0: if (tx_free) begin
            tx_data  <= 8'hA5;
            tx_start <= 1'b1;
            seq      <= Q_H1;
        end

        Q_H1: if (tx_free) begin
            tx_data  <= rcmd;
            tx_start <= 1'b1;
            csum     <= rcmd;
            seq      <= Q_H2;
        end

        Q_H2: if (tx_free) begin
            tx_data  <= total;
            tx_start <= 1'b1;
            csum     <= csum + total;
            seq      <= rtrace ? Q_TWAIT : Q_FETCH;
        end

        // trace: tr_rd follows {tptr, tbyte} one clock after the address changes
        Q_TWAIT: seq <= Q_TB;

        Q_TB: if (tx_free) begin
            tx_data  <= tr_rd;
            tx_start <= 1'b1;
            csum     <= csum + tr_rd;
            tbyte    <= tbyte + 1'b1;
            seq      <= (tbyte == TR_BYTES - 1) ? Q_TNEXT : Q_TWAIT;
        end

        Q_TNEXT: begin
            tptr  <= tptr + 9'd1;
            tbyte <= 0;
            rleft <= rleft - 7'd1;
            seq   <= (rleft == 7'd1) ? Q_CSUM : Q_TWAIT;
        end

        Q_FETCH: seq <= Q_FETCH2;      // rptr is applied to the memories in this clock

        Q_FETCH2: seq <= Q_B0;

        Q_B0: if (tx_free) begin
            tx_data  <= rsnap ? snap_rd[7:0] : cnt_rd[7:0];
            tx_start <= 1'b1;
            csum     <= csum + (rsnap ? snap_rd[7:0] : cnt_rd[7:0]);
            seq      <= Q_B1;
        end

        Q_B1: if (tx_free) begin
            tx_data  <= rsnap ? snap_rd[15:8] : cnt_rd[15:8];
            tx_start <= 1'b1;
            csum     <= csum + (rsnap ? snap_rd[15:8] : cnt_rd[15:8]);
            seq      <= rsnap ? Q_B2 : Q_NEXT;
        end

        Q_B2: if (tx_free) begin
            tx_data  <= {7'd0, snap_rd[16]};
            tx_start <= 1'b1;
            csum     <= csum + {7'd0, snap_rd[16]};
            seq      <= Q_NEXT;
        end

        Q_NEXT: begin
            rptr  <= rptr + 1'b1;
            rleft <= rleft - 7'd1;
            seq   <= (rleft == 7'd1) ? Q_CSUM : Q_FETCH;
        end

        Q_CSUM: if (tx_free) begin
            tx_data  <= csum;
            tx_start <= 1'b1;
            seq      <= Q_IDLE;
        end

        default: seq <= Q_IDLE;
    endcase
end

uart_tx #(.CLK_FRE(CLK_FRE), .BAUD(BAUD)) u_tx (
    .clk   (clk),
    .data  (tx_data),
    .start (tx_start),
    .busy  (tx_busy),
    .tx    (tx)
);

assign led = ~{err_count[2:0], ok_count[2:0]};

endmodule
