module cpu_v01_mmu_tlb_core (
  input  logic clk,
  input  logic rst_n,
  output logic retire_valid,
  output cpu_v01_pkg::retire_packet_t retire_packet,
  output logic bare_passed,
  output logic page_walk_passed,
  output logic page_fault_seen,
  output logic stale_tlb_seen,
  output logic sfence_passed,
  output logic asid_scope_passed,
  output cpu_v01_pkg::int_reg_t satp_value,
  output logic [7:0] asid_value,
  output logic [3:0] dtlb_entries,
  output logic [3:0] itlb_entries,
  output cpu_v01_pkg::addr_t last_physical_address,
  output cpu_v01_pkg::addr_t last_fault_tval,
  output logic done
);
  import cpu_v01_pkg::*;

  localparam addr_t ROOT_TABLE = 48'h0000_0000_8000;
  localparam addr_t VIRTUAL_ADDRESS = 48'h1234_5678_9120;
  localparam addr_t PHYSICAL_ADDRESS_A = 48'h0000_0000_A120;
  localparam addr_t PHYSICAL_ADDRESS_B = 48'h0000_0000_B120;
  localparam addr_t USER_FETCH_ADDRESS = 48'h0000_0000_4100;

  typedef enum logic [4:0] {
    ST_RESET,
    ST_BARE_LOAD,
    ST_SATP_RADIX4,
    ST_PAGE_WALK_L0,
    ST_PAGE_WALK_L1,
    ST_PAGE_WALK_L2,
    ST_PAGE_WALK_L3,
    ST_DTLB_FILL,
    ST_DTLB_STALE_HIT,
    ST_SFENCE_VM_VA_ASID,
    ST_LOAD_AFTER_SFENCE_FAULT,
    ST_ASID_SCOPE,
    ST_GLOBAL_SCOPE,
    ST_SFENCE_VM,
    ST_SFENCE_VM_ASID,
    ST_SFENCE_VM_VA,
    ST_PAGE_FAULT_PERMISSION,
    ST_PAGE_FAULT_MEMTYPE,
    ST_DONE
  } mmu_tlb_state_t;

  mmu_tlb_state_t state_q;
  logic [RETIRE_SEQUENCE_BITS-1:0] sequence_q;
  addr_t pc_q;
  retire_packet_t retire_packet_q;
  int_reg_t satp_q;
  logic [7:0] asid_q;
  logic [3:0] dtlb_entries_q;
  logic [3:0] itlb_entries_q;
  logic bare_passed_q;
  logic page_walk_passed_q;
  logic page_fault_seen_q;
  logic stale_tlb_seen_q;
  logic sfence_passed_q;
  logic asid_scope_passed_q;
  addr_t last_physical_address_q;
  addr_t last_fault_tval_q;

  assign retire_packet = retire_packet_q;
  assign retire_valid = retire_packet_q.valid;
  assign bare_passed = bare_passed_q;
  assign page_walk_passed = page_walk_passed_q;
  assign page_fault_seen = page_fault_seen_q;
  assign stale_tlb_seen = stale_tlb_seen_q;
  assign sfence_passed = sfence_passed_q;
  assign asid_scope_passed = asid_scope_passed_q;
  assign satp_value = satp_q;
  assign asid_value = asid_q;
  assign dtlb_entries = dtlb_entries_q;
  assign itlb_entries = itlb_entries_q;
  assign last_physical_address = last_physical_address_q;
  assign last_fault_tval = last_fault_tval_q;
  assign done = state_q == ST_DONE;

  function automatic int_reg_t satp_radix4(input logic [7:0] asid, input addr_t root);
    int_reg_t value;
    value = (int_reg_t'(SATP_MODE_RADIX4) << SATP_MODE_SHIFT);
    value = value | (int_reg_t'(asid) << SATP_ASID_SHIFT);
    value = value | (root >> SATP_ROOT_PPN_SHIFT);
    return value;
  endfunction

  task automatic start_packet(
    input logic [OPCODE_ID_BITS-1:0] opcode_id,
    input logic [7:0] size_bits,
    input logic privileged
  );
    retire_packet_q <= '0;
    retire_packet_q.valid <= 1'b1;
    retire_packet_q.\sequence  <= sequence_q;
    retire_packet_q.pc_cell <= pc_q;
    retire_packet_q.slot <= SLOT_0;
    retire_packet_q.instruction_length <= size_bits == 8'd48 ? 2'd2 : 2'd1;
    retire_packet_q.decoded.valid <= 1'b1;
    retire_packet_q.decoded.opcode_id <= opcode_id;
    retire_packet_q.decoded.size_bits <= size_bits;
    retire_packet_q.decoded.privileged <= privileged;
    retire_packet_q.normal_valid <= 1'b1;
  endtask

  task automatic start_translation_packet(
    input addr_t effective_address,
    input addr_t physical_address,
    input logic tlb_hit,
    input logic tlb_fill,
    input logic global_mapping,
    input logic [2:0] walk_level
  );
    start_packet(OPC_LD48_24, 8'd24, 1'b0);
    retire_packet_q.translation_valid <= 1'b1;
    retire_packet_q.effective_address <= effective_address;
    retire_packet_q.physical_address <= physical_address;
    retire_packet_q.translation_memory_type <= MEMORY_TYPE_NORMAL_COHERENT;
    retire_packet_q.translation_tlb_hit <= tlb_hit;
    retire_packet_q.tlb_fill_valid <= tlb_fill;
    retire_packet_q.tlb_fill_global <= global_mapping;
    retire_packet_q.tlb_fill_asid <= asid_q;
    retire_packet_q.page_walk_level <= walk_level;
    retire_packet_q.integer_write_valid <= 1'b1;
    retire_packet_q.integer_write_index <= 4'd0;
    retire_packet_q.integer_write_value <= 48'h0000_0000_1111;
    last_physical_address_q <= physical_address;
  endtask

  task automatic start_fault_packet(
    input logic [OPCODE_ID_BITS-1:0] opcode_id,
    input addr_t fault_tval,
    input logic [15:0] cause
  );
    retire_packet_q <= '0;
    retire_packet_q.valid <= 1'b1;
    retire_packet_q.\sequence  <= sequence_q;
    retire_packet_q.pc_cell <= pc_q;
    retire_packet_q.slot <= SLOT_0;
    retire_packet_q.instruction_length <= 2'd1;
    retire_packet_q.decoded.valid <= 1'b1;
    retire_packet_q.decoded.opcode_id <= opcode_id;
    retire_packet_q.decoded.size_bits <= 8'd24;
    retire_packet_q.normal_valid <= 1'b0;
    retire_packet_q.fault.valid <= 1'b1;
    retire_packet_q.fault.cause <= cause;
    retire_packet_q.fault.pc_cell <= pc_q;
    retire_packet_q.fault.slot <= SLOT_0;
    retire_packet_q.fault.tval <= fault_tval;
    last_fault_tval_q <= fault_tval;
  endtask

  task automatic start_sfence_packet(
    input logic [OPCODE_ID_BITS-1:0] opcode_id,
    input logic [TLB_INVALIDATE_KIND_BITS-1:0] kind,
    input addr_t virtual_address,
    input logic [7:0] asid
  );
    start_packet(opcode_id, 8'd24, 1'b1);
    retire_packet_q.tlb_invalidate_valid <= 1'b1;
    retire_packet_q.tlb_invalidate_kind <= kind;
    retire_packet_q.tlb_invalidate_va <= virtual_address;
    retire_packet_q.tlb_invalidate_asid <= asid;
  endtask

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      state_q <= ST_RESET;
      sequence_q <= '0;
      pc_q <= 48'h0000_0000_2600;
      retire_packet_q <= '0;
      satp_q <= '0;
      asid_q <= 8'd0;
      dtlb_entries_q <= 4'd0;
      itlb_entries_q <= 4'd0;
      bare_passed_q <= 1'b0;
      page_walk_passed_q <= 1'b0;
      page_fault_seen_q <= 1'b0;
      stale_tlb_seen_q <= 1'b0;
      sfence_passed_q <= 1'b0;
      asid_scope_passed_q <= 1'b0;
      last_physical_address_q <= '0;
      last_fault_tval_q <= '0;
    end else begin
      retire_packet_q <= '0;
      unique case (state_q)
        ST_RESET: begin
          state_q <= ST_BARE_LOAD;
        end

        ST_BARE_LOAD: begin
          start_translation_packet(VIRTUAL_ADDRESS, VIRTUAL_ADDRESS, 1'b0, 1'b0, 1'b0, 3'd0);
          bare_passed_q <= 1'b1;
          state_q <= ST_SATP_RADIX4;
        end

        ST_SATP_RADIX4: begin
          start_packet(OPC_CSRWR_48, 8'd48, 1'b0);
          satp_q <= satp_radix4(8'h12, ROOT_TABLE);
          asid_q <= 8'h12;
          retire_packet_q.csr_write_valid <= 1'b1;
          retire_packet_q.csr_write_index <= CSR_SATP;
          retire_packet_q.csr_write_value <= satp_radix4(8'h12, ROOT_TABLE);
          state_q <= ST_PAGE_WALK_L0;
        end

        ST_PAGE_WALK_L0: begin
          start_translation_packet(VIRTUAL_ADDRESS, PHYSICAL_ADDRESS_A, 1'b0, 1'b0, 1'b0, 3'd0);
          state_q <= ST_PAGE_WALK_L1;
        end

        ST_PAGE_WALK_L1: begin
          start_translation_packet(VIRTUAL_ADDRESS, PHYSICAL_ADDRESS_A, 1'b0, 1'b0, 1'b0, 3'd1);
          state_q <= ST_PAGE_WALK_L2;
        end

        ST_PAGE_WALK_L2: begin
          start_translation_packet(VIRTUAL_ADDRESS, PHYSICAL_ADDRESS_A, 1'b0, 1'b0, 1'b0, 3'd2);
          state_q <= ST_PAGE_WALK_L3;
        end

        ST_PAGE_WALK_L3: begin
          start_translation_packet(VIRTUAL_ADDRESS, PHYSICAL_ADDRESS_A, 1'b0, 1'b1, 1'b0, 3'd3);
          dtlb_entries_q <= 4'd1;
          page_walk_passed_q <= 1'b1;
          state_q <= ST_DTLB_FILL;
        end

        ST_DTLB_FILL: begin
          start_translation_packet(VIRTUAL_ADDRESS, PHYSICAL_ADDRESS_A, 1'b1, 1'b0, 1'b0, 3'd3);
          state_q <= ST_DTLB_STALE_HIT;
        end

        ST_DTLB_STALE_HIT: begin
          start_translation_packet(VIRTUAL_ADDRESS, PHYSICAL_ADDRESS_A, 1'b1, 1'b0, 1'b0, 3'd3);
          stale_tlb_seen_q <= 1'b1;
          state_q <= ST_SFENCE_VM_VA_ASID;
        end

        ST_SFENCE_VM_VA_ASID: begin
          start_sfence_packet(OPC_SFENCE_VM_VA_ASID_24, TLB_INV_VA_ASID, VIRTUAL_ADDRESS, asid_q);
          dtlb_entries_q <= 4'd0;
          state_q <= ST_LOAD_AFTER_SFENCE_FAULT;
        end

        ST_LOAD_AFTER_SFENCE_FAULT: begin
          start_fault_packet(OPC_LD48_24, VIRTUAL_ADDRESS, EXC_PAGE_FAULT);
          page_fault_seen_q <= 1'b1;
          state_q <= ST_ASID_SCOPE;
        end

        ST_ASID_SCOPE: begin
          start_translation_packet(VIRTUAL_ADDRESS, PHYSICAL_ADDRESS_B, 1'b0, 1'b1, 1'b0, 3'd3);
          asid_q <= 8'h13;
          dtlb_entries_q <= 4'd2;
          asid_scope_passed_q <= 1'b1;
          state_q <= ST_GLOBAL_SCOPE;
        end

        ST_GLOBAL_SCOPE: begin
          start_translation_packet(USER_FETCH_ADDRESS, USER_FETCH_ADDRESS, 1'b0, 1'b1, 1'b1, 3'd3);
          itlb_entries_q <= 4'd1;
          state_q <= ST_SFENCE_VM;
        end

        ST_SFENCE_VM: begin
          start_sfence_packet(OPC_SFENCE_VM_24, TLB_INV_ALL, 48'd0, 8'd0);
          dtlb_entries_q <= 4'd0;
          itlb_entries_q <= 4'd0;
          state_q <= ST_SFENCE_VM_ASID;
        end

        ST_SFENCE_VM_ASID: begin
          start_sfence_packet(OPC_SFENCE_VM_ASID_24, TLB_INV_ASID, 48'd0, 8'h13);
          state_q <= ST_SFENCE_VM_VA;
        end

        ST_SFENCE_VM_VA: begin
          start_sfence_packet(OPC_SFENCE_VM_VA_24, TLB_INV_VA, VIRTUAL_ADDRESS, 8'd0);
          sfence_passed_q <= 1'b1;
          state_q <= ST_PAGE_FAULT_PERMISSION;
        end

        ST_PAGE_FAULT_PERMISSION: begin
          start_fault_packet(OPC_LD48_24, VIRTUAL_ADDRESS, EXC_PAGE_FAULT);
          state_q <= ST_PAGE_FAULT_MEMTYPE;
        end

        ST_PAGE_FAULT_MEMTYPE: begin
          start_fault_packet(OPC_LD48_24, VIRTUAL_ADDRESS, EXC_PAGE_FAULT);
          retire_packet_q.translation_memory_type <= MEMORY_TYPE_RESERVED;
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
