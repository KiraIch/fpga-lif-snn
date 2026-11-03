// Board test for the PC-to-board command link.
//
//   uart_rx -> cmd_decoder -> reply builder -> uart_tx
//
// The decoder accepts WRITE_PARAM and READ_STATUS frames (host/protocol.py).
// On READ_STATUS the board replies with a STATUS frame (cmd 0x86) that carries
// the current parameters and the ok/err counters, so the PC can check them.
// The six LEDs show the low three bits of ok_count (led[2:0]) and err_count
// (led[5:3]); LEDs are active low.
module cmd_test (
    input  wire       clk,
    input  wire       rx,
    output wire       tx,
    output wire [5:0] led
);

localparam CLK_FRE     = 27000000;
localparam BAUD        = 115200;
localparam REPLY_CMD   = 8'h86;   // READ_STATUS | RESPONSE_FLAG
localparam REPLY_LEN   = 8'd11;   // theta, v_reset, v_rest (6 bytes), k_m, k_s, refrac, ok, err
localparam REPLY_BYTES = 15;      // sync, cmd, len, 11 payload bytes, checksum

wire [7:0]        rx_data;
wire              rx_valid;
wire              reply_busy;   // set below: high while a status reply is being sent
wire              sending_w;
assign reply_busy = sending_w;
wire signed [15:0] theta, v_reset, v_rest;
wire [3:0]        k_m, k_s;
wire [2:0]        refrac;
wire [7:0]        ok_count, err_count;
wire              status_req;

uart_rx #(.CLK_FRE(CLK_FRE), .BAUD(BAUD)) u_rx (
    .clk        (clk),
    .rx         (rx),
    .data       (rx_data),
    .data_valid (rx_valid)
);

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
    .buf_addr   (8'd0)
);

// Checksum of the reply, computed from the same values that are copied below.
wire [7:0] reply_sum = REPLY_CMD + REPLY_LEN
                     + theta[7:0] + theta[15:8]
                     + v_reset[7:0] + v_reset[15:8]
                     + v_rest[7:0] + v_rest[15:8]
                     + {4'd0, k_m} + {4'd0, k_s} + {5'd0, refrac}
                     + ok_count + err_count;

reg [7:0] reply [0:REPLY_BYTES-1];
reg [3:0] rsp_idx  = 4'd0;
reg       sending  = 1'b0;
assign    sending_w = sending;
reg       tx_start = 1'b0;
reg [7:0] tx_data  = 8'd0;
wire      tx_busy;

// Copy the reply when a READ_STATUS arrives, then send one byte whenever the
// transmitter is idle. tx_start is a one-cycle pulse, as uart_tx expects.
always @(posedge clk) begin
    tx_start <= 1'b0;
    if (status_req) begin
        reply[0]  <= 8'hA5;
        reply[1]  <= REPLY_CMD;
        reply[2]  <= REPLY_LEN;
        reply[3]  <= theta[7:0];
        reply[4]  <= theta[15:8];
        reply[5]  <= v_reset[7:0];
        reply[6]  <= v_reset[15:8];
        reply[7]  <= v_rest[7:0];
        reply[8]  <= v_rest[15:8];
        reply[9]  <= {4'd0, k_m};
        reply[10] <= {4'd0, k_s};
        reply[11] <= {5'd0, refrac};
        reply[12] <= ok_count;
        reply[13] <= err_count;
        reply[14] <= reply_sum;
        sending   <= 1'b1;
        rsp_idx   <= 4'd0;
    end else if (sending && !tx_busy && !tx_start) begin
        tx_data  <= reply[rsp_idx];
        tx_start <= 1'b1;
        rsp_idx  <= rsp_idx + 4'd1;
        if (rsp_idx == REPLY_BYTES - 1)
            sending <= 1'b0;
    end
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
