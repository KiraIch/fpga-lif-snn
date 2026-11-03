// Icarus testbench for rtl/uart_echo.v.
// Sends four bytes back to back (no gap between frames), then checks that
// tx returns each byte unchanged, in order, with a valid stop bit.
`timescale 1ns/100ps
module tb_uart_echo;

localparam BIT_CLKS = 234;   // 27 MHz / 115200, as in uart_tx and uart_rx

reg  clk = 1'b0;
reg  rx  = 1'b1;
wire tx;

always #18.5 clk = ~clk;

uart_echo dut (
    .clk (clk),
    .rx  (rx),
    .tx  (tx)
);

reg [7:0] stimulus [0:3];
reg [7:0] got;
integer   errors = 0;
integer   n_ok   = 0;
integer   i_send;
integer   i_recv;

initial begin
    stimulus[0] = 8'h55;
    stimulus[1] = 8'hA3;
    stimulus[2] = 8'h00;
    stimulus[3] = 8'hFF;
end

// Drive one 8N1 frame on rx; the stop bit is followed directly by the next frame.
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

// Sample one 8N1 frame on tx at bit centres.
task recv_byte(output [7:0] b, output stop_ok);
    integer k;
    begin
        @(negedge tx);
        repeat (BIT_CLKS / 2) @(posedge clk);   // centre of start bit
        for (k = 0; k < 8; k = k + 1) begin
            repeat (BIT_CLKS) @(posedge clk);
            b[k] = tx;
        end
        repeat (BIT_CLKS) @(posedge clk);       // centre of stop bit
        stop_ok = tx;
    end
endtask

reg [7:0] r;
reg       s_ok;

initial begin
    fork
        begin
            for (i_send = 0; i_send < 4; i_send = i_send + 1)
                send_byte(stimulus[i_send]);
        end
        begin
            for (i_recv = 0; i_recv < 4; i_recv = i_recv + 1) begin
                recv_byte(r, s_ok);
                if (!s_ok) begin
                    errors = errors + 1;
                    $display("FAIL: stop bit low for frame %0d", i_recv);
                end
                if (r !== stimulus[i_recv]) begin
                    errors = errors + 1;
                    $display("FAIL: frame %0d sent %h got %h", i_recv, stimulus[i_recv], r);
                end else begin
                    n_ok = n_ok + 1;
                end
            end
        end
    join

    if (errors == 0 && n_ok == 4)
        $display("PASS: %0d/4 bytes echoed", n_ok);
    else
        $display("FAIL: %0d/4 bytes echoed, %0d errors", n_ok, errors);
    $finish;
end

// Watchdog: the full run needs about 9400 clocks (about 350 us).
initial begin
    #1000000;
    $display("FAIL: timeout");
    $finish;
end

endmodule
