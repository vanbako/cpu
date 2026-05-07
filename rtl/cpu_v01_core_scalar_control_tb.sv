module cpu_v01_core_scalar_control_fixture #(
  parameter int MODE = 0,
  parameter cpu_v01_pkg::addr_t RESET_VECTOR = 48'h0000_0000_0000
) (
  input  logic clk,
  input  logic rst_n,
  output logic csrrd_sr_seen,
  output logic add_seen,
  output logic cmp_seen,
  output logic bcc_not_taken_seen,
  output logic csrwr_seen,
  output logic csrrd_scratch_seen,
  output logic csrwr48_seen,
  output logic csrrd48_seen,
  output logic bra_seen,
  output logic pause_seen,
  output logic epccrd_seen,
  output logic epccwr_seen,
  output logic ccsrwr_seen,
  output logic ccsrrd_seen,
  output logic brk_fault_seen,
  output logic done
);
  import cpu_v01_pkg::*;

  localparam int_reg_t SR_RESET_VALUE = 48'h0000_0000_00C0;
  localparam int_reg_t DOUBLE_SR_VALUE = 48'h0000_0000_0180;

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

  logic rsp_pending_q;
  addr_t pending_addr_q;

  cpu_v01_core #(
    .RESET_VECTOR(RESET_VECTOR),
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
  assign dmem_rsp_valid = 1'b0;
  assign dmem_rsp_fault = '0;
  assign tagmem_req_ready = 1'b1;
  assign tagmem_rsp_valid = 1'b0;
  assign tagmem_rsp_rtag = 1'b0;
  assign retire_ready = 1'b1;

  always_comb begin
    imem_rsp_fault = '0;
    for (int i = 0; i < CAPABILITY_OBJECT_CELLS; i++) begin
      dmem_rsp_rdata[i] = '0;
    end
  end

  task automatic drive_program(input addr_t group_addr);
    imem_rsp_cells[0] = '0;
    imem_rsp_cells[1] = '0;

    unique case (MODE)
      0: begin
        unique case (group_addr)
          48'h0000_0000_0000: begin
            imem_rsp_cells[0] = 24'h661000; // CSRRD D1, SR
            imem_rsp_cells[1] = 24'h12211A; // ADD D2, D1, D1
          end
          48'h0000_0000_0002: begin
            imem_rsp_cells[0] = 24'h2521A0; // CMP D2, D1
            imem_rsp_cells[1] = 24'h511008; // BEQ 0x008, not taken
          end
          48'h0000_0000_0004: begin
            imem_rsp_cells[0] = 24'h677200; // CSRWR SCRATCH, D2
            imem_rsp_cells[1] = 24'h663700; // CSRRD D3, SCRATCH
          end
          48'h0000_0000_0006: begin
            imem_rsp_cells[0] = 24'h6B0000; // CSRWR.L DEBUGCTL, D3
            imem_rsp_cells[1] = 24'h0E3000;
          end
          48'h0000_0000_0008: begin
            imem_rsp_cells[0] = 24'h6A0000; // CSRRD.L D4, DEBUGCTL
            imem_rsp_cells[1] = 24'h40E000;
          end
          48'h0000_0000_000A: begin
            imem_rsp_cells[0] = 24'h50000C; // BRA 0x00C
          end
          48'h0000_0000_000C: begin
            imem_rsp_cells[0] = 24'h00005B; // PAUSE
          end
          default: begin
            imem_rsp_cells[0] = 24'h000999;
          end
        endcase
      end

      1: begin
        unique case (group_addr)
          48'h0000_0000_2000: begin
            imem_rsp_cells[0] = 24'h582200; // EPCCRD C2, D2
            imem_rsp_cells[1] = 24'h592200; // EPCCWR C2, D2
          end
          48'h0000_0000_2002: begin
            imem_rsp_cells[0] = 24'h710000; // CCSRWR DSC, C2
            imem_rsp_cells[1] = 24'h012000;
          end
          48'h0000_0000_2004: begin
            imem_rsp_cells[0] = 24'h700000; // CCSRRD C3, DSC
            imem_rsp_cells[1] = 24'h301000;
          end
          48'h0000_0000_2006: begin
            imem_rsp_cells[0] = 24'h00005B; // PAUSE
          end
          default: begin
            imem_rsp_cells[0] = 24'h000999;
          end
        endcase
      end

      default: begin
        if (group_addr == 48'h0000_0000_3000) begin
          imem_rsp_cells[0] = 24'h000055; // BRK
        end else begin
          imem_rsp_cells[0] = 24'h000999;
        end
      end
    endcase
  endtask

  task automatic check_no_unexpected_fault;
    if (retire_packet.fault.valid && MODE != 2) begin
      $fatal(1, "integrated scalar/control unexpected fault");
    end
  endtask

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      imem_rsp_valid <= 1'b0;
      rsp_pending_q <= 1'b0;
      pending_addr_q <= '0;
      csrrd_sr_seen <= 1'b0;
      add_seen <= 1'b0;
      cmp_seen <= 1'b0;
      bcc_not_taken_seen <= 1'b0;
      csrwr_seen <= 1'b0;
      csrrd_scratch_seen <= 1'b0;
      csrwr48_seen <= 1'b0;
      csrrd48_seen <= 1'b0;
      bra_seen <= 1'b0;
      pause_seen <= 1'b0;
      epccrd_seen <= 1'b0;
      epccwr_seen <= 1'b0;
      ccsrwr_seen <= 1'b0;
      ccsrrd_seen <= 1'b0;
      brk_fault_seen <= 1'b0;
      done <= 1'b0;
      for (int i = 0; i < FETCH_GROUP_CELLS; i++) begin
        imem_rsp_cells[i] <= '0;
      end
    end else begin
      imem_rsp_valid <= 1'b0;
      if (imem_req_valid && imem_req_ready) begin
        pending_addr_q <= imem_req_addr;
        rsp_pending_q <= 1'b1;
      end
      if (rsp_pending_q) begin
        drive_program(pending_addr_q);
        imem_rsp_valid <= 1'b1;
        rsp_pending_q <= 1'b0;
      end

      if (retire_valid && !done) begin
        check_no_unexpected_fault();
        unique case (MODE)
          0: begin
            unique case (retire_packet.decoded.opcode_id)
              OPC_CSRRD_24: begin
                if (retire_packet.integer_write_index == 4'd1) begin
                  if (!retire_packet.integer_write_valid ||
                      retire_packet.integer_write_value != SR_RESET_VALUE) begin
                    $fatal(1, "integrated scalar/control CSRRD SR mismatch");
                  end
                  csrrd_sr_seen <= 1'b1;
                end else if (retire_packet.integer_write_index == 4'd3) begin
                  if (!retire_packet.integer_write_valid ||
                      retire_packet.integer_write_value != DOUBLE_SR_VALUE) begin
                    $fatal(1, "integrated scalar/control CSRRD SCRATCH mismatch");
                  end
                  csrrd_scratch_seen <= 1'b1;
                end
              end

              OPC_ADD_24: begin
                if (!retire_packet.integer_write_valid ||
                    retire_packet.integer_write_index != 4'd2 ||
                    retire_packet.integer_write_value != DOUBLE_SR_VALUE) begin
                  $fatal(1, "integrated scalar/control ADD mismatch");
                end
                add_seen <= 1'b1;
              end

              OPC_CMP_24: begin
                if (!retire_packet.csr_write_valid ||
                    retire_packet.csr_write_index != CSR_SR) begin
                  $fatal(1, "integrated scalar/control CMP SR mismatch");
                end
                cmp_seen <= 1'b1;
              end

              OPC_BCC_24: begin
                if (retire_packet.redirect_valid || retire_packet.pcc_update_valid) begin
                  $fatal(1, "integrated scalar/control BCC should not be taken");
                end
                bcc_not_taken_seen <= 1'b1;
              end

              OPC_CSRWR_24: begin
                if (!retire_packet.csr_write_valid ||
                    retire_packet.csr_write_index != CSR_SCRATCH ||
                    retire_packet.csr_write_value != DOUBLE_SR_VALUE) begin
                  $fatal(1, "integrated scalar/control CSRWR SCRATCH mismatch");
                end
                csrwr_seen <= 1'b1;
              end

              OPC_CSRWR_48: begin
                if (!retire_packet.csr_write_valid ||
                    retire_packet.csr_write_index != CSR_DEBUGCTL ||
                    retire_packet.csr_write_value != DOUBLE_SR_VALUE) begin
                  $fatal(1, "integrated scalar/control CSRWR.L DEBUGCTL mismatch");
                end
                csrwr48_seen <= 1'b1;
              end

              OPC_CSRRD_48: begin
                if (!retire_packet.integer_write_valid ||
                    retire_packet.integer_write_index != 4'd4 ||
                    retire_packet.integer_write_value != DOUBLE_SR_VALUE) begin
                  $fatal(1, "integrated scalar/control CSRRD.L DEBUGCTL mismatch");
                end
                csrrd48_seen <= 1'b1;
              end

              OPC_BRA_24: begin
                if (!retire_packet.pcc_update_valid ||
                    !retire_packet.redirect_valid ||
                    retire_packet.pcc_update_value.payload.cursor != 48'h0000_0000_000C) begin
                  $fatal(1, "integrated scalar/control BRA redirect mismatch");
                end
                bra_seen <= 1'b1;
              end

              OPC_PAUSE_12: begin
                if (!retire_packet.normal_valid ||
                    retire_packet.integer_write_valid ||
                    retire_packet.csr_write_valid ||
                    retire_packet.ccsr_write_valid) begin
                  $fatal(1, "integrated scalar/control PAUSE no-effect mismatch");
                end
                pause_seen <= 1'b1;
                done <= 1'b1;
              end

              default: begin
              end
            endcase
          end

          1: begin
            unique case (retire_packet.decoded.opcode_id)
              OPC_EPCCRD_24: begin
                if (!retire_packet.capability_write_valid ||
                    retire_packet.capability_write_index != 3'd2 ||
                    retire_packet.capability_write_value.payload.cursor != RESET_VECTOR ||
                    !retire_packet.integer_write_valid ||
                    retire_packet.integer_write_index != 4'd2 ||
                    retire_packet.integer_write_value != 48'd0) begin
                  $fatal(1, "integrated scalar/control EPCCRD mismatch");
                end
                epccrd_seen <= 1'b1;
              end

              OPC_EPCCWR_24: begin
                if (!retire_packet.epcc_update_valid ||
                    retire_packet.epcc_update_value.payload.cursor != RESET_VECTOR ||
                    retire_packet.epcc_update_slot != SLOT_0) begin
                  $fatal(1, "integrated scalar/control EPCCWR mismatch");
                end
                epccwr_seen <= 1'b1;
              end

              OPC_CCSRWR_48: begin
                if (!retire_packet.ccsr_write_valid ||
                    retire_packet.ccsr_write_index != CCSR_DSC ||
                    retire_packet.ccsr_write_value.payload.cursor != RESET_VECTOR) begin
                  $fatal(1, "integrated scalar/control CCSRWR mismatch");
                end
                ccsrwr_seen <= 1'b1;
              end

              OPC_CCSRRD_48: begin
                if (!retire_packet.capability_write_valid ||
                    retire_packet.capability_write_index != 3'd3 ||
                    retire_packet.capability_write_value.payload.cursor != RESET_VECTOR) begin
                  $fatal(1, "integrated scalar/control CCSRRD mismatch");
                end
                ccsrrd_seen <= 1'b1;
              end

              OPC_PAUSE_12: begin
                pause_seen <= 1'b1;
                done <= 1'b1;
              end

              default: begin
              end
            endcase
          end

          default: begin
            if (retire_packet.decoded.opcode_id == OPC_BRK_12) begin
              if (retire_packet.normal_valid ||
                  !retire_packet.fault.valid ||
                  retire_packet.fault.cause != EXC_BREAKPOINT ||
                  retire_packet.integer_write_valid ||
                  retire_packet.csr_write_valid ||
                  retire_packet.ccsr_write_valid) begin
                $fatal(1, "integrated scalar/control BRK fault mismatch");
              end
              brk_fault_seen <= 1'b1;
              done <= 1'b1;
            end
          end
        endcase
      end
    end
  end

  // verilator lint_off UNUSEDSIGNAL
  wire logic unused_dmem_tag_outputs = &{
    dmem_req_valid,
    dmem_req_write,
    dmem_req_addr[0],
    dmem_req_len_cells[0],
    dmem_req_wdata[0][0],
    tagmem_req_valid,
    tagmem_req_write,
    tagmem_req_slot_addr[0],
    tagmem_req_wtag,
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

module cpu_v01_core_scalar_control_tb;
  logic clk;
  logic rst_n;

  logic scalar_csrrd_sr_seen;
  logic scalar_add_seen;
  logic scalar_cmp_seen;
  logic scalar_bcc_not_taken_seen;
  logic scalar_csrwr_seen;
  logic scalar_csrrd_scratch_seen;
  logic scalar_csrwr48_seen;
  logic scalar_csrrd48_seen;
  logic scalar_bra_seen;
  logic scalar_pause_seen;
  logic scalar_epccrd_seen;
  logic scalar_epccwr_seen;
  logic scalar_ccsrwr_seen;
  logic scalar_ccsrrd_seen;
  logic scalar_brk_fault_seen;
  logic scalar_done;

  logic cap_csrrd_sr_seen;
  logic cap_add_seen;
  logic cap_cmp_seen;
  logic cap_bcc_not_taken_seen;
  logic cap_csrwr_seen;
  logic cap_csrrd_scratch_seen;
  logic cap_csrwr48_seen;
  logic cap_csrrd48_seen;
  logic cap_bra_seen;
  logic cap_pause_seen;
  logic cap_epccrd_seen;
  logic cap_epccwr_seen;
  logic cap_ccsrwr_seen;
  logic cap_ccsrrd_seen;
  logic cap_brk_fault_seen;
  logic cap_done;

  logic brk_csrrd_sr_seen;
  logic brk_add_seen;
  logic brk_cmp_seen;
  logic brk_bcc_not_taken_seen;
  logic brk_csrwr_seen;
  logic brk_csrrd_scratch_seen;
  logic brk_csrwr48_seen;
  logic brk_csrrd48_seen;
  logic brk_bra_seen;
  logic brk_pause_seen;
  logic brk_epccrd_seen;
  logic brk_epccwr_seen;
  logic brk_ccsrwr_seen;
  logic brk_ccsrrd_seen;
  logic brk_brk_fault_seen;
  logic brk_done;

  cpu_v01_core_scalar_control_fixture #(
    .MODE(0),
    .RESET_VECTOR(48'h0000_0000_0000)
  ) scalar_fixture (
    .clk(clk),
    .rst_n(rst_n),
    .csrrd_sr_seen(scalar_csrrd_sr_seen),
    .add_seen(scalar_add_seen),
    .cmp_seen(scalar_cmp_seen),
    .bcc_not_taken_seen(scalar_bcc_not_taken_seen),
    .csrwr_seen(scalar_csrwr_seen),
    .csrrd_scratch_seen(scalar_csrrd_scratch_seen),
    .csrwr48_seen(scalar_csrwr48_seen),
    .csrrd48_seen(scalar_csrrd48_seen),
    .bra_seen(scalar_bra_seen),
    .pause_seen(scalar_pause_seen),
    .epccrd_seen(scalar_epccrd_seen),
    .epccwr_seen(scalar_epccwr_seen),
    .ccsrwr_seen(scalar_ccsrwr_seen),
    .ccsrrd_seen(scalar_ccsrrd_seen),
    .brk_fault_seen(scalar_brk_fault_seen),
    .done(scalar_done)
  );

  cpu_v01_core_scalar_control_fixture #(
    .MODE(1),
    .RESET_VECTOR(48'h0000_0000_2000)
  ) cap_fixture (
    .clk(clk),
    .rst_n(rst_n),
    .csrrd_sr_seen(cap_csrrd_sr_seen),
    .add_seen(cap_add_seen),
    .cmp_seen(cap_cmp_seen),
    .bcc_not_taken_seen(cap_bcc_not_taken_seen),
    .csrwr_seen(cap_csrwr_seen),
    .csrrd_scratch_seen(cap_csrrd_scratch_seen),
    .csrwr48_seen(cap_csrwr48_seen),
    .csrrd48_seen(cap_csrrd48_seen),
    .bra_seen(cap_bra_seen),
    .pause_seen(cap_pause_seen),
    .epccrd_seen(cap_epccrd_seen),
    .epccwr_seen(cap_epccwr_seen),
    .ccsrwr_seen(cap_ccsrwr_seen),
    .ccsrrd_seen(cap_ccsrrd_seen),
    .brk_fault_seen(cap_brk_fault_seen),
    .done(cap_done)
  );

  cpu_v01_core_scalar_control_fixture #(
    .MODE(2),
    .RESET_VECTOR(48'h0000_0000_3000)
  ) brk_fixture (
    .clk(clk),
    .rst_n(rst_n),
    .csrrd_sr_seen(brk_csrrd_sr_seen),
    .add_seen(brk_add_seen),
    .cmp_seen(brk_cmp_seen),
    .bcc_not_taken_seen(brk_bcc_not_taken_seen),
    .csrwr_seen(brk_csrwr_seen),
    .csrrd_scratch_seen(brk_csrrd_scratch_seen),
    .csrwr48_seen(brk_csrwr48_seen),
    .csrrd48_seen(brk_csrrd48_seen),
    .bra_seen(brk_bra_seen),
    .pause_seen(brk_pause_seen),
    .epccrd_seen(brk_epccrd_seen),
    .epccwr_seen(brk_epccwr_seen),
    .ccsrwr_seen(brk_ccsrwr_seen),
    .ccsrrd_seen(brk_ccsrrd_seen),
    .brk_fault_seen(brk_brk_fault_seen),
    .done(brk_done)
  );

  initial begin
    clk = 1'b0;
    forever #5 clk = ~clk;
  end

  initial begin
    rst_n = 1'b0;
    repeat (2) @(posedge clk);
    rst_n = 1'b1;
    wait (scalar_done && cap_done && brk_done);

    if (!scalar_csrrd_sr_seen ||
        !scalar_add_seen ||
        !scalar_cmp_seen ||
        !scalar_bcc_not_taken_seen ||
        !scalar_csrwr_seen ||
        !scalar_csrrd_scratch_seen ||
        !scalar_csrwr48_seen ||
        !scalar_csrrd48_seen ||
        !scalar_bra_seen ||
        !scalar_pause_seen) begin
      $fatal(1, "integrated scalar/control golden scalar CSR branch sequence mismatch");
    end

    if (!cap_epccrd_seen ||
        !cap_epccwr_seen ||
        !cap_ccsrwr_seen ||
        !cap_ccsrrd_seen ||
        !cap_pause_seen) begin
      $fatal(1, "integrated scalar/control EPCC CCSR sequence mismatch");
    end

    if (!brk_brk_fault_seen) begin
      $fatal(1, "integrated scalar/control BRK no-effect fault mismatch");
    end

    $finish;
  end

  // verilator lint_off UNUSEDSIGNAL
  wire logic unused_scalar_outputs = &{
    scalar_epccrd_seen,
    scalar_epccwr_seen,
    scalar_ccsrwr_seen,
    scalar_ccsrrd_seen,
    scalar_brk_fault_seen,
    cap_csrrd_sr_seen,
    cap_add_seen,
    cap_cmp_seen,
    cap_bcc_not_taken_seen,
    cap_csrwr_seen,
    cap_csrrd_scratch_seen,
    cap_csrwr48_seen,
    cap_csrrd48_seen,
    cap_bra_seen,
    cap_brk_fault_seen,
    brk_csrrd_sr_seen,
    brk_add_seen,
    brk_cmp_seen,
    brk_bcc_not_taken_seen,
    brk_csrwr_seen,
    brk_csrrd_scratch_seen,
    brk_csrwr48_seen,
    brk_csrrd48_seen,
    brk_bra_seen,
    brk_pause_seen,
    brk_epccrd_seen,
    brk_epccwr_seen,
    brk_ccsrwr_seen,
    brk_ccsrrd_seen
  };
  // verilator lint_on UNUSEDSIGNAL
endmodule
