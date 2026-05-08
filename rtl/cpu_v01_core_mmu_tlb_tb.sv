module cpu_v01_core_mmu_tlb_fixture #(
  parameter int MODE = 0,
  parameter cpu_v01_pkg::addr_t RESET_VECTOR = 48'h0000_0000_A000
) (
  input  logic clk,
  input  logic rst_n,
  output logic bare_seen,
  output logic radix_seen,
  output logic stale_seen,
  output logic sfence_seen,
  output logic asid_seen,
  output logic global_seen,
  output logic permission_fault_seen,
  output logic memtype_fault_seen,
  output logic pause_seen,
  output logic done
);
  import cpu_v01_pkg::*;

  localparam logic [7:0] DATA_PERMISSIONS = 8'd31;
  localparam addr_t VIRTUAL_ADDRESS = 48'h1234_5678_9120;
  localparam addr_t PHYSICAL_ADDRESS_A = 48'h0000_0000_A120;
  localparam addr_t PHYSICAL_ADDRESS_B = 48'h0000_0000_B120;
  localparam addr_t USER_FETCH_ADDRESS = 48'h0000_0000_4100;
  localparam int_reg_t ROOT_PPN = 48'h0000_0000_0010;
  localparam int_reg_t PERMISSION_ROOT_PPN = 48'h0000_0000_0011;
  localparam int_reg_t MEMTYPE_ROOT_PPN = 48'h0000_0000_0012;
  localparam int_reg_t BARE_LOAD_VALUE = 48'h0000_0000_1111;
  localparam int_reg_t RADIX_LOAD_VALUE = 48'h0000_0000_2222;
  localparam int_reg_t STALE_LOAD_VALUE = 48'h0000_0000_3333;
  localparam int_reg_t ASID_LOAD_VALUE = 48'h0000_0000_4444;
  localparam int_reg_t GLOBAL_LOAD_VALUE = 48'h0000_0000_5555;

  logic imem_req_valid;
  logic imem_req_ready;
  addr_t imem_req_addr;
  logic imem_rsp_valid;
  logic imem_rsp_ready;
  cell_t imem_rsp_cells [FETCH_GROUP_CELLS];
  fault_packet_t imem_rsp_fault;

  logic dmem_req_valid;
  logic dmem_req_ready;
  logic dmem_req_write;
  addr_t dmem_req_addr;
  logic [2:0] dmem_req_len_cells;
  cell_t dmem_req_wdata [CAPABILITY_OBJECT_CELLS];
  logic dmem_rsp_valid;
  cell_t dmem_rsp_rdata [CAPABILITY_OBJECT_CELLS];
  fault_packet_t dmem_rsp_fault;

  logic tagmem_req_valid;
  logic tagmem_req_ready;
  logic tagmem_req_write;
  addr_t tagmem_req_slot_addr;
  logic tagmem_req_wtag;
  logic tagmem_rsp_valid;
  logic tagmem_rsp_rtag;

  logic retire_valid;
  logic retire_ready;
  retire_packet_t retire_packet;
  logic core_idle;
  logic reset_observed;
  cap_t debug_pcc;
  logic debug_pcc_slot;
  int_reg_t debug_sr;
  logic [RETIRE_SEQUENCE_BITS-1:0] debug_retire_sequence;

  logic imem_rsp_pending_q;
  addr_t imem_pending_addr_q;
  logic dmem_rsp_pending_q;
  int_reg_t dmem_rsp_value_q;
  int unsigned dmem_request_count_q;

  cpu_v01_core #(
    .RESET_VECTOR(RESET_VECTOR),
    .RESET_PCC_PERMISSIONS(DATA_PERMISSIONS),
    .ENABLE_FETCH(1'b1)
  ) core (
    .clk(clk),
    .rst_n(rst_n),
    .imem_req_valid(imem_req_valid),
    .imem_req_ready(imem_req_ready),
    .imem_req_addr(imem_req_addr),
    .imem_rsp_valid(imem_rsp_valid),
    .imem_rsp_ready(imem_rsp_ready),
    .imem_rsp_cells(imem_rsp_cells),
    .imem_rsp_fault(imem_rsp_fault),
    .dmem_req_valid(dmem_req_valid),
    .dmem_req_ready(dmem_req_ready),
    .dmem_req_write(dmem_req_write),
    .dmem_req_addr(dmem_req_addr),
    .dmem_req_len_cells(dmem_req_len_cells),
    .dmem_req_wdata(dmem_req_wdata),
    .dmem_rsp_valid(dmem_rsp_valid),
    .dmem_rsp_rdata(dmem_rsp_rdata),
    .dmem_rsp_fault(dmem_rsp_fault),
    .tagmem_req_valid(tagmem_req_valid),
    .tagmem_req_ready(tagmem_req_ready),
    .tagmem_req_write(tagmem_req_write),
    .tagmem_req_slot_addr(tagmem_req_slot_addr),
    .tagmem_req_wtag(tagmem_req_wtag),
    .tagmem_rsp_valid(tagmem_rsp_valid),
    .tagmem_rsp_rtag(tagmem_rsp_rtag),
    .timer_interrupt_pending(1'b0),
    .software_interrupt_pending(1'b0),
    .external_interrupt_pending(1'b0),
    .external_event_valid(1'b0),
    .external_event_cause(16'd0),
    .debug_halt_request(1'b0),
    .retire_valid(retire_valid),
    .retire_ready(retire_ready),
    .retire_packet(retire_packet),
    .core_idle(core_idle),
    .reset_observed(reset_observed),
    .debug_pcc(debug_pcc),
    .debug_pcc_slot(debug_pcc_slot),
    .debug_sr(debug_sr),
    .debug_retire_sequence(debug_retire_sequence)
  );

  assign imem_req_ready = 1'b1;
  assign dmem_req_ready = 1'b1;
  assign tagmem_req_ready = 1'b1;
  assign tagmem_rsp_valid = 1'b0;
  assign tagmem_rsp_rtag = 1'b0;
  assign retire_ready = 1'b1;

  always_comb begin
    imem_rsp_fault = '0;
    dmem_rsp_fault = '0;
  end

  function automatic int_reg_t satp_radix4(input logic [7:0] asid, input int_reg_t root_ppn);
    int_reg_t value;
    value = (int_reg_t'(SATP_MODE_RADIX4) << SATP_MODE_SHIFT);
    value = value | (int_reg_t'(asid) << SATP_ASID_SHIFT);
    value = value | root_ppn;
    return value;
  endfunction

  function automatic int_reg_t load_value(input int unsigned index);
    unique case (MODE)
      0: begin
        unique case (index)
          0: return VIRTUAL_ADDRESS;
          default: return BARE_LOAD_VALUE;
        endcase
      end
      1: begin
        unique case (index)
          0: return VIRTUAL_ADDRESS;
          1: return satp_radix4(8'h12, ROOT_PPN);
          2: return RADIX_LOAD_VALUE;
          default: return STALE_LOAD_VALUE;
        endcase
      end
      2: begin
        unique case (index)
          0: return VIRTUAL_ADDRESS;
          1: return satp_radix4(8'h13, ROOT_PPN);
          2: return ASID_LOAD_VALUE;
          3: return USER_FETCH_ADDRESS;
          default: return GLOBAL_LOAD_VALUE;
        endcase
      end
      3: begin
        unique case (index)
          0: return VIRTUAL_ADDRESS;
          default: return satp_radix4(8'h12, PERMISSION_ROOT_PPN);
        endcase
      end
      default: begin
        unique case (index)
          0: return VIRTUAL_ADDRESS;
          default: return satp_radix4(8'h12, MEMTYPE_ROOT_PPN);
        endcase
      end
    endcase
  endfunction

  function automatic addr_t expected_data_address(input int unsigned index);
    unique case (MODE)
      0: begin
        unique case (index)
          0: return RESET_VECTOR;
          default: return VIRTUAL_ADDRESS;
        endcase
      end
      1: begin
        unique case (index)
          0: return RESET_VECTOR;
          1: return RESET_VECTOR + 48'd6;
          default: return PHYSICAL_ADDRESS_A;
        endcase
      end
      2: begin
        unique case (index)
          0: return RESET_VECTOR;
          1: return RESET_VECTOR + 48'd6;
          2: return PHYSICAL_ADDRESS_B;
          3: return RESET_VECTOR + 48'd6;
          default: return USER_FETCH_ADDRESS;
        endcase
      end
      default: begin
        unique case (index)
          0: return RESET_VECTOR;
          default: return RESET_VECTOR + 48'd6;
        endcase
      end
    endcase
  endfunction

  task automatic drive_program(input addr_t group_addr);
    addr_t offset;
    offset = group_addr - RESET_VECTOR;
    imem_rsp_cells[0] = '0;
    imem_rsp_cells[1] = '0;

    if (MODE == 0) begin
      unique case (offset)
        48'h0: begin imem_rsp_cells[0] = 24'h700000; imem_rsp_cells[1] = 24'h100000; end // CCSRRD C1, PCC
        48'h2: begin imem_rsp_cells[0] = 24'h302100; imem_rsp_cells[1] = 24'h289000; end // LD48 D2, C1, D0; SETAL D9
        48'h4: begin imem_rsp_cells[0] = 24'h420000; imem_rsp_cells[1] = 24'h112000; end // CSETADDR C1, C1, D2
        48'h6: begin imem_rsp_cells[0] = 24'h303100; imem_rsp_cells[1] = 24'h00005B; end // LD48 D3, C1, D0; PAUSE
        default: imem_rsp_cells[0] = 24'h000999;
      endcase
    end else if (MODE == 1) begin
      unique case (offset)
        48'h0: begin imem_rsp_cells[0] = 24'h700000; imem_rsp_cells[1] = 24'h100000; end // CCSRRD C1, PCC
        48'h2: begin imem_rsp_cells[0] = 24'h302100; imem_rsp_cells[1] = 24'h289000; end // LD48 D2, C1, D0; SETAL D9
        48'h4: begin imem_rsp_cells[0] = 24'h420000; imem_rsp_cells[1] = 24'h112000; end // CSETADDR C1, C1, D2
        48'h6: begin imem_rsp_cells[0] = 24'h700000; imem_rsp_cells[1] = 24'h200000; end // CCSRRD C2, PCC
        48'h8: begin imem_rsp_cells[0] = 24'h304200; imem_rsp_cells[1] = 24'h289000; end // LD48 D4, C2, D0; SETAL D9
        48'hA: begin imem_rsp_cells[0] = 24'h67C400; imem_rsp_cells[1] = 24'h305100; end // CSRWR SATP, D4; LD48 D5, C1, D0
        48'hC: begin imem_rsp_cells[0] = 24'h305100; imem_rsp_cells[1] = 24'h666D00; end // LD48 D5, C1, D0; CSRRD D6, ASID
        48'hE: begin imem_rsp_cells[0] = 24'h652600; imem_rsp_cells[1] = 24'h305100; end // SFENCE.VM.VA_ASID D2, D6; LD48 D5, C1, D0
        default: imem_rsp_cells[0] = 24'h000999;
      endcase
    end else if (MODE == 2) begin
      unique case (offset)
        48'h0: begin imem_rsp_cells[0] = 24'h700000; imem_rsp_cells[1] = 24'h100000; end // CCSRRD C1, PCC
        48'h2: begin imem_rsp_cells[0] = 24'h302100; imem_rsp_cells[1] = 24'h289000; end // LD48 D2, C1, D0; SETAL D9
        48'h4: begin imem_rsp_cells[0] = 24'h420000; imem_rsp_cells[1] = 24'h112000; end // CSETADDR C1, C1, D2
        48'h6: begin imem_rsp_cells[0] = 24'h700000; imem_rsp_cells[1] = 24'h200000; end // CCSRRD C2, PCC
        48'h8: begin imem_rsp_cells[0] = 24'h304200; imem_rsp_cells[1] = 24'h289000; end // LD48 D4, C2, D0; SETAL D9
        48'hA: begin imem_rsp_cells[0] = 24'h67C400; imem_rsp_cells[1] = 24'h666D00; end // CSRWR SATP, D4; CSRRD D6, ASID
        48'hC: begin imem_rsp_cells[0] = 24'h305100; imem_rsp_cells[1] = 24'h307200; end // LD48 D5, C1, D0; LD48 D7, C2, D0
        48'hE: begin imem_rsp_cells[0] = 24'h420000; imem_rsp_cells[1] = 24'h127000; end // CSETADDR C1, C2, D7
        48'h10: begin imem_rsp_cells[0] = 24'h308100; imem_rsp_cells[1] = 24'h620000; end // LD48 D8, C1, D0; SFENCE.VM
        48'h12: begin imem_rsp_cells[0] = 24'h636000; imem_rsp_cells[1] = 24'h647000; end // SFENCE.VM.ASID D6; SFENCE.VM.VA D7
        48'h14: begin imem_rsp_cells[0] = 24'h00005B; end // PAUSE
        default: imem_rsp_cells[0] = 24'h000999;
      endcase
    end else begin
      unique case (offset)
        48'h0: begin imem_rsp_cells[0] = 24'h700000; imem_rsp_cells[1] = 24'h100000; end // CCSRRD C1, PCC
        48'h2: begin imem_rsp_cells[0] = 24'h302100; imem_rsp_cells[1] = 24'h289000; end // LD48 D2, C1, D0; SETAL D9
        48'h4: begin imem_rsp_cells[0] = 24'h420000; imem_rsp_cells[1] = 24'h112000; end // CSETADDR C1, C1, D2
        48'h6: begin imem_rsp_cells[0] = 24'h700000; imem_rsp_cells[1] = 24'h200000; end // CCSRRD C2, PCC
        48'h8: begin imem_rsp_cells[0] = 24'h304200; imem_rsp_cells[1] = 24'h289000; end // LD48 D4, C2, D0; SETAL D9
        48'hA: begin imem_rsp_cells[0] = 24'h67C400; imem_rsp_cells[1] = 24'h305100; end // CSRWR SATP, D4; LD48 D5, C1, D0
        default: imem_rsp_cells[0] = 24'h000999;
      endcase
    end
  endtask

  task automatic check_translation(
    input addr_t expected_effective,
    input addr_t expected_physical
  );
    if (!retire_packet.translation_valid ||
        retire_packet.effective_address != expected_effective ||
        retire_packet.physical_address != expected_physical ||
        retire_packet.translation_memory_type != MEMORY_TYPE_NORMAL_COHERENT) begin
      $fatal(1, "integrated mmu/tlb translation mismatch");
    end
  endtask

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      imem_rsp_valid <= 1'b0;
      imem_rsp_pending_q <= 1'b0;
      imem_pending_addr_q <= '0;
      dmem_rsp_valid <= 1'b0;
      dmem_rsp_pending_q <= 1'b0;
      dmem_rsp_value_q <= '0;
      dmem_request_count_q <= 0;
      bare_seen <= 1'b0;
      radix_seen <= 1'b0;
      stale_seen <= 1'b0;
      sfence_seen <= 1'b0;
      asid_seen <= 1'b0;
      global_seen <= 1'b0;
      permission_fault_seen <= 1'b0;
      memtype_fault_seen <= 1'b0;
      pause_seen <= 1'b0;
      done <= 1'b0;
      for (int i = 0; i < FETCH_GROUP_CELLS; i++) begin
        imem_rsp_cells[i] <= '0;
      end
      for (int i = 0; i < CAPABILITY_OBJECT_CELLS; i++) begin
        dmem_rsp_rdata[i] <= '0;
      end
    end else begin
      imem_rsp_valid <= 1'b0;
      dmem_rsp_valid <= 1'b0;

      if (imem_req_valid && imem_req_ready) begin
        imem_pending_addr_q <= imem_req_addr;
        imem_rsp_pending_q <= 1'b1;
      end
      if (imem_rsp_pending_q) begin
        drive_program(imem_pending_addr_q);
        imem_rsp_valid <= 1'b1;
        imem_rsp_pending_q <= 1'b0;
      end

      if (dmem_req_valid && dmem_req_ready) begin
        if (dmem_req_write || dmem_req_len_cells != 3'd2) begin
          $fatal(1, "integrated mmu/tlb unexpected data request kind");
        end
        if (dmem_req_addr != expected_data_address(dmem_request_count_q)) begin
          $fatal(1, "integrated mmu/tlb data address mismatch");
        end
        dmem_rsp_value_q <= load_value(dmem_request_count_q);
        dmem_rsp_pending_q <= 1'b1;
        dmem_request_count_q <= dmem_request_count_q + 1;
      end
      if (dmem_rsp_pending_q) begin
        dmem_rsp_rdata[0] <= dmem_rsp_value_q[23:0];
        dmem_rsp_rdata[1] <= dmem_rsp_value_q[47:24];
        dmem_rsp_rdata[2] <= '0;
        dmem_rsp_rdata[3] <= '0;
        dmem_rsp_valid <= 1'b1;
        dmem_rsp_pending_q <= 1'b0;
      end

      if (retire_valid && !done) begin
        unique case (MODE)
          0: begin
            if (retire_packet.decoded.opcode_id == OPC_LD48_24 &&
                retire_packet.integer_write_index == 4'd3) begin
              check_translation(VIRTUAL_ADDRESS, VIRTUAL_ADDRESS);
              if (retire_packet.translation_tlb_hit ||
                  retire_packet.tlb_fill_valid ||
                  retire_packet.integer_write_value != BARE_LOAD_VALUE) begin
                $fatal(1, "integrated mmu/tlb bare load mismatch");
              end
              bare_seen <= 1'b1;
            end else if (retire_packet.decoded.opcode_id == OPC_PAUSE_12) begin
              pause_seen <= 1'b1;
              done <= 1'b1;
            end
          end

          1: begin
            if (retire_packet.fault.valid) begin
              if (retire_packet.decoded.opcode_id != OPC_LD48_24 ||
                  retire_packet.fault.cause != EXC_PAGE_FAULT ||
                  retire_packet.fault.tval != VIRTUAL_ADDRESS ||
                  !retire_packet.translation_valid) begin
                $fatal(1, "integrated mmu/tlb RADIX4 page fault result mismatch");
              end
              done <= 1'b1;
            end else if (retire_packet.decoded.opcode_id == OPC_LD48_24 &&
                         retire_packet.integer_write_index == 4'd5 &&
                         !radix_seen) begin
              check_translation(VIRTUAL_ADDRESS, PHYSICAL_ADDRESS_A);
              if (!retire_packet.tlb_fill_valid ||
                  retire_packet.tlb_fill_asid != 8'h12 ||
                  retire_packet.page_walk_level != 3'd3 ||
                  retire_packet.integer_write_value != RADIX_LOAD_VALUE) begin
                $fatal(1, "integrated mmu/tlb RADIX4 page-walk translation result mismatch");
              end
              radix_seen <= 1'b1;
            end else if (retire_packet.decoded.opcode_id == OPC_LD48_24 &&
                         retire_packet.integer_write_index == 4'd5 &&
                         radix_seen &&
                         !stale_seen) begin
              check_translation(VIRTUAL_ADDRESS, PHYSICAL_ADDRESS_A);
              if (!retire_packet.translation_tlb_hit ||
                  retire_packet.tlb_fill_valid ||
                  retire_packet.integer_write_value != STALE_LOAD_VALUE) begin
                $fatal(1, "integrated mmu/tlb stale TLB hit before SFENCE result mismatch");
              end
              stale_seen <= 1'b1;
            end else if (retire_packet.decoded.opcode_id == OPC_SFENCE_VM_VA_ASID_24) begin
              if (!retire_packet.tlb_invalidate_valid ||
                  retire_packet.tlb_invalidate_kind != TLB_INV_VA_ASID ||
                  retire_packet.tlb_invalidate_va != VIRTUAL_ADDRESS ||
                  retire_packet.tlb_invalidate_asid != 8'h12) begin
                $fatal(1, "integrated mmu/tlb SFENCE.VM.VA_ASID mismatch");
              end
              sfence_seen <= 1'b1;
            end
          end

          2: begin
            if (retire_packet.decoded.opcode_id == OPC_LD48_24 &&
                retire_packet.integer_write_index == 4'd5) begin
              check_translation(VIRTUAL_ADDRESS, PHYSICAL_ADDRESS_B);
              if (!retire_packet.tlb_fill_valid ||
                  retire_packet.tlb_fill_asid != 8'h13 ||
                  retire_packet.integer_write_value != ASID_LOAD_VALUE) begin
                $fatal(1, "integrated mmu/tlb ASID-specific fill mismatch");
              end
              asid_seen <= 1'b1;
            end else if (retire_packet.decoded.opcode_id == OPC_LD48_24 &&
                         retire_packet.integer_write_index == 4'd8) begin
              check_translation(USER_FETCH_ADDRESS, USER_FETCH_ADDRESS);
              if (!retire_packet.tlb_fill_valid ||
                  !retire_packet.tlb_fill_global ||
                  retire_packet.integer_write_value != GLOBAL_LOAD_VALUE) begin
                $fatal(1, "integrated mmu/tlb ASID/global TLB scope result mismatch");
              end
              global_seen <= 1'b1;
            end else if (retire_packet.decoded.opcode_id == OPC_SFENCE_VM_24) begin
              if (!retire_packet.tlb_invalidate_valid ||
                  retire_packet.tlb_invalidate_kind != TLB_INV_ALL) begin
                $fatal(1, "integrated mmu/tlb SFENCE.VM invalidation result mismatch");
              end
              sfence_seen <= 1'b1;
            end else if (retire_packet.decoded.opcode_id == OPC_SFENCE_VM_ASID_24) begin
              if (!retire_packet.tlb_invalidate_valid ||
                  retire_packet.tlb_invalidate_kind != TLB_INV_ASID ||
                  retire_packet.tlb_invalidate_asid != 8'h13) begin
                $fatal(1, "integrated mmu/tlb SFENCE.VM.ASID mismatch");
              end
            end else if (retire_packet.decoded.opcode_id == OPC_SFENCE_VM_VA_24) begin
              if (!retire_packet.tlb_invalidate_valid ||
                  retire_packet.tlb_invalidate_kind != TLB_INV_VA ||
                  retire_packet.tlb_invalidate_va != USER_FETCH_ADDRESS) begin
                $fatal(1, "integrated mmu/tlb SFENCE.VM.VA mismatch");
              end
            end else if (retire_packet.decoded.opcode_id == OPC_PAUSE_12) begin
              pause_seen <= 1'b1;
              done <= 1'b1;
            end
          end

          3: begin
            if (retire_packet.fault.valid) begin
              if (retire_packet.fault.cause != EXC_PAGE_FAULT ||
                  retire_packet.fault.tval != VIRTUAL_ADDRESS ||
                  retire_packet.translation_memory_type != MEMORY_TYPE_NORMAL_COHERENT) begin
                $fatal(1, "integrated mmu/tlb permission page fault mismatch");
              end
              permission_fault_seen <= 1'b1;
              done <= 1'b1;
            end
          end

          default: begin
            if (retire_packet.fault.valid) begin
              if (retire_packet.fault.cause != EXC_PAGE_FAULT ||
                  retire_packet.fault.tval != VIRTUAL_ADDRESS ||
                  retire_packet.translation_memory_type != MEMORY_TYPE_RESERVED) begin
                $fatal(1, "integrated mmu/tlb reserved memory type page fault mismatch");
              end
              memtype_fault_seen <= 1'b1;
              done <= 1'b1;
            end
          end
        endcase
      end
    end
  end

  // verilator lint_off UNUSEDSIGNAL
  wire logic unused_ports = &{
    tagmem_req_valid,
    tagmem_req_write,
    tagmem_req_slot_addr[0],
    tagmem_req_wtag,
    dmem_req_wdata[0][0],
    imem_rsp_ready,
    core_idle,
    reset_observed,
    debug_pcc.tag,
    debug_pcc_slot,
    debug_sr[0],
    debug_retire_sequence[0]
  };
  // verilator lint_on UNUSEDSIGNAL
endmodule

module cpu_v01_core_mmu_tlb_tb;
  logic clk;
  logic rst_n;

  logic bare_bare_seen;
  logic bare_radix_seen;
  logic bare_stale_seen;
  logic bare_sfence_seen;
  logic bare_asid_seen;
  logic bare_global_seen;
  logic bare_permission_fault_seen;
  logic bare_memtype_fault_seen;
  logic bare_pause_seen;
  logic bare_done;

  logic radix_bare_seen;
  logic radix_radix_seen;
  logic radix_stale_seen;
  logic radix_sfence_seen;
  logic radix_asid_seen;
  logic radix_global_seen;
  logic radix_permission_fault_seen;
  logic radix_memtype_fault_seen;
  logic radix_pause_seen;
  logic radix_done;

  logic asid_bare_seen;
  logic asid_radix_seen;
  logic asid_stale_seen;
  logic asid_sfence_seen;
  logic asid_asid_seen;
  logic asid_global_seen;
  logic asid_permission_fault_seen;
  logic asid_memtype_fault_seen;
  logic asid_pause_seen;
  logic asid_done;

  logic perm_bare_seen;
  logic perm_radix_seen;
  logic perm_stale_seen;
  logic perm_sfence_seen;
  logic perm_asid_seen;
  logic perm_global_seen;
  logic perm_permission_fault_seen;
  logic perm_memtype_fault_seen;
  logic perm_pause_seen;
  logic perm_done;

  logic memtype_bare_seen;
  logic memtype_radix_seen;
  logic memtype_stale_seen;
  logic memtype_sfence_seen;
  logic memtype_asid_seen;
  logic memtype_global_seen;
  logic memtype_permission_fault_seen;
  logic memtype_memtype_fault_seen;
  logic memtype_pause_seen;
  logic memtype_done;

  cpu_v01_core_mmu_tlb_fixture #(
    .MODE(0),
    .RESET_VECTOR(48'h0000_0000_A000)
  ) bare_fixture (
    .clk(clk),
    .rst_n(rst_n),
    .bare_seen(bare_bare_seen),
    .radix_seen(bare_radix_seen),
    .stale_seen(bare_stale_seen),
    .sfence_seen(bare_sfence_seen),
    .asid_seen(bare_asid_seen),
    .global_seen(bare_global_seen),
    .permission_fault_seen(bare_permission_fault_seen),
    .memtype_fault_seen(bare_memtype_fault_seen),
    .pause_seen(bare_pause_seen),
    .done(bare_done)
  );

  cpu_v01_core_mmu_tlb_fixture #(
    .MODE(1),
    .RESET_VECTOR(48'h0000_0000_B000)
  ) radix_fixture (
    .clk(clk),
    .rst_n(rst_n),
    .bare_seen(radix_bare_seen),
    .radix_seen(radix_radix_seen),
    .stale_seen(radix_stale_seen),
    .sfence_seen(radix_sfence_seen),
    .asid_seen(radix_asid_seen),
    .global_seen(radix_global_seen),
    .permission_fault_seen(radix_permission_fault_seen),
    .memtype_fault_seen(radix_memtype_fault_seen),
    .pause_seen(radix_pause_seen),
    .done(radix_done)
  );

  cpu_v01_core_mmu_tlb_fixture #(
    .MODE(2),
    .RESET_VECTOR(48'h0000_0000_C000)
  ) asid_fixture (
    .clk(clk),
    .rst_n(rst_n),
    .bare_seen(asid_bare_seen),
    .radix_seen(asid_radix_seen),
    .stale_seen(asid_stale_seen),
    .sfence_seen(asid_sfence_seen),
    .asid_seen(asid_asid_seen),
    .global_seen(asid_global_seen),
    .permission_fault_seen(asid_permission_fault_seen),
    .memtype_fault_seen(asid_memtype_fault_seen),
    .pause_seen(asid_pause_seen),
    .done(asid_done)
  );

  cpu_v01_core_mmu_tlb_fixture #(
    .MODE(3),
    .RESET_VECTOR(48'h0000_0000_D000)
  ) permission_fixture (
    .clk(clk),
    .rst_n(rst_n),
    .bare_seen(perm_bare_seen),
    .radix_seen(perm_radix_seen),
    .stale_seen(perm_stale_seen),
    .sfence_seen(perm_sfence_seen),
    .asid_seen(perm_asid_seen),
    .global_seen(perm_global_seen),
    .permission_fault_seen(perm_permission_fault_seen),
    .memtype_fault_seen(perm_memtype_fault_seen),
    .pause_seen(perm_pause_seen),
    .done(perm_done)
  );

  cpu_v01_core_mmu_tlb_fixture #(
    .MODE(4),
    .RESET_VECTOR(48'h0000_0000_E000)
  ) memtype_fixture (
    .clk(clk),
    .rst_n(rst_n),
    .bare_seen(memtype_bare_seen),
    .radix_seen(memtype_radix_seen),
    .stale_seen(memtype_stale_seen),
    .sfence_seen(memtype_sfence_seen),
    .asid_seen(memtype_asid_seen),
    .global_seen(memtype_global_seen),
    .permission_fault_seen(memtype_permission_fault_seen),
    .memtype_fault_seen(memtype_memtype_fault_seen),
    .pause_seen(memtype_pause_seen),
    .done(memtype_done)
  );

  initial begin
    clk = 1'b0;
    forever #5 clk = ~clk;
  end

  initial begin
    rst_n = 1'b0;
    repeat (2) @(posedge clk);
    rst_n = 1'b1;
    wait (bare_done && radix_done && asid_done && perm_done && memtype_done);

    if (!bare_bare_seen || !bare_pause_seen) begin
      $fatal(1, "integrated mmu/tlb bare SATP identity translation result mismatch");
    end
    if (!radix_radix_seen || !radix_stale_seen || !radix_sfence_seen) begin
      $fatal(1, "integrated mmu/tlb RADIX4 stale/SFENCE sequence mismatch");
    end
    if (!asid_asid_seen || !asid_global_seen || !asid_sfence_seen || !asid_pause_seen) begin
      $fatal(1, "integrated mmu/tlb ASID/global TLB scope result mismatch");
    end
    if (!perm_permission_fault_seen || !memtype_memtype_fault_seen) begin
      $fatal(1, "integrated mmu/tlb page fault sequence mismatch");
    end

    $finish;
  end

  // verilator lint_off UNUSEDSIGNAL
  wire logic unused_fixture_outputs = &{
    bare_radix_seen,
    bare_stale_seen,
    bare_sfence_seen,
    bare_asid_seen,
    bare_global_seen,
    bare_permission_fault_seen,
    bare_memtype_fault_seen,
    radix_bare_seen,
    radix_asid_seen,
    radix_global_seen,
    radix_permission_fault_seen,
    radix_memtype_fault_seen,
    radix_pause_seen,
    asid_bare_seen,
    asid_radix_seen,
    asid_stale_seen,
    asid_permission_fault_seen,
    asid_memtype_fault_seen,
    perm_bare_seen,
    perm_radix_seen,
    perm_stale_seen,
    perm_sfence_seen,
    perm_asid_seen,
    perm_global_seen,
    perm_memtype_fault_seen,
    perm_pause_seen,
    memtype_bare_seen,
    memtype_radix_seen,
    memtype_stale_seen,
    memtype_sfence_seen,
    memtype_asid_seen,
    memtype_global_seen,
    memtype_permission_fault_seen,
    memtype_pause_seen
  };
  // verilator lint_on UNUSEDSIGNAL
endmodule
