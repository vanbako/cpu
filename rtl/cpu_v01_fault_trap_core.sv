module cpu_v01_fault_trap_core (
  input  logic clk,
  input  logic rst_n,
  output logic retire_valid,
  output cpu_v01_pkg::retire_packet_t retire_packet,
  output logic divide_fault_seen,
  output logic trap_entered,
  output logic iret_restored,
  output logic call_pushed,
  output logic ret_restored,
  output cpu_v01_pkg::cap_t rsc_value,
  output cpu_v01_pkg::cap_t return_stack_slot,
  output logic return_stack_tag,
  output logic done
);
  import cpu_v01_pkg::*;

  typedef enum logic [2:0] {
    ST_RESET,
    ST_DIV_ZERO_FAULT,
    ST_SYS_TRAP,
    ST_IRET,
    ST_CALL,
    ST_RET,
    ST_DONE
  } fault_trap_state_t;

  fault_trap_state_t state_q;
  logic [RETIRE_SEQUENCE_BITS-1:0] sequence_q;
  addr_t pc_q;
  retire_packet_t retire_packet_q;
  cap_t rsc_q;
  cap_t return_stack_slot_q;
  logic return_stack_tag_q;
  logic divide_fault_seen_q;
  logic trap_entered_q;
  logic iret_restored_q;
  logic call_pushed_q;
  logic ret_restored_q;

  assign retire_packet = retire_packet_q;
  assign retire_valid = retire_packet_q.valid;
  assign divide_fault_seen = divide_fault_seen_q;
  assign trap_entered = trap_entered_q;
  assign iret_restored = iret_restored_q;
  assign call_pushed = call_pushed_q;
  assign ret_restored = ret_restored_q;
  assign rsc_value = rsc_q;
  assign return_stack_slot = return_stack_slot_q;
  assign return_stack_tag = return_stack_tag_q;
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

  function automatic cap_t return_stack_cap(input addr_t cursor);
    cap_t value;
    value.payload.cursor = cursor;
    value.payload.bounds_metadata = 30'd46148608;
    value.payload.permissions = 8'd59;
    value.payload.otype = 8'd0;
    value.payload.flags = 2'd1;
    value.tag = 1'b1;
    return value;
  endfunction

  function automatic cap_t sealed_return_cap(input addr_t cursor);
    cap_t value;
    value.payload.cursor = cursor;
    value.payload.bounds_metadata = 30'd0;
    value.payload.permissions = 8'd4;
    value.payload.otype = 8'hFF;
    value.payload.flags = 2'd0;
    value.tag = 1'b1;
    return value;
  endfunction

  function automatic cap_t unsealed_return_target(input cap_t source);
    cap_t value;
    value = source;
    value.payload.otype = 8'd0;
    return value;
  endfunction

  task automatic start_packet(input logic [OPCODE_ID_BITS-1:0] opcode_id, input logic [7:0] size_bits);
    retire_packet_q <= '0;
    retire_packet_q.valid <= 1'b1;
    retire_packet_q.sequence <= sequence_q;
    retire_packet_q.pc_cell <= pc_q;
    retire_packet_q.slot <= SLOT_0;
    retire_packet_q.instruction_length <= size_bits == 8'd48 ? 2'd2 : 2'd1;
    retire_packet_q.decoded.valid <= 1'b1;
    retire_packet_q.decoded.opcode_id <= opcode_id;
    retire_packet_q.decoded.size_bits <= size_bits;
    retire_packet_q.decoded.privileged <= opcode_id == OPC_IRET_24;
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
    retire_packet_q.decoded.privileged <= 1'b0;
    retire_packet_q.normal_valid <= 1'b0;
    retire_packet_q.fault.valid <= 1'b1;
    retire_packet_q.fault.cause <= cause;
    retire_packet_q.fault.pc_cell <= pc_q;
    retire_packet_q.fault.slot <= SLOT_0;
  endtask

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      state_q <= ST_RESET;
      sequence_q <= '0;
      pc_q <= 48'h0000_0000_1600;
      retire_packet_q <= '0;
      rsc_q <= return_stack_cap(48'h0000_0000_3004);
      return_stack_slot_q <= '0;
      return_stack_tag_q <= 1'b0;
      divide_fault_seen_q <= 1'b0;
      trap_entered_q <= 1'b0;
      iret_restored_q <= 1'b0;
      call_pushed_q <= 1'b0;
      ret_restored_q <= 1'b0;
    end else begin
      retire_packet_q <= '0;
      unique case (state_q)
        ST_RESET: begin
          state_q <= ST_DIV_ZERO_FAULT;
        end

        ST_DIV_ZERO_FAULT: begin
          start_fault_packet(OPC_DIV_24, 8'd24, EXC_DIVIDE_BY_ZERO);
          divide_fault_seen_q <= 1'b1;
          pc_q <= 48'h0000_0000_1750;
          sequence_q <= sequence_q + 64'd1;
          state_q <= ST_SYS_TRAP;
        end

        ST_SYS_TRAP: begin
          start_fault_packet(OPC_SYS_12, 8'd12, EXC_SYSCALL_TRAP);
          retire_packet_q.trap_entry_valid <= 1'b1;
          retire_packet_q.trap_target <= executable_cap(48'h0000_0000_9000);
          retire_packet_q.trap_target_slot <= SLOT_0;
          retire_packet_q.epcc_update_valid <= 1'b1;
          retire_packet_q.epcc_update_value <= executable_cap(48'h0000_0000_1750);
          retire_packet_q.epcc_update_slot <= SLOT_0;
          retire_packet_q.csr_write_valid <= 1'b1;
          retire_packet_q.csr_write_index <= CSR_CAUSE;
          retire_packet_q.csr_write_value <= 48'h0000_0000_0008;
          trap_entered_q <= 1'b1;
          pc_q <= 48'h0000_0000_9000;
          sequence_q <= sequence_q + 64'd1;
          state_q <= ST_IRET;
        end

        ST_IRET: begin
          start_packet(OPC_IRET_24, 8'd24);
          retire_packet_q.csr_write_valid <= 1'b1;
          retire_packet_q.csr_write_index <= CSR_SR;
          retire_packet_q.csr_write_value <= 48'h0000_0000_00C0;
          retire_packet_q.pcc_update_valid <= 1'b1;
          retire_packet_q.pcc_update_value <= executable_cap(48'h0000_0000_1750);
          retire_packet_q.pcc_update_slot <= SLOT_0;
          iret_restored_q <= 1'b1;
          pc_q <= 48'h0000_0000_1500;
          sequence_q <= sequence_q + 64'd1;
          state_q <= ST_CALL;
        end

        ST_CALL: begin
          start_packet(OPC_CALL_24, 8'd24);
          return_stack_slot_q <= sealed_return_cap(48'h0000_0000_1501);
          return_stack_tag_q <= 1'b1;
          rsc_q <= return_stack_cap(48'h0000_0000_3000);
          retire_packet_q.ccsr_write_valid <= 1'b1;
          retire_packet_q.ccsr_write_index <= CCSR_RSC;
          retire_packet_q.ccsr_write_value <= return_stack_cap(48'h0000_0000_3000);
          retire_packet_q.memory_effect_kind <= MEM_EFFECT_RETURN_STACK_PUSH;
          retire_packet_q.memory_effect_address <= 48'h0000_0000_3000;
          retire_packet_q.memory_capability_value <= sealed_return_cap(48'h0000_0000_1501);
          retire_packet_q.tag_write_valid <= 1'b1;
          retire_packet_q.tag_write_value <= 1'b1;
          retire_packet_q.pcc_update_valid <= 1'b1;
          retire_packet_q.pcc_update_value <= executable_cap(48'h0000_0000_1510);
          retire_packet_q.pcc_update_slot <= SLOT_0;
          call_pushed_q <= 1'b1;
          pc_q <= 48'h0000_0000_1510;
          sequence_q <= sequence_q + 64'd1;
          state_q <= ST_RET;
        end

        ST_RET: begin
          start_packet(OPC_RET_12, 8'd12);
          rsc_q <= return_stack_cap(48'h0000_0000_3004);
          retire_packet_q.ccsr_write_valid <= 1'b1;
          retire_packet_q.ccsr_write_index <= CCSR_RSC;
          retire_packet_q.ccsr_write_value <= return_stack_cap(48'h0000_0000_3004);
          retire_packet_q.pcc_update_valid <= 1'b1;
          retire_packet_q.pcc_update_value <= unsealed_return_target(return_stack_slot_q);
          retire_packet_q.pcc_update_slot <= SLOT_0;
          ret_restored_q <= 1'b1;
          pc_q <= 48'h0000_0000_1501;
          sequence_q <= sequence_q + 64'd1;
          state_q <= ST_DONE;
        end

        default: begin
          state_q <= ST_DONE;
        end
      endcase
    end
  end
endmodule
