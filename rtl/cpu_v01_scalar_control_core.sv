module cpu_v01_scalar_control_core (
  input  logic clk,
  input  logic rst_n,
  output logic retire_valid,
  output cpu_v01_pkg::retire_packet_t retire_packet,
  output logic scalar_passed,
  output logic branch_passed,
  output logic csr_passed,
  output logic ccsr_passed,
  output logic breakpoint_seen,
  output logic pause_seen,
  output cpu_v01_pkg::int_reg_t scalar_result,
  output cpu_v01_pkg::cap_t pcc_value,
  output cpu_v01_pkg::cap_t epcc_value,
  output logic [15:0] last_fault_cause,
  output logic done
);
  import cpu_v01_pkg::*;

  typedef enum logic [5:0] {
    ST_RESET,
    ST_CPY,
    ST_NEG,
    ST_ADD,
    ST_ADDU,
    ST_SUB,
    ST_SUBU,
    ST_MUL,
    ST_MULU,
    ST_DIV,
    ST_DIVU,
    ST_MOD,
    ST_MODU,
    ST_NOT,
    ST_AND,
    ST_OR,
    ST_XOR,
    ST_SHL,
    ST_SHRS,
    ST_SHRU,
    ST_ROL,
    ST_ROR,
    ST_CMP,
    ST_CMPU,
    ST_TST,
    ST_SETCC,
    ST_CMOVCC,
    ST_BSET,
    ST_BCLR,
    ST_BRA,
    ST_BCC_TAKEN,
    ST_BCC_NOT_TAKEN,
    ST_JMP,
    ST_EPCCRD,
    ST_EPCCWR,
    ST_PAUSE,
    ST_BRK,
    ST_CSRRD,
    ST_CSRWR,
    ST_CSRSET,
    ST_CSRCLR,
    ST_CSRRD48,
    ST_CSRWR48,
    ST_CSRSET48,
    ST_CSRCLR48,
    ST_CCSRRD,
    ST_CCSRWR,
    ST_DONE
  } scalar_control_state_t;

  scalar_control_state_t state_q;
  logic [RETIRE_SEQUENCE_BITS-1:0] sequence_q;
  addr_t pc_q;
  retire_packet_t retire_packet_q;
  int_reg_t d0_q;
  int_reg_t csr_scratch_q;
  cap_t pcc_q;
  cap_t epcc_q;
  cap_t scratch_ccsr_q;
  logic scalar_passed_q;
  logic branch_passed_q;
  logic csr_passed_q;
  logic ccsr_passed_q;
  logic breakpoint_seen_q;
  logic pause_seen_q;
  logic [15:0] last_fault_cause_q;

  assign retire_packet = retire_packet_q;
  assign retire_valid = retire_packet_q.valid;
  assign scalar_passed = scalar_passed_q;
  assign branch_passed = branch_passed_q;
  assign csr_passed = csr_passed_q;
  assign ccsr_passed = ccsr_passed_q;
  assign breakpoint_seen = breakpoint_seen_q;
  assign pause_seen = pause_seen_q;
  assign scalar_result = d0_q;
  assign pcc_value = pcc_q;
  assign epcc_value = epcc_q;
  assign last_fault_cause = last_fault_cause_q;
  assign done = state_q == ST_DONE;

  function automatic cap_t executable_cap(input addr_t cursor);
    cap_t value;
    value.payload.cursor = cursor;
    value.payload.bounds_metadata = 30'd0;
    value.payload.permissions = 8'd4;
    value.payload.otype = 8'd0;
    value.payload.flags = 2'd1;
    value.tag = 1'b1;
    return value;
  endfunction

  task automatic start_packet(
    input logic [OPCODE_ID_BITS-1:0] opcode_id,
    input logic [7:0] size_bits,
    input logic privileged
  );
    retire_packet_q <= '0;
    retire_packet_q.valid <= 1'b1;
    retire_packet_q.sequence <= sequence_q;
    retire_packet_q.pc_cell <= pc_q;
    retire_packet_q.slot <= SLOT_0;
    retire_packet_q.instruction_length <= size_bits == 8'd48 ? 2'd2 : 2'd1;
    retire_packet_q.decoded.valid <= 1'b1;
    retire_packet_q.decoded.opcode_id <= opcode_id;
    retire_packet_q.decoded.size_bits <= size_bits;
    retire_packet_q.decoded.privileged <= privileged;
    retire_packet_q.normal_valid <= 1'b1;
  endtask

  task automatic start_fault_packet(
    input logic [OPCODE_ID_BITS-1:0] opcode_id,
    input logic [7:0] size_bits,
    input logic [15:0] cause
  );
    retire_packet_q <= '0;
    retire_packet_q.valid <= 1'b1;
    retire_packet_q.sequence <= sequence_q;
    retire_packet_q.pc_cell <= pc_q;
    retire_packet_q.slot <= SLOT_0;
    retire_packet_q.instruction_length <= size_bits == 8'd48 ? 2'd2 : 2'd1;
    retire_packet_q.decoded.valid <= 1'b1;
    retire_packet_q.decoded.opcode_id <= opcode_id;
    retire_packet_q.decoded.size_bits <= size_bits;
    retire_packet_q.normal_valid <= 1'b0;
    retire_packet_q.fault.valid <= 1'b1;
    retire_packet_q.fault.cause <= cause;
    retire_packet_q.fault.pc_cell <= pc_q;
    retire_packet_q.fault.slot <= SLOT_0;
  endtask

  task automatic integer_write(
    input logic [OPCODE_ID_BITS-1:0] opcode_id,
    input int_reg_t value
  );
    start_packet(opcode_id, 8'd24, 1'b0);
    d0_q <= value;
    retire_packet_q.integer_write_valid <= 1'b1;
    retire_packet_q.integer_write_index <= 4'd0;
    retire_packet_q.integer_write_value <= value;
  endtask

  task automatic csr_write(
    input logic [OPCODE_ID_BITS-1:0] opcode_id,
    input logic [7:0] size_bits,
    input logic [CSR_NUMBER_BITS-1:0] csr_index,
    input int_reg_t value
  );
    start_packet(opcode_id, size_bits, 1'b0);
    csr_scratch_q <= value;
    retire_packet_q.csr_write_valid <= 1'b1;
    retire_packet_q.csr_write_index <= csr_index;
    retire_packet_q.csr_write_value <= value;
  endtask

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      state_q <= ST_RESET;
      sequence_q <= '0;
      pc_q <= 48'h0000_0000_1800;
      retire_packet_q <= '0;
      d0_q <= 48'h0000_0000_0011;
      csr_scratch_q <= 48'h0000_0000_0100;
      pcc_q <= executable_cap(48'h0000_0000_1800);
      epcc_q <= executable_cap(48'h0000_0000_1E00);
      scratch_ccsr_q <= executable_cap(48'h0000_0000_2400);
      scalar_passed_q <= 1'b0;
      branch_passed_q <= 1'b0;
      csr_passed_q <= 1'b0;
      ccsr_passed_q <= 1'b0;
      breakpoint_seen_q <= 1'b0;
      pause_seen_q <= 1'b0;
      last_fault_cause_q <= EXC_ILLEGAL_INSTRUCTION;
    end else begin
      retire_packet_q <= '0;
      unique case (state_q)
        ST_RESET: begin
          state_q <= ST_CPY;
        end

        ST_CPY: begin
          integer_write(OPC_CPY_24, 48'h0000_0000_0021);
          state_q <= ST_NEG;
        end

        ST_NEG: begin
          integer_write(OPC_NEG_24, 48'hFFFF_FFFF_FFDF);
          state_q <= ST_ADD;
        end

        ST_ADD: begin
          integer_write(OPC_ADD_24, 48'h0000_0000_0030);
          state_q <= ST_ADDU;
        end

        ST_ADDU: begin
          integer_write(OPC_ADDU_24, 48'h0000_0000_0031);
          state_q <= ST_SUB;
        end

        ST_SUB: begin
          integer_write(OPC_SUB_24, 48'h0000_0000_002F);
          state_q <= ST_SUBU;
        end

        ST_SUBU: begin
          integer_write(OPC_SUBU_24, 48'h0000_0000_002E);
          state_q <= ST_MUL;
        end

        ST_MUL: begin
          integer_write(OPC_MUL_24, 48'h0000_0000_0060);
          state_q <= ST_MULU;
        end

        ST_MULU: begin
          integer_write(OPC_MULU_24, 48'h0000_0000_0061);
          state_q <= ST_DIV;
        end

        ST_DIV: begin
          integer_write(OPC_DIV_24, 48'h0000_0000_000C);
          state_q <= ST_DIVU;
        end

        ST_DIVU: begin
          integer_write(OPC_DIVU_24, 48'h0000_0000_000D);
          state_q <= ST_MOD;
        end

        ST_MOD: begin
          integer_write(OPC_MOD_24, 48'h0000_0000_0002);
          state_q <= ST_MODU;
        end

        ST_MODU: begin
          integer_write(OPC_MODU_24, 48'h0000_0000_0003);
          state_q <= ST_NOT;
        end

        ST_NOT: begin
          integer_write(OPC_NOT_24, 48'hFFFF_FFFF_FFFC);
          state_q <= ST_AND;
        end

        ST_AND: begin
          integer_write(OPC_AND_24, 48'h0000_0000_000F);
          state_q <= ST_OR;
        end

        ST_OR: begin
          integer_write(OPC_OR_24, 48'h0000_0000_00FF);
          state_q <= ST_XOR;
        end

        ST_XOR: begin
          integer_write(OPC_XOR_24, 48'h0000_0000_00F0);
          state_q <= ST_SHL;
        end

        ST_SHL: begin
          integer_write(OPC_SHL_24, 48'h0000_0000_0100);
          state_q <= ST_SHRS;
        end

        ST_SHRS: begin
          integer_write(OPC_SHRS_24, 48'hFFFF_FFFF_FFFE);
          state_q <= ST_SHRU;
        end

        ST_SHRU: begin
          integer_write(OPC_SHRU_24, 48'h0000_0000_0001);
          state_q <= ST_ROL;
        end

        ST_ROL: begin
          integer_write(OPC_ROL_24, 48'h0000_0000_0101);
          state_q <= ST_ROR;
        end

        ST_ROR: begin
          integer_write(OPC_ROR_24, 48'h8000_0000_0000);
          state_q <= ST_CMP;
        end

        ST_CMP: begin
          csr_write(OPC_CMP_24, 8'd24, CSR_SR, 48'h0000_0000_0005);
          state_q <= ST_CMPU;
        end

        ST_CMPU: begin
          csr_write(OPC_CMPU_24, 8'd24, CSR_SR, 48'h0000_0000_0004);
          state_q <= ST_TST;
        end

        ST_TST: begin
          csr_write(OPC_TST_24, 8'd24, CSR_SR, 48'h0000_0000_0001);
          state_q <= ST_SETCC;
        end

        ST_SETCC: begin
          integer_write(OPC_SETCC_24, 48'h0000_0000_0001);
          state_q <= ST_CMOVCC;
        end

        ST_CMOVCC: begin
          integer_write(OPC_CMOVCC_24, 48'h0000_0000_0042);
          state_q <= ST_BSET;
        end

        ST_BSET: begin
          integer_write(OPC_BSET_24, 48'h0000_0000_0046);
          state_q <= ST_BCLR;
        end

        ST_BCLR: begin
          integer_write(OPC_BCLR_24, 48'h0000_0000_0042);
          scalar_passed_q <= 1'b1;
          state_q <= ST_BRA;
        end

        ST_BRA: begin
          start_packet(OPC_BRA_24, 8'd24, 1'b0);
          pcc_q <= executable_cap(48'h0000_0000_1900);
          retire_packet_q.pcc_update_valid <= 1'b1;
          retire_packet_q.pcc_update_value <= executable_cap(48'h0000_0000_1900);
          retire_packet_q.pcc_update_slot <= SLOT_0;
          state_q <= ST_BCC_TAKEN;
        end

        ST_BCC_TAKEN: begin
          start_packet(OPC_BCC_24, 8'd24, 1'b0);
          pcc_q <= executable_cap(48'h0000_0000_1910);
          retire_packet_q.pcc_update_valid <= 1'b1;
          retire_packet_q.pcc_update_value <= executable_cap(48'h0000_0000_1910);
          retire_packet_q.pcc_update_slot <= SLOT_0;
          state_q <= ST_BCC_NOT_TAKEN;
        end

        ST_BCC_NOT_TAKEN: begin
          start_packet(OPC_BCC_24, 8'd24, 1'b0);
          state_q <= ST_JMP;
        end

        ST_JMP: begin
          start_packet(OPC_JMP_24, 8'd24, 1'b0);
          pcc_q <= executable_cap(48'h0000_0000_1A00);
          retire_packet_q.pcc_update_valid <= 1'b1;
          retire_packet_q.pcc_update_value <= executable_cap(48'h0000_0000_1A00);
          retire_packet_q.pcc_update_slot <= SLOT_0;
          state_q <= ST_EPCCRD;
        end

        ST_EPCCRD: begin
          start_packet(OPC_EPCCRD_24, 8'd24, 1'b1);
          retire_packet_q.capability_write_valid <= 1'b1;
          retire_packet_q.capability_write_index <= 3'd2;
          retire_packet_q.capability_write_value <= epcc_q;
          retire_packet_q.integer_write_valid <= 1'b1;
          retire_packet_q.integer_write_index <= 4'd2;
          retire_packet_q.integer_write_value <= 48'd0;
          state_q <= ST_EPCCWR;
        end

        ST_EPCCWR: begin
          start_packet(OPC_EPCCWR_24, 8'd24, 1'b1);
          epcc_q <= executable_cap(48'h0000_0000_1E20);
          retire_packet_q.epcc_update_valid <= 1'b1;
          retire_packet_q.epcc_update_value <= executable_cap(48'h0000_0000_1E20);
          retire_packet_q.epcc_update_slot <= SLOT_0;
          branch_passed_q <= 1'b1;
          state_q <= ST_PAUSE;
        end

        ST_PAUSE: begin
          start_packet(OPC_PAUSE_12, 8'd12, 1'b0);
          pause_seen_q <= 1'b1;
          state_q <= ST_BRK;
        end

        ST_BRK: begin
          start_fault_packet(OPC_BRK_12, 8'd12, EXC_BREAKPOINT);
          last_fault_cause_q <= EXC_BREAKPOINT;
          breakpoint_seen_q <= 1'b1;
          state_q <= ST_CSRRD;
        end

        ST_CSRRD: begin
          start_packet(OPC_CSRRD_24, 8'd24, 1'b0);
          retire_packet_q.integer_write_valid <= 1'b1;
          retire_packet_q.integer_write_index <= 4'd3;
          retire_packet_q.integer_write_value <= csr_scratch_q;
          state_q <= ST_CSRWR;
        end

        ST_CSRWR: begin
          csr_write(OPC_CSRWR_24, 8'd24, CSR_SCRATCH, 48'h0000_0000_2201);
          state_q <= ST_CSRSET;
        end

        ST_CSRSET: begin
          csr_write(OPC_CSRSET_24, 8'd24, CSR_SCRATCH, 48'h0000_0000_220F);
          retire_packet_q.integer_write_valid <= 1'b1;
          retire_packet_q.integer_write_index <= 4'd3;
          retire_packet_q.integer_write_value <= csr_scratch_q;
          state_q <= ST_CSRCLR;
        end

        ST_CSRCLR: begin
          csr_write(OPC_CSRCLR_24, 8'd24, CSR_SCRATCH, 48'h0000_0000_2200);
          retire_packet_q.integer_write_valid <= 1'b1;
          retire_packet_q.integer_write_index <= 4'd3;
          retire_packet_q.integer_write_value <= csr_scratch_q;
          state_q <= ST_CSRRD48;
        end

        ST_CSRRD48: begin
          start_packet(OPC_CSRRD_48, 8'd48, 1'b0);
          retire_packet_q.integer_write_valid <= 1'b1;
          retire_packet_q.integer_write_index <= 4'd4;
          retire_packet_q.integer_write_value <= csr_scratch_q;
          state_q <= ST_CSRWR48;
        end

        ST_CSRWR48: begin
          csr_write(OPC_CSRWR_48, 8'd48, CSR_DEBUGCTL, 48'h0000_0000_2301);
          state_q <= ST_CSRSET48;
        end

        ST_CSRSET48: begin
          csr_write(OPC_CSRSET_48, 8'd48, CSR_DEBUGCTL, 48'h0000_0000_2307);
          retire_packet_q.integer_write_valid <= 1'b1;
          retire_packet_q.integer_write_index <= 4'd4;
          retire_packet_q.integer_write_value <= csr_scratch_q;
          state_q <= ST_CSRCLR48;
        end

        ST_CSRCLR48: begin
          csr_write(OPC_CSRCLR_48, 8'd48, CSR_DEBUGCTL, 48'h0000_0000_2300);
          retire_packet_q.integer_write_valid <= 1'b1;
          retire_packet_q.integer_write_index <= 4'd4;
          retire_packet_q.integer_write_value <= csr_scratch_q;
          csr_passed_q <= 1'b1;
          state_q <= ST_CCSRRD;
        end

        ST_CCSRRD: begin
          start_packet(OPC_CCSRRD_48, 8'd48, 1'b1);
          retire_packet_q.capability_write_valid <= 1'b1;
          retire_packet_q.capability_write_index <= 3'd3;
          retire_packet_q.capability_write_value <= scratch_ccsr_q;
          state_q <= ST_CCSRWR;
        end

        ST_CCSRWR: begin
          start_packet(OPC_CCSRWR_48, 8'd48, 1'b1);
          scratch_ccsr_q <= executable_cap(48'h0000_0000_2410);
          retire_packet_q.ccsr_write_valid <= 1'b1;
          retire_packet_q.ccsr_write_index <= CCSR_DSC;
          retire_packet_q.ccsr_write_value <= executable_cap(48'h0000_0000_2410);
          ccsr_passed_q <= 1'b1;
          state_q <= ST_DONE;
        end

        default: begin
          state_q <= ST_DONE;
        end
      endcase

      if (state_q != ST_RESET && state_q != ST_DONE) begin
        sequence_q <= sequence_q + 64'd1;
        pc_q <= pc_q + 48'd1;
      end
    end
  end
endmodule
