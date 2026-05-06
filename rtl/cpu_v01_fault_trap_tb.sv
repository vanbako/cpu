module cpu_v01_fault_trap_tb;
  import cpu_v01_pkg::*;

  logic clk;
  logic rst_n;
  logic retire_valid;
  retire_packet_t packet;
  logic divide_fault_seen;
  logic trap_entered;
  logic iret_restored;
  logic call_pushed;
  logic ret_restored;
  cap_t rsc_value;
  cap_t return_stack_slot;
  logic return_stack_tag;
  logic done;

  cpu_v01_fault_trap_core dut (
    .clk(clk),
    .rst_n(rst_n),
    .retire_valid(retire_valid),
    .retire_packet(packet),
    .divide_fault_seen(divide_fault_seen),
    .trap_entered(trap_entered),
    .iret_restored(iret_restored),
    .call_pushed(call_pushed),
    .ret_restored(ret_restored),
    .rsc_value(rsc_value),
    .return_stack_slot(return_stack_slot),
    .return_stack_tag(return_stack_tag),
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

    if (!divide_fault_seen) begin
      $fatal(1, "divide fault smoke result mismatch");
    end
    if (!trap_entered) begin
      $fatal(1, "SYS trap entry smoke result mismatch");
    end
    if (!iret_restored) begin
      $fatal(1, "IRET PCC restore smoke result mismatch");
    end
    if (!call_pushed ||
        !return_stack_tag ||
        return_stack_slot.payload.cursor != 48'h0000_0000_1501 ||
        return_stack_slot.payload.otype != 8'hFF) begin
      $fatal(1, "CALL protected return-stack push smoke result mismatch");
    end
    if (!ret_restored ||
        rsc_value.payload.cursor != 48'h0000_0000_3004 ||
        !retire_valid ||
        !packet.normal_valid ||
        !packet.pcc_update_valid ||
        packet.pcc_update_value.payload.cursor != 48'h0000_0000_1501) begin
      $fatal(1, "RET protected return-stack restore smoke result mismatch");
    end

    $finish;
  end
endmodule
