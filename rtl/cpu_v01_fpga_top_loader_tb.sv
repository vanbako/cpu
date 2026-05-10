module cpu_v01_fpga_top_loader_tb;
  import cpu_v01_pkg::*;

  localparam addr_t DATA_RAM_BASE = 48'h0000_0001_0000;
  localparam addr_t ROM_BASE = 48'h0000_0000_1000;

  logic board_clk_i;
  logic board_reset_n_i;
  logic debug_halt_request_i;
  logic uart_rx_i;
  logic loader_req_valid_i;
  logic loader_req_ready_o;
  logic loader_req_write_i;
  addr_t loader_req_addr_i;
  cell_t loader_req_wdata_i;
  logic loader_req_tag_i;
  logic loader_uart_tx_i;
  logic uart_tx_o;
  logic loader_status_valid_o;
  logic [15:0] loader_status_code_o;
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
    .loader_req_valid_i(loader_req_valid_i),
    .loader_req_ready_o(loader_req_ready_o),
    .loader_req_write_i(loader_req_write_i),
    .loader_req_addr_i(loader_req_addr_i),
    .loader_req_wdata_i(loader_req_wdata_i),
    .loader_req_tag_i(loader_req_tag_i),
    .loader_uart_tx_i(loader_uart_tx_i),
    .uart_tx_o(uart_tx_o),
    .loader_status_valid_o(loader_status_valid_o),
    .loader_status_code_o(loader_status_code_o),
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

  task automatic clear_loader_request();
    loader_req_valid_i = 1'b0;
    loader_req_write_i = 1'b0;
    loader_req_addr_i = '0;
    loader_req_wdata_i = '0;
    loader_req_tag_i = 1'b0;
  endtask

  task automatic send_loader_request(
      input addr_t addr,
      input cell_t wdata,
      input logic tag,
      input logic write
  );
    loader_req_addr_i = addr;
    loader_req_wdata_i = wdata;
    loader_req_tag_i = tag;
    loader_req_write_i = write;
    loader_req_valid_i = 1'b1;
    #1;
    if (!loader_req_ready_o) begin
      $fatal(1, "FPGA SoC loader handoff request was not ready");
    end
    @(posedge board_clk_i);
    #1;
    clear_loader_request();
    repeat (2) @(posedge board_clk_i);
    #1;
  endtask

  initial begin
    debug_halt_request_i = 1'b0;
    uart_rx_i = 1'b1;
    loader_uart_tx_i = 1'b1;
    clear_loader_request();
    board_reset_n_i = 1'b0;
    repeat (2) @(posedge board_clk_i);
    board_reset_n_i = 1'b1;
    repeat (4) @(posedge board_clk_i);
    #1;

    dut.tag_ram.tag_q[4] = 1'b1;
    send_loader_request(DATA_RAM_BASE + 48'd4, 24'h123456, 1'b0, 1'b1);
    if (!loader_status_valid_o || loader_status_code_o != 16'h0000) begin
      $fatal(1, "FPGA SoC loader handoff did not report LOAD OK");
    end
    if (dut.data_ram.ram_q[4] != 24'h123456 || dut.tag_ram.tag_q[4] != 1'b0) begin
      $fatal(1, "FPGA SoC loader handoff did not write data_ram and clear tag_ram");
    end

    send_loader_request(ROM_BASE, 24'h654321, 1'b0, 1'b1);
    if (!loader_status_valid_o || loader_status_code_o != 16'h2603) begin
      $fatal(1, "FPGA SoC loader handoff did not reject instruction_rom target");
    end
    if (!status_fault_valid_o || status_fault_code_o != 16'h2603) begin
      $fatal(1, "FPGA SoC loader handoff did not expose debug/status failure code");
    end

    send_loader_request(DATA_RAM_BASE + 48'd5, 24'h0BADF0, 1'b1, 1'b1);
    if (!loader_status_valid_o || loader_status_code_o != 16'h2605) begin
      $fatal(1, "FPGA SoC loader handoff did not reject tag-bearing traffic");
    end
    if (dut.data_ram.ram_q[5] == 24'h0BADF0) begin
      $fatal(1, "FPGA SoC loader handoff wrote data for a tag-policy rejection");
    end

    send_loader_request(DATA_RAM_BASE + 48'd6, 24'h0D00D0, 1'b0, 1'b0);
    if (!loader_status_valid_o || loader_status_code_o != 16'h2607) begin
      $fatal(1, "FPGA SoC loader handoff did not reject malformed non-write traffic");
    end

    loader_uart_tx_i = 1'b0;
    #1;
    if (uart_tx_o !== 1'b0) begin
      $fatal(1, "FPGA SoC loader handoff did not arbitrate loader UART TX");
    end
    loader_uart_tx_i = 1'b1;
    #1;

    $finish;
  end

  // verilator lint_off UNUSEDSIGNAL
  wire logic unused_loader_tb_outputs = &{
    pass_led_o,
    fail_led_o,
    heartbeat_led_o,
    status_reset_observed_o,
    status_core_idle_o,
    status_retire_valid_o,
    status_core_port_activity_o,
    status_retire_count_o,
    debug_pcc_valid_o,
    debug_pcc_cursor_low_o,
    debug_pcc_permissions_o,
    debug_sr_low_o
  };
  // verilator lint_on UNUSEDSIGNAL
endmodule
