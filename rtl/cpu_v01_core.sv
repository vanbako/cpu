module cpu_v01_core #(
  parameter cpu_v01_pkg::addr_t RESET_VECTOR = 48'h0000_0000_1000,
  parameter logic [cpu_v01_pkg::CAP_PERMISSION_BITS-1:0] RESET_PCC_PERMISSIONS = 8'd4,
  parameter logic [cpu_v01_pkg::CAP_BOUNDS_METADATA_BITS-1:0] RESET_PCC_BOUNDS_METADATA = 30'd0,
  parameter logic [cpu_v01_pkg::CAP_FLAG_BITS-1:0] RESET_PCC_FLAGS = 2'd1
) (
  input  logic clk,
  input  logic rst_n,

  output logic imem_req_valid,
  input  logic imem_req_ready,
  output cpu_v01_pkg::addr_t imem_req_addr,
  input  logic imem_rsp_valid,
  output logic imem_rsp_ready,
  input  cpu_v01_pkg::cell_t imem_rsp_cells [cpu_v01_pkg::FETCH_GROUP_CELLS],
  input  cpu_v01_pkg::fault_packet_t imem_rsp_fault,

  output logic dmem_req_valid,
  input  logic dmem_req_ready,
  output logic dmem_req_write,
  output cpu_v01_pkg::addr_t dmem_req_addr,
  output logic [2:0] dmem_req_len_cells,
  output cpu_v01_pkg::cell_t dmem_req_wdata [cpu_v01_pkg::CAPABILITY_OBJECT_CELLS],
  input  logic dmem_rsp_valid,
  input  cpu_v01_pkg::cell_t dmem_rsp_rdata [cpu_v01_pkg::CAPABILITY_OBJECT_CELLS],
  input  cpu_v01_pkg::fault_packet_t dmem_rsp_fault,

  output logic tagmem_req_valid,
  input  logic tagmem_req_ready,
  output logic tagmem_req_write,
  output cpu_v01_pkg::addr_t tagmem_req_slot_addr,
  output logic tagmem_req_wtag,
  input  logic tagmem_rsp_valid,
  input  logic tagmem_rsp_rtag,

  input  logic timer_interrupt_pending,
  input  logic software_interrupt_pending,
  input  logic external_interrupt_pending,
  input  logic external_event_valid,
  input  logic [15:0] external_event_cause,
  input  logic debug_halt_request,

  output logic retire_valid,
  input  logic retire_ready,
  output cpu_v01_pkg::retire_packet_t retire_packet,

  output logic core_idle,
  output logic reset_observed,
  output cpu_v01_pkg::cap_t debug_pcc,
  output logic debug_pcc_slot,
  output cpu_v01_pkg::int_reg_t debug_sr,
  output logic [cpu_v01_pkg::RETIRE_SEQUENCE_BITS-1:0] debug_retire_sequence
);
  import cpu_v01_pkg::*;

  localparam int_reg_t SR_RESET_VALUE = 48'h0000_0000_00C0;

  typedef enum logic [1:0] {
    ST_RESET,
    ST_IDLE
  } core_state_t;

  core_state_t state_q;
  cap_t pcc_q;
  logic pcc_slot_q;
  int_reg_t sr_q;
  logic [RETIRE_SEQUENCE_BITS-1:0] retire_sequence_q;
  retire_packet_t retire_packet_q;
  logic reset_observed_q;

  assign imem_req_valid = 1'b0;
  assign imem_req_addr = pcc_q.payload.cursor;
  assign imem_rsp_ready = 1'b0;

  assign dmem_req_valid = 1'b0;
  assign dmem_req_write = 1'b0;
  assign dmem_req_addr = '0;
  assign dmem_req_len_cells = '0;

  assign tagmem_req_valid = 1'b0;
  assign tagmem_req_write = 1'b0;
  assign tagmem_req_slot_addr = '0;
  assign tagmem_req_wtag = 1'b0;

  assign retire_packet = retire_packet_q;
  assign retire_valid = retire_packet_q.valid;

  assign core_idle = state_q == ST_IDLE;
  assign reset_observed = reset_observed_q;
  assign debug_pcc = pcc_q;
  assign debug_pcc_slot = pcc_slot_q;
  assign debug_sr = sr_q;
  assign debug_retire_sequence = retire_sequence_q;

  always_comb begin
    for (int i = 0; i < CAPABILITY_OBJECT_CELLS; i++) begin
      dmem_req_wdata[i] = '0;
    end
  end

  function automatic cap_t reset_pcc(input addr_t cursor);
    cap_t value;
    value.payload.cursor = cursor;
    value.payload.bounds_metadata = RESET_PCC_BOUNDS_METADATA;
    value.payload.permissions = RESET_PCC_PERMISSIONS;
    value.payload.otype = 8'd0;
    value.payload.flags = RESET_PCC_FLAGS;
    value.tag = 1'b1;
    return value;
  endfunction

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      state_q <= ST_RESET;
      pcc_q <= reset_pcc(RESET_VECTOR);
      pcc_slot_q <= SLOT_0;
      sr_q <= SR_RESET_VALUE;
      retire_sequence_q <= '0;
      retire_packet_q <= '0;
      reset_observed_q <= 1'b0;
    end else begin
      retire_packet_q <= '0;

      unique case (state_q)
        ST_RESET: begin
          state_q <= ST_IDLE;
          reset_observed_q <= 1'b1;
        end

        default: begin
          state_q <= ST_IDLE;
        end
      endcase
    end
  end

  // verilator lint_off UNUSEDSIGNAL
  wire logic unused_inputs = &{
    imem_req_ready,
    imem_rsp_valid,
    imem_rsp_fault.valid,
    dmem_req_ready,
    dmem_rsp_valid,
    dmem_rsp_fault.valid,
    tagmem_req_ready,
    tagmem_rsp_valid,
    tagmem_rsp_rtag,
    timer_interrupt_pending,
    software_interrupt_pending,
    external_interrupt_pending,
    external_event_valid,
    external_event_cause[0],
    debug_halt_request,
    retire_ready
  };

  wire logic unused_payload_inputs = ^{
    imem_rsp_cells[0],
    imem_rsp_cells[1],
    dmem_rsp_rdata[0],
    dmem_rsp_rdata[1],
    dmem_rsp_rdata[2],
    dmem_rsp_rdata[3],
    unused_inputs
  };
  // verilator lint_on UNUSEDSIGNAL
endmodule
