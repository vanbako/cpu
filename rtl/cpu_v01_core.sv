module cpu_v01_core #(
  parameter cpu_v01_pkg::addr_t RESET_VECTOR = 48'h0000_0000_1000,
  parameter logic [cpu_v01_pkg::CAP_PERMISSION_BITS-1:0] RESET_PCC_PERMISSIONS = 8'd4,
  parameter logic [cpu_v01_pkg::CAP_BOUNDS_METADATA_BITS-1:0] RESET_PCC_BOUNDS_METADATA = 30'd0,
  parameter logic [cpu_v01_pkg::CAP_FLAG_BITS-1:0] RESET_PCC_FLAGS = 2'd1,
  parameter bit ENABLE_FETCH = 1'b1
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

  typedef enum logic [2:0] {
    ST_RESET,
    ST_IDLE,
    ST_FETCH_REQ,
    ST_FETCH_WAIT,
    ST_DECODE
  } core_state_t;

  core_state_t state_q;
  cap_t pcc_q;
  logic pcc_slot_q;
  int_reg_t sr_q;
  logic [RETIRE_SEQUENCE_BITS-1:0] retire_sequence_q;
  retire_packet_t retire_packet_q;
  logic reset_observed_q;
  cell_t fetch_cells_q [FETCH_GROUP_CELLS];
  fault_packet_t fetch_fault_q;
  addr_t fetch_pc_q;
  logic fetch_slot_q;

  wire logic fetch_enabled = ENABLE_FETCH;
  wire addr_t fetch_group_base = {pcc_q.payload.cursor[ADDR_BITS-1:1], 1'b0};

  assign imem_req_valid = fetch_enabled && state_q == ST_FETCH_REQ;
  assign imem_req_addr = fetch_group_base;
  assign imem_rsp_ready = fetch_enabled && state_q == ST_FETCH_WAIT;

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

  assign core_idle = state_q == ST_IDLE || (!fetch_enabled && state_q == ST_FETCH_REQ);
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

  function automatic logic is_12_opcode(input logic [11:0] opcode);
    unique case (opcode)
      12'h053,
      12'h055,
      12'h056,
      12'h05A,
      12'h05B: return 1'b1;
      default: return 1'b0;
    endcase
  endfunction

  function automatic logic is_24_major(input logic [7:0] major);
    unique case (major)
      8'h10, 8'h11, 8'h12, 8'h13, 8'h14, 8'h15, 8'h16, 8'h17,
      8'h18, 8'h19, 8'h1A, 8'h1B, 8'h1C, 8'h1D, 8'h1E, 8'h1F,
      8'h20, 8'h21, 8'h22, 8'h23, 8'h24, 8'h25, 8'h26, 8'h27,
      8'h28, 8'h29, 8'h2A, 8'h2B,
      8'h30, 8'h31, 8'h32, 8'h33, 8'h34, 8'h35,
      8'h50, 8'h51, 8'h52, 8'h54, 8'h57, 8'h58, 8'h59, 8'h5C,
      8'h60, 8'h61, 8'h62, 8'h63, 8'h64, 8'h65, 8'h66, 8'h67,
      8'h68, 8'h69,
      8'h80, 8'h81, 8'h82: return 1'b1;
      default: return 1'b0;
    endcase
  endfunction

  function automatic logic is_48_major(input logic [7:0] major);
    unique case (major)
      8'h40, 8'h41, 8'h42, 8'h43, 8'h44, 8'h45, 8'h46, 8'h47,
      8'h6A, 8'h6B, 8'h6C, 8'h6D, 8'h70, 8'h71: return 1'b1;
      default: return 1'b0;
    endcase
  endfunction

  function automatic logic [7:0] opcode_id_for_12(input logic [11:0] opcode);
    unique case (opcode)
      12'h053: return OPC_RET_12;
      12'h055: return OPC_BRK_12;
      12'h056: return OPC_SYS_12;
      12'h05A: return OPC_WFI_12;
      12'h05B: return OPC_PAUSE_12;
      default: return '0;
    endcase
  endfunction

  function automatic logic is_kernel_opcode(input logic [7:0] opcode_id);
    unique case (opcode_id)
      OPC_IRET_24,
      OPC_EPCCRD_24,
      OPC_EPCCWR_24,
      OPC_WFI_12,
      OPC_FENCE_I_24,
      OPC_SFENCE_VM_24,
      OPC_SFENCE_VM_ASID_24,
      OPC_SFENCE_VM_VA_24,
      OPC_SFENCE_VM_VA_ASID_24,
      OPC_CCSRRD_48,
      OPC_CCSRWR_48,
      OPC_CACHE_CLEAN_24,
      OPC_CACHE_INVAL_24,
      OPC_CACHE_CLEANINVAL_24: return 1'b1;
      default: return 1'b0;
    endcase
  endfunction

  task automatic start_decoded_packet(
    input logic [OPCODE_ID_BITS-1:0] opcode_id,
    input logic [7:0] size_bits,
    input logic [1:0] instruction_length
  );
    retire_packet_q <= '0;
    retire_packet_q.valid <= 1'b1;
    retire_packet_q.sequence <= retire_sequence_q;
    retire_packet_q.pc_cell <= fetch_pc_q;
    retire_packet_q.slot <= fetch_slot_q;
    retire_packet_q.instruction_length <= instruction_length;
    retire_packet_q.decoded.valid <= 1'b1;
    retire_packet_q.decoded.opcode_id <= opcode_id;
    retire_packet_q.decoded.size_bits <= size_bits;
    retire_packet_q.decoded.privileged <= is_kernel_opcode(opcode_id);
    retire_packet_q.normal_valid <= 1'b1;
  endtask

  task automatic start_fault_packet(
    input logic [15:0] cause,
    input addr_t tval
  );
    retire_packet_q <= '0;
    retire_packet_q.valid <= 1'b1;
    retire_packet_q.sequence <= retire_sequence_q;
    retire_packet_q.pc_cell <= fetch_pc_q;
    retire_packet_q.slot <= fetch_slot_q;
    retire_packet_q.instruction_length <= 2'd1;
    retire_packet_q.normal_valid <= 1'b0;
    retire_packet_q.fault.valid <= 1'b1;
    retire_packet_q.fault.cause <= cause;
    retire_packet_q.fault.pc_cell <= fetch_pc_q;
    retire_packet_q.fault.slot <= fetch_slot_q;
    retire_packet_q.fault.tval <= tval;
  endtask

  task automatic advance_pc(input logic [7:0] size_bits);
    if (size_bits == 8'd12 && fetch_slot_q == SLOT_0) begin
      pcc_slot_q <= SLOT_1;
      sr_q[9] <= SLOT_1;
    end else begin
      pcc_slot_q <= SLOT_0;
      sr_q[9] <= SLOT_0;
      if (size_bits == 8'd48) begin
        pcc_q.payload.cursor <= fetch_pc_q + 48'd2;
      end else begin
        pcc_q.payload.cursor <= fetch_pc_q + 48'd1;
      end
    end
  endtask

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      state_q <= ST_RESET;
      pcc_q <= reset_pcc(RESET_VECTOR);
      pcc_slot_q <= SLOT_0;
      sr_q <= SR_RESET_VALUE;
      retire_sequence_q <= '0;
      retire_packet_q <= '0;
      reset_observed_q <= 1'b0;
      fetch_fault_q <= '0;
      fetch_pc_q <= RESET_VECTOR;
      fetch_slot_q <= SLOT_0;
      for (int i = 0; i < FETCH_GROUP_CELLS; i++) begin
        fetch_cells_q[i] <= '0;
      end
    end else begin
      retire_packet_q <= '0;

      unique case (state_q)
        ST_RESET: begin
          state_q <= fetch_enabled ? ST_FETCH_REQ : ST_IDLE;
          reset_observed_q <= 1'b1;
        end

        ST_IDLE: begin
          state_q <= fetch_enabled ? ST_FETCH_REQ : ST_IDLE;
        end

        ST_FETCH_REQ: begin
          if (!fetch_enabled) begin
            state_q <= ST_IDLE;
          end else if (imem_req_ready) begin
            fetch_pc_q <= pcc_q.payload.cursor;
            fetch_slot_q <= pcc_slot_q;
            state_q <= ST_FETCH_WAIT;
          end
        end

        ST_FETCH_WAIT: begin
          if (imem_rsp_valid) begin
            for (int i = 0; i < FETCH_GROUP_CELLS; i++) begin
              fetch_cells_q[i] <= imem_rsp_cells[i];
            end
            fetch_fault_q <= imem_rsp_fault;
            state_q <= ST_DECODE;
          end
        end

        ST_DECODE: begin
          automatic cell_t selected_cell;
          automatic logic [7:0] major;
          automatic logic [11:0] selected_half;
          selected_cell = fetch_cells_q[fetch_pc_q[0]];
          major = selected_cell[23:16];
          selected_half = fetch_slot_q == SLOT_0 ? selected_cell[11:0] : selected_cell[23:12];

          if (fetch_fault_q.valid) begin
            retire_packet_q <= '0;
            retire_packet_q.valid <= 1'b1;
            retire_packet_q.sequence <= retire_sequence_q;
            retire_packet_q.pc_cell <= fetch_pc_q;
            retire_packet_q.slot <= fetch_slot_q;
            retire_packet_q.instruction_length <= 2'd1;
            retire_packet_q.fault <= fetch_fault_q;
          end else if (fetch_slot_q == SLOT_1 && (is_24_major(major) || is_48_major(major))) begin
            start_fault_packet(EXC_ALIGN_FAULT, fetch_pc_q);
          end else if (fetch_slot_q == SLOT_0 && is_48_major(major) && fetch_pc_q[0]) begin
            start_fault_packet(EXC_ALIGN_FAULT, fetch_pc_q);
          end else if (fetch_slot_q == SLOT_0 && is_48_major(major)) begin
            start_decoded_packet(major, 8'd48, 2'd2);
            advance_pc(8'd48);
          end else if (fetch_slot_q == SLOT_0 && is_24_major(major)) begin
            start_decoded_packet(major, 8'd24, 2'd1);
            advance_pc(8'd24);
          end else if (is_12_opcode(selected_half)) begin
            start_decoded_packet(opcode_id_for_12(selected_half), 8'd12, 2'd1);
            advance_pc(8'd12);
          end else begin
            start_fault_packet(EXC_ILLEGAL_INSTRUCTION, '0);
          end

          retire_sequence_q <= retire_sequence_q + 64'd1;
          state_q <= ST_FETCH_REQ;
        end

        default: begin
          state_q <= ST_IDLE;
        end
      endcase
    end
  end

  // verilator lint_off UNUSEDSIGNAL
  wire logic unused_inputs = &{
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
    dmem_rsp_rdata[0],
    dmem_rsp_rdata[1],
    dmem_rsp_rdata[2],
    dmem_rsp_rdata[3],
    unused_inputs
  };
  // verilator lint_on UNUSEDSIGNAL
endmodule
