module cpu_v01_fpga_top_tb;
  logic board_clk_i;
  logic board_reset_n_i;
  logic debug_halt_request_i;
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

  cpu_v01_fpga_top dut (
    .board_clk_i(board_clk_i),
    .board_reset_n_i(board_reset_n_i),
    .debug_halt_request_i(debug_halt_request_i),
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
    board_reset_n_i = 1'b0;
    repeat (2) @(posedge board_clk_i);
    if (status_reset_observed_o || pass_led_o) begin
      $fatal(1, "FPGA top wrapper reset synchronization failed");
    end

    board_reset_n_i = 1'b1;
    repeat (5) @(posedge board_clk_i);

    if (!status_reset_observed_o || !status_core_idle_o || !pass_led_o) begin
      $fatal(1, "FPGA top wrapper did not expose reset-idle status");
    end
    if (fail_led_o || status_fault_valid_o || status_fault_code_o != 16'd0) begin
      $fatal(1, "FPGA top wrapper reported an unexpected fault");
    end
    if (status_retire_valid_o || status_retire_count_o != 32'd0 || heartbeat_led_o) begin
      $fatal(1, "FPGA top wrapper should not retire before BRAM adapters");
    end
    if (status_core_port_activity_o) begin
      $fatal(1, "FPGA top wrapper should stay memory idle before BRAM adapters");
    end
    if (!debug_pcc_valid_o ||
        debug_pcc_cursor_low_o != 32'h0000_1000 ||
        debug_pcc_permissions_o != 8'd4 ||
        debug_sr_low_o != 8'hC0) begin
      $fatal(1, "FPGA top wrapper reset debug projection mismatch");
    end

    $finish;
  end
endmodule
