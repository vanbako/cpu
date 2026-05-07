module cpu_v01_atomic_cache_core (
  input  logic clk,
  input  logic rst_n,
  output logic retire_valid,
  output cpu_v01_pkg::retire_packet_t retire_packet,
  output logic llsc_success_seen,
  output logic sc_failure_seen,
  output logic conflict_clear_seen,
  output logic fault_clear_seen,
  output logic trap_csr_fence_clear_seen,
  output logic fence_seen,
  output logic fence_i_seen,
  output logic cache_access_seen,
  output logic cache_fault_seen,
  output logic reservation_valid,
  output cpu_v01_pkg::addr_t reservation_word_address,
  output cpu_v01_pkg::int_reg_t memory_word,
  output logic memory_tag,
  output logic done
);
  import cpu_v01_pkg::*;

  localparam addr_t WORD_PA = 48'h0000_0000_A000;
  localparam addr_t DEVICE_PA = 48'h0000_0000_F000;
  localparam addr_t VIRTUAL_ADDRESS = 48'h0000_0000_4000;

  typedef enum logic [4:0] {
    ST_RESET,
    ST_LL48,
    ST_SC48_SUCCESS,
    ST_LL48_REINSTALL,
    ST_SC48_FAILURE,
    ST_LL48_CONFLICT,
    ST_CONFLICT_STORE_CLEAR,
    ST_FAULTING_LL48_CLEAR,
    ST_LL48_FOR_CSR_CLEAR,
    ST_CSR_CLEAR,
    ST_LL48_FOR_TRAP_CLEAR,
    ST_TRAP_CLEAR,
    ST_LL48_FOR_FENCE_CLEAR,
    ST_SFENCE_CLEAR,
    ST_FENCE,
    ST_FENCE_I,
    ST_CACHE_CLEAN,
    ST_CACHE_INVAL,
    ST_CACHE_CLEANINVAL,
    ST_CACHE_DEVICE_FAULT,
    ST_DONE
  } atomic_cache_state_t;

  atomic_cache_state_t state_q;
  logic [RETIRE_SEQUENCE_BITS-1:0] sequence_q;
  addr_t pc_q;
  retire_packet_t retire_packet_q;
  logic reservation_valid_q;
  addr_t reservation_word_address_q;
  int_reg_t memory_word_q;
  logic memory_tag_q;
  logic llsc_success_seen_q;
  logic sc_failure_seen_q;
  logic conflict_clear_seen_q;
  logic fault_clear_seen_q;
  logic trap_csr_fence_clear_seen_q;
  logic fence_seen_q;
  logic fence_i_seen_q;
  logic cache_access_seen_q;
  logic cache_fault_seen_q;

  assign retire_packet = retire_packet_q;
  assign retire_valid = retire_packet_q.valid;
  assign llsc_success_seen = llsc_success_seen_q;
  assign sc_failure_seen = sc_failure_seen_q;
  assign conflict_clear_seen = conflict_clear_seen_q;
  assign fault_clear_seen = fault_clear_seen_q;
  assign trap_csr_fence_clear_seen = trap_csr_fence_clear_seen_q;
  assign fence_seen = fence_seen_q;
  assign fence_i_seen = fence_i_seen_q;
  assign cache_access_seen = cache_access_seen_q;
  assign cache_fault_seen = cache_fault_seen_q;
  assign reservation_valid = reservation_valid_q;
  assign reservation_word_address = reservation_word_address_q;
  assign memory_word = memory_word_q;
  assign memory_tag = memory_tag_q;
  assign done = state_q == ST_DONE;

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
    input logic [15:0] cause,
    input addr_t tval
  );
    retire_packet_q <= '0;
    retire_packet_q.valid <= 1'b1;
    retire_packet_q.sequence <= sequence_q;
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
    retire_packet_q.fault.tval <= tval;
  endtask

  task automatic start_ll48_packet(input addr_t physical_address);
    start_packet(OPC_LL48_24, 8'd24, 1'b0);
    retire_packet_q.integer_write_valid <= 1'b1;
    retire_packet_q.integer_write_index <= 4'd0;
    retire_packet_q.integer_write_value <= memory_word_q;
    retire_packet_q.translation_valid <= 1'b1;
    retire_packet_q.effective_address <= VIRTUAL_ADDRESS;
    retire_packet_q.physical_address <= physical_address;
    retire_packet_q.translation_memory_type <= MEMORY_TYPE_NORMAL_COHERENT;
    retire_packet_q.reservation_install_valid <= 1'b1;
    retire_packet_q.reservation_word_address <= physical_address;
    retire_packet_q.reservation_memory_type <= MEMORY_TYPE_NORMAL_COHERENT;
  endtask

  task automatic start_sc48_packet(input logic success, input int_reg_t store_value);
    start_packet(OPC_SC48_24, 8'd24, 1'b0);
    retire_packet_q.integer_write_valid <= 1'b1;
    retire_packet_q.integer_write_index <= 4'd4;
    retire_packet_q.integer_write_value <= success ? 48'd0 : 48'd1;
    retire_packet_q.translation_valid <= 1'b1;
    retire_packet_q.effective_address <= VIRTUAL_ADDRESS;
    retire_packet_q.physical_address <= WORD_PA;
    retire_packet_q.translation_memory_type <= MEMORY_TYPE_NORMAL_COHERENT;
    retire_packet_q.sc_success <= success;
    retire_packet_q.reservation_clear_valid <= 1'b1;
    retire_packet_q.reservation_word_address <= WORD_PA;
    retire_packet_q.reservation_memory_type <= MEMORY_TYPE_NORMAL_COHERENT;
    if (success) begin
      retire_packet_q.memory_effect_kind <= MEM_EFFECT_ST48;
      retire_packet_q.memory_effect_address <= WORD_PA;
      retire_packet_q.memory_integer_value <= store_value;
      retire_packet_q.tag_write_valid <= 1'b1;
      retire_packet_q.tag_write_value <= 1'b0;
    end
  endtask

  task automatic start_cache_packet(
    input logic [OPCODE_ID_BITS-1:0] opcode_id,
    input logic [CACHE_MAINT_KIND_BITS-1:0] kind,
    input logic clear_reservation
  );
    start_packet(opcode_id, 8'd24, 1'b1);
    retire_packet_q.cache_maintenance_valid <= 1'b1;
    retire_packet_q.cache_maintenance_kind <= kind;
    retire_packet_q.cache_maintenance_address <= WORD_PA;
    retire_packet_q.cache_maintenance_length <= 48'd16;
    if (clear_reservation) begin
      retire_packet_q.reservation_clear_valid <= 1'b1;
      retire_packet_q.reservation_word_address <= WORD_PA;
      retire_packet_q.reservation_memory_type <= MEMORY_TYPE_NORMAL_COHERENT;
    end
  endtask

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      state_q <= ST_RESET;
      sequence_q <= '0;
      pc_q <= 48'h0000_0000_2A00;
      retire_packet_q <= '0;
      reservation_valid_q <= 1'b0;
      reservation_word_address_q <= '0;
      memory_word_q <= 48'h0000_0000_AAAA;
      memory_tag_q <= 1'b1;
      llsc_success_seen_q <= 1'b0;
      sc_failure_seen_q <= 1'b0;
      conflict_clear_seen_q <= 1'b0;
      fault_clear_seen_q <= 1'b0;
      trap_csr_fence_clear_seen_q <= 1'b0;
      fence_seen_q <= 1'b0;
      fence_i_seen_q <= 1'b0;
      cache_access_seen_q <= 1'b0;
      cache_fault_seen_q <= 1'b0;
    end else begin
      retire_packet_q <= '0;
      unique case (state_q)
        ST_RESET: begin
          state_q <= ST_LL48;
        end

        ST_LL48: begin
          start_ll48_packet(WORD_PA);
          reservation_valid_q <= 1'b1;
          reservation_word_address_q <= WORD_PA;
          state_q <= ST_SC48_SUCCESS;
        end

        ST_SC48_SUCCESS: begin
          start_sc48_packet(1'b1, 48'h0000_0000_BBBB);
          memory_word_q <= 48'h0000_0000_BBBB;
          memory_tag_q <= 1'b0;
          reservation_valid_q <= 1'b0;
          reservation_word_address_q <= '0;
          llsc_success_seen_q <= 1'b1;
          state_q <= ST_LL48_REINSTALL;
        end

        ST_LL48_REINSTALL: begin
          start_ll48_packet(WORD_PA);
          reservation_valid_q <= 1'b1;
          reservation_word_address_q <= WORD_PA;
          state_q <= ST_SC48_FAILURE;
        end

        ST_SC48_FAILURE: begin
          start_sc48_packet(1'b0, 48'h0000_0000_CCCC);
          reservation_valid_q <= 1'b0;
          reservation_word_address_q <= '0;
          sc_failure_seen_q <= 1'b1;
          state_q <= ST_LL48_CONFLICT;
        end

        ST_LL48_CONFLICT: begin
          start_ll48_packet(WORD_PA);
          reservation_valid_q <= 1'b1;
          reservation_word_address_q <= WORD_PA;
          state_q <= ST_CONFLICT_STORE_CLEAR;
        end

        ST_CONFLICT_STORE_CLEAR: begin
          start_packet(OPC_ST48_24, 8'd24, 1'b0);
          retire_packet_q.memory_effect_kind <= MEM_EFFECT_ST48;
          retire_packet_q.memory_effect_address <= WORD_PA;
          retire_packet_q.memory_integer_value <= 48'h0000_0000_DDDD;
          retire_packet_q.reservation_clear_valid <= 1'b1;
          retire_packet_q.reservation_word_address <= WORD_PA;
          retire_packet_q.reservation_memory_type <= MEMORY_TYPE_NORMAL_COHERENT;
          reservation_valid_q <= 1'b0;
          reservation_word_address_q <= '0;
          memory_word_q <= 48'h0000_0000_DDDD;
          conflict_clear_seen_q <= 1'b1;
          state_q <= ST_FAULTING_LL48_CLEAR;
        end

        ST_FAULTING_LL48_CLEAR: begin
          reservation_valid_q <= 1'b0;
          reservation_word_address_q <= '0;
          start_fault_packet(OPC_LL48_24, EXC_ALIGN_FAULT, WORD_PA + 48'd1);
          retire_packet_q.reservation_clear_valid <= 1'b1;
          retire_packet_q.reservation_word_address <= WORD_PA;
          retire_packet_q.reservation_memory_type <= MEMORY_TYPE_NORMAL_COHERENT;
          fault_clear_seen_q <= 1'b1;
          state_q <= ST_LL48_FOR_CSR_CLEAR;
        end

        ST_LL48_FOR_CSR_CLEAR: begin
          start_ll48_packet(WORD_PA);
          reservation_valid_q <= 1'b1;
          reservation_word_address_q <= WORD_PA;
          state_q <= ST_CSR_CLEAR;
        end

        ST_CSR_CLEAR: begin
          start_packet(OPC_CSRWR_24, 8'd24, 1'b0);
          retire_packet_q.csr_write_valid <= 1'b1;
          retire_packet_q.csr_write_index <= CSR_ASID;
          retire_packet_q.csr_write_value <= 48'h0000_0000_0001;
          retire_packet_q.reservation_clear_valid <= 1'b1;
          retire_packet_q.reservation_word_address <= WORD_PA;
          retire_packet_q.reservation_memory_type <= MEMORY_TYPE_NORMAL_COHERENT;
          reservation_valid_q <= 1'b0;
          state_q <= ST_LL48_FOR_TRAP_CLEAR;
        end

        ST_LL48_FOR_TRAP_CLEAR: begin
          start_ll48_packet(WORD_PA);
          reservation_valid_q <= 1'b1;
          reservation_word_address_q <= WORD_PA;
          state_q <= ST_TRAP_CLEAR;
        end

        ST_TRAP_CLEAR: begin
          start_fault_packet(OPC_BRK_12, EXC_BREAKPOINT, 48'd0);
          retire_packet_q.trap_entry_valid <= 1'b1;
          retire_packet_q.reservation_clear_valid <= 1'b1;
          retire_packet_q.reservation_word_address <= WORD_PA;
          retire_packet_q.reservation_memory_type <= MEMORY_TYPE_NORMAL_COHERENT;
          reservation_valid_q <= 1'b0;
          state_q <= ST_LL48_FOR_FENCE_CLEAR;
        end

        ST_LL48_FOR_FENCE_CLEAR: begin
          start_ll48_packet(WORD_PA);
          reservation_valid_q <= 1'b1;
          reservation_word_address_q <= WORD_PA;
          state_q <= ST_SFENCE_CLEAR;
        end

        ST_SFENCE_CLEAR: begin
          start_packet(OPC_SFENCE_VM_24, 8'd24, 1'b1);
          retire_packet_q.tlb_invalidate_valid <= 1'b1;
          retire_packet_q.tlb_invalidate_kind <= TLB_INV_ALL;
          retire_packet_q.reservation_clear_valid <= 1'b1;
          retire_packet_q.reservation_word_address <= WORD_PA;
          retire_packet_q.reservation_memory_type <= MEMORY_TYPE_NORMAL_COHERENT;
          reservation_valid_q <= 1'b0;
          trap_csr_fence_clear_seen_q <= 1'b1;
          state_q <= ST_FENCE;
        end

        ST_FENCE: begin
          start_packet(OPC_FENCE_24, 8'd24, 1'b0);
          retire_packet_q.fence_order_valid <= 1'b1;
          fence_seen_q <= 1'b1;
          state_q <= ST_FENCE_I;
        end

        ST_FENCE_I: begin
          start_packet(OPC_FENCE_I_24, 8'd24, 1'b1);
          retire_packet_q.fence_i_valid <= 1'b1;
          fence_i_seen_q <= 1'b1;
          state_q <= ST_CACHE_CLEAN;
        end

        ST_CACHE_CLEAN: begin
          start_cache_packet(OPC_CACHE_CLEAN_24, CACHE_MAINT_CLEAN, 1'b0);
          reservation_valid_q <= 1'b1;
          reservation_word_address_q <= WORD_PA;
          cache_access_seen_q <= 1'b1;
          state_q <= ST_CACHE_INVAL;
        end

        ST_CACHE_INVAL: begin
          reservation_valid_q <= 1'b0;
          start_cache_packet(OPC_CACHE_INVAL_24, CACHE_MAINT_INVAL, 1'b1);
          state_q <= ST_CACHE_CLEANINVAL;
        end

        ST_CACHE_CLEANINVAL: begin
          start_cache_packet(OPC_CACHE_CLEANINVAL_24, CACHE_MAINT_CLEANINVAL, 1'b1);
          state_q <= ST_CACHE_DEVICE_FAULT;
        end

        ST_CACHE_DEVICE_FAULT: begin
          start_fault_packet(OPC_CACHE_CLEAN_24, EXC_ACCESS_FAULT, DEVICE_PA);
          retire_packet_q.translation_valid <= 1'b1;
          retire_packet_q.effective_address <= VIRTUAL_ADDRESS;
          retire_packet_q.physical_address <= DEVICE_PA;
          retire_packet_q.translation_memory_type <= MEMORY_TYPE_DEVICE_ORDERED;
          cache_fault_seen_q <= 1'b1;
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
