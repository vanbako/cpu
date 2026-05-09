module cpu_v01_fpga_ddr_calibration_gate_tb;
  import cpu_v01_pkg::*;

  logic clk;
  logic rst_n;
  logic calibration_done;
  logic calibration_error;
  logic init_in_progress;
  logic [15:0] controller_error_code;
  logic reset_request;
  logic controller_reset;
  logic cpu_req_valid;
  logic cpu_req_ready;
  logic cpu_req_write;
  addr_t cpu_req_addr;
  cell_t cpu_req_wdata;
  logic [1:0] cpu_req_wstrb;
  logic cpu_rsp_valid;
  logic cpu_rsp_ready;
  cell_t cpu_rsp_rdata;
  fault_packet_t cpu_rsp_fault;
  logic ctrl_req_valid;
  logic ctrl_req_ready;
  logic ctrl_req_write;
  addr_t ctrl_req_addr;
  cell_t ctrl_req_wdata;
  logic [1:0] ctrl_req_wstrb;
  logic ctrl_rsp_valid;
  logic ctrl_rsp_ready;
  cell_t ctrl_rsp_rdata;
  logic ctrl_rsp_error;
  logic status_calibration_done;
  logic status_calibration_error;
  logic status_init_in_progress;
  logic status_controller_ready;
  logic status_access_gate_closed;
  logic status_timeout;
  logic [15:0] status_error_code;
  logic fail_visible;

  cpu_v01_fpga_ddr_calibration_gate #(
    .CALIBRATION_TIMEOUT_CYCLES(4)
  ) dut (
    .clk(clk),
    .rst_n(rst_n),
    .calibration_done_i(calibration_done),
    .calibration_error_i(calibration_error),
    .init_in_progress_i(init_in_progress),
    .controller_error_code_i(controller_error_code),
    .reset_request_i(reset_request),
    .controller_reset_o(controller_reset),
    .cpu_req_valid_i(cpu_req_valid),
    .cpu_req_ready_o(cpu_req_ready),
    .cpu_req_write_i(cpu_req_write),
    .cpu_req_addr_i(cpu_req_addr),
    .cpu_req_wdata_i(cpu_req_wdata),
    .cpu_req_wstrb_i(cpu_req_wstrb),
    .cpu_rsp_valid_o(cpu_rsp_valid),
    .cpu_rsp_ready_i(cpu_rsp_ready),
    .cpu_rsp_rdata_o(cpu_rsp_rdata),
    .cpu_rsp_fault_o(cpu_rsp_fault),
    .ctrl_req_valid_o(ctrl_req_valid),
    .ctrl_req_ready_i(ctrl_req_ready),
    .ctrl_req_write_o(ctrl_req_write),
    .ctrl_req_addr_o(ctrl_req_addr),
    .ctrl_req_wdata_o(ctrl_req_wdata),
    .ctrl_req_wstrb_o(ctrl_req_wstrb),
    .ctrl_rsp_valid_i(ctrl_rsp_valid),
    .ctrl_rsp_ready_o(ctrl_rsp_ready),
    .ctrl_rsp_rdata_i(ctrl_rsp_rdata),
    .ctrl_rsp_error_i(ctrl_rsp_error),
    .status_calibration_done_o(status_calibration_done),
    .status_calibration_error_o(status_calibration_error),
    .status_init_in_progress_o(status_init_in_progress),
    .status_controller_ready_o(status_controller_ready),
    .status_access_gate_closed_o(status_access_gate_closed),
    .status_timeout_o(status_timeout),
    .status_error_code_o(status_error_code),
    .fail_visible_o(fail_visible)
  );

  always #5 clk = !clk;

  task automatic reset_dut();
    begin
      rst_n = 1'b0;
      calibration_done = 1'b0;
      calibration_error = 1'b0;
      init_in_progress = 1'b1;
      controller_error_code = 16'd0;
      reset_request = 1'b0;
      cpu_req_valid = 1'b0;
      cpu_req_write = 1'b0;
      cpu_req_addr = 48'h0000_0100_0000;
      cpu_req_wdata = 24'h000000;
      cpu_req_wstrb = 2'b11;
      cpu_rsp_ready = 1'b1;
      ctrl_req_ready = 1'b1;
      ctrl_rsp_valid = 1'b0;
      ctrl_rsp_rdata = 24'h000000;
      ctrl_rsp_error = 1'b0;
      repeat (3) @(posedge clk);
      rst_n = 1'b1;
      @(posedge clk);
      #1;
    end
  endtask

  task automatic issue_cpu_request(input logic write, input addr_t addr, input cell_t data);
    begin
      cpu_req_write = write;
      cpu_req_addr = addr;
      cpu_req_wdata = data;
      cpu_req_valid = 1'b1;
      #1;
      if (!cpu_req_ready) begin
        $fatal(1, "FPGA DDR calibration gate did not accept CPU request");
      end
    end
  endtask

  task automatic accept_cpu_request();
    begin
      @(posedge clk);
      #1;
      cpu_req_valid = 1'b0;
      #1;
    end
  endtask

  initial begin
    clk = 1'b0;
    reset_dut();

    issue_cpu_request(1'b0, 48'h0000_0100_0000, 24'h000000);
    #1;
    if (ctrl_req_valid) begin
      $fatal(1, "FPGA DDR calibration gate forwarded request before controller_ready");
    end
    if (!cpu_rsp_valid || !cpu_rsp_fault.valid || cpu_rsp_fault.cause != EXC_ACCESS_FAULT) begin
      $fatal(1, "FPGA DDR calibration gate did not fault while calibration was blocked");
    end
    if (!status_access_gate_closed || status_controller_ready) begin
      $fatal(1, "FPGA DDR calibration gate status did not show a closed access gate");
    end
    cpu_req_valid = 1'b0;
    #1;

    reset_dut();
    init_in_progress = 1'b0;
    calibration_done = 1'b1;
    @(posedge clk);
    #1;
    if (!status_controller_ready || status_access_gate_closed) begin
      $fatal(1, "FPGA DDR calibration gate did not expose controller_ready");
    end
    issue_cpu_request(1'b1, 48'h0000_0100_0048, 24'h00A5C3);
    if (!ctrl_req_valid || !ctrl_req_write || ctrl_req_addr != 48'h0000_0100_0048) begin
      $fatal(1, "FPGA DDR calibration gate did not forward ready CPU request");
    end
    accept_cpu_request();
    ctrl_rsp_rdata = 24'h123456;
    ctrl_rsp_valid = 1'b1;
    #1;
    if (!cpu_rsp_valid || cpu_rsp_fault.valid || cpu_rsp_rdata != 24'h123456) begin
      $fatal(1, "FPGA DDR calibration gate did not pass through controller response");
    end
    @(posedge clk);
    #1;
    ctrl_rsp_valid = 1'b0;

    issue_cpu_request(1'b0, 48'h0000_0100_0050, 24'h000000);
    accept_cpu_request();
    controller_error_code = 16'h00D0;
    ctrl_rsp_error = 1'b1;
    ctrl_rsp_valid = 1'b1;
    #1;
    if (!cpu_rsp_valid || !cpu_rsp_fault.valid || cpu_rsp_fault.tval != 48'h0000_0100_0050) begin
      $fatal(1, "FPGA DDR calibration gate did not convert controller error to CPU fault");
    end
    @(posedge clk);
    #1;
    if (!fail_visible || status_error_code != 16'h00D0) begin
      $fatal(1, "FPGA DDR calibration gate did not expose controller failure visibly");
    end
    ctrl_rsp_valid = 1'b0;
    ctrl_rsp_error = 1'b0;

    reset_dut();
    repeat (5) @(posedge clk);
    #1;
    if (!status_timeout || !fail_visible || status_error_code != 16'h0001) begin
      $fatal(1, "FPGA DDR calibration gate did not fail visibly on calibration timeout");
    end
    reset_request = 1'b1;
    @(posedge clk);
    #1;
    if (!controller_reset) begin
      $fatal(1, "FPGA DDR calibration gate did not forward reset_request");
    end
    reset_request = 1'b0;
    @(posedge clk);
    #1;
    if (status_timeout || fail_visible) begin
      $fatal(1, "FPGA DDR calibration gate did not clear sticky status after reset_request");
    end

    $finish;
  end
endmodule
