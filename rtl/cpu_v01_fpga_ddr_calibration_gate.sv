module cpu_v01_fpga_ddr_calibration_gate #(
  parameter int CALIBRATION_TIMEOUT_CYCLES = 25_000_000
) (
  input  logic clk,
  input  logic rst_n,

  input  logic calibration_done_i,
  input  logic calibration_error_i,
  input  logic init_in_progress_i,
  input  logic [15:0] controller_error_code_i,
  input  logic reset_request_i,
  output logic controller_reset_o,

  input  logic cpu_req_valid_i,
  output logic cpu_req_ready_o,
  input  logic cpu_req_write_i,
  input  cpu_v01_pkg::addr_t cpu_req_addr_i,
  input  cpu_v01_pkg::cell_t cpu_req_wdata_i,
  input  logic [1:0] cpu_req_wstrb_i,

  output logic cpu_rsp_valid_o,
  input  logic cpu_rsp_ready_i,
  output cpu_v01_pkg::cell_t cpu_rsp_rdata_o,
  output cpu_v01_pkg::fault_packet_t cpu_rsp_fault_o,

  output logic ctrl_req_valid_o,
  input  logic ctrl_req_ready_i,
  output logic ctrl_req_write_o,
  output cpu_v01_pkg::addr_t ctrl_req_addr_o,
  output cpu_v01_pkg::cell_t ctrl_req_wdata_o,
  output logic [1:0] ctrl_req_wstrb_o,

  input  logic ctrl_rsp_valid_i,
  output logic ctrl_rsp_ready_o,
  input  cpu_v01_pkg::cell_t ctrl_rsp_rdata_i,
  input  logic ctrl_rsp_error_i,

  output logic status_calibration_done_o,
  output logic status_calibration_error_o,
  output logic status_init_in_progress_o,
  output logic status_controller_ready_o,
  output logic status_access_gate_closed_o,
  output logic status_timeout_o,
  output logic [15:0] status_error_code_o,
  output logic fail_visible_o
);
  import cpu_v01_pkg::*;

  localparam logic [15:0] DDR_GATE_ERROR_TIMEOUT = 16'h0001;
  localparam logic [15:0] DDR_GATE_ERROR_CALIBRATION = 16'h0002;
  localparam logic [15:0] DDR_GATE_ERROR_CONTROLLER = 16'h0003;
  localparam int TIMEOUT_COUNTER_BITS =
      (CALIBRATION_TIMEOUT_CYCLES < 2) ? 1 : $clog2(CALIBRATION_TIMEOUT_CYCLES + 1);

  logic [TIMEOUT_COUNTER_BITS-1:0] timeout_count_q;
  logic timeout_q;
  logic controller_error_seen_q;
  logic outstanding_q;
  logic [15:0] sticky_error_code_q;
  addr_t outstanding_addr_q;
  logic controller_ready;
  logic blocked_request;

  assign controller_ready =
      calibration_done_i && !calibration_error_i && !timeout_q && !controller_error_seen_q;
  assign blocked_request = cpu_req_valid_i && !controller_ready;

  assign controller_reset_o = reset_request_i;

  assign cpu_req_ready_o =
      controller_ready ? (!outstanding_q && ctrl_req_ready_i) : cpu_rsp_ready_i;
  assign ctrl_req_valid_o = cpu_req_valid_i && controller_ready && !outstanding_q;
  assign ctrl_req_write_o = cpu_req_write_i;
  assign ctrl_req_addr_o = cpu_req_addr_i;
  assign ctrl_req_wdata_o = cpu_req_wdata_i;
  assign ctrl_req_wstrb_o = cpu_req_wstrb_i;

  assign ctrl_rsp_ready_o = outstanding_q && cpu_rsp_ready_i;
  assign cpu_rsp_valid_o = controller_ready ? (outstanding_q && ctrl_rsp_valid_i) : blocked_request;
  assign cpu_rsp_rdata_o =
      (controller_ready && outstanding_q && ctrl_rsp_valid_i && !ctrl_rsp_error_i) ?
      ctrl_rsp_rdata_i : '0;

  assign status_calibration_done_o = calibration_done_i;
  assign status_calibration_error_o = calibration_error_i;
  assign status_init_in_progress_o = init_in_progress_i;
  assign status_controller_ready_o = controller_ready;
  assign status_access_gate_closed_o = !controller_ready;
  assign status_timeout_o = timeout_q;
  assign status_error_code_o = sticky_error_code_q;
  assign fail_visible_o = calibration_error_i || timeout_q || controller_error_seen_q;

  function automatic fault_packet_t access_fault(input addr_t addr);
    fault_packet_t fault;
    fault = '0;
    fault.valid = 1'b1;
    fault.cause = EXC_ACCESS_FAULT;
    fault.tval = addr;
    return fault;
  endfunction

  always_comb begin
    cpu_rsp_fault_o = '0;
    if (!controller_ready && cpu_req_valid_i) begin
      cpu_rsp_fault_o = access_fault(cpu_req_addr_i);
    end else if (controller_ready && outstanding_q && ctrl_rsp_valid_i && ctrl_rsp_error_i) begin
      cpu_rsp_fault_o = access_fault(outstanding_addr_q);
    end
  end

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      timeout_count_q <= '0;
      timeout_q <= 1'b0;
      controller_error_seen_q <= 1'b0;
      outstanding_q <= 1'b0;
      outstanding_addr_q <= '0;
      sticky_error_code_q <= 16'd0;
    end else if (reset_request_i) begin
      timeout_count_q <= '0;
      timeout_q <= 1'b0;
      controller_error_seen_q <= 1'b0;
      outstanding_q <= 1'b0;
      outstanding_addr_q <= '0;
      sticky_error_code_q <= 16'd0;
    end else begin
      if (ctrl_req_valid_o && ctrl_req_ready_i) begin
        outstanding_q <= 1'b1;
        outstanding_addr_q <= cpu_req_addr_i;
      end
      if (ctrl_rsp_valid_i && ctrl_rsp_ready_o) begin
        outstanding_q <= 1'b0;
        if (ctrl_rsp_error_i) begin
          controller_error_seen_q <= 1'b1;
          sticky_error_code_q <= (controller_error_code_i != 16'd0) ?
              controller_error_code_i : DDR_GATE_ERROR_CONTROLLER;
        end
      end

      if (calibration_error_i) begin
        sticky_error_code_q <= (controller_error_code_i != 16'd0) ?
            controller_error_code_i : DDR_GATE_ERROR_CALIBRATION;
      end

      if (CALIBRATION_TIMEOUT_CYCLES > 0 &&
          !calibration_done_i && !calibration_error_i && init_in_progress_i && !timeout_q) begin
        if (timeout_count_q >= TIMEOUT_COUNTER_BITS'(CALIBRATION_TIMEOUT_CYCLES - 1)) begin
          timeout_q <= 1'b1;
          sticky_error_code_q <= DDR_GATE_ERROR_TIMEOUT;
        end else begin
          timeout_count_q <= timeout_count_q + TIMEOUT_COUNTER_BITS'(1);
        end
      end else if (calibration_done_i) begin
        timeout_count_q <= '0;
      end
    end
  end
endmodule
