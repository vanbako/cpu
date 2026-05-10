module cpu_v01_fpga_top_soc_peripherals_tb;
  logic board_clk_i;
  logic board_reset_n_i;
  logic debug_halt_request_i;
  logic uart_rx_i;
  logic uart_tx_o;
  logic pass_led_o;
  logic fail_led_o;
  logic heartbeat_led_o;
  logic status_reset_observed_o;
  logic status_core_idle_o;
  logic status_retire_valid_o;
  logic status_fault_valid_o;
  logic status_core_port_activity_o;
  logic [15:0] status_fault_code_o;
  logic [31:0] status_retire_count_o;
  logic debug_pcc_valid_o;
  logic [31:0] debug_pcc_cursor_low_o;
  logic [7:0] debug_pcc_permissions_o;
  logic [7:0] debug_sr_low_o;

  cpu_v01_fpga_top #(
    .ENABLE_FETCH(1'b0),
    .UART_STATUS_CLOCK_HZ(10),
    .UART_STATUS_BAUD(10),
    .UART_STATUS_INTERVAL_CYCLES(2)
  ) dut (
    .board_clk_i(board_clk_i),
    .board_reset_n_i(board_reset_n_i),
    .debug_halt_request_i(debug_halt_request_i),
    .uart_rx_i(uart_rx_i),
    .uart_tx_o(uart_tx_o),
    .pass_led_o(pass_led_o),
    .fail_led_o(fail_led_o),
    .heartbeat_led_o(heartbeat_led_o),
    .status_reset_observed_o(status_reset_observed_o),
    .status_core_idle_o(status_core_idle_o),
    .status_retire_valid_o(status_retire_valid_o),
    .status_fault_valid_o(status_fault_valid_o),
    .status_core_port_activity_o(status_core_port_activity_o),
    .status_fault_code_o(status_fault_code_o),
    .status_retire_count_o(status_retire_count_o),
    .debug_pcc_valid_o(debug_pcc_valid_o),
    .debug_pcc_cursor_low_o(debug_pcc_cursor_low_o),
    .debug_pcc_permissions_o(debug_pcc_permissions_o),
    .debug_sr_low_o(debug_sr_low_o)
  );

  initial begin
    board_clk_i = 1'b0;
    forever #5 board_clk_i = ~board_clk_i;
  end

  initial begin
    debug_halt_request_i = 1'b0;
    uart_rx_i = 1'b1;
    board_reset_n_i = 1'b0;
    repeat (2) @(posedge board_clk_i);
    board_reset_n_i = 1'b1;
    repeat (6) @(posedge board_clk_i);
    #1;

    if (dut.firmware_uart.uart_rx_i !== uart_rx_i) begin
      $fatal(1, "FPGA SoC top peripherals did not wire firmware UART RX");
    end
    if (uart_tx_o !== (dut.uart_mmio_tx & dut.status_uart_tx)) begin
      $fatal(1, "FPGA SoC top peripherals UART TX mux policy mismatch");
    end
    if (dut.timer_interrupt_pending !== dut.timer_compare_irq) begin
      $fatal(1, "FPGA SoC top peripherals did not route timer interrupt pending");
    end
    if (dut.external_interrupt_pending !== |(dut.irq_pending_enabled & 16'h000B)) begin
      $fatal(1, "FPGA SoC top peripherals external interrupt aggregate mismatch");
    end
    if (pass_led_o !== ((dut.pass_sticky_q && !dut.fault_sticky_q) || dut.gpio_pass_led)) begin
      $fatal(1, "FPGA SoC top peripherals GPIO pass LED mux mismatch");
    end
    if (fail_led_o !== (dut.fault_sticky_q || dut.gpio_fail_led)) begin
      $fatal(1, "FPGA SoC top peripherals GPIO fail LED mux mismatch");
    end
    if (heartbeat_led_o !== (dut.debug_retire_sequence[0] || dut.gpio_heartbeat_led)) begin
      $fatal(1, "FPGA SoC top peripherals GPIO heartbeat LED mux mismatch");
    end
    if (status_fault_code_o != 16'd0 || status_retire_count_o != 32'd0) begin
      $fatal(1, "FPGA SoC top peripherals reset-idle status projection changed");
    end

    $finish;
  end

  // verilator lint_off UNUSEDSIGNAL
  wire logic unused_soc_peripheral_outputs = &{
    status_reset_observed_o,
    status_core_idle_o,
    status_retire_valid_o,
    status_fault_valid_o,
    status_core_port_activity_o,
    debug_pcc_valid_o,
    debug_pcc_cursor_low_o,
    debug_pcc_permissions_o,
    debug_sr_low_o
  };
  // verilator lint_on UNUSEDSIGNAL
endmodule
