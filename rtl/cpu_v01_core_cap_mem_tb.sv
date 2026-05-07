module cpu_v01_core_cap_mem_fixture #(
  parameter int MODE = 0,
  parameter cpu_v01_pkg::addr_t RESET_VECTOR = 48'h0000_0000_2000
) (
  input  logic clk,
  input  logic rst_n,
  output logic ccsrrd_seen,
  output logic csrrd_seen,
  output logic setcc_seen,
  output logic cmove_seen,
  output logic cgetaddr_seen,
  output logic csetaddr_seen,
  output logic candperm_seen,
  output logic csc_seen,
  output logic clc_seen,
  output logic st48_seen,
  output logic ld48_seen,
  output logic pause_seen,
  output logic invalid_tag_fault_seen,
  output logic memory_tag_value,
  output logic done
);
  import cpu_v01_pkg::*;

  localparam int_reg_t SR_RESET_VALUE = 48'h0000_0000_00C0;
  localparam logic [7:0] DATA_PERMISSIONS = 8'd31;

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
  cell_t dmem_rsp_cells_q [CAPABILITY_OBJECT_CELLS];
  logic tagmem_rsp_pending_q;
  logic tagmem_rsp_tag_q;
  cell_t memory_cells_q [CAPABILITY_OBJECT_CELLS];
  logic memory_tag_q;

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
  assign retire_ready = 1'b1;
  assign memory_tag_value = memory_tag_q;

  always_comb begin
    imem_rsp_fault = '0;
    dmem_rsp_fault = '0;
  end

  task automatic drive_program(input addr_t group_addr);
    imem_rsp_cells[0] = '0;
    imem_rsp_cells[1] = '0;

    if (MODE == 0) begin
      unique case (group_addr)
        48'h0000_0000_2000: begin
          imem_rsp_cells[0] = 24'h700000; // CCSRRD C1, PCC
          imem_rsp_cells[1] = 24'h100000;
        end
        48'h0000_0000_2002: begin
          imem_rsp_cells[0] = 24'h667000; // CSRRD D7, SR
          imem_rsp_cells[1] = 24'h281000; // SETAL D1
        end
        48'h0000_0000_2004: begin
          imem_rsp_cells[0] = 24'h400000; // CMOVE C2, C1
          imem_rsp_cells[1] = 24'h210000;
        end
        48'h0000_0000_2006: begin
          imem_rsp_cells[0] = 24'h410000; // CGETADDR D3, C2
          imem_rsp_cells[1] = 24'h320000;
        end
        48'h0000_0000_2008: begin
          imem_rsp_cells[0] = 24'h420000; // CSETADDR C4, C1, D3
          imem_rsp_cells[1] = 24'h413000;
        end
        48'h0000_0000_200A: begin
          imem_rsp_cells[0] = 24'h450000; // CANDPERM C5, C4, D1
          imem_rsp_cells[1] = 24'h541000;
        end
        48'h0000_0000_200C: begin
          imem_rsp_cells[0] = 24'h331020; // CSC C1, D0, C2
          imem_rsp_cells[1] = 24'h326100; // CLC C6, C1, D0
        end
        48'h0000_0000_200E: begin
          imem_rsp_cells[0] = 24'h311070; // ST48 C1, D0, D7
          imem_rsp_cells[1] = 24'h308100; // LD48 D8, C1, D0
        end
        48'h0000_0000_2010: begin
          imem_rsp_cells[0] = 24'h00005B; // PAUSE
        end
        default: begin
          imem_rsp_cells[0] = 24'h000999;
        end
      endcase
    end else if (group_addr == 48'h0000_0000_3000) begin
      imem_rsp_cells[0] = 24'h420000; // CSETADDR C2, C1, D0 with invalid C1
      imem_rsp_cells[1] = 24'h210000;
    end else begin
      imem_rsp_cells[0] = 24'h000999;
    end
  endtask

  task automatic check_no_unexpected_fault;
    if (retire_packet.fault.valid && MODE == 0) begin
      $fatal(1, "integrated cap/mem unexpected fault");
    end
  endtask

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      imem_rsp_valid <= 1'b0;
      imem_rsp_pending_q <= 1'b0;
      imem_pending_addr_q <= '0;
      dmem_rsp_valid <= 1'b0;
      dmem_rsp_pending_q <= 1'b0;
      tagmem_rsp_valid <= 1'b0;
      tagmem_rsp_pending_q <= 1'b0;
      tagmem_rsp_tag_q <= 1'b0;
      tagmem_rsp_rtag <= 1'b0;
      memory_tag_q <= 1'b0;
      ccsrrd_seen <= 1'b0;
      csrrd_seen <= 1'b0;
      setcc_seen <= 1'b0;
      cmove_seen <= 1'b0;
      cgetaddr_seen <= 1'b0;
      csetaddr_seen <= 1'b0;
      candperm_seen <= 1'b0;
      csc_seen <= 1'b0;
      clc_seen <= 1'b0;
      st48_seen <= 1'b0;
      ld48_seen <= 1'b0;
      pause_seen <= 1'b0;
      invalid_tag_fault_seen <= 1'b0;
      done <= 1'b0;
      for (int i = 0; i < FETCH_GROUP_CELLS; i++) begin
        imem_rsp_cells[i] <= '0;
      end
      for (int i = 0; i < CAPABILITY_OBJECT_CELLS; i++) begin
        dmem_rsp_rdata[i] <= '0;
        dmem_rsp_cells_q[i] <= '0;
        memory_cells_q[i] <= '0;
      end
    end else begin
      imem_rsp_valid <= 1'b0;
      dmem_rsp_valid <= 1'b0;
      tagmem_rsp_valid <= 1'b0;

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
        if (dmem_req_addr != RESET_VECTOR) begin
          $fatal(1, "integrated cap/mem unexpected data address");
        end
        if (dmem_req_write) begin
          memory_cells_q[0] <= dmem_req_wdata[0];
          memory_cells_q[1] <= dmem_req_wdata[1];
          if (dmem_req_len_cells == 3'd4) begin
            memory_cells_q[2] <= dmem_req_wdata[2];
            memory_cells_q[3] <= dmem_req_wdata[3];
          end
        end else begin
          for (int i = 0; i < CAPABILITY_OBJECT_CELLS; i++) begin
            dmem_rsp_cells_q[i] <= memory_cells_q[i];
          end
          dmem_rsp_pending_q <= 1'b1;
        end
      end
      if (dmem_rsp_pending_q) begin
        for (int i = 0; i < CAPABILITY_OBJECT_CELLS; i++) begin
          dmem_rsp_rdata[i] <= dmem_rsp_cells_q[i];
        end
        dmem_rsp_valid <= 1'b1;
        dmem_rsp_pending_q <= 1'b0;
      end

      if (tagmem_req_valid && tagmem_req_ready) begin
        if (tagmem_req_slot_addr != RESET_VECTOR) begin
          $fatal(1, "integrated cap/mem unexpected tag address");
        end
        if (tagmem_req_write) begin
          memory_tag_q <= tagmem_req_wtag;
        end else begin
          tagmem_rsp_tag_q <= memory_tag_q;
          tagmem_rsp_pending_q <= 1'b1;
        end
      end
      if (tagmem_rsp_pending_q) begin
        tagmem_rsp_rtag <= tagmem_rsp_tag_q;
        tagmem_rsp_valid <= 1'b1;
        tagmem_rsp_pending_q <= 1'b0;
      end

      if (retire_valid && !done) begin
        check_no_unexpected_fault();
        if (MODE == 0) begin
          unique case (retire_packet.decoded.opcode_id)
            OPC_CCSRRD_48: begin
              if (!retire_packet.capability_write_valid ||
                  retire_packet.capability_write_index != 3'd1 ||
                  !retire_packet.capability_write_value.tag ||
                  retire_packet.capability_write_value.payload.cursor != RESET_VECTOR) begin
                $fatal(1, "integrated cap/mem CCSR read PCC mismatch");
              end
              ccsrrd_seen <= 1'b1;
            end

            OPC_CSRRD_24: begin
              if (!retire_packet.integer_write_valid ||
                  retire_packet.integer_write_index != 4'd7 ||
                  retire_packet.integer_write_value != SR_RESET_VALUE) begin
                $fatal(1, "integrated cap/mem CSRRD SR mismatch");
              end
              csrrd_seen <= 1'b1;
            end

            OPC_SETCC_24: begin
              if (!retire_packet.integer_write_valid ||
                  retire_packet.integer_write_index != 4'd1 ||
                  retire_packet.integer_write_value != 48'd1) begin
                $fatal(1, "integrated cap/mem SETAL mismatch");
              end
              setcc_seen <= 1'b1;
            end

            OPC_CMOVE_48: begin
              if (!retire_packet.capability_write_valid ||
                  retire_packet.capability_write_index != 3'd2 ||
                  retire_packet.capability_write_value.payload.cursor != RESET_VECTOR) begin
                $fatal(1, "integrated cap/mem CMOVE mismatch");
              end
              cmove_seen <= 1'b1;
            end

            OPC_CGETADDR_48: begin
              if (!retire_packet.integer_write_valid ||
                  retire_packet.integer_write_index != 4'd3 ||
                  retire_packet.integer_write_value != RESET_VECTOR) begin
                $fatal(1, "integrated cap/mem CGETADDR mismatch");
              end
              cgetaddr_seen <= 1'b1;
            end

            OPC_CSETADDR_48: begin
              if (!retire_packet.capability_write_valid ||
                  retire_packet.capability_write_index != 3'd4 ||
                  retire_packet.capability_write_value.payload.cursor != RESET_VECTOR) begin
                $fatal(1, "integrated cap/mem CSETADDR mismatch");
              end
              csetaddr_seen <= 1'b1;
            end

            OPC_CANDPERM_48: begin
              if (!retire_packet.capability_write_valid ||
                  retire_packet.capability_write_index != 3'd5 ||
                  retire_packet.capability_write_value.payload.permissions != 8'h01) begin
                $fatal(1, "integrated cap/mem CANDPERM mismatch");
              end
              candperm_seen <= 1'b1;
            end

            OPC_CSC_24: begin
              if (retire_packet.memory_effect_kind != MEM_EFFECT_CSC ||
                  retire_packet.memory_effect_address != RESET_VECTOR ||
                  !retire_packet.tag_write_valid ||
                  !retire_packet.tag_write_value ||
                  retire_packet.memory_capability_value.payload.cursor != RESET_VECTOR) begin
                $fatal(1, "integrated cap/mem CSC mismatch");
              end
              csc_seen <= 1'b1;
            end

            OPC_CLC_24: begin
              if (!retire_packet.capability_write_valid ||
                  retire_packet.capability_write_index != 3'd6 ||
                  !retire_packet.capability_write_value.tag ||
                  retire_packet.capability_write_value.payload.cursor != RESET_VECTOR) begin
                $fatal(1, "integrated cap/mem CLC mismatch");
              end
              clc_seen <= 1'b1;
            end

            OPC_ST48_24: begin
              if (retire_packet.memory_effect_kind != MEM_EFFECT_ST48 ||
                  retire_packet.memory_effect_address != RESET_VECTOR ||
                  retire_packet.memory_integer_value != SR_RESET_VALUE ||
                  !retire_packet.tag_write_valid ||
                  retire_packet.tag_write_value) begin
                $fatal(1, "integrated cap/mem ST48 mismatch");
              end
              st48_seen <= 1'b1;
            end

            OPC_LD48_24: begin
              if (!retire_packet.integer_write_valid ||
                  retire_packet.integer_write_index != 4'd8 ||
                  retire_packet.integer_write_value != SR_RESET_VALUE) begin
                $fatal(1, "integrated cap/mem LD48 mismatch");
              end
              ld48_seen <= 1'b1;
            end

            OPC_PAUSE_12: begin
              pause_seen <= 1'b1;
              done <= 1'b1;
            end

            default: begin
            end
          endcase
        end else if (retire_packet.decoded.opcode_id == OPC_CSETADDR_48) begin
          if (retire_packet.normal_valid ||
              !retire_packet.fault.valid ||
              retire_packet.fault.cause != EXC_CAPABILITY_TAG_FAULT ||
              retire_packet.fault.capcause != CAPCAUSE_TAG ||
              retire_packet.fault.fault_cap_idx != FAULT_CAP_IDX_C1 ||
              retire_packet.capability_write_valid) begin
            $fatal(1, "integrated cap/mem invalid-tag fault mismatch");
          end
          invalid_tag_fault_seen <= 1'b1;
          done <= 1'b1;
        end
      end
    end
  end

  // verilator lint_off UNUSEDSIGNAL
  wire logic unused_outputs = &{
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

module cpu_v01_core_cap_mem_tb;
  logic clk;
  logic rst_n;

  logic normal_ccsrrd_seen;
  logic normal_csrrd_seen;
  logic normal_setcc_seen;
  logic normal_cmove_seen;
  logic normal_cgetaddr_seen;
  logic normal_csetaddr_seen;
  logic normal_candperm_seen;
  logic normal_csc_seen;
  logic normal_clc_seen;
  logic normal_st48_seen;
  logic normal_ld48_seen;
  logic normal_pause_seen;
  logic normal_invalid_tag_fault_seen;
  logic normal_memory_tag_value;
  logic normal_done;

  logic fault_ccsrrd_seen;
  logic fault_csrrd_seen;
  logic fault_setcc_seen;
  logic fault_cmove_seen;
  logic fault_cgetaddr_seen;
  logic fault_csetaddr_seen;
  logic fault_candperm_seen;
  logic fault_csc_seen;
  logic fault_clc_seen;
  logic fault_st48_seen;
  logic fault_ld48_seen;
  logic fault_pause_seen;
  logic fault_invalid_tag_fault_seen;
  logic fault_memory_tag_value;
  logic fault_done;

  cpu_v01_core_cap_mem_fixture #(
    .MODE(0),
    .RESET_VECTOR(48'h0000_0000_2000)
  ) normal_fixture (
    .clk(clk),
    .rst_n(rst_n),
    .ccsrrd_seen(normal_ccsrrd_seen),
    .csrrd_seen(normal_csrrd_seen),
    .setcc_seen(normal_setcc_seen),
    .cmove_seen(normal_cmove_seen),
    .cgetaddr_seen(normal_cgetaddr_seen),
    .csetaddr_seen(normal_csetaddr_seen),
    .candperm_seen(normal_candperm_seen),
    .csc_seen(normal_csc_seen),
    .clc_seen(normal_clc_seen),
    .st48_seen(normal_st48_seen),
    .ld48_seen(normal_ld48_seen),
    .pause_seen(normal_pause_seen),
    .invalid_tag_fault_seen(normal_invalid_tag_fault_seen),
    .memory_tag_value(normal_memory_tag_value),
    .done(normal_done)
  );

  cpu_v01_core_cap_mem_fixture #(
    .MODE(1),
    .RESET_VECTOR(48'h0000_0000_3000)
  ) fault_fixture (
    .clk(clk),
    .rst_n(rst_n),
    .ccsrrd_seen(fault_ccsrrd_seen),
    .csrrd_seen(fault_csrrd_seen),
    .setcc_seen(fault_setcc_seen),
    .cmove_seen(fault_cmove_seen),
    .cgetaddr_seen(fault_cgetaddr_seen),
    .csetaddr_seen(fault_csetaddr_seen),
    .candperm_seen(fault_candperm_seen),
    .csc_seen(fault_csc_seen),
    .clc_seen(fault_clc_seen),
    .st48_seen(fault_st48_seen),
    .ld48_seen(fault_ld48_seen),
    .pause_seen(fault_pause_seen),
    .invalid_tag_fault_seen(fault_invalid_tag_fault_seen),
    .memory_tag_value(fault_memory_tag_value),
    .done(fault_done)
  );

  initial begin
    clk = 1'b0;
    forever #5 clk = ~clk;
  end

  initial begin
    rst_n = 1'b0;
    repeat (2) @(posedge clk);
    rst_n = 1'b1;
    wait (normal_done && fault_done);

    if (!normal_ccsrrd_seen ||
        !normal_csrrd_seen ||
        !normal_setcc_seen ||
        !normal_cmove_seen ||
        !normal_cgetaddr_seen ||
        !normal_csetaddr_seen ||
        !normal_candperm_seen ||
        !normal_csc_seen ||
        !normal_clc_seen ||
        !normal_st48_seen ||
        !normal_ld48_seen ||
        !normal_pause_seen ||
        normal_memory_tag_value) begin
      $fatal(1, "integrated cap/mem normal sequence mismatch");
    end

    if (!fault_invalid_tag_fault_seen) begin
      $fatal(1, "integrated cap/mem invalid-tag sequence mismatch");
    end

    $finish;
  end

  // verilator lint_off UNUSEDSIGNAL
  wire logic unused_fault_outputs = &{
    normal_invalid_tag_fault_seen,
    fault_ccsrrd_seen,
    fault_csrrd_seen,
    fault_setcc_seen,
    fault_cmove_seen,
    fault_cgetaddr_seen,
    fault_csetaddr_seen,
    fault_candperm_seen,
    fault_csc_seen,
    fault_clc_seen,
    fault_st48_seen,
    fault_ld48_seen,
    fault_pause_seen,
    fault_memory_tag_value
  };
  // verilator lint_on UNUSEDSIGNAL
endmodule
