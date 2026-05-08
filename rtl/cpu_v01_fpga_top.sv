module cpu_v01_fpga_top #(
  parameter cpu_v01_pkg::addr_t RESET_VECTOR = 48'h0000_0000_1000,
  parameter int RESET_SYNC_STAGES = 2,
  parameter bit ENABLE_FETCH = 1'b1,
  parameter int FIRST_TEST_PASS_RETIRE_COUNT = 8,
  parameter cpu_v01_pkg::addr_t DATA_RAM_BASE = 48'h0000_0001_0000,
  parameter int INSTRUCTION_ROM_CELLS = 1024,
  parameter int DATA_RAM_CELLS = 4096,
  parameter bit USE_ROM_INIT_FILE = 1'b0,
  parameter string ROM_INIT_FILE = "",
  parameter bit USE_DATA_INIT_FILE = 1'b0,
  parameter string DATA_INIT_FILE = ""
) (
  input  logic board_clk_i,
  input  logic board_reset_n_i,
  input  logic debug_halt_request_i,

  output logic pass_led_o,
  output logic fail_led_o,
  output logic heartbeat_led_o,
  output logic status_reset_observed_o,
  output logic status_core_idle_o,
  output logic status_retire_valid_o,
  output logic status_fault_valid_o,
  output logic status_core_port_activity_o,
  output logic [15:0] status_fault_code_o,
  output logic [31:0] status_retire_count_o,
  output logic debug_pcc_valid_o,
  output logic [31:0] debug_pcc_cursor_low_o,
  output logic [7:0] debug_pcc_permissions_o,
  output logic [7:0] debug_sr_low_o
);
  import cpu_v01_pkg::*;

  localparam logic [RETIRE_SEQUENCE_BITS-1:0] FIRST_TEST_PASS_THRESHOLD =
      RETIRE_SEQUENCE_BITS'(FIRST_TEST_PASS_RETIRE_COUNT - 1);

  logic [RESET_SYNC_STAGES-1:0] reset_sync_q;
  logic core_rst_n;

  logic imem_req_valid;
  logic imem_req_ready;
  addr_t imem_req_addr;
  logic imem_rsp_valid;
  logic imem_rsp_ready;
  cell_t imem_rsp_cells [FETCH_GROUP_CELLS];
  fault_packet_t imem_rsp_fault;

  logic dmem_req_valid;
  logic dmem_req_ready;
  logic dmem_req_write;
  addr_t dmem_req_addr;
  logic [2:0] dmem_req_len_cells;
  cell_t dmem_req_wdata [CAPABILITY_OBJECT_CELLS];
  logic dmem_rsp_valid;
  cell_t dmem_rsp_rdata [CAPABILITY_OBJECT_CELLS];
  fault_packet_t dmem_rsp_fault;

  logic tagmem_req_valid;
  logic tagmem_req_ready;
  logic tagmem_req_write;
  addr_t tagmem_req_slot_addr;
  logic tagmem_req_wtag;
  logic tagmem_rsp_valid;
  logic tagmem_rsp_rtag;

  logic retire_valid;
  retire_packet_t retire_packet;
  logic core_idle;
  logic reset_observed;
  cap_t debug_pcc;
  logic debug_pcc_slot;
  int_reg_t debug_sr;
  logic [RETIRE_SEQUENCE_BITS-1:0] debug_retire_sequence;
  logic pass_sticky_q;
  logic fault_sticky_q;
  logic [15:0] fault_code_q;
  logic core_port_activity;

  assign core_rst_n = reset_sync_q[RESET_SYNC_STAGES-1];

  assign pass_led_o = pass_sticky_q && !fault_sticky_q;
  assign fail_led_o = fault_sticky_q;
  assign heartbeat_led_o = debug_retire_sequence[0];
  assign status_reset_observed_o = reset_observed;
  assign status_core_idle_o = core_idle;
  assign status_retire_valid_o = retire_valid;
  assign status_fault_valid_o = fault_sticky_q;
  assign status_core_port_activity_o = core_port_activity;
  assign status_fault_code_o = fault_code_q;
  assign status_retire_count_o = debug_retire_sequence[31:0];
  assign debug_pcc_valid_o = debug_pcc.tag && !debug_pcc_slot;
  assign debug_pcc_cursor_low_o = debug_pcc.payload.cursor[31:0];
  assign debug_pcc_permissions_o = debug_pcc.payload.permissions;
  assign debug_sr_low_o = debug_sr[7:0];

  always_ff @(posedge board_clk_i or negedge board_reset_n_i) begin
    if (!board_reset_n_i) begin
      reset_sync_q <= '0;
    end else begin
      reset_sync_q <= {reset_sync_q[RESET_SYNC_STAGES-2:0], 1'b1};
    end
  end

  always_ff @(posedge board_clk_i or negedge core_rst_n) begin
    if (!core_rst_n) begin
      pass_sticky_q <= 1'b0;
      fault_sticky_q <= 1'b0;
      fault_code_q <= 16'd0;
    end else if (retire_packet.fault.valid) begin
      fault_sticky_q <= 1'b1;
      fault_code_q <= retire_packet.fault.cause;
    end else if (retire_valid && debug_retire_sequence >= FIRST_TEST_PASS_THRESHOLD) begin
      pass_sticky_q <= 1'b1;
    end
  end

  always_comb begin
    core_port_activity =
        imem_req_valid || imem_rsp_ready || (imem_req_valid && (|imem_req_addr)) ||
        dmem_req_valid || dmem_req_write || (dmem_req_valid && (|dmem_req_addr)) ||
        (dmem_req_valid && (|dmem_req_len_cells)) ||
        tagmem_req_valid || tagmem_req_write ||
        (tagmem_req_valid && (|tagmem_req_slot_addr)) ||
        tagmem_req_wtag || retire_valid;
    for (int i = 0; i < CAPABILITY_OBJECT_CELLS; i++) begin
      core_port_activity = core_port_activity || (dmem_req_valid && (|dmem_req_wdata[i]));
    end
  end

  cpu_v01_fpga_imem_rom #(
    .BASE_CELL(RESET_VECTOR),
    .DEPTH_CELLS(INSTRUCTION_ROM_CELLS),
    .USE_INIT_FILE(USE_ROM_INIT_FILE),
    .INIT_FILE(ROM_INIT_FILE)
  ) instruction_rom (
    .clk(board_clk_i),
    .rst_n(core_rst_n),
    .req_valid(imem_req_valid),
    .req_ready(imem_req_ready),
    .req_addr(imem_req_addr),
    .rsp_valid(imem_rsp_valid),
    .rsp_ready(imem_rsp_ready),
    .rsp_cells(imem_rsp_cells),
    .rsp_fault(imem_rsp_fault)
  );

  cpu_v01_fpga_data_ram #(
    .BASE_CELL(DATA_RAM_BASE),
    .DEPTH_CELLS(DATA_RAM_CELLS),
    .USE_INIT_FILE(USE_DATA_INIT_FILE),
    .INIT_FILE(DATA_INIT_FILE)
  ) data_ram (
    .clk(board_clk_i),
    .rst_n(core_rst_n),
    .req_valid(dmem_req_valid),
    .req_ready(dmem_req_ready),
    .req_write(dmem_req_write),
    .req_addr(dmem_req_addr),
    .req_len_cells(dmem_req_len_cells),
    .req_wdata(dmem_req_wdata),
    .rsp_valid(dmem_rsp_valid),
    .rsp_rdata(dmem_rsp_rdata),
    .rsp_fault(dmem_rsp_fault)
  );

  cpu_v01_fpga_tag_ram #(
    .BASE_CELL(DATA_RAM_BASE),
    .DEPTH_ENTRIES(DATA_RAM_CELLS)
  ) tag_ram (
    .clk(board_clk_i),
    .rst_n(core_rst_n),
    .req_valid(tagmem_req_valid),
    .req_ready(tagmem_req_ready),
    .req_write(tagmem_req_write),
    .req_slot_addr(tagmem_req_slot_addr),
    .req_wtag(tagmem_req_wtag),
    .rsp_valid(tagmem_rsp_valid),
    .rsp_rtag(tagmem_rsp_rtag)
  );

  cpu_v01_core #(
    .RESET_VECTOR(RESET_VECTOR),
    .ENABLE_FETCH(ENABLE_FETCH)
  ) core (
    .clk(board_clk_i),
    .rst_n(core_rst_n),
    .imem_req_valid(imem_req_valid),
    .imem_req_ready(imem_req_ready),
    .imem_req_addr(imem_req_addr),
    .imem_rsp_valid(imem_rsp_valid),
    .imem_rsp_ready(imem_rsp_ready),
    .imem_rsp_cells(imem_rsp_cells),
    .imem_rsp_fault(imem_rsp_fault),
    .dmem_req_valid(dmem_req_valid),
    .dmem_req_ready(dmem_req_ready),
    .dmem_req_write(dmem_req_write),
    .dmem_req_addr(dmem_req_addr),
    .dmem_req_len_cells(dmem_req_len_cells),
    .dmem_req_wdata(dmem_req_wdata),
    .dmem_rsp_valid(dmem_rsp_valid),
    .dmem_rsp_rdata(dmem_rsp_rdata),
    .dmem_rsp_fault(dmem_rsp_fault),
    .tagmem_req_valid(tagmem_req_valid),
    .tagmem_req_ready(tagmem_req_ready),
    .tagmem_req_write(tagmem_req_write),
    .tagmem_req_slot_addr(tagmem_req_slot_addr),
    .tagmem_req_wtag(tagmem_req_wtag),
    .tagmem_rsp_valid(tagmem_rsp_valid),
    .tagmem_rsp_rtag(tagmem_rsp_rtag),
    .timer_interrupt_pending(1'b0),
    .software_interrupt_pending(1'b0),
    .external_interrupt_pending(1'b0),
    .external_event_valid(1'b0),
    .external_event_cause(16'd0),
    .debug_halt_request(debug_halt_request_i),
    .retire_valid(retire_valid),
    .retire_ready(1'b1),
    .retire_packet(retire_packet),
    .core_idle(core_idle),
    .reset_observed(reset_observed),
    .debug_pcc(debug_pcc),
    .debug_pcc_slot(debug_pcc_slot),
    .debug_sr(debug_sr),
    .debug_retire_sequence(debug_retire_sequence)
  );
endmodule
