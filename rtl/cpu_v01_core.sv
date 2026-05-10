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
  localparam int CSR_COUNT = 1 << CSR_NUMBER_BITS;
  localparam logic [2:0] WIDTH_W8 = 3'd0;
  localparam logic [2:0] WIDTH_W16 = 3'd1;
  localparam logic [2:0] WIDTH_W24 = 3'd2;
  localparam logic [2:0] WIDTH_W32 = 3'd3;
  localparam logic [2:0] WIDTH_W48 = 3'd5;
  localparam logic [7:0] CAP_PERM_LD = 8'h01;
  localparam logic [7:0] CAP_PERM_ST = 8'h02;
  localparam logic [7:0] CAP_PERM_LC = 8'h08;
  localparam logic [7:0] CAP_PERM_SC = 8'h10;
  localparam logic [7:0] CAP_PERM_SL = 8'h20;
  localparam addr_t MMU_TLB_VIRTUAL_ADDRESS = 48'h1234_5678_9120;
  localparam addr_t MMU_TLB_PHYSICAL_ADDRESS_A = 48'h0000_0000_A120;
  localparam addr_t MMU_TLB_PHYSICAL_ADDRESS_B = 48'h0000_0000_B120;
  localparam addr_t MMU_TLB_USER_FETCH_ADDRESS = 48'h0000_0000_4100;
  localparam int_reg_t MMU_TLB_ROOT_PPN = 48'h0000_0000_0010;
  localparam int_reg_t MMU_TLB_PERMISSION_ROOT_PPN = 48'h0000_0000_0011;
  localparam int_reg_t MMU_TLB_MEMTYPE_ROOT_PPN = 48'h0000_0000_0012;
  localparam addr_t ATOMIC_CACHE_DEVICE_PA = 48'h0000_0000_F000;
  localparam addr_t SOC_MMIO_BASE = 48'h0000_00F0_0000;
  localparam addr_t SOC_MMIO_LIMIT = 48'h0000_00F0_1000;

  typedef enum logic [3:0] {
    ST_RESET,
    ST_IDLE,
    ST_FETCH_REQ,
    ST_FETCH_WAIT,
    ST_DECODE,
    ST_MEM_DREQ,
    ST_MEM_DWAIT,
    ST_MEM_TAG_REQ,
    ST_MEM_TAG_WAIT
  } core_state_t;

  typedef struct packed {
    logic fault;
    logic [15:0] cause;
    logic [3:0] capcause;
    logic [7:0] fault_cap_idx;
    addr_t tval;
  } access_check_t;

  typedef struct packed {
    logic fault;
    logic [15:0] cause;
    addr_t effective_address;
    addr_t physical_address;
    logic [MEMORY_TYPE_BITS-1:0] memory_type;
    logic tlb_hit;
    logic tlb_fill;
    logic tlb_global;
    logic [7:0] asid;
    logic [2:0] page_walk_level;
  } translation_result_t;

  core_state_t state_q;
  cap_t pcc_q;
  logic pcc_slot_q;
  cap_t epcc_q;
  logic epcc_slot_q;
  cap_t dsc_q;
  cap_t rsc_q;
  cap_t ddc_q;
  cap_t tvc_q;
  cap_t ksc_q;
  cap_t krc_q;
  cap_t return_stack_slot_q;
  logic return_stack_slot_slot_q;
  int_reg_t sr_q;
  int_reg_t d_regs [INT_REG_COUNT];
  cap_t c_regs [CAP_REG_COUNT];
  int_reg_t csr_regs [CSR_COUNT];
  logic [RETIRE_SEQUENCE_BITS-1:0] retire_sequence_q;
  retire_packet_t retire_packet_q;
  logic reset_observed_q;
  cell_t fetch_cells_q [FETCH_GROUP_CELLS];
  fault_packet_t fetch_fault_q;
  addr_t fetch_pc_q;
  logic fetch_slot_q;
  logic [OPCODE_ID_BITS-1:0] mem_opcode_q;
  logic [7:0] mem_size_bits_q;
  logic [1:0] mem_instruction_length_q;
  logic [RETIRE_SEQUENCE_BITS-1:0] mem_sequence_q;
  addr_t mem_pc_q;
  logic mem_slot_q;
  addr_t mem_address_q;
  addr_t mem_effective_address_q;
  logic mem_translation_valid_q;
  logic [MEMORY_TYPE_BITS-1:0] mem_translation_memory_type_q;
  logic mem_translation_tlb_hit_q;
  logic mem_tlb_fill_valid_q;
  logic mem_tlb_fill_global_q;
  logic [7:0] mem_tlb_fill_asid_q;
  logic [2:0] mem_page_walk_level_q;
  logic [3:0] mem_integer_index_q;
  logic [2:0] mem_capability_index_q;
  int_reg_t mem_integer_value_q;
  cap_t mem_capability_value_q;
  cell_t mem_rdata_q [CAPABILITY_OBJECT_CELLS];
  logic dtlb_valid_q;
  logic dtlb_global_q;
  addr_t dtlb_va_q;
  addr_t dtlb_pa_q;
  logic [7:0] dtlb_asid_q;
  logic mapping_a_removed_q;
  logic reservation_valid_q;
  addr_t reservation_word_address_q;
  logic [MEMORY_TYPE_BITS-1:0] reservation_memory_type_q;

  wire logic fetch_enabled = ENABLE_FETCH;
  wire addr_t fetch_group_base =
      translate_instruction_address({pcc_q.payload.cursor[ADDR_BITS-1:1], 1'b0});

  assign imem_req_valid = fetch_enabled && state_q == ST_FETCH_REQ;
  assign imem_req_addr = fetch_group_base;
  assign imem_rsp_ready = fetch_enabled && state_q == ST_FETCH_WAIT;

  assign dmem_req_valid = state_q == ST_MEM_DREQ;
  assign dmem_req_write =
      mem_opcode_q == OPC_ST48_24 || mem_opcode_q == OPC_CSC_24 || mem_opcode_q == OPC_SC48_24;
  assign dmem_req_addr = mem_address_q;
  assign dmem_req_len_cells =
      (mem_opcode_q == OPC_CLC_24 || mem_opcode_q == OPC_CSC_24) ? 3'd4 : 3'd2;

  assign tagmem_req_valid = state_q == ST_MEM_TAG_REQ;
  assign tagmem_req_write =
      mem_opcode_q == OPC_ST48_24 || mem_opcode_q == OPC_CSC_24 || mem_opcode_q == OPC_SC48_24;
  assign tagmem_req_slot_addr =
      (mem_opcode_q == OPC_ST48_24 || mem_opcode_q == OPC_SC48_24) ?
          capability_slot_base(mem_address_q) : mem_address_q;
  assign tagmem_req_wtag = mem_opcode_q == OPC_CSC_24 ? mem_capability_value_q.tag : 1'b0;

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
    if (mem_opcode_q == OPC_ST48_24 || mem_opcode_q == OPC_SC48_24) begin
      dmem_req_wdata[0] = mem_integer_value_q[23:0];
      dmem_req_wdata[1] = mem_integer_value_q[47:24];
    end else if (mem_opcode_q == OPC_CSC_24) begin
      for (int i = 0; i < CAPABILITY_OBJECT_CELLS; i++) begin
        dmem_req_wdata[i] = cap_payload_cell(mem_capability_value_q, i);
      end
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

  function automatic cap_t return_stack_cap(input addr_t cursor);
    cap_t value;
    value.payload.cursor = cursor;
    value.payload.bounds_metadata = 30'd0;
    value.payload.permissions = CAP_PERM_ST | CAP_PERM_LD | CAP_PERM_LC | CAP_PERM_SC | CAP_PERM_SL;
    value.payload.otype = 8'd0;
    value.payload.flags = 2'd0;
    value.tag = 1'b1;
    return value;
  endfunction

  function automatic cap_t return_capability(input cap_t source);
    cap_t value;
    value = source;
    value.payload.otype = 8'hFF;
    value.payload.flags = 2'd0;
    value.tag = 1'b1;
    return value;
  endfunction

  function automatic cap_t unsealed_capability(input cap_t source);
    cap_t value;
    value = source;
    value.payload.otype = 8'd0;
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

  function automatic logic [39:0] operands_24(input cell_t instr_cell);
    return {24'd0, instr_cell[15:0]};
  endfunction

  function automatic logic [39:0] operands_48(input cell_t low_cell, input cell_t high_cell);
    return {high_cell, low_cell[15:0]};
  endfunction

  function automatic logic next_slot(input logic [7:0] size_bits);
    if (size_bits == 8'd12 && fetch_slot_q == SLOT_0) begin
      return SLOT_1;
    end
    return SLOT_0;
  endfunction

  function automatic cap_t next_pcc(input logic [7:0] size_bits);
    cap_t value;
    value = pcc_q;
    if (size_bits == 8'd12 && fetch_slot_q == SLOT_0) begin
      value.payload.cursor = fetch_pc_q;
    end else if (size_bits == 8'd48) begin
      value.payload.cursor = fetch_pc_q + 48'd2;
    end else begin
      value.payload.cursor = fetch_pc_q + 48'd1;
    end
    return value;
  endfunction

  function automatic int_reg_t width_mask(input logic [2:0] width_code);
    unique case (width_code)
      WIDTH_W8: return 48'h0000_0000_00FF;
      WIDTH_W16: return 48'h0000_0000_FFFF;
      WIDTH_W24: return 48'h0000_00FF_FFFF;
      WIDTH_W32: return 48'h0000_FFFF_FFFF;
      default: return 48'hFFFF_FFFF_FFFF;
    endcase
  endfunction

  function automatic int_reg_t apply_width(input int_reg_t value, input logic [2:0] width_code);
    return value & width_mask(width_code);
  endfunction

  function automatic logic width_sign_bit(input int_reg_t value, input logic [2:0] width_code);
    unique case (width_code)
      WIDTH_W8: return value[7];
      WIDTH_W16: return value[15];
      WIDTH_W24: return value[23];
      WIDTH_W32: return value[31];
      default: return value[47];
    endcase
  endfunction

  function automatic int_reg_t sr_with_zn(input int_reg_t result, input logic [2:0] width_code);
    int_reg_t next_sr;
    int_reg_t masked_result;
    next_sr = sr_q;
    masked_result = apply_width(result, width_code);
    next_sr[0] = masked_result == '0;
    next_sr[1] = width_sign_bit(masked_result, width_code);
    next_sr[2] = 1'b0;
    next_sr[3] = 1'b0;
    return next_sr;
  endfunction

  function automatic logic condition_true(input logic [3:0] condition_code);
    logic zero;
    logic negative;
    logic carry;
    logic overflow;
    zero = sr_q[0];
    negative = sr_q[1];
    carry = sr_q[2];
    overflow = sr_q[3];
    unique case (condition_code)
      4'h0: return 1'b1;
      4'h1: return zero;
      4'h2: return !zero;
      4'h3: return carry;
      4'h4: return !carry;
      4'h5: return negative;
      4'h6: return !negative;
      4'h7: return overflow;
      4'h8: return !overflow;
      4'h9: return !zero && (negative == overflow);
      4'hA: return zero || (negative != overflow);
      default: return 1'b0;
    endcase
  endfunction

  function automatic int_reg_t csr_read(input logic [CSR_NUMBER_BITS-1:0] csr_index);
    if (csr_index == CSR_SR) begin
      return sr_q;
    end
    return csr_regs[csr_index];
  endfunction

  function automatic cap_t ccsr_read(input logic [CCSR_NUMBER_BITS-1:0] ccsr_index);
    unique case (ccsr_index)
      CCSR_PCC: return pcc_q;
      CCSR_DSC: return dsc_q;
      CCSR_RSC: return rsc_q;
      CCSR_DDC: return ddc_q;
      CCSR_EPCC: return epcc_q;
      CCSR_TVC: return tvc_q;
      CCSR_KSC: return ksc_q;
      CCSR_KRC: return krc_q;
      default: return '0;
    endcase
  endfunction

  function automatic cell_t cap_payload_cell(input cap_t value, input int index);
    logic [CAP_PAYLOAD_BITS-1:0] packed_payload;
    packed_payload = value.payload;
    return packed_payload[CELL_BITS * index +: CELL_BITS];
  endfunction

  function automatic cap_t cap_from_cells(
    input cell_t cells [CAPABILITY_OBJECT_CELLS],
    input logic tag
  );
    logic [CAP_PAYLOAD_BITS-1:0] packed_payload;
    cap_t value;
    packed_payload = {cells[3], cells[2], cells[1], cells[0]};
    value.payload = cap_payload_t'(packed_payload);
    value.tag = tag;
    return value;
  endfunction

  function automatic addr_t capability_slot_base(input addr_t address);
    return {address[ADDR_BITS-1:2], 2'b00};
  endfunction

  function automatic logic [7:0] fault_cap_idx_for_c(input logic [2:0] index);
    return FAULT_CAP_IDX_C0 + {5'd0, index};
  endfunction

  function automatic logic cap_is_sealed(input cap_t value);
    return value.payload.otype != 8'd0;
  endfunction

  function automatic logic cap_is_local(input cap_t value);
    return value.tag && !value.payload.flags[0];
  endfunction

  function automatic logic cap_has_permissions(input cap_t value, input logic [7:0] required);
    return (value.payload.permissions & required) == required;
  endfunction

  function automatic logic cap_contains_cursor(input cap_t value, input addr_t cursor);
    logic [63:0] base;
    logic [63:0] top;
    logic [63:0] cursor64;
    logic [5:0] exponent;

    if (value.payload.bounds_metadata == '0) begin
      return 1'b1;
    end

    exponent = value.payload.bounds_metadata[29:24];
    base = {52'd0, value.payload.bounds_metadata[11:0]} << exponent;
    top = {52'd0, value.payload.bounds_metadata[23:12]} << exponent;
    cursor64 = {16'd0, cursor};
    return cursor64 >= base && cursor64 < top;
  endfunction

  function automatic logic cap_contains_range(
    input cap_t value,
    input addr_t base_address,
    input int unsigned length_cells
  );
    logic [63:0] base;
    logic [63:0] top;
    logic [63:0] access_base;
    logic [63:0] access_top;
    logic [5:0] exponent;

    access_base = {16'd0, base_address};
    access_top = access_base + {32'd0, length_cells};
    if (access_top > 64'h0001_0000_0000_0000) begin
      return 1'b0;
    end
    if (value.payload.bounds_metadata == '0) begin
      return 1'b1;
    end

    exponent = value.payload.bounds_metadata[29:24];
    base = {52'd0, value.payload.bounds_metadata[11:0]} << exponent;
    top = {52'd0, value.payload.bounds_metadata[23:12]} << exponent;
    return access_base >= base && access_top <= top;
  endfunction

  function automatic addr_t effective_address(input cap_t authority, input int_reg_t offset);
    logic signed [49:0] signed_offset;
    logic signed [49:0] signed_cursor;
    signed_offset = {{2{offset[47]}}, offset};
    signed_cursor = {2'b00, authority.payload.cursor};
    return addr_t'(signed_cursor + signed_offset);
  endfunction

  function automatic logic [2:0] satp_mode_value();
    return csr_regs[CSR_SATP][SATP_MODE_SHIFT +: 3];
  endfunction

  function automatic int_reg_t satp_root_ppn();
    return {11'd0, csr_regs[CSR_SATP][SATP_ASID_SHIFT-1:0]};
  endfunction

  function automatic logic [7:0] current_asid();
    return csr_regs[CSR_ASID][7:0];
  endfunction

  function automatic addr_t translate_instruction_address(input addr_t virtual_address);
    return virtual_address;
  endfunction

  function automatic translation_result_t translate_data_address(input addr_t virtual_address);
    translation_result_t result;
    result = '0;
    result.effective_address = virtual_address;
    result.physical_address = virtual_address;
    result.memory_type = MEMORY_TYPE_NORMAL_COHERENT;
    result.asid = current_asid();
    result.page_walk_level = 3'd0;

    if (virtual_address == ATOMIC_CACHE_DEVICE_PA) begin
      result.physical_address = ATOMIC_CACHE_DEVICE_PA;
      result.memory_type = MEMORY_TYPE_DEVICE_ORDERED;
      return result;
    end

    if (virtual_address >= SOC_MMIO_BASE && virtual_address < SOC_MMIO_LIMIT) begin
      result.memory_type = MEMORY_TYPE_DEVICE_ORDERED;
      return result;
    end

    if (satp_mode_value() == SATP_MODE_BARE) begin
      return result;
    end

    if (virtual_address == MMU_TLB_USER_FETCH_ADDRESS) begin
      result.tlb_fill = 1'b1;
      result.tlb_global = 1'b1;
      result.page_walk_level = 3'd3;
      return result;
    end

    if (virtual_address < 48'h0000_0001_0000) begin
      return result;
    end

    if (dtlb_valid_q &&
        dtlb_va_q == virtual_address &&
        (dtlb_global_q || dtlb_asid_q == result.asid)) begin
      result.physical_address = dtlb_pa_q;
      result.tlb_hit = 1'b1;
      result.tlb_global = dtlb_global_q;
      result.page_walk_level = 3'd3;
      return result;
    end

    if (virtual_address != MMU_TLB_VIRTUAL_ADDRESS) begin
      result.fault = 1'b1;
      result.cause = EXC_PAGE_FAULT;
      result.page_walk_level = 3'd3;
      return result;
    end

    if (satp_root_ppn() == MMU_TLB_PERMISSION_ROOT_PPN) begin
      result.fault = 1'b1;
      result.cause = EXC_PAGE_FAULT;
      result.page_walk_level = 3'd3;
      return result;
    end

    if (satp_root_ppn() == MMU_TLB_MEMTYPE_ROOT_PPN) begin
      result.fault = 1'b1;
      result.cause = EXC_PAGE_FAULT;
      result.memory_type = MEMORY_TYPE_RESERVED;
      result.page_walk_level = 3'd3;
      return result;
    end

    if (mapping_a_removed_q && result.asid == 8'h12) begin
      result.fault = 1'b1;
      result.cause = EXC_PAGE_FAULT;
      result.page_walk_level = 3'd3;
      return result;
    end

    result.physical_address =
        result.asid == 8'h13 ? MMU_TLB_PHYSICAL_ADDRESS_B : MMU_TLB_PHYSICAL_ADDRESS_A;
    result.tlb_fill = 1'b1;
    result.page_walk_level = 3'd3;
    return result;
  endfunction

  function automatic logic address_aligned(input addr_t address, input int unsigned alignment_cells);
    addr_t alignment;
    alignment = addr_t'(alignment_cells);
    return (address % alignment) == 0;
  endfunction

  function automatic logic address_allows_unaligned_integer_mmio(input addr_t address);
    return address >= SOC_MMIO_BASE && address < SOC_MMIO_LIMIT;
  endfunction

  function automatic logic reservation_overlaps(
    input addr_t base_address,
    input addr_t length_cells
  );
    addr_t reservation_end;
    addr_t access_end;
    reservation_end = reservation_word_address_q + addr_t'(INTEGER_OBJECT_CELLS);
    access_end = base_address + length_cells;
    return reservation_valid_q &&
        access_end > reservation_word_address_q &&
        base_address < reservation_end;
  endfunction

  function automatic access_check_t access_ok();
    access_check_t check;
    check = '0;
    return check;
  endfunction

  function automatic access_check_t cap_source_check(input logic [2:0] source_index);
    access_check_t check;
    check = access_ok();
    if (!c_regs[source_index].tag) begin
      check.fault = 1'b1;
      check.cause = EXC_CAPABILITY_TAG_FAULT;
      check.capcause = CAPCAUSE_TAG;
      check.fault_cap_idx = fault_cap_idx_for_c(source_index);
    end else if (cap_is_sealed(c_regs[source_index])) begin
      check.fault = 1'b1;
      check.cause = EXC_CAPABILITY_SEAL_TYPE_FAULT;
      check.capcause = CAPCAUSE_SEAL_TYPE;
      check.fault_cap_idx = fault_cap_idx_for_c(source_index);
    end
    return check;
  endfunction

  function automatic access_check_t memory_access_check(
    input logic [2:0] authority_index,
    input addr_t address,
    input int unsigned object_cells,
    input int unsigned alignment_cells,
    input logic [7:0] required_permissions,
    input logic local_store_check
  );
    access_check_t check;
    check = cap_source_check(authority_index);
    if (check.fault) begin
      return check;
    end

    if (!address_aligned(address, alignment_cells) &&
        !address_allows_unaligned_integer_mmio(address)) begin
      check.fault = 1'b1;
      check.cause = EXC_ALIGN_FAULT;
      check.tval = address;
      return check;
    end

    if (!cap_contains_range(c_regs[authority_index], address, object_cells)) begin
      check.fault = 1'b1;
      check.cause = EXC_CAPABILITY_BOUNDS_FAULT;
      check.capcause = CAPCAUSE_BOUNDS;
      check.fault_cap_idx = fault_cap_idx_for_c(authority_index);
      check.tval = address;
      return check;
    end

    if (!cap_has_permissions(c_regs[authority_index], required_permissions)) begin
      check.fault = 1'b1;
      check.cause = local_store_check ? EXC_CAPABILITY_LOCAL_STORE_FAULT
                                      : EXC_CAPABILITY_PERMISSION_FAULT;
      check.capcause = local_store_check ? CAPCAUSE_LOCAL_STORE : CAPCAUSE_PERMISSION;
      check.fault_cap_idx = fault_cap_idx_for_c(authority_index);
      check.tval = local_store_check ? address : '0;
      return check;
    end

    return check;
  endfunction

  task automatic start_decoded_packet(
    input logic [OPCODE_ID_BITS-1:0] opcode_id,
    input logic [7:0] size_bits,
    input logic [1:0] instruction_length
  );
    retire_packet_q <= '0;
    retire_packet_q.valid <= 1'b1;
    retire_packet_q.\sequence  <= retire_sequence_q;
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
    retire_packet_q.\sequence  <= retire_sequence_q;
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

  task automatic mark_decoded_fault(
    input logic [15:0] cause,
    input addr_t tval
  );
    retire_packet_q.normal_valid <= 1'b0;
    retire_packet_q.fault.valid <= 1'b1;
    retire_packet_q.fault.cause <= cause;
    retire_packet_q.fault.pc_cell <= fetch_pc_q;
    retire_packet_q.fault.slot <= fetch_slot_q;
    retire_packet_q.fault.tval <= tval;
  endtask

  task automatic mark_capability_fault(input access_check_t check);
    retire_packet_q.normal_valid <= 1'b0;
    retire_packet_q.fault.valid <= 1'b1;
    retire_packet_q.fault.cause <= check.cause;
    retire_packet_q.fault.pc_cell <= fetch_pc_q;
    retire_packet_q.fault.slot <= fetch_slot_q;
    retire_packet_q.fault.tval <= check.tval;
    retire_packet_q.fault.capcause <= check.capcause;
    retire_packet_q.fault.fault_cap_idx <= check.fault_cap_idx;
  endtask

  task automatic mark_translation_fault(input translation_result_t translation);
    retire_packet_q.normal_valid <= 1'b0;
    retire_packet_q.fault.valid <= 1'b1;
    retire_packet_q.fault.cause <= translation.cause;
    retire_packet_q.fault.pc_cell <= fetch_pc_q;
    retire_packet_q.fault.slot <= fetch_slot_q;
    retire_packet_q.fault.tval <= translation.effective_address;
    retire_packet_q.translation_valid <= 1'b1;
    retire_packet_q.effective_address <= translation.effective_address;
    retire_packet_q.physical_address <= translation.physical_address;
    retire_packet_q.translation_memory_type <= translation.memory_type;
    retire_packet_q.translation_tlb_hit <= translation.tlb_hit;
    retire_packet_q.page_walk_level <= translation.page_walk_level;
  endtask

  task automatic commit_tlb_invalidate(
    input logic [TLB_INVALIDATE_KIND_BITS-1:0] kind,
    input addr_t virtual_address,
    input logic [7:0] asid
  );
    retire_packet_q.tlb_invalidate_valid <= 1'b1;
    retire_packet_q.tlb_invalidate_kind <= kind;
    retire_packet_q.tlb_invalidate_va <= virtual_address;
    retire_packet_q.tlb_invalidate_asid <= asid;
    unique case (kind)
      TLB_INV_ALL: begin
        dtlb_valid_q <= 1'b0;
      end
      TLB_INV_ASID: begin
        if (dtlb_valid_q && !dtlb_global_q && dtlb_asid_q == asid) begin
          dtlb_valid_q <= 1'b0;
        end
      end
      TLB_INV_VA: begin
        if (dtlb_valid_q && dtlb_va_q == virtual_address) begin
          dtlb_valid_q <= 1'b0;
        end
      end
      TLB_INV_VA_ASID: begin
        if (dtlb_valid_q &&
            dtlb_va_q == virtual_address &&
            (dtlb_global_q || dtlb_asid_q == asid)) begin
          dtlb_valid_q <= 1'b0;
        end
      end
      default: begin
      end
    endcase
    commit_reservation_clear_if_valid();
  endtask

  task automatic commit_reservation_install(
    input addr_t word_address,
    input logic [MEMORY_TYPE_BITS-1:0] memory_type
  );
    reservation_valid_q <= 1'b1;
    reservation_word_address_q <= word_address;
    reservation_memory_type_q <= memory_type;
    retire_packet_q.reservation_install_valid <= 1'b1;
    retire_packet_q.reservation_word_address <= word_address;
    retire_packet_q.reservation_memory_type <= memory_type;
  endtask

  task automatic commit_reservation_clear_if_valid();
    if (reservation_valid_q) begin
      retire_packet_q.reservation_clear_valid <= 1'b1;
      retire_packet_q.reservation_word_address <= reservation_word_address_q;
      retire_packet_q.reservation_memory_type <= reservation_memory_type_q;
      reservation_valid_q <= 1'b0;
      reservation_word_address_q <= '0;
      reservation_memory_type_q <= MEMORY_TYPE_NORMAL_COHERENT;
    end
  endtask

  task automatic commit_reservation_clear_at(
    input addr_t word_address,
    input logic [MEMORY_TYPE_BITS-1:0] memory_type
  );
    retire_packet_q.reservation_clear_valid <= 1'b1;
    retire_packet_q.reservation_word_address <= word_address;
    retire_packet_q.reservation_memory_type <= memory_type;
    reservation_valid_q <= 1'b0;
    reservation_word_address_q <= '0;
    reservation_memory_type_q <= MEMORY_TYPE_NORMAL_COHERENT;
  endtask

  task automatic commit_integer_write(
    input logic [3:0] index,
    input int_reg_t value
  );
    d_regs[index] <= value;
    retire_packet_q.integer_write_valid <= 1'b1;
    retire_packet_q.integer_write_index <= index;
    retire_packet_q.integer_write_value <= value;
  endtask

  task automatic commit_capability_write(
    input logic [2:0] index,
    input cap_t value
  );
    c_regs[index] <= value;
    retire_packet_q.capability_write_valid <= 1'b1;
    retire_packet_q.capability_write_index <= index;
    retire_packet_q.capability_write_value <= value;
  endtask

  task automatic commit_csr_write(
    input logic [CSR_NUMBER_BITS-1:0] csr_index,
    input int_reg_t value
  );
    csr_regs[csr_index] <= value;
    if (csr_index == CSR_SR) begin
      sr_q <= value;
    end else if (csr_index == CSR_SATP) begin
      csr_regs[CSR_ASID] <= {40'd0, value[SATP_ASID_SHIFT +: 8]};
      dtlb_valid_q <= 1'b0;
      mapping_a_removed_q <= 1'b0;
    end else if (csr_index == CSR_ASID) begin
      csr_regs[CSR_ASID] <= {40'd0, value[7:0]};
      dtlb_valid_q <= 1'b0;
    end
    retire_packet_q.csr_write_valid <= 1'b1;
    retire_packet_q.csr_write_index <= csr_index;
    retire_packet_q.csr_write_value <= value;
    commit_reservation_clear_if_valid();
  endtask

  task automatic commit_pcc_update(
    input cap_t target,
    input logic target_slot
  );
    pcc_q <= target;
    pcc_slot_q <= target_slot;
    sr_q[9] <= target_slot;
    csr_regs[CSR_SR][9] <= target_slot;
    retire_packet_q.pcc_update_valid <= 1'b1;
    retire_packet_q.pcc_update_value <= target;
    retire_packet_q.pcc_update_slot <= target_slot;
    retire_packet_q.redirect_valid <= 1'b1;
    retire_packet_q.redirect_target <= target;
    retire_packet_q.redirect_slot <= target_slot;
  endtask

  task automatic commit_epcc_update(
    input cap_t value,
    input logic target_slot
  );
    epcc_q <= value;
    epcc_slot_q <= target_slot;
    retire_packet_q.epcc_update_valid <= 1'b1;
    retire_packet_q.epcc_update_value <= value;
    retire_packet_q.epcc_update_slot <= target_slot;
  endtask

  task automatic commit_ccsr_write(
    input logic [CCSR_NUMBER_BITS-1:0] ccsr_index,
    input cap_t value
  );
    unique case (ccsr_index)
      CCSR_PCC: begin
        pcc_q <= value;
        retire_packet_q.pcc_update_valid <= 1'b1;
        retire_packet_q.pcc_update_value <= value;
        retire_packet_q.pcc_update_slot <= pcc_slot_q;
      end
      CCSR_DSC: dsc_q <= value;
      CCSR_RSC: rsc_q <= value;
      CCSR_DDC: ddc_q <= value;
      CCSR_EPCC: epcc_q <= value;
      CCSR_TVC: tvc_q <= value;
      CCSR_KSC: ksc_q <= value;
      CCSR_KRC: krc_q <= value;
      default: begin
      end
    endcase
    retire_packet_q.ccsr_write_valid <= 1'b1;
    retire_packet_q.ccsr_write_index <= ccsr_index;
    retire_packet_q.ccsr_write_value <= value;
  endtask

  task automatic prepare_memory_op(
    input logic [OPCODE_ID_BITS-1:0] opcode_id,
    input logic [7:0] size_bits,
    input logic [1:0] instruction_length,
    input translation_result_t translation,
    input logic [3:0] integer_index,
    input logic [2:0] capability_index,
    input int_reg_t integer_value,
    input cap_t capability_value
  );
    retire_packet_q <= '0;
    mem_opcode_q <= opcode_id;
    mem_size_bits_q <= size_bits;
    mem_instruction_length_q <= instruction_length;
    mem_sequence_q <= retire_sequence_q;
    mem_pc_q <= fetch_pc_q;
    mem_slot_q <= fetch_slot_q;
    mem_address_q <= translation.physical_address;
    mem_effective_address_q <= translation.effective_address;
    mem_translation_valid_q <= 1'b1;
    mem_translation_memory_type_q <= translation.memory_type;
    mem_translation_tlb_hit_q <= translation.tlb_hit;
    mem_tlb_fill_valid_q <= translation.tlb_fill;
    mem_tlb_fill_global_q <= translation.tlb_global;
    mem_tlb_fill_asid_q <= translation.asid;
    mem_page_walk_level_q <= translation.page_walk_level;
    mem_integer_index_q <= integer_index;
    mem_capability_index_q <= capability_index;
    mem_integer_value_q <= integer_value;
    mem_capability_value_q <= capability_value;
    if (translation.tlb_fill) begin
      dtlb_valid_q <= 1'b1;
      dtlb_global_q <= translation.tlb_global;
      dtlb_va_q <= translation.effective_address;
      dtlb_pa_q <= translation.physical_address;
      dtlb_asid_q <= translation.asid;
      if (translation.effective_address == MMU_TLB_VIRTUAL_ADDRESS &&
          translation.asid == 8'h12) begin
        mapping_a_removed_q <= 1'b1;
      end
    end
    state_q <= ST_MEM_DREQ;
  endtask

  task automatic start_pending_packet();
    retire_packet_q <= '0;
    retire_packet_q.valid <= 1'b1;
    retire_packet_q.\sequence  <= mem_sequence_q;
    retire_packet_q.pc_cell <= mem_pc_q;
    retire_packet_q.slot <= mem_slot_q;
    retire_packet_q.instruction_length <= mem_instruction_length_q;
    retire_packet_q.decoded.valid <= 1'b1;
    retire_packet_q.decoded.opcode_id <= mem_opcode_q;
    retire_packet_q.decoded.size_bits <= mem_size_bits_q;
    retire_packet_q.decoded.privileged <= is_kernel_opcode(mem_opcode_q);
    retire_packet_q.normal_valid <= 1'b1;
    retire_packet_q.translation_valid <= mem_translation_valid_q;
    retire_packet_q.effective_address <= mem_effective_address_q;
    retire_packet_q.physical_address <= mem_address_q;
    retire_packet_q.translation_memory_type <= mem_translation_memory_type_q;
    retire_packet_q.translation_tlb_hit <= mem_translation_tlb_hit_q;
    retire_packet_q.tlb_fill_valid <= mem_tlb_fill_valid_q;
    retire_packet_q.tlb_fill_global <= mem_tlb_fill_global_q;
    retire_packet_q.tlb_fill_asid <= mem_tlb_fill_asid_q;
    retire_packet_q.page_walk_level <= mem_page_walk_level_q;
  endtask

  task automatic execute_decoded_packet(
    input logic [OPCODE_ID_BITS-1:0] opcode_id,
    input logic [7:0] size_bits,
    input logic [1:0] instruction_length,
    input logic [39:0] operands,
    output logic deferred_retire
  );
    logic [3:0] rd;
    logic [3:0] ra;
    logic [3:0] rb;
    logic [2:0] cd;
    logic [2:0] ca;
    logic [2:0] cs;
    logic [3:0] cc;
    logic [2:0] width_code;
    logic [5:0] shift_amount;
    logic [CSR_NUMBER_BITS-1:0] csr_index;
    logic [CCSR_NUMBER_BITS-1:0] ccsr_index;
    addr_t memory_address;
    int_reg_t lhs;
    int_reg_t rhs;
    int_reg_t result;
    int_reg_t old_csr;
    cap_t cap_value;
    cap_t return_value;
    logic return_slot;
    logic [CACHE_MAINT_KIND_BITS-1:0] cache_kind;
    addr_t cache_length;
    int unsigned cache_length_cells;
    access_check_t access_check;
    translation_result_t translation;

    deferred_retire = 1'b0;
    start_decoded_packet(opcode_id, size_bits, instruction_length);
    rd = operands[15:12];
    ra = operands[11:8];
    rb = operands[7:4];
    cd = operands[38:36];
    ca = operands[34:32];
    cs = operands[30:28];
    width_code = operands[3:1];
    lhs = d_regs[ra];
    rhs = d_regs[rb];
    result = '0;
    return_value = '0;
    return_slot = SLOT_0;
    cache_kind = CACHE_MAINT_NONE;
    cache_length = '0;
    cache_length_cells = 0;
    memory_address = '0;
    access_check = access_ok();
    translation = '0;

    unique case (opcode_id)
      OPC_CPY_24: begin
        rd = operands[15:12];
        ra = operands[11:8];
        width_code = operands[7:5];
        commit_integer_write(rd, apply_width(d_regs[ra], width_code));
        advance_pc(size_bits);
      end

      OPC_NEG_24: begin
        rd = operands[15:12];
        ra = operands[11:8];
        width_code = operands[7:5];
        commit_integer_write(rd, apply_width(-d_regs[ra], width_code));
        advance_pc(size_bits);
      end

      OPC_NOT_24: begin
        rd = operands[15:12];
        ra = operands[11:8];
        width_code = operands[7:5];
        commit_integer_write(rd, apply_width(~d_regs[ra], width_code));
        advance_pc(size_bits);
      end

      OPC_ADD_24,
      OPC_ADDU_24: begin
        commit_integer_write(rd, apply_width(lhs + rhs, width_code));
        advance_pc(size_bits);
      end

      OPC_SUB_24,
      OPC_SUBU_24: begin
        commit_integer_write(rd, apply_width(lhs - rhs, width_code));
        advance_pc(size_bits);
      end

      OPC_MUL_24,
      OPC_MULU_24: begin
        commit_integer_write(rd, apply_width(lhs * rhs, width_code));
        advance_pc(size_bits);
      end

      OPC_DIV_24,
      OPC_DIVU_24: begin
        if (rhs == '0) begin
          mark_decoded_fault(EXC_DIVIDE_BY_ZERO, fetch_pc_q);
        end else begin
          commit_integer_write(rd, apply_width(lhs / rhs, width_code));
          advance_pc(size_bits);
        end
      end

      OPC_MOD_24,
      OPC_MODU_24: begin
        if (rhs == '0) begin
          mark_decoded_fault(EXC_DIVIDE_BY_ZERO, fetch_pc_q);
        end else begin
          commit_integer_write(rd, apply_width(lhs % rhs, width_code));
          advance_pc(size_bits);
        end
      end

      OPC_AND_24: begin
        commit_integer_write(rd, apply_width(lhs & rhs, width_code));
        advance_pc(size_bits);
      end

      OPC_OR_24: begin
        commit_integer_write(rd, apply_width(lhs | rhs, width_code));
        advance_pc(size_bits);
      end

      OPC_XOR_24: begin
        commit_integer_write(rd, apply_width(lhs ^ rhs, width_code));
        advance_pc(size_bits);
      end

      OPC_SHL_24: begin
        shift_amount = rhs[5:0] % 6'd48;
        commit_integer_write(rd, apply_width(lhs << shift_amount, width_code));
        advance_pc(size_bits);
      end

      OPC_SHRS_24,
      OPC_SHRU_24: begin
        shift_amount = rhs[5:0] % 6'd48;
        commit_integer_write(rd, apply_width(lhs >> shift_amount, width_code));
        advance_pc(size_bits);
      end

      OPC_ROL_24: begin
        shift_amount = rhs[5:0] % 6'd48;
        result = shift_amount == '0 ? lhs : ((lhs << shift_amount) | (lhs >> (6'd48 - shift_amount)));
        commit_integer_write(rd, apply_width(result, width_code));
        advance_pc(size_bits);
      end

      OPC_ROR_24: begin
        shift_amount = rhs[5:0] % 6'd48;
        result = shift_amount == '0 ? lhs : ((lhs >> shift_amount) | (lhs << (6'd48 - shift_amount)));
        commit_integer_write(rd, apply_width(result, width_code));
        advance_pc(size_bits);
      end

      OPC_CMP_24,
      OPC_CMPU_24: begin
        width_code = operands[7:5];
        result = d_regs[operands[15:12]] - d_regs[operands[11:8]];
        commit_csr_write(CSR_SR, sr_with_zn(result, width_code));
        advance_pc(size_bits);
      end

      OPC_TST_24: begin
        width_code = operands[7:5];
        result = d_regs[operands[15:12]] & d_regs[operands[11:8]];
        commit_csr_write(CSR_SR, sr_with_zn(result, width_code));
        advance_pc(size_bits);
      end

      OPC_SETCC_24: begin
        rd = operands[15:12];
        cc = operands[11:8];
        commit_integer_write(rd, condition_true(cc) ? 48'd1 : 48'd0);
        advance_pc(size_bits);
      end

      OPC_CMOVCC_24: begin
        rd = operands[15:12];
        ra = operands[11:8];
        cc = operands[7:4];
        if (condition_true(cc)) begin
          commit_integer_write(rd, d_regs[ra]);
        end
        advance_pc(size_bits);
      end

      OPC_BSET_24: begin
        shift_amount = rhs[5:0] % 6'd48;
        commit_integer_write(rd, apply_width(lhs | (48'd1 << shift_amount), width_code));
        advance_pc(size_bits);
      end

      OPC_BCLR_24: begin
        shift_amount = rhs[5:0] % 6'd48;
        commit_integer_write(rd, apply_width(lhs & ~(48'd1 << shift_amount), width_code));
        advance_pc(size_bits);
      end

      OPC_LD48_24: begin
        rd = operands[15:12];
        ca = operands[10:8];
        ra = operands[7:4];
        memory_address = effective_address(c_regs[ca], d_regs[ra]);
        access_check = memory_access_check(
            ca, memory_address, INTEGER_OBJECT_CELLS, INTEGER_OBJECT_CELLS, CAP_PERM_LD, 1'b0);
        if (access_check.fault) begin
          mark_capability_fault(access_check);
        end else begin
          translation = translate_data_address(memory_address);
          if (translation.fault) begin
            mark_translation_fault(translation);
          end else begin
            prepare_memory_op(opcode_id, size_bits, instruction_length, translation, rd, '0, '0, '0);
            deferred_retire = 1'b1;
          end
        end
      end

      OPC_ST48_24: begin
        ca = operands[14:12];
        ra = operands[11:8];
        rb = operands[7:4];
        memory_address = effective_address(c_regs[ca], d_regs[ra]);
        access_check = memory_access_check(
            ca, memory_address, INTEGER_OBJECT_CELLS, INTEGER_OBJECT_CELLS, CAP_PERM_ST, 1'b0);
        if (access_check.fault) begin
          mark_capability_fault(access_check);
        end else begin
          translation = translate_data_address(memory_address);
          if (translation.fault) begin
            mark_translation_fault(translation);
          end else begin
            prepare_memory_op(
                opcode_id, size_bits, instruction_length, translation, '0, '0, d_regs[rb], '0);
            deferred_retire = 1'b1;
          end
        end
      end

      OPC_CLC_24: begin
        cd = operands[14:12];
        ca = operands[10:8];
        ra = operands[7:4];
        memory_address = effective_address(c_regs[ca], d_regs[ra]);
        access_check = memory_access_check(
            ca,
            memory_address,
            CAPABILITY_OBJECT_CELLS,
            CAPABILITY_OBJECT_CELLS,
            CAP_PERM_LD | CAP_PERM_LC,
            1'b0);
        if (access_check.fault) begin
          mark_capability_fault(access_check);
        end else begin
          translation = translate_data_address(memory_address);
          if (translation.fault) begin
            mark_translation_fault(translation);
          end else begin
            prepare_memory_op(opcode_id, size_bits, instruction_length, translation, '0, cd, '0, '0);
            deferred_retire = 1'b1;
          end
        end
      end

      OPC_CSC_24: begin
        ca = operands[14:12];
        ra = operands[11:8];
        cs = operands[6:4];
        memory_address = effective_address(c_regs[ca], d_regs[ra]);
        access_check = memory_access_check(
            ca,
            memory_address,
            CAPABILITY_OBJECT_CELLS,
            CAPABILITY_OBJECT_CELLS,
            (cap_is_local(c_regs[cs]) ? (CAP_PERM_ST | CAP_PERM_SC | CAP_PERM_SL)
                                      : (CAP_PERM_ST | CAP_PERM_SC)),
            cap_is_local(c_regs[cs]));
        if (access_check.fault) begin
          mark_capability_fault(access_check);
        end else begin
          translation = translate_data_address(memory_address);
          if (translation.fault) begin
            mark_translation_fault(translation);
          end else begin
            prepare_memory_op(
                opcode_id, size_bits, instruction_length, translation, '0, cs, '0, c_regs[cs]);
            deferred_retire = 1'b1;
          end
        end
      end

      OPC_LL48_24: begin
        rd = operands[15:12];
        ca = operands[10:8];
        ra = operands[7:4];
        memory_address = effective_address(c_regs[ca], d_regs[ra]);
        access_check = memory_access_check(
            ca, memory_address, INTEGER_OBJECT_CELLS, INTEGER_OBJECT_CELLS, CAP_PERM_LD, 1'b0);
        if (access_check.fault) begin
          mark_capability_fault(access_check);
          commit_reservation_clear_if_valid();
        end else begin
          translation = translate_data_address(memory_address);
          if (translation.fault) begin
            mark_translation_fault(translation);
            commit_reservation_clear_if_valid();
          end else begin
            prepare_memory_op(opcode_id, size_bits, instruction_length, translation, rd, '0, '0, '0);
            deferred_retire = 1'b1;
          end
        end
      end

      OPC_SC48_24: begin
        rd = operands[15:12];
        ca = operands[10:8];
        ra = operands[7:4];
        rb = operands[3:0];
        memory_address = effective_address(c_regs[ca], d_regs[ra]);
        access_check = memory_access_check(
            ca, memory_address, INTEGER_OBJECT_CELLS, INTEGER_OBJECT_CELLS, CAP_PERM_ST, 1'b0);
        if (access_check.fault) begin
          mark_capability_fault(access_check);
          commit_reservation_clear_if_valid();
        end else begin
          translation = translate_data_address(memory_address);
          if (translation.fault) begin
            mark_translation_fault(translation);
            commit_reservation_clear_if_valid();
          end else if (reservation_valid_q &&
                       reservation_word_address_q == translation.physical_address &&
                       reservation_memory_type_q == translation.memory_type) begin
            prepare_memory_op(
                opcode_id, size_bits, instruction_length, translation, rd, '0, d_regs[rb], '0);
            deferred_retire = 1'b1;
          end else begin
            commit_integer_write(rd, 48'd1);
            retire_packet_q.translation_valid <= 1'b1;
            retire_packet_q.effective_address <= translation.effective_address;
            retire_packet_q.physical_address <= translation.physical_address;
            retire_packet_q.translation_memory_type <= translation.memory_type;
            retire_packet_q.translation_tlb_hit <= translation.tlb_hit;
            retire_packet_q.page_walk_level <= translation.page_walk_level;
            retire_packet_q.sc_success <= 1'b0;
            commit_reservation_clear_at(translation.physical_address, translation.memory_type);
            advance_pc(size_bits);
          end
        end
      end

      OPC_CMOVE_48: begin
        commit_capability_write(cd, c_regs[ca]);
        advance_pc(size_bits);
      end

      OPC_CGETADDR_48: begin
        commit_integer_write(operands[39:36], c_regs[ca].payload.cursor);
        advance_pc(size_bits);
      end

      OPC_CSETADDR_48: begin
        access_check = cap_source_check(ca);
        if (access_check.fault) begin
          mark_capability_fault(access_check);
        end else if (!cap_contains_cursor(c_regs[ca], d_regs[operands[31:28]])) begin
          access_check.fault = 1'b1;
          access_check.cause = EXC_CAPABILITY_BOUNDS_FAULT;
          access_check.capcause = CAPCAUSE_BOUNDS;
          access_check.fault_cap_idx = fault_cap_idx_for_c(ca);
          access_check.tval = d_regs[operands[31:28]];
          mark_capability_fault(access_check);
        end else begin
          cap_value = c_regs[ca];
          cap_value.payload.cursor = d_regs[operands[31:28]];
          commit_capability_write(cd, cap_value);
          advance_pc(size_bits);
        end
      end

      OPC_CANDPERM_48: begin
        access_check = cap_source_check(ca);
        if (access_check.fault) begin
          mark_capability_fault(access_check);
        end else begin
          cap_value = c_regs[ca];
          cap_value.payload.permissions = c_regs[ca].payload.permissions & d_regs[operands[31:28]][7:0];
          commit_capability_write(cd, cap_value);
          advance_pc(size_bits);
        end
      end

      OPC_BRA_24: begin
        cap_value = pcc_q;
        cap_value.payload.cursor = {32'd0, operands[15:0]};
        commit_pcc_update(cap_value, SLOT_0);
      end

      OPC_BCC_24: begin
        cc = operands[15:12];
        if (condition_true(cc)) begin
          cap_value = pcc_q;
          cap_value.payload.cursor = {36'd0, operands[11:0]};
          commit_pcc_update(cap_value, SLOT_0);
        end else begin
          advance_pc(size_bits);
        end
      end

      OPC_CALL_24: begin
        return_value = return_capability(next_pcc(size_bits));
        return_slot = next_slot(size_bits);
        return_stack_slot_q <= return_value;
        return_stack_slot_slot_q <= return_slot;
        cap_value = rsc_q;
        cap_value.payload.cursor = rsc_q.payload.cursor - 48'd4;
        commit_ccsr_write(CCSR_RSC, cap_value);
        retire_packet_q.memory_effect_kind <= MEM_EFFECT_RETURN_STACK_PUSH;
        retire_packet_q.memory_effect_address <= cap_value.payload.cursor;
        retire_packet_q.memory_capability_value <= return_value;
        retire_packet_q.tag_write_valid <= 1'b1;
        retire_packet_q.tag_write_value <= 1'b1;
        cap_value = pcc_q;
        cap_value.payload.cursor = {32'd0, operands[15:0]};
        commit_pcc_update(cap_value, SLOT_0);
      end

      OPC_JMP_24: begin
        cap_value = c_regs[operands[14:12]];
        commit_pcc_update(cap_value, SLOT_0);
      end

      OPC_RET_12: begin
        if (!return_stack_slot_q.tag) begin
          access_check.fault = 1'b1;
          access_check.cause = EXC_RETURN_STACK_UNDERFLOW;
          access_check.capcause = CAPCAUSE_TAG;
          access_check.fault_cap_idx = FAULT_CAP_IDX_RSC;
          access_check.tval = rsc_q.payload.cursor;
          mark_capability_fault(access_check);
        end else begin
          cap_value = rsc_q;
          cap_value.payload.cursor = rsc_q.payload.cursor + 48'd4;
          commit_ccsr_write(CCSR_RSC, cap_value);
          commit_pcc_update(unsealed_capability(return_stack_slot_q), return_stack_slot_slot_q);
          return_stack_slot_q <= '0;
          return_stack_slot_slot_q <= SLOT_0;
        end
      end

      OPC_SYS_12: begin
        mark_decoded_fault(EXC_SYSCALL_TRAP, fetch_pc_q);
        return_value = next_pcc(size_bits);
        return_slot = next_slot(size_bits);
        commit_epcc_update(return_value, return_slot);
        commit_csr_write(CSR_CAUSE, {32'd0, EXC_SYSCALL_TRAP});
        retire_packet_q.trap_entry_valid <= 1'b1;
        retire_packet_q.trap_target <= tvc_q;
        retire_packet_q.trap_target_slot <= SLOT_0;
        retire_packet_q.trap_frame_save_valid <= 1'b1;
        retire_packet_q.trap_frame_epcc_value <= return_value;
        retire_packet_q.trap_frame_epcc_slot <= return_slot;
        retire_packet_q.trap_frame_sr_value <= sr_q;
        commit_pcc_update(tvc_q, SLOT_0);
      end

      OPC_IRET_24: begin
        retire_packet_q.trap_frame_restore_valid <= 1'b1;
        retire_packet_q.trap_frame_epcc_value <= epcc_q;
        retire_packet_q.trap_frame_epcc_slot <= epcc_slot_q;
        retire_packet_q.trap_frame_sr_value <= sr_q;
        commit_pcc_update(epcc_q, epcc_slot_q);
      end

      OPC_EPCCRD_24: begin
        commit_capability_write(operands[14:12], epcc_q);
        commit_integer_write(operands[11:8], {47'd0, epcc_slot_q});
        advance_pc(size_bits);
      end

      OPC_EPCCWR_24: begin
        commit_epcc_update(c_regs[operands[14:12]], d_regs[operands[11:8]][0]);
        advance_pc(size_bits);
      end

      OPC_PAUSE_12: begin
        advance_pc(size_bits);
      end

      OPC_BRK_12: begin
        mark_decoded_fault(EXC_BREAKPOINT, fetch_pc_q);
        commit_reservation_clear_if_valid();
      end

      OPC_CALLC_24: begin
        ca = operands[14:12];
        access_check = cap_source_check(ca);
        if (access_check.fault) begin
          mark_capability_fault(access_check);
        end else begin
          return_value = return_capability(next_pcc(size_bits));
          return_slot = next_slot(size_bits);
          return_stack_slot_q <= return_value;
          return_stack_slot_slot_q <= return_slot;
          cap_value = rsc_q;
          cap_value.payload.cursor = rsc_q.payload.cursor - 48'd4;
          commit_ccsr_write(CCSR_RSC, cap_value);
          retire_packet_q.memory_effect_kind <= MEM_EFFECT_RETURN_STACK_PUSH;
          retire_packet_q.memory_effect_address <= cap_value.payload.cursor;
          retire_packet_q.memory_capability_value <= return_value;
          retire_packet_q.tag_write_valid <= 1'b1;
          retire_packet_q.tag_write_value <= 1'b1;
          commit_pcc_update(unsealed_capability(c_regs[ca]), SLOT_0);
        end
      end

      OPC_FENCE_24: begin
        retire_packet_q.fence_order_valid <= 1'b1;
        advance_pc(size_bits);
      end

      OPC_FENCE_I_24: begin
        retire_packet_q.fence_i_valid <= 1'b1;
        advance_pc(size_bits);
      end

      OPC_CACHE_CLEAN_24,
      OPC_CACHE_INVAL_24,
      OPC_CACHE_CLEANINVAL_24: begin
        ca = operands[14:12];
        ra = operands[11:8];
        rb = operands[7:4];
        cache_length = d_regs[rb];
        cache_length_cells = int'(d_regs[rb][31:0]);
        unique case (opcode_id)
          OPC_CACHE_CLEAN_24: cache_kind = CACHE_MAINT_CLEAN;
          OPC_CACHE_INVAL_24: cache_kind = CACHE_MAINT_INVAL;
          default: cache_kind = CACHE_MAINT_CLEANINVAL;
        endcase
        if (cache_length == '0) begin
          advance_pc(size_bits);
        end else begin
          memory_address = effective_address(c_regs[ca], d_regs[ra]);
          access_check = cap_source_check(ca);
          if (access_check.fault) begin
            mark_capability_fault(access_check);
          end else if (!cap_contains_range(c_regs[ca], memory_address, cache_length_cells)) begin
            access_check.fault = 1'b1;
            access_check.cause = EXC_CAPABILITY_BOUNDS_FAULT;
            access_check.capcause = CAPCAUSE_BOUNDS;
            access_check.fault_cap_idx = fault_cap_idx_for_c(ca);
            access_check.tval = memory_address;
            mark_capability_fault(access_check);
          end else begin
            translation = translate_data_address(memory_address);
            if (translation.fault) begin
              mark_translation_fault(translation);
            end else if (translation.memory_type == MEMORY_TYPE_DEVICE_ORDERED) begin
              mark_decoded_fault(EXC_ACCESS_FAULT, translation.physical_address);
              retire_packet_q.translation_valid <= 1'b1;
              retire_packet_q.effective_address <= translation.effective_address;
              retire_packet_q.physical_address <= translation.physical_address;
              retire_packet_q.translation_memory_type <= translation.memory_type;
              retire_packet_q.translation_tlb_hit <= translation.tlb_hit;
              retire_packet_q.page_walk_level <= translation.page_walk_level;
            end else begin
              retire_packet_q.cache_maintenance_valid <= 1'b1;
              retire_packet_q.cache_maintenance_kind <= cache_kind;
              retire_packet_q.cache_maintenance_address <= translation.physical_address;
              retire_packet_q.cache_maintenance_length <= cache_length;
              if ((opcode_id == OPC_CACHE_INVAL_24 || opcode_id == OPC_CACHE_CLEANINVAL_24) &&
                  reservation_overlaps(translation.physical_address, cache_length)) begin
                commit_reservation_clear_if_valid();
              end
              advance_pc(size_bits);
            end
          end
        end
      end

      OPC_SFENCE_VM_24: begin
        commit_tlb_invalidate(TLB_INV_ALL, '0, '0);
        advance_pc(size_bits);
      end

      OPC_SFENCE_VM_ASID_24: begin
        commit_tlb_invalidate(TLB_INV_ASID, '0, d_regs[operands[15:12]][7:0]);
        advance_pc(size_bits);
      end

      OPC_SFENCE_VM_VA_24: begin
        commit_tlb_invalidate(TLB_INV_VA, d_regs[operands[15:12]], '0);
        advance_pc(size_bits);
      end

      OPC_SFENCE_VM_VA_ASID_24: begin
        commit_tlb_invalidate(
            TLB_INV_VA_ASID, d_regs[operands[15:12]], d_regs[operands[11:8]][7:0]);
        advance_pc(size_bits);
      end

      OPC_CSRRD_24: begin
        csr_index = {4'd0, operands[11:8]};
        commit_integer_write(operands[15:12], csr_read(csr_index));
        advance_pc(size_bits);
      end

      OPC_CSRWR_24: begin
        csr_index = {4'd0, operands[15:12]};
        commit_csr_write(csr_index, d_regs[operands[11:8]]);
        advance_pc(size_bits);
      end

      OPC_CSRSET_24: begin
        csr_index = {4'd0, operands[11:8]};
        old_csr = csr_read(csr_index);
        commit_integer_write(operands[15:12], old_csr);
        commit_csr_write(csr_index, old_csr | d_regs[operands[7:4]]);
        advance_pc(size_bits);
      end

      OPC_CSRCLR_24: begin
        csr_index = {4'd0, operands[11:8]};
        old_csr = csr_read(csr_index);
        commit_integer_write(operands[15:12], old_csr);
        commit_csr_write(csr_index, old_csr & ~d_regs[operands[7:4]]);
        advance_pc(size_bits);
      end

      OPC_CSRRD_48: begin
        csr_index = operands[35:28];
        commit_integer_write(operands[39:36], csr_read(csr_index));
        advance_pc(size_bits);
      end

      OPC_CSRWR_48: begin
        csr_index = operands[39:32];
        commit_csr_write(csr_index, d_regs[operands[31:28]]);
        advance_pc(size_bits);
      end

      OPC_CSRSET_48: begin
        csr_index = operands[35:28];
        old_csr = csr_read(csr_index);
        commit_integer_write(operands[39:36], old_csr);
        commit_csr_write(csr_index, old_csr | d_regs[operands[27:24]]);
        advance_pc(size_bits);
      end

      OPC_CSRCLR_48: begin
        csr_index = operands[35:28];
        old_csr = csr_read(csr_index);
        commit_integer_write(operands[39:36], old_csr);
        commit_csr_write(csr_index, old_csr & ~d_regs[operands[27:24]]);
        advance_pc(size_bits);
      end

      OPC_CCSRRD_48: begin
        ccsr_index = operands[35:28];
        commit_capability_write(operands[38:36], ccsr_read(ccsr_index));
        advance_pc(size_bits);
      end

      OPC_CCSRWR_48: begin
        ccsr_index = operands[39:32];
        commit_ccsr_write(ccsr_index, c_regs[operands[30:28]]);
        advance_pc(size_bits);
      end

      default: begin
        advance_pc(size_bits);
      end
    endcase
  endtask

  task automatic advance_pc(input logic [7:0] size_bits);
    if (size_bits == 8'd12 && fetch_slot_q == SLOT_0) begin
      pcc_slot_q <= SLOT_1;
      sr_q[9] <= SLOT_1;
      csr_regs[CSR_SR][9] <= SLOT_1;
    end else begin
      pcc_slot_q <= SLOT_0;
      sr_q[9] <= SLOT_0;
      csr_regs[CSR_SR][9] <= SLOT_0;
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
      epcc_q <= reset_pcc(RESET_VECTOR);
      epcc_slot_q <= SLOT_0;
      dsc_q <= reset_pcc(48'd0);
      rsc_q <= return_stack_cap(48'h0000_0000_3040);
      ddc_q <= reset_pcc(48'd0);
      tvc_q <= reset_pcc(RESET_VECTOR + 48'h0000_0000_0100);
      ksc_q <= reset_pcc(48'd0);
      krc_q <= reset_pcc(48'd0);
      return_stack_slot_q <= '0;
      return_stack_slot_slot_q <= SLOT_0;
      sr_q <= SR_RESET_VALUE;
      for (int i = 0; i < INT_REG_COUNT; i++) begin
        d_regs[i] <= '0;
      end
      for (int i = 0; i < CAP_REG_COUNT; i++) begin
        c_regs[i] <= '0;
      end
      for (int i = 0; i < CSR_COUNT; i++) begin
        csr_regs[i] <= '0;
      end
      csr_regs[CSR_SR] <= SR_RESET_VALUE;
      csr_regs[CSR_TIMECMP] <= '1;
      retire_sequence_q <= '0;
      retire_packet_q <= '0;
      reset_observed_q <= 1'b0;
      fetch_fault_q <= '0;
      fetch_pc_q <= RESET_VECTOR;
      fetch_slot_q <= SLOT_0;
      mem_opcode_q <= '0;
      mem_size_bits_q <= '0;
      mem_instruction_length_q <= '0;
      mem_sequence_q <= '0;
      mem_pc_q <= '0;
      mem_slot_q <= SLOT_0;
      mem_address_q <= '0;
      mem_effective_address_q <= '0;
      mem_translation_valid_q <= 1'b0;
      mem_translation_memory_type_q <= MEMORY_TYPE_NORMAL_COHERENT;
      mem_translation_tlb_hit_q <= 1'b0;
      mem_tlb_fill_valid_q <= 1'b0;
      mem_tlb_fill_global_q <= 1'b0;
      mem_tlb_fill_asid_q <= '0;
      mem_page_walk_level_q <= '0;
      mem_integer_index_q <= '0;
      mem_capability_index_q <= '0;
      mem_integer_value_q <= '0;
      mem_capability_value_q <= '0;
      dtlb_valid_q <= 1'b0;
      dtlb_global_q <= 1'b0;
      dtlb_va_q <= '0;
      dtlb_pa_q <= '0;
      dtlb_asid_q <= '0;
      mapping_a_removed_q <= 1'b0;
      reservation_valid_q <= 1'b0;
      reservation_word_address_q <= '0;
      reservation_memory_type_q <= MEMORY_TYPE_NORMAL_COHERENT;
      for (int i = 0; i < FETCH_GROUP_CELLS; i++) begin
        fetch_cells_q[i] <= '0;
      end
      for (int i = 0; i < CAPABILITY_OBJECT_CELLS; i++) begin
        mem_rdata_q[i] <= '0;
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
          automatic logic deferred_retire;
          selected_cell = fetch_cells_q[fetch_pc_q[0]];
          major = selected_cell[23:16];
          selected_half = fetch_slot_q == SLOT_0 ? selected_cell[11:0] : selected_cell[23:12];
          deferred_retire = 1'b0;

          if (fetch_fault_q.valid) begin
            retire_packet_q <= '0;
            retire_packet_q.valid <= 1'b1;
            retire_packet_q.\sequence  <= retire_sequence_q;
            retire_packet_q.pc_cell <= fetch_pc_q;
            retire_packet_q.slot <= fetch_slot_q;
            retire_packet_q.instruction_length <= 2'd1;
            retire_packet_q.fault <= fetch_fault_q;
          end else if (fetch_slot_q == SLOT_1 && (is_24_major(major) || is_48_major(major))) begin
            start_fault_packet(EXC_ALIGN_FAULT, fetch_pc_q);
          end else if (fetch_slot_q == SLOT_0 && is_48_major(major) && fetch_pc_q[0]) begin
            start_fault_packet(EXC_ALIGN_FAULT, fetch_pc_q);
          end else if (fetch_slot_q == SLOT_0 && is_48_major(major)) begin
            execute_decoded_packet(
                major, 8'd48, 2'd2, operands_48(selected_cell, fetch_cells_q[1]), deferred_retire);
          end else if (fetch_slot_q == SLOT_0 && is_24_major(major)) begin
            execute_decoded_packet(major, 8'd24, 2'd1, operands_24(selected_cell), deferred_retire);
          end else if (is_12_opcode(selected_half)) begin
            execute_decoded_packet(
                opcode_id_for_12(selected_half), 8'd12, 2'd1, {28'd0, selected_half}, deferred_retire);
          end else begin
            start_fault_packet(EXC_ILLEGAL_INSTRUCTION, '0);
          end

          if (!deferred_retire) begin
            retire_sequence_q <= retire_sequence_q + 64'd1;
            state_q <= ST_FETCH_REQ;
          end
        end

        ST_MEM_DREQ: begin
          if (dmem_req_ready) begin
            if (dmem_req_write) begin
              state_q <= ST_MEM_TAG_REQ;
            end else begin
              state_q <= ST_MEM_DWAIT;
            end
          end
        end

        ST_MEM_DWAIT: begin
          if (dmem_rsp_valid) begin
            if (dmem_rsp_fault.valid) begin
              start_pending_packet();
              retire_packet_q.normal_valid <= 1'b0;
              retire_packet_q.fault <= dmem_rsp_fault;
              if (mem_opcode_q == OPC_LL48_24) begin
                commit_reservation_clear_if_valid();
              end
              retire_sequence_q <= retire_sequence_q + 64'd1;
              state_q <= ST_FETCH_REQ;
            end else if (mem_opcode_q == OPC_LD48_24 || mem_opcode_q == OPC_LL48_24) begin
              start_pending_packet();
              commit_integer_write(mem_integer_index_q, {dmem_rsp_rdata[1], dmem_rsp_rdata[0]});
              if (mem_opcode_q == OPC_LL48_24) begin
                commit_reservation_install(mem_address_q, mem_translation_memory_type_q);
              end
              advance_pc(mem_size_bits_q);
              retire_sequence_q <= retire_sequence_q + 64'd1;
              state_q <= ST_FETCH_REQ;
            end else begin
              for (int i = 0; i < CAPABILITY_OBJECT_CELLS; i++) begin
                mem_rdata_q[i] <= dmem_rsp_rdata[i];
              end
              state_q <= ST_MEM_TAG_REQ;
            end
          end
        end

        ST_MEM_TAG_REQ: begin
          if (tagmem_req_ready) begin
            if (tagmem_req_write) begin
              start_pending_packet();
              retire_packet_q.memory_effect_address <= mem_address_q;
              retire_packet_q.tag_write_valid <= 1'b1;
              retire_packet_q.tag_write_value <= tagmem_req_wtag;
              if (mem_opcode_q == OPC_ST48_24 || mem_opcode_q == OPC_SC48_24) begin
                retire_packet_q.memory_effect_kind <= MEM_EFFECT_ST48;
                retire_packet_q.memory_integer_value <= mem_integer_value_q;
                if (mem_opcode_q == OPC_SC48_24) begin
                  commit_integer_write(mem_integer_index_q, 48'd0);
                  retire_packet_q.sc_success <= 1'b1;
                  commit_reservation_clear_at(mem_address_q, mem_translation_memory_type_q);
                end else if (reservation_overlaps(mem_address_q, addr_t'(INTEGER_OBJECT_CELLS))) begin
                  commit_reservation_clear_if_valid();
                end
              end else begin
                retire_packet_q.memory_effect_kind <= MEM_EFFECT_CSC;
                retire_packet_q.memory_capability_value <= mem_capability_value_q;
              end
              advance_pc(mem_size_bits_q);
              retire_sequence_q <= retire_sequence_q + 64'd1;
              state_q <= ST_FETCH_REQ;
            end else begin
              state_q <= ST_MEM_TAG_WAIT;
            end
          end
        end

        ST_MEM_TAG_WAIT: begin
          if (tagmem_rsp_valid) begin
            start_pending_packet();
            commit_capability_write(
                mem_capability_index_q, cap_from_cells(mem_rdata_q, tagmem_rsp_rtag));
            advance_pc(mem_size_bits_q);
            retire_sequence_q <= retire_sequence_q + 64'd1;
            state_q <= ST_FETCH_REQ;
          end
        end

        default: begin
          state_q <= ST_IDLE;
        end
      endcase
    end
  end

  // verilator lint_off UNUSEDSIGNAL
  wire logic unused_inputs = &{
    timer_interrupt_pending,
    software_interrupt_pending,
    external_interrupt_pending,
    external_event_valid,
    external_event_cause[0],
    debug_halt_request,
    retire_ready
  };
  // verilator lint_on UNUSEDSIGNAL
endmodule
