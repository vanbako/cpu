module cpu_v01_control_trap_tb;
  import cpu_v01_pkg::*;

  logic clk;
  logic rst_n;
  logic retire_valid;
  retire_packet_t packet;
  logic callc_entry_seen;
  logic callc_fault_seen;
  logic ret_pop_seen;
  logic ret_fault_seen;
  logic sys_trap_seen;
  logic scall_alias_seen;
  logic syscall_frame_saved;
  logic syscall_frame_restored;
  logic iret_user_seen;
  logic final_user_mode;
  cap_t rsc_value;
  cap_t return_stack_slot;
  int_reg_t syscall_return_d0;
  int_reg_t syscall_return_d1;
  cap_t syscall_return_c0;
  logic done;

  cpu_v01_control_trap_core dut (
    .clk(clk),
    .rst_n(rst_n),
    .retire_valid(retire_valid),
    .retire_packet(packet),
    .callc_entry_seen(callc_entry_seen),
    .callc_fault_seen(callc_fault_seen),
    .ret_pop_seen(ret_pop_seen),
    .ret_fault_seen(ret_fault_seen),
    .sys_trap_seen(sys_trap_seen),
    .scall_alias_seen(scall_alias_seen),
    .syscall_frame_saved(syscall_frame_saved),
    .syscall_frame_restored(syscall_frame_restored),
    .iret_user_seen(iret_user_seen),
    .final_user_mode(final_user_mode),
    .rsc_value(rsc_value),
    .return_stack_slot(return_stack_slot),
    .syscall_return_d0(syscall_return_d0),
    .syscall_return_d1(syscall_return_d1),
    .syscall_return_c0(syscall_return_c0),
    .done(done)
  );

  initial begin
    clk = 1'b0;
    forever #5 clk = ~clk;
  end

  initial begin
    rst_n = 1'b0;
    repeat (2) @(posedge clk);
    rst_n = 1'b1;
    wait (done);

    if (!callc_entry_seen ||
        !return_stack_slot.tag ||
        return_stack_slot.payload.otype != 8'hFF ||
        return_stack_slot.payload.cursor != 48'h0000_0000_1001) begin
      $fatal(1, "CALLC entry protected-stack result mismatch");
    end
    if (!callc_fault_seen) begin
      $fatal(1, "CALLC entry fault result mismatch");
    end
    if (!ret_pop_seen || rsc_value.payload.cursor != 48'h0000_0000_3040) begin
      $fatal(1, "RET pop result mismatch");
    end
    if (!ret_fault_seen) begin
      $fatal(1, "RET protected pop fault result mismatch");
    end
    if (!sys_trap_seen || !scall_alias_seen || !syscall_frame_saved) begin
      $fatal(1, "SYS/SCALL trap-frame save result mismatch");
    end
    if (!syscall_frame_restored ||
        syscall_return_d0 != 48'h0000_0000_0000 ||
        syscall_return_d1 != 48'h0000_0018_0312 ||
        syscall_return_c0.payload.cursor != 48'h0000_4000_0122) begin
      $fatal(1, "syscall frame restore result mismatch");
    end
    if (!iret_user_seen ||
        !final_user_mode ||
        !retire_valid ||
        !packet.normal_valid ||
        !packet.trap_frame_restore_valid ||
        !packet.pcc_update_valid ||
        packet.pcc_update_value.payload.cursor != 48'h0000_0000_1400 ||
        packet.pcc_update_slot != SLOT_1) begin
      $fatal(1, "IRET user return result mismatch");
    end

    $finish;
  end
endmodule
