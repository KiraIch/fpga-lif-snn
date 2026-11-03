# cocotb + Icarus Verilog testbench for rtl/uart_tx.v and rtl/uart_rx.v.
# Run from this directory: make

SIM ?= icarus
TOPLEVEL_LANG = verilog

TOPLEVEL = uart_tb_top
MODULE   = test_uart

VERILOG_SOURCES = $(CURDIR)/uart_tb_top.v \
                  $(CURDIR)/../rtl/uart_tx.v \
                  $(CURDIR)/../rtl/uart_rx.v

COMPILE_ARGS += -g2012

include $(shell cocotb-config --makefiles)/Makefile.sim
