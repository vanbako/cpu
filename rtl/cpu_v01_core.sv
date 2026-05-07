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
  cap_t epcc_q;
  logic epcc_slot_q;
  cap_t dsc_q;
  cap_t rsc_q;
  cap_t ddc_q;
  cap_t tvc_q;
  cap_t ksc_q;
  cap_t krc_q;
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

  function automatic logic [39:0] operands_24(input cell_t instr_cell);
    return {24'd0, instr_cell[15:0]};
  endfunction

  function automatic logic [39:0] operands_48(input cell_t low_cell, input cell_t high_cell);
    return {high_cell, low_cell[15:0]};
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
    end
    retire_packet_q.csr_write_valid <= 1'b1;
    retire_packet_q.csr_write_index <= csr_index;
    retire_packet_q.csr_write_value <= value;
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

  task automatic execute_decoded_packet(
    input logic [OPCODE_ID_BITS-1:0] opcode_id,
    input logic [7:0] size_bits,
    input logic [1:0] instruction_length,
    input logic [39:0] operands
  );
    logic [3:0] rd;
    logic [3:0] ra;
    logic [3:0] rb;
    logic [3:0] cc;
    logic [2:0] width_code;
    logic [5:0] shift_amount;
    logic [CSR_NUMBER_BITS-1:0] csr_index;
    logic [CCSR_NUMBER_BITS-1:0] ccsr_index;
    int_reg_t lhs;
    int_reg_t rhs;
    int_reg_t result;
    int_reg_t old_csr;
    cap_t cap_value;

    start_decoded_packet(opcode_id, size_bits, instruction_length);
    rd = operands[15:12];
    ra = operands[11:8];
    rb = operands[7:4];
    width_code = operands[3:1];
    lhs = d_regs[ra];
    rhs = d_regs[rb];
    result = '0;

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

      OPC_JMP_24: begin
        cap_value = c_regs[operands[14:12]];
        commit_pcc_update(cap_value, SLOT_0);
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
      rsc_q <= reset_pcc(48'd0);
      ddc_q <= reset_pcc(48'd0);
      tvc_q <= reset_pcc(48'd0);
      ksc_q <= reset_pcc(48'd0);
      krc_q <= reset_pcc(48'd0);
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
            execute_decoded_packet(major, 8'd48, 2'd2, operands_48(selected_cell, fetch_cells_q[1]));
          end else if (fetch_slot_q == SLOT_0 && is_24_major(major)) begin
            execute_decoded_packet(major, 8'd24, 2'd1, operands_24(selected_cell));
          end else if (is_12_opcode(selected_half)) begin
            execute_decoded_packet(opcode_id_for_12(selected_half), 8'd12, 2'd1, {28'd0, selected_half});
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
