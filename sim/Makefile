# Simulation entry point for the Icarus Verilog testbenches (and the cocotb ones via the
# Makefile.lif / Makefile.uart files). Run in WSL after loading the tools:
#   source ~/oss-cad-suite/environment
#   cd sim && make decoder_busy
#   cd sim && make network_top N=16 T=200     # N must be a power of two, N >= 16
#   cd sim && make all                        # every target; the uart cocotb target takes about 13 minutes
#
# Each Icarus target writes its .vvp and .log into sim_build_iv/ and fails (non-zero exit)
# when the testbench prints FAIL or does not print PASS.
#
# The network and network_top targets overwrite the tracked sim/net_*.mem and sim/nt_*.mem.
# host/board_network_test.py needs the N = 256 version (the board bitstream). Restore it with
# `make network_top N=256` (slow), or with `git checkout -- sim/nt_*.mem`.

N ?= 16
T ?= 200
B := sim_build_iv
IVFLAGS := -g2012

.PHONY: all lif uart bsram decoder decoder_busy cmd_test neuron_top uart_echo network network_top

all: lif uart bsram decoder decoder_busy cmd_test neuron_top uart_echo network network_top

lif:
	$(MAKE) -f Makefile.lif

uart:
	$(MAKE) -f Makefile.uart

bsram:
	mkdir -p $(B)
	iverilog $(IVFLAGS) -s tb_bsram -o $(B)/bsram.vvp ../rtl/bsram_test.v tb_bsram.v
	vvp -n $(B)/bsram.vvp | tee $(B)/bsram.log
	grep -q PASS $(B)/bsram.log && ! grep -q FAIL $(B)/bsram.log

decoder:
	python3 ../host/gen_cmd_vectors.py
	mkdir -p $(B)
	iverilog $(IVFLAGS) -s tb_cmd_decoder -o $(B)/decoder.vvp ../rtl/cmd_decoder.v tb_cmd_decoder.v
	vvp -n $(B)/decoder.vvp | tee $(B)/decoder.log
	grep -q PASS $(B)/decoder.log && ! grep -q FAIL $(B)/decoder.log

decoder_busy:
	mkdir -p $(B)
	iverilog $(IVFLAGS) -s tb_decoder_busy -o $(B)/decoder_busy.vvp ../rtl/cmd_decoder.v tb_decoder_busy.v
	vvp -n $(B)/decoder_busy.vvp | tee $(B)/decoder_busy.log
	grep -q PASS $(B)/decoder_busy.log && ! grep -q FAIL $(B)/decoder_busy.log

cmd_test:
	python3 ../host/gen_cmd_vectors.py
	mkdir -p $(B)
	iverilog $(IVFLAGS) -s tb_cmd_test -o $(B)/cmd_test.vvp ../rtl/uart_rx.v ../rtl/uart_tx.v \
	    ../rtl/cmd_decoder.v ../rtl/cmd_test.v tb_cmd_test.v
	vvp -n $(B)/cmd_test.vvp | tee $(B)/cmd_test.log
	grep -q PASS $(B)/cmd_test.log && ! grep -q FAIL $(B)/cmd_test.log

neuron_top:
	python3 ../host/gen_neuron_vectors.py
	mkdir -p $(B)
	iverilog $(IVFLAGS) -s tb_neuron_top -o $(B)/neuron_top.vvp ../rtl/uart_rx.v ../rtl/uart_tx.v \
	    ../rtl/cmd_decoder.v ../rtl/lif_core.v ../rtl/neuron_top.v tb_neuron_top.v
	vvp -n $(B)/neuron_top.vvp | tee $(B)/neuron_top.log
	grep -q PASS $(B)/neuron_top.log && ! grep -q FAIL $(B)/neuron_top.log

uart_echo:
	mkdir -p $(B)
	iverilog $(IVFLAGS) -s tb_uart_echo -o $(B)/uart_echo.vvp ../rtl/uart_rx.v ../rtl/uart_tx.v \
	    ../rtl/uart_echo.v tb_uart_echo.v
	vvp -n $(B)/uart_echo.vvp | tee $(B)/uart_echo.log
	grep -q PASS $(B)/uart_echo.log && ! grep -q FAIL $(B)/uart_echo.log

network:
	python3 ../host/gen_net_vectors.py $(N)
	mkdir -p $(B)
	iverilog $(IVFLAGS) -s tb_network -P tb_network.N=$(N) -o $(B)/network.vvp \
	    ../rtl/lif_core.v ../rtl/network.v tb_network.v
	vvp -n $(B)/network.vvp | tee $(B)/network.log
	grep -q PASS $(B)/network.log && ! grep -q FAIL $(B)/network.log

network_top:
	python3 ../host/gen_net_top_vectors.py $(N) $(T)
	mkdir -p $(B)
	iverilog $(IVFLAGS) -s tb_network_top -P tb_network_top.N=$(N) -o $(B)/network_top.vvp \
	    ../rtl/uart_rx.v ../rtl/uart_tx.v ../rtl/cmd_decoder.v ../rtl/lif_core.v \
	    ../rtl/network.v ../rtl/network_top.v tb_network_top.v
	vvp -n $(B)/network_top.vvp | tee $(B)/network_top.log
	grep -q PASS $(B)/network_top.log && ! grep -q FAIL $(B)/network_top.log
