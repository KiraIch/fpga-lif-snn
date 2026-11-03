// Icarus testbench for rtl/neuron_top.v at the pin level.
// Sends the frames in sim/neuron_stream.mem as serial bits on rx. After each
// frame, it waits for that frame's reply on tx (if it has one) and compares the
// bytes with sim/neuron_expect.mem. The replies are computed by the Python model
// in host/gen_neuron_vectors.py. Frames are sent one at a time, as the host does.
// Run from the sim/ directory after generating the vectors.
`timescale 1ns/100ps
module tb_neuron_top;

localparam BIT_CLKS = 234;   // 27 MHz / 115200, as in uart_tx and uart_rx

reg  clk = 1'b0;
reg  rx  = 1'b1;
wire tx;
wire [5:0] led;

always #18.5 clk = ~clk;

neuron_top dut (
    .clk (clk),
    .rx  (rx),
    .tx  (tx),
    .led (led)
);

reg [7:0]  stream  [0:4095];
reg [7:0]  exp_mem [0:4095];
reg [15:0] meta    [0:127];   // frame count, then (frame length, reply length) per frame
integer    errors = 0;
integer    n_checked = 0;
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

// One 8N1 frame sampled on tx at bit centres. Waits for the start bit level, so a
// reply that has already begun is still caught.
task recv_byte(output [7:0] b, output stop_ok);
    integer k;
    begin
        wait (tx == 1'b0);
        repeat (BIT_CLKS / 2) @(posedge clk);
        for (k = 0; k < 8; k = k + 1) begin
            repeat (BIT_CLKS) @(posedge clk);
            b[k] = tx;
        end
        repeat (BIT_CLKS) @(posedge clk);
        stop_ok = tx;
    end
endtask

integer f, j, n_frames, flen, rlen;
integer pos = 0;
integer epos = 0;

initial begin
    $readmemh("neuron_stream.mem", stream);
    $readmemh("neuron_expect.mem", exp_mem);
    $readmemh("neuron_meta.mem", meta);
    n_frames = meta[0];

    for (f = 0; f < n_frames; f = f + 1) begin
        flen = meta[1 + 2 * f];
        rlen = meta[2 + 2 * f];

        for (j = 0; j < flen; j = j + 1) begin
            send_byte(stream[pos]);
            pos = pos + 1;
        end

        if (rlen > 0) begin
            for (j = 0; j < rlen; j = j + 1) begin
                recv_byte(r, s_ok);
                n_checked = n_checked + 1;
                if (!s_ok) begin
                    errors = errors + 1;
                    $display("FAIL: stop bit low, frame %0d reply byte %0d", f, j);
                end
                if (r !== exp_mem[epos]) begin
                    errors = errors + 1;
                    if (errors <= 10)
                        $display("FAIL: frame %0d reply byte %0d expected %h got %h", f, j, exp_mem[epos], r);
                end
                epos = epos + 1;
            end
        end else begin
            // No reply: give the board time to finish the run (about 38 us at most).
            repeat (BIT_CLKS * 20) @(posedge clk);
        end
    end

    if (errors == 0)
        $display("PASS: %0d frames, %0d reply bytes match the model", n_frames, n_checked);
    else
        $display("FAIL: %0d mismatches in %0d reply bytes", errors, n_checked);
    $finish;
end

initial begin
    #80000000;
    $display("FAIL: timeout after %0d reply bytes", n_checked);
    $finish;
end

endmodule
