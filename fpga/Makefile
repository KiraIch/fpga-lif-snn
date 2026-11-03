# Build flow for Tang Nano 20K (GW2AR-18). Run inside WSL with the OSS CAD Suite
# environment loaded: source ~/oss-cad-suite/environment
#
#   make                          build the default design (TOP=blink)
#   make TOP=bsram_test           build another design: rtl/$(TOP).v + fpga/$(TOP).cst
#   make flash TOP=<name>         load build/<name>.fs into SRAM (volatile, lost on power-off)
#   make sim-bsram                run the Icarus testbench for bsram_test

TOP    ?= blink
CST    := $(TOP).cst
DEVICE := GW2AR-LV18QN88C8/I7
FAMILY := GW2A-18C
BOARD  := tangnano20k
OUT    := build

# Extra RTL a top level needs besides rtl/$(TOP).v.
uart_echo_deps := ../rtl/uart_rx.v ../rtl/uart_tx.v
cmd_test_deps  := ../rtl/uart_rx.v ../rtl/uart_tx.v ../rtl/cmd_decoder.v
neuron_top_deps := ../rtl/uart_rx.v ../rtl/uart_tx.v ../rtl/cmd_decoder.v ../rtl/lif_core.v
network_top_deps := ../rtl/uart_rx.v ../rtl/uart_tx.v ../rtl/cmd_decoder.v ../rtl/lif_core.v ../rtl/network.v
SRC := ../rtl/$(TOP).v $($(TOP)_deps)

.PHONY: bitstream flash sim-bsram clean

bitstream: $(OUT)/$(TOP).fs

$(OUT)/$(TOP).json: $(SRC)
	mkdir -p $(OUT)
	yosys -q -p "read_verilog $(SRC); synth_gowin -top $(TOP) -json $@"

$(OUT)/$(TOP)_pnr.json: $(OUT)/$(TOP).json $(CST)
	nextpnr-himbaechel --device $(DEVICE) --vopt family=$(FAMILY) --vopt cst=$(CST) --json $< --write $@ --freq 27

$(OUT)/$(TOP).fs: $(OUT)/$(TOP)_pnr.json
	gowin_pack -d $(FAMILY) -o $@ $<

flash: $(OUT)/$(TOP).fs
	openFPGALoader -b $(BOARD) $<

sim-bsram:
	mkdir -p $(OUT)
	iverilog -o $(OUT)/tb_bsram.vvp ../rtl/bsram_test.v ../sim/tb_bsram.v
	vvp $(OUT)/tb_bsram.vvp

clean:
	rm -rf $(OUT)
