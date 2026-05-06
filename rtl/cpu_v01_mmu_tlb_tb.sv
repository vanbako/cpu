module cpu_v01_mmu_tlb_tb;
  import cpu_v01_pkg::*;

  logic clk;
  logic rst_n;
  logic retire_valid;
  retire_packet_t packet;
  logic bare_passed;
  logic page_walk_passed;
  logic page_fault_seen;
  logic stale_tlb_seen;
  logic sfence_passed;
  logic asid_scope_passed;
  int_reg_t satp_value;
  logic [7:0] asid_value;
  logic [3:0] dtlb_entries;
  logic [3:0] itlb_entries;
  addr_t last_physical_address;
  addr_t last_fault_tval;
  logic done;

  cpu_v01_mmu_tlb_core dut (
    .clk(clk),
    .rst_n(rst_n),
    .retire_valid(retire_valid),
    .retire_packet(packet),
    .bare_passed(bare_passed),
    .page_walk_passed(page_walk_passed),
    .page_fault_seen(page_fault_seen),
    .stale_tlb_seen(stale_tlb_seen),
    .sfence_passed(sfence_passed),
    .asid_scope_passed(asid_scope_passed),
    .satp_value(satp_value),
    .asid_value(asid_value),
    .dtlb_entries(dtlb_entries),
    .itlb_entries(itlb_entries),
    .last_physical_address(last_physical_address),
    .last_fault_tval(last_fault_tval),
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

    if (!bare_passed) begin
      $fatal(1, "bare SATP identity translation result mismatch");
    end
    if (!page_walk_passed ||
        satp_value[47:45] != SATP_MODE_RADIX4 ||
        asid_value != 8'h13 ||
        last_physical_address != 48'h0000_0000_4100) begin
      $fatal(1, "RADIX4 page-walk translation result mismatch");
    end
    if (!stale_tlb_seen) begin
      $fatal(1, "stale TLB hit before SFENCE result mismatch");
    end
    if (!sfence_passed || dtlb_entries != 4'd0 || itlb_entries != 4'd0) begin
      $fatal(1, "SFENCE.VM invalidation result mismatch");
    end
    if (!asid_scope_passed) begin
      $fatal(1, "ASID/global TLB scope result mismatch");
    end
    if (!page_fault_seen ||
        last_fault_tval != 48'h1234_5678_9120 ||
        !retire_valid ||
        packet.normal_valid ||
        !packet.fault.valid ||
        packet.fault.cause != EXC_PAGE_FAULT) begin
      $fatal(1, "RADIX4 page fault result mismatch");
    end

    $finish;
  end
endmodule
