// BSRAM self-test for Tang Nano 20K.
// Writes a 256 x 16 pattern, reads every word back, and reports on the LEDs.
//
// LED layout (LEDs are active low on this board, so the output is inverted):
//   led[0]   done
//   led[1]   pass   (done and no mismatches)
//   led[2]   fail   (done and at least one mismatch)
//   led[5:3] mismatch count, low 3 bits
module bsram_test (
    input  wire       clk,
    output wire [5:0] led
);

localparam DEPTH = 256;

localparam S_WRITE = 2'd0;
localparam S_READ  = 2'd1;
localparam S_DRAIN = 2'd2;
localparam S_DONE  = 2'd3;

function [15:0] pattern(input [7:0] a);
    pattern = {a, ~a} ^ 16'h5AA5;
endfunction

reg [15:0] mem [0:DEPTH-1];

reg [1:0]  state  = S_WRITE;
reg [7:0]  addr   = 8'd0;
reg        done   = 1'b0;

// Synchronous read port: data for rd_idx is valid one cycle after rd_en.
reg [15:0] rdata;
reg [7:0]  rd_idx;
reg        rd_valid = 1'b0;

reg [7:0]  errors = 8'd0;

// Write and read ports are kept in separate blocks.
always @(posedge clk) begin
    if (state == S_WRITE)
        mem[addr] <= pattern(addr);
end

always @(posedge clk) begin
    rd_valid <= (state == S_READ) || (state == S_DRAIN);
    rdata    <= mem[addr];
    rd_idx   <= addr;
end

always @(posedge clk) begin
    if (rd_valid && rdata != pattern(rd_idx))
        errors <= errors + 8'd1;
end

// Control sequence: write 256 words, read 256 words, drain the last read, finish.
always @(posedge clk) begin
    case (state)
        S_WRITE: begin
            if (addr == DEPTH - 1) begin
                addr  <= 8'd0;
                state <= S_READ;
            end else begin
                addr <= addr + 8'd1;
            end
        end
        S_READ: begin
            if (addr == DEPTH - 1) begin
                state <= S_DRAIN;
            end
            addr <= addr + 8'd1;
        end
        S_DRAIN: begin
            state <= S_DONE;
        end
        S_DONE: begin
            done <= 1'b1;
        end
    endcase
end

wire pass = done && (errors == 8'd0);
wire fail = done && (errors != 8'd0);

wire [5:0] status = {errors[2:0], fail, pass, done};

assign led = ~status;

endmodule
