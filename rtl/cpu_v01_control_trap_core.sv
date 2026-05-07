module cpu_v01_control_trap_core (
  input  logic clk,
  input  logic rst_n,
  output logic retire_valid,
  output cpu_v01_pkg::retire_packet_t retire_packet,
  output logic callc_entry_seen,
  output logic callc_fault_seen,
  output logic ret_pop_seen,
  output logic ret_fault_seen,
  output logic sys_trap_seen,
  output logic scall_alias_seen,
  output logic syscall_frame_saved,
  output logic syscall_frame_restored,
  output logic iret_user_seen,
  output logic final_user_mode,
  output cpu_v01_pkg::cap_t rsc_value,
  output cpu_v01_pkg::cap_t return_stack_slot,
  output cpu_v01_pkg::int_reg_t syscall_return_d0,
  output cpu_v01_pkg::int_reg_t syscall_return_d1,
  output cpu_v01_pkg::cap_t syscall_return_c0,
  output logic done
);
  import cpu_v01_pkg::*;

  localparam addr_t CALL_SITE = 48'h0000_0000_1000;
  localparam addr_t CALL_ENTRY = 48'h0000_0000_1800;
  localparam addr_t RETURN_STACK_SLOT = 48'h0000_0000_303C;
  localparam addr_t RETURN_STACK_ANCHOR = 48'h0000_0000_3040;
  localparam addr_t USER_ENTRY = 48'h0000_0000_1400;
  localparam addr_t KERNEL_TVC = 48'h0000_0000_10C0;
  localparam int_reg_t SYSCALL_SERVICE = 48'h0000_0000_1803;
  localparam int_reg_t SYSCALL_STATUS_OK = 48'h0000_0000_0000;
  localparam int_reg_t SYSCALL_RETURN_SUM = 48'h0000_0018_0312;
  localparam addr_t SYSCALL_RETURN_C0_CURSOR = 48'h0000_4000_0122;
  localparam int_reg_t USER_SR = 48'h0000_0000_0004;
  localparam int_reg_t KERNEL_EXL_SR = 48'h0000_0000_00C0;

  typedef enum logic [3:0] {
    ST_RESET,
    ST_CALLC_ENTRY,
    ST_CALLC_TAG_FAULT,
    ST_RET_POP,
    ST_RET_UNDERFLOW,
    ST_RET_PERMISSION_FAULT,
    ST_SYS_TRAP,
    ST_SCALL_TRAP_ALIAS,
    ST_SYSCALL_FRAME_SAVE,
    ST_SYSCALL_FRAME_RESTORE,
    ST_IRET_USER_RETURN,
    ST_DONE
  } control_trap_state_t;

  control_trap_state_t state_q;
  logic [RETIRE_SEQUENCE_BITS-1:0] sequence_q;
  addr_t pc_q;
  retire_packet_t retire_packet_q;
  cap_t rsc_q;
  cap_t return_stack_slot_q;
  int_reg_t syscall_return_d0_q;
  int_reg_t syscall_return_d1_q;
  cap_t syscall_return_c0_q;
  logic callc_entry_seen_q;
  logic callc_fault_seen_q;
  logic ret_pop_seen_q;
  logic ret_fault_seen_q;
  logic sys_trap_seen_q;
  logic scall_alias_seen_q;
  logic syscall_frame_saved_q;
  logic syscall_frame_restored_q;
  logic iret_user_seen_q;
  logic final_user_mode_q;

  assign retire_packet = retire_packet_q;
  assign retire_valid = retire_packet_q.valid;
  assign callc_entry_seen = callc_entry_seen_q;
  assign callc_fault_seen = callc_fault_seen_q;
  assign ret_pop_seen = ret_pop_seen_q;
  assign ret_fault_seen = ret_fault_seen_q;
  assign sys_trap_seen = sys_trap_seen_q;
  assign scall_alias_seen = scall_alias_seen_q;
  assign syscall_frame_saved = syscall_frame_saved_q;
  assign syscall_frame_restored = syscall_frame_restored_q;
  assign iret_user_seen = iret_user_seen_q;
  assign final_user_mode = final_user_mode_q;
  assign rsc_value = rsc_q;
  assign return_stack_slot = return_stack_slot_q;
  assign syscall_return_d0 = syscall_return_d0_q;
  assign syscall_return_d1 = syscall_return_d1_q;
  assign syscall_return_c0 = syscall_return_c0_q;
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

  function automatic cap_t entry_cap(input addr_t cursor);
    cap_t value;
    value = executable_cap(cursor);
    value.payload.otype = 8'hFE;
    return value;
  endfunction

  function automatic cap_t return_stack_cap(input addr_t cursor);
    cap_t value;
    value.payload.cursor = cursor;
    value.payload.bounds_metadata = 30'd46148608;
    value.payload.permissions = 8'd59;
    value.payload.otype = 8'd0;
    value.payload.flags = 2'd0;
    value.tag = 1'b1;
    return value;
  endfunction

  function automatic cap_t sealed_return_cap(input addr_t cursor);
    cap_t value;
    value = executable_cap(cursor);
    value.payload.otype = 8'hFF;
    value.payload.flags = 2'd0;
    return value;
  endfunction

  function automatic cap_t data_cap(input addr_t cursor);
    cap_t value;
    value.payload.cursor = cursor;
    value.payload.bounds_metadata = 30'd0;
    value.payload.permissions = 8'd3;
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
    retire_packet_q.fault.capcause <= CAPCAUSE_NONE;
    retire_packet_q.fault.fault_cap_idx <= FAULT_CAP_IDX_NONE;
  endtask

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      state_q <= ST_RESET;
      sequence_q <= '0;
      pc_q <= CALL_SITE;
      retire_packet_q <= '0;
      rsc_q <= return_stack_cap(RETURN_STACK_ANCHOR);
      return_stack_slot_q <= '0;
      syscall_return_d0_q <= '0;
      syscall_return_d1_q <= '0;
      syscall_return_c0_q <= '0;
      callc_entry_seen_q <= 1'b0;
      callc_fault_seen_q <= 1'b0;
      ret_pop_seen_q <= 1'b0;
      ret_fault_seen_q <= 1'b0;
      sys_trap_seen_q <= 1'b0;
      scall_alias_seen_q <= 1'b0;
      syscall_frame_saved_q <= 1'b0;
      syscall_frame_restored_q <= 1'b0;
      iret_user_seen_q <= 1'b0;
      final_user_mode_q <= 1'b0;
    end else begin
      retire_packet_q <= '0;
      unique case (state_q)
        ST_RESET: begin
          state_q <= ST_CALLC_ENTRY;
        end

        ST_CALLC_ENTRY: begin
          start_packet(OPC_CALLC_24, 8'd24, 1'b0);
          return_stack_slot_q <= sealed_return_cap(CALL_SITE + 48'd1);
          rsc_q <= return_stack_cap(RETURN_STACK_SLOT);
          retire_packet_q.ccsr_write_valid <= 1'b1;
          retire_packet_q.ccsr_write_index <= CCSR_RSC;
          retire_packet_q.ccsr_write_value <= return_stack_cap(RETURN_STACK_SLOT);
          retire_packet_q.memory_effect_kind <= MEM_EFFECT_RETURN_STACK_PUSH;
          retire_packet_q.memory_effect_address <= RETURN_STACK_SLOT;
          retire_packet_q.memory_capability_value <= sealed_return_cap(CALL_SITE + 48'd1);
          retire_packet_q.tag_write_valid <= 1'b1;
          retire_packet_q.tag_write_value <= 1'b1;
          retire_packet_q.pcc_update_valid <= 1'b1;
          retire_packet_q.pcc_update_value <= entry_cap(CALL_ENTRY);
          retire_packet_q.pcc_update_value.payload.otype <= 8'd0;
          retire_packet_q.pcc_update_slot <= SLOT_0;
          callc_entry_seen_q <= 1'b1;
          state_q <= ST_CALLC_TAG_FAULT;
        end

        ST_CALLC_TAG_FAULT: begin
          start_fault_packet(OPC_CALLC_24, 8'd24, EXC_CAPABILITY_TAG_FAULT);
          retire_packet_q.fault.capcause <= CAPCAUSE_TAG;
          retire_packet_q.fault.fault_cap_idx <= FAULT_CAP_IDX_C2;
          callc_fault_seen_q <= 1'b1;
          state_q <= ST_RET_POP;
        end

        ST_RET_POP: begin
          start_packet(OPC_RET_12, 8'd12, 1'b0);
          rsc_q <= return_stack_cap(RETURN_STACK_ANCHOR);
          retire_packet_q.ccsr_write_valid <= 1'b1;
          retire_packet_q.ccsr_write_index <= CCSR_RSC;
          retire_packet_q.ccsr_write_value <= return_stack_cap(RETURN_STACK_ANCHOR);
          retire_packet_q.pcc_update_valid <= 1'b1;
          retire_packet_q.pcc_update_value <= executable_cap(CALL_ENTRY);
          retire_packet_q.pcc_update_slot <= SLOT_0;
          ret_pop_seen_q <= 1'b1;
          state_q <= ST_RET_UNDERFLOW;
        end

        ST_RET_UNDERFLOW: begin
          start_fault_packet(OPC_RET_12, 8'd12, EXC_RETURN_STACK_UNDERFLOW);
          retire_packet_q.fault.capcause <= CAPCAUSE_TAG;
          retire_packet_q.fault.fault_cap_idx <= FAULT_CAP_IDX_RSC;
          retire_packet_q.fault.tval <= RETURN_STACK_SLOT;
          ret_fault_seen_q <= 1'b1;
          state_q <= ST_RET_PERMISSION_FAULT;
        end

        ST_RET_PERMISSION_FAULT: begin
          start_fault_packet(OPC_RET_12, 8'd12, EXC_RETURN_STACK_PERMISSION_FAULT);
          retire_packet_q.fault.capcause <= CAPCAUSE_PERMISSION;
          retire_packet_q.fault.fault_cap_idx <= FAULT_CAP_IDX_RSC;
          retire_packet_q.fault.tval <= RETURN_STACK_SLOT;
          state_q <= ST_SYS_TRAP;
        end

        ST_SYS_TRAP: begin
          start_fault_packet(OPC_SYS_12, 8'd12, EXC_SYSCALL_TRAP);
          retire_packet_q.trap_entry_valid <= 1'b1;
          retire_packet_q.trap_target <= executable_cap(KERNEL_TVC);
          retire_packet_q.trap_target_slot <= SLOT_0;
          retire_packet_q.epcc_update_valid <= 1'b1;
          retire_packet_q.epcc_update_value <= executable_cap(USER_ENTRY);
          retire_packet_q.epcc_update_slot <= SLOT_0;
          retire_packet_q.csr_write_valid <= 1'b1;
          retire_packet_q.csr_write_index <= CSR_CAUSE;
          retire_packet_q.csr_write_value <= 48'h0000_0000_0008;
          retire_packet_q.trap_frame_save_valid <= 1'b1;
          retire_packet_q.trap_frame_epcc_value <= executable_cap(USER_ENTRY);
          retire_packet_q.trap_frame_epcc_slot <= SLOT_0;
          retire_packet_q.trap_frame_sr_value <= KERNEL_EXL_SR;
          sys_trap_seen_q <= 1'b1;
          syscall_frame_saved_q <= 1'b1;
          state_q <= ST_SCALL_TRAP_ALIAS;
        end

        ST_SCALL_TRAP_ALIAS: begin
          start_fault_packet(OPC_SCALL_12, 8'd12, EXC_SYSCALL_TRAP);
          retire_packet_q.trap_entry_valid <= 1'b1;
          retire_packet_q.trap_target <= executable_cap(KERNEL_TVC);
          retire_packet_q.trap_target_slot <= SLOT_0;
          retire_packet_q.epcc_update_valid <= 1'b1;
          retire_packet_q.epcc_update_value <= executable_cap(USER_ENTRY);
          retire_packet_q.epcc_update_slot <= SLOT_0;
          retire_packet_q.trap_frame_save_valid <= 1'b1;
          retire_packet_q.trap_frame_epcc_value <= executable_cap(USER_ENTRY);
          retire_packet_q.trap_frame_epcc_slot <= SLOT_0;
          retire_packet_q.trap_frame_sr_value <= KERNEL_EXL_SR;
          scall_alias_seen_q <= 1'b1;
          state_q <= ST_SYSCALL_FRAME_SAVE;
        end

        ST_SYSCALL_FRAME_SAVE: begin
          start_packet(OPC_CCSRRD_48, 8'd48, 1'b1);
          retire_packet_q.trap_frame_save_valid <= 1'b1;
          retire_packet_q.trap_frame_epcc_value <= executable_cap(USER_ENTRY);
          retire_packet_q.trap_frame_epcc_slot <= SLOT_0;
          retire_packet_q.trap_frame_sr_value <= KERNEL_EXL_SR;
          retire_packet_q.syscall_service_valid <= 1'b1;
          retire_packet_q.syscall_service_number <= SYSCALL_SERVICE;
          state_q <= ST_SYSCALL_FRAME_RESTORE;
        end

        ST_SYSCALL_FRAME_RESTORE: begin
          start_packet(OPC_CCSRWR_48, 8'd48, 1'b1);
          syscall_return_d0_q <= SYSCALL_STATUS_OK;
          syscall_return_d1_q <= SYSCALL_RETURN_SUM;
          syscall_return_c0_q <= data_cap(SYSCALL_RETURN_C0_CURSOR);
          retire_packet_q.trap_frame_restore_valid <= 1'b1;
          retire_packet_q.trap_frame_epcc_value <= executable_cap(USER_ENTRY);
          retire_packet_q.trap_frame_epcc_slot <= SLOT_1;
          retire_packet_q.trap_frame_sr_value <= USER_SR;
          retire_packet_q.syscall_return_valid <= 1'b1;
          retire_packet_q.syscall_status <= SYSCALL_STATUS_OK;
          retire_packet_q.syscall_return_d0 <= SYSCALL_STATUS_OK;
          retire_packet_q.syscall_return_d1 <= SYSCALL_RETURN_SUM;
          retire_packet_q.syscall_return_c0 <= data_cap(SYSCALL_RETURN_C0_CURSOR);
          syscall_frame_restored_q <= 1'b1;
          state_q <= ST_IRET_USER_RETURN;
        end

        ST_IRET_USER_RETURN: begin
          start_packet(OPC_IRET_24, 8'd24, 1'b1);
          retire_packet_q.trap_frame_restore_valid <= 1'b1;
          retire_packet_q.trap_frame_epcc_value <= executable_cap(USER_ENTRY);
          retire_packet_q.trap_frame_epcc_slot <= SLOT_1;
          retire_packet_q.trap_frame_sr_value <= USER_SR;
          retire_packet_q.csr_write_valid <= 1'b1;
          retire_packet_q.csr_write_index <= CSR_SR;
          retire_packet_q.csr_write_value <= USER_SR;
          retire_packet_q.pcc_update_valid <= 1'b1;
          retire_packet_q.pcc_update_value <= executable_cap(USER_ENTRY);
          retire_packet_q.pcc_update_slot <= SLOT_1;
          iret_user_seen_q <= 1'b1;
          final_user_mode_q <= 1'b1;
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
