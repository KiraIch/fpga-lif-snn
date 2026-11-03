// Icarus testbench for rtl/network_top.v at the pin level.
// Sends the frames in sim/nt_stream.mem bit by bit on rx and checks every byte
// sent on tx against sim/nt_expect.mem. Each frame is sent only after the board
// has finished the previous one (reply sent, copy done, network done), as the
// host does. Run from the sim/ directory after host/gen_net_top_vectors.py N.
`timescale 1ns/100ps
module tb_network_top;

parameter N = 16;             // must match the N used by gen_net_top_vectors.py
localparam BIT_CLKS = 234;    // 27 MHz / 115200, as in uart_tx and uart_rx

reg  clk = 1'b0;
reg  rx  = 1'b1;
wire tx;
wire [5:0] led;

always #18.5 clk = ~clk;

network_top #(.N(N)) dut (
    .clk (clk),
    .rx  (rx),
    .tx  (tx),
    .led (led)
);

reg [7:0]  stream   [0:131071];   // N = 256 sends about 70 KB
reg [15:0] frame_len[0:4095];
reg [7:0]  expect_b [0:16383];
reg [15:0] meta     [0:2];
integer    nframes, nreply, f, b, pos, rcount, errors;
reg [7:0]  r;
reg        s_ok;

// One 8N1 frame on rx.
task send_byte(input [7:0] bb);
    integer k;
    begin
        rx = 1'b0;
        repeat (BIT_CLKS) @(posedge clk);
        for (k = 0; k < 8; k = k + 1) begin
            rx = bb[k];
            repeat (BIT_CLKS) @(posedge clk);
        end
        rx = 1'b1;
        repeat (BIT_CLKS) @(posedge clk);
    end
endtask

// One 8N1 frame sampled on tx at bit centres.
task recv_byte(output [7:0] bb, output stop_ok);
    integer k;
    begin
        @(negedge tx);
        repeat (BIT_CLKS / 2) @(posedge clk);
        for (k = 0; k < 8; k = k + 1) begin
            repeat (BIT_CLKS) @(posedge clk);
            bb[k] = tx;
        end
        repeat (BIT_CLKS) @(posedge clk);
        stop_ok = tx;
    end
endtask

initial begin
    $readmemh("nt_stream.mem", stream);
    $readmemh("nt_frames.mem", frame_len);
    $readmemh("nt_expect.mem", expect_b);
    $readmemh("nt_meta.mem", meta);
    nframes = meta[1];
    nreply  = meta[2];
    if (meta[0] != N) begin
        $display("FAIL: vectors are for N=%0d, testbench is N=%0d", meta[0], N);
        $finish;
    end

    rcount = 0;
    errors = 0;
    pos    = 0;

    fork
        begin : sender
            for (f = 0; f < nframes; f = f + 1) begin
                for (b = 0; b < frame_len[f]; b = b + 1)
                    send_byte(stream[pos + b]);
                pos = pos + frame_len[f];
                // the decoder sees the last byte during its stop bit; wait for it
                repeat (3 * 10 * BIT_CLKS) @(posedge clk);
                while (dut.reply_busy || dut.run_busy || dut.copy_busy)
                    @(posedge clk);
            end
        end

        begin : receiver
            while (rcount < nreply) begin
                recv_byte(r, s_ok);
                if (!s_ok) begin
                    errors = errors + 1;
                    $display("FAIL: stop bit low at reply byte %0d", rcount);
                end
                if (r !== expect_b[rcount]) begin
                    errors = errors + 1;
                    if (errors <= 10)
                        $display("FAIL: reply byte %0d expected %h got %h", rcount, expect_b[rcount], r);
                end
                rcount = rcount + 1;
            end
        end
    join

    if (errors == 0)
        $display("PASS: %0d frames, %0d reply bytes match the model", nframes, nreply);
    else
        $display("FAIL: %0d mismatches in %0d reply bytes", errors, nreply);
    $finish;
end

initial begin
    #20000000000;                 // 20 s of sim time: N = 256 needs about 6 s
    $display("FAIL: timeout after %0d of %0d reply bytes", rcount, nreply);
    $finish;
end

endmodule
