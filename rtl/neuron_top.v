// Single-neuron board test (M2): one LIF neuron driven over the UART link.
//
//   uart_rx -> cmd_decoder -> lif_core (one step per clock) -> record memory
//                  |                                              |
//                  +-> reply sequencer <--------------------------+
//                              |
//                           uart_tx
//
// Frames (host/protocol.py):
//   WRITE_PARAM  set theta, v_reset, v_rest, k_m, k_s, refrac
//   RUN          reset the neuron (V = 0, I = 0, no refractory), then run `steps`
//                steps with a constant input. V and spike of every step go into
//                the record memory. No reply.
//   READ_RECORD  reply (cmd 0x85) with `count` samples from `start`. Each sample is
//                3 bytes: V low, V high, spike.
//   READ_STATUS  reply (cmd 0x86) with parameters and counters (see cmd_test.v).
//
// The reply sequencer handles one request at a time. A request that arrives
// while a reply is being sent is refused (counted in err_count) and not queued.
// The host must wait for each reply before sending the next request.
module neuron_top (
    input  wire       clk,
    input  wire       rx,
    output wire       tx,
    output wire [5:0] led
);

localparam CLK_FRE     = 27000000;
localparam BAUD        = 115200;
localparam STAT_CMD    = 8'h86;
localparam STAT_LEN    = 8'd11;
localparam STAT_BYTES  = 15;     // sync, cmd, len, 11 payload, checksum
localparam REC_CMD     = 8'h85;

wire [7:0] rx_data;
wire       rx_valid;

uart_rx #(.CLK_FRE(CLK_FRE), .BAUD(BAUD)) u_rx (
    .clk        (clk),
    .rx         (rx),
    .data       (rx_data),
    .data_valid (rx_valid)
);

wire signed [15:0] theta, v_reset, v_rest, run_input;
wire        [3:0]  k_m, k_s;
wire        [2:0]  refrac;
wire        [7:0]  ok_count, err_count;
wire               status_req, run_req, rec_req;
wire        [10:0] run_len;
wire        [9:0]  rec_start;
wire        [6:0]  rec_count;

wire reply_busy;   // from the reply sequencer below

cmd_decoder u_dec (
    .clk        (clk),
    .byte_in    (rx_data),
    .byte_valid (rx_valid),
    .busy       (reply_busy),
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
    .buf_addr   (8'd0)
);

// ---- neuron ----
reg signed [15:0] nv = 16'sd0;
reg signed [15:0] ni = 16'sd0;
reg        [2:0]  nref = 3'd0;
reg               running = 1'b0;
reg        [10:0] step = 11'd0;

wire signed [15:0] lv_next, li_next;
wire        [2:0]  lref_next;
wire               spike;

lif_core u_lif (
    .v       (nv),
    .i       (ni),
    .ref_cnt (nref),
    .syn_in  (run_input),
    .theta   (theta),
    .v_reset (v_reset),
    .v_rest  (v_rest),
    .k_m     (k_m),
    .k_s     (k_s),
    .refrac  (refrac),
    .v_next  (lv_next),
    .i_next  (li_next),
    .ref_next(lref_next),
    .spike   (spike)
);

always @(posedge clk) begin
    if (run_req) begin
        nv      <= 16'sd0;
        ni      <= 16'sd0;
        nref    <= 3'd0;
        step    <= 11'd0;
        running <= 1'b1;
    end else if (running) begin
        nv   <= lv_next;
        ni   <= li_next;
        nref <= lref_next;
        step <= step + 11'd1;
        if (step == run_len - 11'd1)
            running <= 1'b0;
    end
end

// ---- record memory: {spike, V} per step, 1024 steps ----
reg [16:0] rec_mem [0:1023];
reg [9:0]  rd_addr = 10'd0;
reg [16:0] rec_rd  = 17'd0;

always @(posedge clk) begin
    if (running)
        rec_mem[step[9:0]] <= {spike, lv_next};
    rec_rd <= rec_mem[rd_addr];
end

// ---- status reply copy ----
reg [7:0] stat [0:STAT_BYTES-1];
wire [7:0] stat_sum = STAT_CMD + STAT_LEN
                    + theta[7:0] + theta[15:8]
                    + v_reset[7:0] + v_reset[15:8]
                    + v_rest[7:0] + v_rest[15:8]
                    + {4'd0, k_m} + {4'd0, k_s} + {5'd0, refrac}
                    + ok_count + err_count;

// ---- reply sequencer ----
localparam Q_IDLE   = 4'd0;
localparam Q_STAT   = 4'd1;
localparam Q_H0     = 4'd2;   // sync
localparam Q_H1     = 4'd3;   // cmd
localparam Q_H2     = 4'd4;   // len
localparam Q_FETCH  = 4'd5;   // set record address
localparam Q_FETCH2 = 4'd6;   // wait one clock for the record read
localparam Q_B0     = 4'd7;   // V low
localparam Q_B1     = 4'd8;   // V high
localparam Q_B2     = 4'd9;   // spike
localparam Q_NEXT   = 4'd10;
localparam Q_CSUM   = 4'd11;

reg [3:0] seq = Q_IDLE;
assign reply_busy = (seq != Q_IDLE);
reg [3:0] sidx = 4'd0;
reg [9:0] rptr = 10'd0;
reg [6:0] rleft = 7'd0;
reg [7:0] total = 8'd0;   // payload length of a record reply: 3 * count
reg [7:0] csum = 8'd0;

reg       tx_start = 1'b0;
reg [7:0] tx_data  = 8'd0;
wire      tx_busy;
wire      tx_free = ~tx_busy & ~tx_start;

always @(posedge clk) begin
    tx_start <= 1'b0;
    case (seq)
        Q_IDLE: begin
            if (status_req) begin
                stat[0]  <= 8'hA5;
                stat[1]  <= STAT_CMD;
                stat[2]  <= STAT_LEN;
                stat[3]  <= theta[7:0];
                stat[4]  <= theta[15:8];
                stat[5]  <= v_reset[7:0];
                stat[6]  <= v_reset[15:8];
                stat[7]  <= v_rest[7:0];
                stat[8]  <= v_rest[15:8];
                stat[9]  <= {4'd0, k_m};
                stat[10] <= {4'd0, k_s};
                stat[11] <= {5'd0, refrac};
                stat[12] <= ok_count;
                stat[13] <= err_count;
                stat[14] <= stat_sum;
                sidx     <= 4'd0;
                seq      <= Q_STAT;
            end else if (rec_req) begin
                rptr  <= rec_start;
                rleft <= rec_count;
                total <= {rec_count, 1'b0} + {1'b0, rec_count};
                seq   <= Q_H0;
            end
        end

        Q_STAT: if (tx_free) begin
            tx_data  <= stat[sidx];
            tx_start <= 1'b1;
            sidx     <= sidx + 4'd1;
            if (sidx == STAT_BYTES - 1)
                seq <= Q_IDLE;
        end

        Q_H0: if (tx_free) begin
            tx_data  <= 8'hA5;
            tx_start <= 1'b1;
            seq      <= Q_H1;
        end

        Q_H1: if (tx_free) begin
            tx_data  <= REC_CMD;
            tx_start <= 1'b1;
            csum     <= REC_CMD;
            seq      <= Q_H2;
        end

        Q_H2: if (tx_free) begin
            tx_data  <= total;
            tx_start <= 1'b1;
            csum     <= csum + total;
            seq      <= Q_FETCH;
        end

        Q_FETCH: begin
            rd_addr <= rptr;
            seq     <= Q_FETCH2;
        end

        Q_FETCH2: seq <= Q_B0;

        Q_B0: if (tx_free) begin
            tx_data  <= rec_rd[7:0];
            tx_start <= 1'b1;
            csum     <= csum + rec_rd[7:0];
            seq      <= Q_B1;
        end

        Q_B1: if (tx_free) begin
            tx_data  <= rec_rd[15:8];
            tx_start <= 1'b1;
            csum     <= csum + rec_rd[15:8];
            seq      <= Q_B2;
        end

        Q_B2: if (tx_free) begin
            tx_data  <= {7'd0, rec_rd[16]};
            tx_start <= 1'b1;
            csum     <= csum + {7'd0, rec_rd[16]};
            seq      <= Q_NEXT;
        end

        Q_NEXT: begin
            rptr  <= rptr + 10'd1;
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
