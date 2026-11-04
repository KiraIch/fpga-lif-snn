// Icarus testbench for rtl/cmd_decoder.v with busy = 1.
// While busy, every command must be refused: counted as an error, no pulse on any
// request output, and no parameter change. After busy drops, WRITE_PARAM and RUN
// must be accepted again.
// Run from the sim/ directory: make decoder_busy
`timescale 1ns/100ps
module tb_decoder_busy;

reg         clk = 1'b0;
reg  [7:0]  byte_in = 8'd0;
reg         byte_valid = 1'b0;
reg         busy = 1'b1;

wire signed [15:0] theta, v_reset, v_rest;
wire        [3:0]  k_m, k_s;
wire        [2:0]  refrac;
wire        [7:0]  ok_count, err_count;
wire               status_req, run_req, rec_req, wr_req, rd_req;

always #18.5 clk = ~clk;

cmd_decoder dut (
    .clk        (clk),
    .byte_in    (byte_in),
    .byte_valid (byte_valid),
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
    .rec_req    (rec_req),
    .wr_req     (wr_req),
    .rd_req     (rd_req),
    .buf_addr   (8'd0)
);

reg [7:0]  pay [0:15];     // payload of the frame being sent
integer    errors = 0;
integer    busy_pulses = 0;
integer    run_pulses = 0;
integer    k;
reg [7:0]  err0, ok0, ok1;
reg [15:0] theta0;

// Any request pulse while busy is a failure. A pulse is seen one clock after it is set.
always @(posedge clk) begin
    if (run_req)
        run_pulses = run_pulses + 1;
    if (busy && (status_req || run_req || rec_req || wr_req || rd_req)) begin
        busy_pulses = busy_pulses + 1;
        $display("FAIL: request pulse while busy at %0t (status %b run %b rec %b wr %b rd %b)",
                 $time, status_req, run_req, rec_req, wr_req, rd_req);
    end
end

// One byte per clock, with idle clocks between bytes (as in tb_cmd_decoder).
task send_byte(input [7:0] b);
    begin
        @(posedge clk);
        byte_in    <= b;
        byte_valid <= 1'b1;
        @(posedge clk);
        byte_valid <= 1'b0;
        repeat (2) @(posedge clk);
    end
endtask

// Frame: [A5][cmd][len][data ... len bytes][checksum = (cmd + len + sum(data)) mod 256].
// The payload is taken from pay[0 .. len-1].
task send_frame(input [7:0] cmd, input [7:0] len);
    reg [7:0] sum;
    integer   j;
    begin
        sum = cmd + len;
        for (j = 0; j < len; j = j + 1)
            sum = sum + pay[j];
        send_byte(8'hA5);
        send_byte(cmd);
        send_byte(len);
        for (j = 0; j < len; j = j + 1)
            send_byte(pay[j]);
        send_byte(sum);
        repeat (4) @(posedge clk);
    end
endtask

task set_param_payload;     // theta 384, v_reset 0, v_rest 0, k_m 4, k_s 3, refrac 2
    begin
        pay[0] = 8'h80; pay[1] = 8'h01;
        pay[2] = 8'h00; pay[3] = 8'h00;
        pay[4] = 8'h00; pay[5] = 8'h00;
        pay[6] = 8'd4;  pay[7] = 8'd3;  pay[8] = 8'd2;
    end
endtask

task set_run_payload;       // input 0, steps 10
    begin
        pay[0] = 8'h00; pay[1] = 8'h00;
        pay[2] = 8'd10; pay[3] = 8'h00;
    end
endtask

task set_block_payload;     // start 0, count 1 (READ_COUNTS, READ_SNAPSHOT, READ_RECORD, READ_TRACE)
    begin
        pay[0] = 8'h00; pay[1] = 8'h00;
        pay[2] = 8'd1;
    end
endtask

initial begin
    repeat (5) @(posedge clk);
    theta0 = theta;
    err0   = err_count;
    ok0    = ok_count;

    // ---- busy = 1: every command is refused ----
    set_param_payload;
    send_frame(8'h01, 8'd9);                        // WRITE_PARAM
    pay[0] = 8'd0; pay[1] = 8'd0; pay[2] = 8'd5;
    send_frame(8'h02, 8'd3);                        // WRITE_WEIGHTS: start 0, 1 weight
    pay[0] = 8'd0; pay[1] = 8'd0; pay[2] = 8'd0; pay[3] = 8'd1;
    send_frame(8'h03, 8'd4);                        // SET_INPUT: start 0, 1 value (256)
    set_run_payload;
    send_frame(8'h04, 8'd4);                        // RUN: input 0, steps 10
    send_frame(8'h06, 8'd0);                        // READ_STATUS
    set_block_payload;
    send_frame(8'h07, 8'd3);                        // READ_COUNTS
    send_frame(8'h08, 8'd3);                        // READ_SNAPSHOT
    send_frame(8'h05, 8'd3);                        // READ_RECORD
    send_frame(8'h09, 8'd3);                        // READ_TRACE
    repeat (20) @(posedge clk);

    if (err_count !== err0 + 8'd9) begin
        errors = errors + 1;
        $display("FAIL: err_count %0d, want %0d (+9 refused frames)", err_count, err0 + 8'd9);
    end
    if (ok_count !== ok0) begin
        errors = errors + 1;
        $display("FAIL: ok_count %0d, want unchanged %0d while busy", ok_count, ok0);
    end
    if (theta !== theta0) begin
        errors = errors + 1;
        $display("FAIL: theta changed to %0d while busy", theta);
    end
    if (busy_pulses != 0) begin
        errors = errors + busy_pulses;
    end

    // ---- busy = 0: WRITE_PARAM and RUN are accepted ----
    @(negedge clk);
    busy = 1'b0;
    run_pulses = 0;
    ok1 = ok_count;
    set_param_payload;
    send_frame(8'h01, 8'd9);                        // WRITE_PARAM
    set_run_payload;
    send_frame(8'h04, 8'd4);                        // RUN: steps 10
    repeat (20) @(posedge clk);

    if (ok_count !== ok1 + 8'd2) begin
        errors = errors + 1;
        $display("FAIL: ok_count %0d, want %0d (WRITE_PARAM and RUN accepted)", ok_count, ok1 + 8'd2);
    end
    if (theta !== 16'd384) begin
        errors = errors + 1;
        $display("FAIL: theta %0d after WRITE_PARAM, want 384", theta);
    end
    if (run_pulses != 1) begin
        errors = errors + 1;
        $display("FAIL: run_req pulsed %0d times after RUN, want 1", run_pulses);
    end

    if (errors == 0)
        $display("PASS: 9 commands refused while busy (err +9, no pulse, theta unchanged); WRITE_PARAM and RUN accepted after busy");
    else
        $display("FAIL: %0d mismatches", errors);
    $finish;
end

initial begin
    #2000000;
    $display("FAIL: timeout");
    $finish;
end

endmodule
