// Icarus testbench for rtl/cmd_test.v at the pin level.
// Sends the frames in sim/top_stream.mem as serial bits on rx, samples the
// reply on tx, and compares it byte by byte with sim/top_expect.mem.
// Run from the sim/ directory after host/gen_cmd_vectors.py.
`timescale 1ns/100ps
module tb_cmd_test;

localparam BIT_CLKS = 234;   // 27 MHz / 115200, as in uart_tx and uart_rx

reg  clk = 1'b0;
reg  rx  = 1'b1;
wire tx;
wire [5:0] led;

always #18.5 clk = ~clk;

cmd_test dut (
    .clk (clk),
    .rx  (rx),
    .tx  (tx),
    .led (led)
);

reg [7:0]  stream [0:4095];
reg [7:0]  reply  [0:31];
integer    n_in;
integer    n_out;
integer    i_send;
integer    i_recv;
integer    errors = 0;
reg [7:0]  r;
reg        s_ok;

// One 8N1 frame on rx.
task send_byte(input [7:0] b);
    integer k;
    begin
        rx = 1'b0;
        repeat (BIT_CLKS) @(posedge clk);
        for (k = 0; k < 8; k = k + 1) begin
            rx = b[k];
            repeat (BIT_CLKS) @(posedge clk);
        end
        rx = 1'b1;
        repeat (BIT_CLKS) @(posedge clk);
    end
endtask

// One 8N1 frame sampled on tx at bit centres.
task recv_byte(output [7:0] b, output stop_ok);
    integer k;
    begin
        @(negedge tx);
        repeat (BIT_CLKS / 2) @(posedge clk);
        for (k = 0; k < 8; k = k + 1) begin
            repeat (BIT_CLKS) @(posedge clk);
            b[k] = tx;
        end
        repeat (BIT_CLKS) @(posedge clk);
        stop_ok = tx;
    end
endtask

initial begin
    $readmemh("top_stream.mem", stream);
    $readmemh("top_expect.mem", reply);
    n_in  = 17;          // WRITE_PARAM (14 bytes) + READ_STATUS (3 bytes)
    n_out = 15;          // STATUS reply: sync, cmd, len, 11 payload, checksum

    fork
        begin
            for (i_send = 0; i_send < n_in; i_send = i_send + 1)
                send_byte(stream[i_send]);
        end
        begin
            for (i_recv = 0; i_recv < n_out; i_recv = i_recv + 1) begin
                recv_byte(r, s_ok);
                if (!s_ok) begin
                    errors = errors + 1;
                    $display("FAIL: stop bit low at reply byte %0d", i_recv);
                end
                if (r !== reply[i_recv]) begin
                    errors = errors + 1;
                    $display("FAIL: reply byte %0d expected %h got %h", i_recv, reply[i_recv], r);
                end
            end
        end
    join

    if (errors == 0)
        $display("PASS: %0d-byte status reply matches", n_out);
    else
        $display("FAIL: %0d mismatches", errors);
    $finish;
end

initial begin
    #20000000;
    $display("FAIL: timeout");
    $finish;
end

endmodule
