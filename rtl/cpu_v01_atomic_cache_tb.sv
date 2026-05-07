module cpu_v01_atomic_cache_tb;
  import cpu_v01_pkg::*;

  logic clk;
  logic rst_n;
  logic retire_valid;
  retire_packet_t packet;
  logic llsc_success_seen;
  logic sc_failure_seen;
  logic conflict_clear_seen;
  logic fault_clear_seen;
  logic trap_csr_fence_clear_seen;
  logic fence_seen;
  logic fence_i_seen;
  logic cache_access_seen;
  logic cache_fault_seen;
  logic reservation_valid;
  addr_t reservation_word_address;
  int_reg_t memory_word;
  logic memory_tag;
  logic done;

  cpu_v01_atomic_cache_core dut (
    .clk(clk),
    .rst_n(rst_n),
    .retire_valid(retire_valid),
    .retire_packet(packet),
    .llsc_success_seen(llsc_success_seen),
    .sc_failure_seen(sc_failure_seen),
    .conflict_clear_seen(conflict_clear_seen),
    .fault_clear_seen(fault_clear_seen),
    .trap_csr_fence_clear_seen(trap_csr_fence_clear_seen),
    .fence_seen(fence_seen),
    .fence_i_seen(fence_i_seen),
    .cache_access_seen(cache_access_seen),
    .cache_fault_seen(cache_fault_seen),
    .reservation_valid(reservation_valid),
    .reservation_word_address(reservation_word_address),
    .memory_word(memory_word),
    .memory_tag(memory_tag),
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

    if (!llsc_success_seen || memory_word != 48'h0000_0000_DDDD || memory_tag) begin
      $fatal(1, "LL48/SC48 success result mismatch");
    end
    if (!sc_failure_seen) begin
      $fatal(1, "SC48 failure result mismatch");
    end
    if (!conflict_clear_seen || reservation_valid) begin
      $fatal(1, "LL/SC conflict clear result mismatch");
    end
    if (!fault_clear_seen) begin
      $fatal(1, "faulting LL48 reservation clear result mismatch");
    end
    if (!trap_csr_fence_clear_seen) begin
      $fatal(1, "trap CSR fence reservation clear result mismatch");
    end
    if (!fence_seen || !fence_i_seen) begin
      $fatal(1, "FENCE/FENCE.I ordering result mismatch");
    end
    if (!cache_access_seen) begin
      $fatal(1, "CACHE maintenance access result mismatch");
    end
    if (!cache_fault_seen ||
        !retire_valid ||
        packet.normal_valid ||
        !packet.fault.valid ||
        packet.fault.cause != EXC_ACCESS_FAULT ||
        packet.fault.tval != 48'h0000_0000_F000) begin
      $fatal(1, "CACHE device access fault result mismatch");
    end

    $finish;
  end
endmodule
