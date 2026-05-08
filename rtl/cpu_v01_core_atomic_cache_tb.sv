module cpu_v01_core_atomic_cache_fixture #(
  parameter int MODE = 0,
  parameter cpu_v01_pkg::addr_t RESET_VECTOR = 48'h0000_0000_F000
) (
  input  logic clk,
  input  logic rst_n,
  output logic normal_seen,
  output logic fault_clear_seen,
  output logic trap_csr_fence_seen,
  output logic device_fault_seen,
  output logic done
);
  import cpu_v01_pkg::*;

  localparam logic [7:0] DATA_PERMISSIONS = 8'd31;
  localparam int_reg_t SR_RESET_VALUE = 48'h0000_0000_00C0;
  localparam addr_t DEVICE_PA = 48'h0000_0000_F000;
  localparam int_reg_t INITIAL_VALUE = 48'h0000_0000_1111;

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
  int_reg_t memory_value_q;
  logic memory_tag_q;

  logic ll_install_q;
  logic sc_success_q;
  logic sc_failure_q;
  logic conflict_clear_q;
  logic fence_q;
  logic fence_i_q;
  logic cache_clean_q;
  logic cache_inval_q;
  logic cache_cleaninval_q;
  logic csr_clear_q;
  logic sfence_clear_q;

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
    .dmem_req_addr(dmem_req_addr),
    .dmem_req_write(dmem_req_write),
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

  task automatic drive_program(input addr_t group_addr);
    addr_t offset;
    offset = group_addr - RESET_VECTOR;
    imem_rsp_cells[0] = '0;
    imem_rsp_cells[1] = '0;

    unique case (MODE)
      0: begin
        unique case (offset)
          48'h0: begin imem_rsp_cells[0] = 24'h700000; imem_rsp_cells[1] = 24'h100000; end // CCSRRD C1, PCC
          48'h2: begin imem_rsp_cells[0] = 24'h342100; imem_rsp_cells[1] = 24'h664000; end // LL48 D2, C1, D0; CSRRD D4, SR
          48'h4: begin imem_rsp_cells[0] = 24'h353104; imem_rsp_cells[1] = 24'h355104; end // SC48 D3, C1, D0, D4; SC48 D5, C1, D0, D4
          48'h6: begin imem_rsp_cells[0] = 24'h346100; imem_rsp_cells[1] = 24'h311040; end // LL48 D6, C1, D0; ST48 C1, D0, D4
          48'h8: begin imem_rsp_cells[0] = 24'h600000; imem_rsp_cells[1] = 24'h610000; end // FENCE; FENCE.I
          48'hA: begin imem_rsp_cells[0] = 24'h287000; imem_rsp_cells[1] = 24'h801070; end // SETAL D7; CACHE.CLEAN C1, D0, D7
          48'hC: begin imem_rsp_cells[0] = 24'h346100; imem_rsp_cells[1] = 24'h811070; end // LL48 D6, C1, D0; CACHE.INVAL C1, D0, D7
          48'hE: begin imem_rsp_cells[0] = 24'h346100; imem_rsp_cells[1] = 24'h821070; end // LL48 D6, C1, D0; CACHE.CLEANINVAL C1, D0, D7
          48'h10: begin imem_rsp_cells[0] = 24'h00005B; end // PAUSE
          default: begin imem_rsp_cells[0] = 24'h000999; end
        endcase
      end

      1: begin
        unique case (offset)
          48'h0: begin imem_rsp_cells[0] = 24'h700000; imem_rsp_cells[1] = 24'h100000; end // CCSRRD C1, PCC
          48'h2: begin imem_rsp_cells[0] = 24'h342100; imem_rsp_cells[1] = 24'h287000; end // LL48 D2, C1, D0; SETAL D7
          48'h4: begin imem_rsp_cells[0] = 24'h343170; end // LL48 D3, C1, D7
          default: begin imem_rsp_cells[0] = 24'h000999; end
        endcase
      end

      2: begin
        unique case (offset)
          48'h0: begin imem_rsp_cells[0] = 24'h700000; imem_rsp_cells[1] = 24'h100000; end // CCSRRD C1, PCC
          48'h2: begin imem_rsp_cells[0] = 24'h287000; imem_rsp_cells[1] = 24'h342100; end // SETAL D7; LL48 D2, C1, D0
          48'h4: begin imem_rsp_cells[0] = 24'h67D700; imem_rsp_cells[1] = 24'h342100; end // CSRWR ASID, D7; LL48 D2, C1, D0
          48'h6: begin imem_rsp_cells[0] = 24'h620000; imem_rsp_cells[1] = 24'h342100; end // SFENCE.VM; LL48 D2, C1, D0
          48'h8: begin imem_rsp_cells[0] = 24'h000055; end // BRK
          default: begin imem_rsp_cells[0] = 24'h000999; end
        endcase
      end

      default: begin
        unique case (offset)
          48'h0: begin imem_rsp_cells[0] = 24'h700000; imem_rsp_cells[1] = 24'h100000; end // CCSRRD C1, PCC
          48'h2: begin imem_rsp_cells[0] = 24'h302100; imem_rsp_cells[1] = 24'h287000; end // LD48 D2, C1, D0; SETAL D7
          48'h4: begin imem_rsp_cells[0] = 24'h420000; imem_rsp_cells[1] = 24'h112000; end // CSETADDR C1, C1, D2
          48'h6: begin imem_rsp_cells[0] = 24'h801070; end // CACHE.CLEAN C1, D0, D7
          default: begin imem_rsp_cells[0] = 24'h000999; end
        endcase
      end
    endcase
  endtask

  task automatic check_reservation_install;
    if (!retire_packet.reservation_install_valid ||
        retire_packet.reservation_word_address != RESET_VECTOR ||
        retire_packet.reservation_memory_type != MEMORY_TYPE_NORMAL_COHERENT) begin
      $fatal(1, "integrated atomic/cache LL48 reservation install mismatch");
    end
  endtask

  task automatic check_reservation_clear;
    if (!retire_packet.reservation_clear_valid ||
        retire_packet.reservation_word_address != RESET_VECTOR ||
        retire_packet.reservation_memory_type != MEMORY_TYPE_NORMAL_COHERENT) begin
      $fatal(1, "integrated atomic/cache reservation clear mismatch");
    end
  endtask

  task automatic check_cache_maintenance(input logic [CACHE_MAINT_KIND_BITS-1:0] kind);
    if (!retire_packet.cache_maintenance_valid ||
        retire_packet.cache_maintenance_kind != kind ||
        retire_packet.cache_maintenance_address != RESET_VECTOR ||
        retire_packet.cache_maintenance_length != 48'd1) begin
      $fatal(1, "integrated atomic/cache CACHE maintenance access result mismatch");
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
      memory_value_q <= INITIAL_VALUE;
      memory_tag_q <= 1'b1;
      ll_install_q <= 1'b0;
      sc_success_q <= 1'b0;
      sc_failure_q <= 1'b0;
      conflict_clear_q <= 1'b0;
      fence_q <= 1'b0;
      fence_i_q <= 1'b0;
      cache_clean_q <= 1'b0;
      cache_inval_q <= 1'b0;
      cache_cleaninval_q <= 1'b0;
      csr_clear_q <= 1'b0;
      sfence_clear_q <= 1'b0;
      normal_seen <= 1'b0;
      fault_clear_seen <= 1'b0;
      trap_csr_fence_seen <= 1'b0;
      device_fault_seen <= 1'b0;
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
        if (dmem_req_addr != RESET_VECTOR || dmem_req_len_cells != 3'd2) begin
          $fatal(1, "integrated atomic/cache unexpected data request");
        end
        if (dmem_req_write) begin
          memory_value_q <= {dmem_req_wdata[1], dmem_req_wdata[0]};
        end else begin
          dmem_rsp_value_q <= MODE == 3 ? DEVICE_PA : memory_value_q;
          dmem_rsp_pending_q <= 1'b1;
        end
      end
      if (dmem_rsp_pending_q) begin
        dmem_rsp_rdata[0] <= dmem_rsp_value_q[23:0];
        dmem_rsp_rdata[1] <= dmem_rsp_value_q[47:24];
        dmem_rsp_rdata[2] <= '0;
        dmem_rsp_rdata[3] <= '0;
        dmem_rsp_valid <= 1'b1;
        dmem_rsp_pending_q <= 1'b0;
      end

      if (tagmem_req_valid && tagmem_req_ready) begin
        if (!tagmem_req_write || tagmem_req_slot_addr != {RESET_VECTOR[ADDR_BITS-1:2], 2'b00}) begin
          $fatal(1, "integrated atomic/cache unexpected tag request");
        end
        memory_tag_q <= tagmem_req_wtag;
      end

      if (retire_valid && !done) begin
        unique case (MODE)
          0: begin
            if (retire_packet.fault.valid) begin
              $fatal(1, "integrated atomic/cache unexpected normal-mode fault");
            end
            unique case (retire_packet.decoded.opcode_id)
              OPC_LL48_24: begin
                check_reservation_install();
                ll_install_q <= 1'b1;
              end

              OPC_SC48_24: begin
                if (retire_packet.integer_write_index == 4'd3) begin
                  if (!retire_packet.sc_success ||
                      !retire_packet.integer_write_valid ||
                      retire_packet.integer_write_value != 48'd0 ||
                      retire_packet.memory_effect_kind != MEM_EFFECT_ST48 ||
                      retire_packet.memory_effect_address != RESET_VECTOR ||
                      retire_packet.memory_integer_value != SR_RESET_VALUE ||
                      !retire_packet.tag_write_valid ||
                      retire_packet.tag_write_value) begin
                    $fatal(1, "integrated atomic/cache LL48/SC48 success result mismatch");
                  end
                  check_reservation_clear();
                  sc_success_q <= 1'b1;
                end else if (retire_packet.integer_write_index == 4'd5) begin
                  if (retire_packet.sc_success ||
                      !retire_packet.integer_write_valid ||
                      retire_packet.integer_write_value != 48'd1 ||
                      retire_packet.memory_effect_kind != MEM_EFFECT_NONE ||
                      retire_packet.tag_write_valid) begin
                    $fatal(1, "integrated atomic/cache SC48 failure result mismatch");
                  end
                  check_reservation_clear();
                  sc_failure_q <= 1'b1;
                end
              end

              OPC_ST48_24: begin
                if (retire_packet.memory_effect_kind != MEM_EFFECT_ST48 ||
                    retire_packet.memory_effect_address != RESET_VECTOR ||
                    retire_packet.memory_integer_value != SR_RESET_VALUE ||
                    !retire_packet.tag_write_valid ||
                    retire_packet.tag_write_value) begin
                  $fatal(1, "integrated atomic/cache LL/SC conflict clear result mismatch");
                end
                check_reservation_clear();
                conflict_clear_q <= 1'b1;
              end

              OPC_FENCE_24: begin
                if (!retire_packet.fence_order_valid) begin
                  $fatal(1, "integrated atomic/cache FENCE/FENCE.I ordering result mismatch");
                end
                fence_q <= 1'b1;
              end

              OPC_FENCE_I_24: begin
                if (!retire_packet.fence_i_valid) begin
                  $fatal(1, "integrated atomic/cache FENCE/FENCE.I ordering result mismatch");
                end
                fence_i_q <= 1'b1;
              end

              OPC_CACHE_CLEAN_24: begin
                check_cache_maintenance(CACHE_MAINT_CLEAN);
                if (retire_packet.reservation_clear_valid) begin
                  $fatal(1, "integrated atomic/cache CACHE.CLEAN cleared reservation");
                end
                cache_clean_q <= 1'b1;
              end

              OPC_CACHE_INVAL_24: begin
                check_cache_maintenance(CACHE_MAINT_INVAL);
                check_reservation_clear();
                cache_inval_q <= 1'b1;
              end

              OPC_CACHE_CLEANINVAL_24: begin
                check_cache_maintenance(CACHE_MAINT_CLEANINVAL);
                check_reservation_clear();
                cache_cleaninval_q <= 1'b1;
              end

              OPC_PAUSE_12: begin
                if (!ll_install_q || !sc_success_q) begin
                  $fatal(1, "integrated atomic/cache LL48/SC48 success result mismatch");
                end
                if (!sc_failure_q) begin
                  $fatal(1, "integrated atomic/cache SC48 failure result mismatch");
                end
                if (!conflict_clear_q) begin
                  $fatal(1, "integrated atomic/cache LL/SC conflict clear result mismatch");
                end
                if (!fence_q || !fence_i_q) begin
                  $fatal(1, "integrated atomic/cache FENCE/FENCE.I ordering result mismatch");
                end
                if (!cache_clean_q || !cache_inval_q || !cache_cleaninval_q) begin
                  $fatal(1, "integrated atomic/cache CACHE maintenance access result mismatch");
                end
                normal_seen <= 1'b1;
                done <= 1'b1;
              end

              default: begin
              end
            endcase
          end

          1: begin
            if (retire_packet.fault.valid) begin
              if (retire_packet.decoded.opcode_id != OPC_LL48_24 ||
                  retire_packet.fault.cause != EXC_ALIGN_FAULT ||
                  retire_packet.fault.tval != RESET_VECTOR + 48'd1) begin
                $fatal(1, "integrated atomic/cache faulting LL48 reservation clear result mismatch");
              end
              check_reservation_clear();
              fault_clear_seen <= 1'b1;
              done <= 1'b1;
            end else if (retire_packet.decoded.opcode_id == OPC_LL48_24) begin
              check_reservation_install();
            end
          end

          2: begin
            if (retire_packet.fault.valid) begin
              if (retire_packet.decoded.opcode_id != OPC_BRK_12 ||
                  retire_packet.fault.cause != EXC_BREAKPOINT) begin
                $fatal(1, "integrated atomic/cache trap CSR fence reservation clear result mismatch");
              end
              check_reservation_clear();
              if (!csr_clear_q || !sfence_clear_q) begin
                $fatal(1, "integrated atomic/cache trap CSR fence reservation clear result mismatch");
              end
              trap_csr_fence_seen <= 1'b1;
              done <= 1'b1;
            end else if (retire_packet.decoded.opcode_id == OPC_LL48_24) begin
              check_reservation_install();
            end else if (retire_packet.decoded.opcode_id == OPC_CSRWR_24) begin
              if (!retire_packet.csr_write_valid ||
                  retire_packet.csr_write_index != CSR_ASID ||
                  retire_packet.csr_write_value != 48'd1) begin
                $fatal(1, "integrated atomic/cache trap CSR fence reservation clear result mismatch");
              end
              check_reservation_clear();
              csr_clear_q <= 1'b1;
            end else if (retire_packet.decoded.opcode_id == OPC_SFENCE_VM_24) begin
              if (!retire_packet.tlb_invalidate_valid ||
                  retire_packet.tlb_invalidate_kind != TLB_INV_ALL) begin
                $fatal(1, "integrated atomic/cache trap CSR fence reservation clear result mismatch");
              end
              check_reservation_clear();
              sfence_clear_q <= 1'b1;
            end
          end

          default: begin
            if (retire_packet.fault.valid) begin
              if (retire_packet.decoded.opcode_id != OPC_CACHE_CLEAN_24 ||
                  retire_packet.fault.cause != EXC_ACCESS_FAULT ||
                  retire_packet.fault.tval != DEVICE_PA ||
                  !retire_packet.translation_valid ||
                  retire_packet.translation_memory_type != MEMORY_TYPE_DEVICE_ORDERED ||
                  retire_packet.cache_maintenance_valid) begin
                $fatal(1, "integrated atomic/cache CACHE device access fault result mismatch");
              end
              device_fault_seen <= 1'b1;
              done <= 1'b1;
            end
          end
        endcase
      end
    end
  end

  // verilator lint_off UNUSEDSIGNAL
  wire logic unused_signals = &{
    memory_tag_q,
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

module cpu_v01_core_atomic_cache_tb;
  logic clk;
  logic rst_n;

  logic normal_seen;
  logic normal_fault_clear_seen;
  logic normal_trap_csr_fence_seen;
  logic normal_device_fault_seen;
  logic normal_done;

  logic fault_normal_seen;
  logic fault_clear_seen;
  logic fault_trap_csr_fence_seen;
  logic fault_device_fault_seen;
  logic fault_done;

  logic trap_normal_seen;
  logic trap_fault_clear_seen;
  logic trap_csr_fence_seen;
  logic trap_device_fault_seen;
  logic trap_done;

  logic device_normal_seen;
  logic device_fault_clear_seen;
  logic device_trap_csr_fence_seen;
  logic device_fault_seen;
  logic device_done;

  cpu_v01_core_atomic_cache_fixture #(
    .MODE(0),
    .RESET_VECTOR(48'h0000_0000_6000)
  ) normal_fixture (
    .clk(clk),
    .rst_n(rst_n),
    .normal_seen(normal_seen),
    .fault_clear_seen(normal_fault_clear_seen),
    .trap_csr_fence_seen(normal_trap_csr_fence_seen),
    .device_fault_seen(normal_device_fault_seen),
    .done(normal_done)
  );

  cpu_v01_core_atomic_cache_fixture #(
    .MODE(1),
    .RESET_VECTOR(48'h0000_0000_7000)
  ) fault_fixture (
    .clk(clk),
    .rst_n(rst_n),
    .normal_seen(fault_normal_seen),
    .fault_clear_seen(fault_clear_seen),
    .trap_csr_fence_seen(fault_trap_csr_fence_seen),
    .device_fault_seen(fault_device_fault_seen),
    .done(fault_done)
  );

  cpu_v01_core_atomic_cache_fixture #(
    .MODE(2),
    .RESET_VECTOR(48'h0000_0000_8000)
  ) trap_fixture (
    .clk(clk),
    .rst_n(rst_n),
    .normal_seen(trap_normal_seen),
    .fault_clear_seen(trap_fault_clear_seen),
    .trap_csr_fence_seen(trap_csr_fence_seen),
    .device_fault_seen(trap_device_fault_seen),
    .done(trap_done)
  );

  cpu_v01_core_atomic_cache_fixture #(
    .MODE(3),
    .RESET_VECTOR(48'h0000_0000_9000)
  ) device_fixture (
    .clk(clk),
    .rst_n(rst_n),
    .normal_seen(device_normal_seen),
    .fault_clear_seen(device_fault_clear_seen),
    .trap_csr_fence_seen(device_trap_csr_fence_seen),
    .device_fault_seen(device_fault_seen),
    .done(device_done)
  );

  initial begin
    clk = 1'b0;
    forever #5 clk = ~clk;
  end

  initial begin
    rst_n = 1'b0;
    repeat (2) @(posedge clk);
    rst_n = 1'b1;
    wait (normal_done && fault_done && trap_done && device_done);

    if (!normal_seen) begin
      $fatal(1, "integrated atomic/cache normal sequence mismatch");
    end
    if (!fault_clear_seen) begin
      $fatal(1, "integrated atomic/cache faulting LL48 reservation clear result mismatch");
    end
    if (!trap_csr_fence_seen) begin
      $fatal(1, "integrated atomic/cache trap CSR fence reservation clear result mismatch");
    end
    if (!device_fault_seen) begin
      $fatal(1, "integrated atomic/cache CACHE device access fault result mismatch");
    end

    $finish;
  end

  // verilator lint_off UNUSEDSIGNAL
  wire logic unused_fixture_outputs = &{
    normal_fault_clear_seen,
    normal_trap_csr_fence_seen,
    normal_device_fault_seen,
    fault_normal_seen,
    fault_trap_csr_fence_seen,
    fault_device_fault_seen,
    trap_normal_seen,
    trap_fault_clear_seen,
    trap_device_fault_seen,
    device_normal_seen,
    device_fault_clear_seen,
    device_trap_csr_fence_seen
  };
  // verilator lint_on UNUSEDSIGNAL
endmodule
