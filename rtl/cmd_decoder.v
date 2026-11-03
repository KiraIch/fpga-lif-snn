// Command decoder for the PC-to-board link. Frame format is defined in host/protocol.py:
//
//   [0xA5][cmd][len][data ... len bytes][checksum]     checksum = (cmd + len + sum(data)) mod 256
//
// Bytes arrive one per byte_valid pulse (from uart_rx). The whole payload is buffered
// (up to 255 bytes) and the checksum is checked before anything changes, so a damaged
// frame leaves the parameters as they were.
//
// Implemented:
//   WRITE_PARAM   (0x01, 9 bytes)      sets theta, v_reset, v_rest, k_m, k_s, refrac.
//   WRITE_WEIGHTS (0x02, 3..255 bytes) start (2 bytes), then weights (1 byte each).
//                                      wr_req pulse; the top level copies the payload.
//   SET_INPUT     (0x03, 4..255 bytes) start (2 bytes), then Q8.8 inputs (2 bytes each).
//                                      wr_req pulse with wr_is_input set.
//   READ_STATUS   (0x06, no data)      raises status_req for one cycle.
//   RUN           (0x04, 4 bytes)      input (Q8.8, 2 bytes), steps (1..1024, 2 bytes).
//                                      raises run_req for one cycle; run_input and run_len are set.
//   READ_RECORD   (0x05, 3 bytes)      start (2 bytes), count (1 byte, 1..64). Valid only
//                                      inside the last run. raises rec_req for one cycle.
//   READ_COUNTS   (0x07, 3 bytes)      start, count. raises rd_req with rd_is_snap = 0.
//   READ_SNAPSHOT (0x08, 3 bytes)      start, count. raises rd_req with rd_is_snap = 1.
//   READ_TRACE    (0x09, 3 bytes)      start (step), count (1..7). raises rd_req with
//                                      rd_is_trace = 1. Only steps already in the last run
//                                      can be read: start + count <= min(run_len, 512).
// The top level builds all replies. Any other valid frame, and any frame with an
// out-of-range value, is counted in err_count. Counters wrap at 255.
// While `busy` is high (a reply is being sent, or the network is running or loading),
// every command except READ_RECORD is refused and counted as an error, so a run never
// sees a parameter or weight change, and a reply is never overwritten.
//
// Limitation: the parser has no timeout. If a length byte is corrupted, the
// decoder waits for the wrong number of bytes until the next frame is
// misaligned. The host recovers by re-sending from a known point.
module cmd_decoder #(
    parameter NET_N = 256        // neurons in the network: range limit for the network commands
)(
    input  wire              clk,
    input  wire      [7:0]   byte_in,
    input  wire              byte_valid,
    input  wire              busy,       // refuses every command except READ_RECORD
    output reg signed [15:0] theta = 16'sd0,
    output reg signed [15:0] v_reset = 16'sd0,
    output reg signed [15:0] v_rest = 16'sd0,
    output reg       [3:0]   k_m = 4'd0,
    output reg       [3:0]   k_s = 4'd0,
    output reg       [2:0]   refrac = 3'd0,
    output reg       [7:0]   ok_count = 8'd0,
    output reg       [7:0]   err_count = 8'd0,
    output reg               status_req = 1'b0,   // one-cycle pulse
    output reg               run_req = 1'b0,      // one-cycle pulse
    output reg signed [15:0] run_input = 16'sd0,
    output reg       [10:0]  run_len = 11'd0,     // steps in the last accepted run
    output reg               rec_req = 1'b0,      // one-cycle pulse
    output reg       [9:0]   rec_start = 10'd0,
    output reg       [6:0]   rec_count = 7'd0,
    // network commands
    output reg               wr_req = 1'b0,       // one-cycle pulse: copy the payload into the network
    output reg               wr_is_input = 1'b0,  // 0: weights (1 byte each), 1: inputs (2 bytes each)
    output reg       [15:0]  wr_start = 16'd0,
    output reg       [7:0]   wr_count = 8'd0,     // elements: bytes for weights, values for inputs
    output reg               rd_req = 1'b0,       // one-cycle pulse: reply with counts or snapshot
    output reg               rd_is_snap = 1'b0,   // 0: counts (2 bytes each), 1: snapshot (3 bytes each)
    output reg               rd_is_trace = 1'b0,  // 1: spike trace of steps rd_start.. (rd_is_snap = 0)
    output reg       [15:0]  rd_start = 16'd0,
    output reg       [6:0]   rd_count = 7'd0,
    input  wire      [7:0]   buf_addr,            // payload index to read (for the copy)
    output wire      [7:0]   buf_dout
);

localparam SYNC_BYTE        = 8'hA5;
localparam CMD_WRITE_PARAM  = 8'h01;
localparam CMD_WRITE_WEIGHTS = 8'h02;
localparam CMD_SET_INPUT    = 8'h03;
localparam CMD_RUN          = 8'h04;
localparam CMD_READ_RECORD  = 8'h05;
localparam CMD_READ_STATUS  = 8'h06;
localparam CMD_READ_COUNTS  = 8'h07;
localparam CMD_READ_SNAPSHOT = 8'h08;
localparam CMD_READ_TRACE   = 8'h09;
localparam PARAM_LEN        = 8'd9;
localparam RUN_LEN          = 8'd4;
localparam REC_LEN          = 8'd3;
localparam RUN_MAX_STEPS    = 16'd1024;
localparam REC_MAX_COUNT    = 8'd64;
localparam NET_CELLS        = NET_N * NET_N;   // weight matrix entries

localparam S_SYNC = 3'd0;
localparam S_CMD  = 3'd1;
localparam S_LEN  = 3'd2;
localparam S_DATA = 3'd3;
localparam S_CSUM = 3'd4;

reg [2:0] state = S_SYNC;
reg [7:0] cmd   = 8'd0;
reg [7:0] len   = 8'd0;
reg [7:0] idx   = 8'd0;     // payload bytes received so far
reg [7:0] sum   = 8'd0;     // running checksum
reg [7:0] buf_mem [0:255];  // whole payload of the frame being received

assign buf_dout = buf_mem[buf_addr];

// Values from the payload buffer, for the range checks below.
wire [15:0] run_steps = {buf_mem[3], buf_mem[2]};
wire [15:0] first     = {buf_mem[1], buf_mem[0]};   // start index of the network commands
wire [7:0]  rec_n     = buf_mem[2];
wire [15:0] rec_first = first;
wire        run_ok    = (run_steps != 16'd0) && (run_steps <= RUN_MAX_STEPS);
wire        rec_ok    = (rec_n != 8'd0) && (rec_n <= REC_MAX_COUNT)
                      && ({1'b0, rec_first} + {9'd0, rec_n} <= {6'd0, run_len});

// Network commands. The end of the range must not pass the array.
wire [7:0]  wr_w_bytes = len - 8'd2;                 // weights in a WRITE_WEIGHTS frame
wire [7:0]  wr_i_values = (len - 8'd2) >> 1;         // inputs in a SET_INPUT frame
wire [16:0] wr_w_end   = {1'b0, first} + {9'd0, wr_w_bytes};
wire [16:0] wr_i_end   = {1'b0, first} + {9'd0, wr_i_values};
wire        wr_w_ok    = (len >= 8'd3) && (wr_w_end <= NET_CELLS);
wire        wr_i_ok    = (len >= 8'd4) && !len[0] && (wr_i_end <= NET_N);
wire [7:0]  rd_n       = buf_mem[2];
wire        rd_ok      = (len == 8'd3) && (rd_n != 8'd0) && (rd_n <= REC_MAX_COUNT)
                      && ({1'b0, first} + {9'd0, rd_n} <= NET_N);

// Trace: the last run has min(run_len, TR_STEPS) steps in the trace memory.
localparam TR_STEPS     = 10'd512;
localparam TR_MAX_COUNT = 8'd7;                       // 7 steps x N/8 bytes fit in one reply
wire [9:0]  tr_len     = (run_len > {1'b0, TR_STEPS}) ? TR_STEPS : run_len[9:0];
wire        tr_ok      = (len == 8'd3) && (rd_n != 8'd0) && (rd_n <= TR_MAX_COUNT)
                      && ({1'b0, first} + {9'd0, rd_n} <= {7'd0, tr_len});

always @(posedge clk) begin
    status_req <= 1'b0;
    run_req    <= 1'b0;
    rec_req    <= 1'b0;
    wr_req     <= 1'b0;
    rd_req     <= 1'b0;
    if (byte_valid) begin
        case (state)
            S_SYNC: begin
                // Bytes other than the sync byte are ignored.
                if (byte_in == SYNC_BYTE)
                    state <= S_CMD;
            end

            S_CMD: begin
                cmd   <= byte_in;
                sum   <= byte_in;
                state <= S_LEN;
            end

            S_LEN: begin
                len   <= byte_in;
                sum   <= sum + byte_in;
                idx   <= 8'd0;
                state <= (byte_in == 8'd0) ? S_CSUM : S_DATA;
            end

            S_DATA: begin
                buf_mem[idx] <= byte_in;
                sum <= sum + byte_in;
                idx <= idx + 8'd1;
                if (idx == len - 8'd1)
                    state <= S_CSUM;
            end

            S_CSUM: begin
                state <= S_SYNC;
                if (byte_in != sum) begin
                    err_count <= err_count + 8'd1;          // checksum mismatch
                end else if (cmd == CMD_WRITE_PARAM && len == PARAM_LEN && !busy
                             && buf_mem[6] <= 8'd15 && buf_mem[7] <= 8'd15 && buf_mem[8] <= 8'd7) begin
                    theta    <= {buf_mem[1], buf_mem[0]};
                    v_reset  <= {buf_mem[3], buf_mem[2]};
                    v_rest   <= {buf_mem[5], buf_mem[4]};
                    k_m      <= buf_mem[6][3:0];
                    k_s      <= buf_mem[7][3:0];
                    refrac   <= buf_mem[8][2:0];
                    ok_count <= ok_count + 8'd1;
                end else if (cmd == CMD_WRITE_WEIGHTS && wr_w_ok && !busy) begin
                    wr_req      <= 1'b1;
                    wr_is_input <= 1'b0;
                    wr_start    <= first;
                    wr_count    <= wr_w_bytes;
                    ok_count    <= ok_count + 8'd1;
                end else if (cmd == CMD_SET_INPUT && wr_i_ok && !busy) begin
                    wr_req      <= 1'b1;
                    wr_is_input <= 1'b1;
                    wr_start    <= first;
                    wr_count    <= wr_i_values;
                    ok_count    <= ok_count + 8'd1;
                end else if (cmd == CMD_READ_STATUS && len == 8'd0 && !busy) begin
                    ok_count   <= ok_count + 8'd1;
                    status_req <= 1'b1;
                end else if (cmd == CMD_RUN && len == RUN_LEN && run_ok && !busy) begin
                    run_input <= {buf_mem[1], buf_mem[0]};
                    run_len   <= run_steps[10:0];
                    run_req   <= 1'b1;
                    ok_count  <= ok_count + 8'd1;
                end else if (cmd == CMD_READ_RECORD && len == REC_LEN && rec_ok && !busy) begin
                    rec_start <= rec_first[9:0];
                    rec_count <= rec_n[6:0];
                    rec_req   <= 1'b1;
                    ok_count  <= ok_count + 8'd1;
                end else if ((cmd == CMD_READ_COUNTS || cmd == CMD_READ_SNAPSHOT) && rd_ok && !busy) begin
                    rd_req      <= 1'b1;
                    rd_is_snap  <= (cmd == CMD_READ_SNAPSHOT);
                    rd_is_trace <= 1'b0;
                    rd_start    <= first;
                    rd_count    <= rd_n[6:0];
                    ok_count    <= ok_count + 8'd1;
                end else if (cmd == CMD_READ_TRACE && tr_ok && !busy) begin
                    rd_req      <= 1'b1;
                    rd_is_snap  <= 1'b0;
                    rd_is_trace <= 1'b1;
                    rd_start    <= first;
                    rd_count    <= rd_n[6:0];
                    ok_count    <= ok_count + 8'd1;
                end else begin
                    err_count <= err_count + 8'd1;          // unknown command or bad value
                end
            end

            default: state <= S_SYNC;
        endcase
    end
end

endmodule
