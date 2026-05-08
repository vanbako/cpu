module cpu_v01_core_control_trap_fixture #(
  parameter int MODE = 0,
  parameter cpu_v01_pkg::addr_t RESET_VECTOR = 48'h0000_0000_5000
) (
  input  logic clk,
  input  logic rst_n,
  output logic call_seen,
  output logic callc_seen,
  output logic ret_seen,
  output logic sys_seen,
  output logic iret_seen,
  output logic fault_seen,
  output logic pause_seen,
  output logic done
);
  import cpu_v01_pkg::*;

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
  assign tagmem_req_ready = 1'b1;
  assign tagmem_rsp_valid = 1'b0;
  assign tagmem_rsp_rtag = 1'b0;
  assign retire_ready = 1'b1;

  always_comb begin
    imem_rsp_fault = '0;
    dmem_rsp_fault = '0;
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
          48'h0000_0000_5000: begin
            imem_rsp_cells[0] = 24'h525002; // CALL 0x5002
            imem_rsp_cells[1] = 24'h505004; // BRA 0x5004
          end
          48'h0000_0000_5002: begin
            imem_rsp_cells[0] = 24'h000053; // RET
          end
          48'h0000_0000_5004: begin
            imem_rsp_cells[0] = 24'h00005B; // PAUSE
          end
          default: imem_rsp_cells[0] = 24'h000999;
        endcase
      end

      1: begin
        unique case (group_addr)
          48'h0000_0000_6000: begin
            imem_rsp_cells[0] = 24'h700000; // CCSRRD C1, TVC
            imem_rsp_cells[1] = 24'h105000;
          end
          48'h0000_0000_6002: begin
            imem_rsp_cells[0] = 24'h5C1000; // CALLC C1
            imem_rsp_cells[1] = 24'h506004; // BRA 0x6004
          end
          48'h0000_0000_6004: begin
            imem_rsp_cells[0] = 24'h00005B; // PAUSE
          end
          48'h0000_0000_6100: begin
            imem_rsp_cells[0] = 24'h000053; // RET
          end
          default: imem_rsp_cells[0] = 24'h000999;
        endcase
      end

      2: begin
        unique case (group_addr)
          48'h0000_0000_7000: begin
            imem_rsp_cells[0] = 24'h05B056; // SYS; PAUSE
          end
          48'h0000_0000_7100: begin
            imem_rsp_cells[0] = 24'h570000; // IRET
          end
          default: imem_rsp_cells[0] = 24'h000999;
        endcase
      end

      3: begin
        if (group_addr == 48'h0000_0000_8000) begin
          imem_rsp_cells[0] = 24'h5C0000; // CALLC C0 invalid tag
        end else begin
          imem_rsp_cells[0] = 24'h000999;
        end
      end

      default: begin
        if (group_addr == 48'h0000_0000_9000) begin
          imem_rsp_cells[0] = 24'h000053; // RET with empty protected return stack
        end else begin
          imem_rsp_cells[0] = 24'h000999;
        end
      end
    endcase
  endtask

  task automatic check_no_unexpected_fault;
    if (retire_packet.fault.valid && MODE != 2 && MODE < 3) begin
      $fatal(1, "integrated control/trap unexpected fault");
    end
  endtask

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      imem_rsp_valid <= 1'b0;
      rsp_pending_q <= 1'b0;
      pending_addr_q <= '0;
      call_seen <= 1'b0;
      callc_seen <= 1'b0;
      ret_seen <= 1'b0;
      sys_seen <= 1'b0;
      iret_seen <= 1'b0;
      fault_seen <= 1'b0;
      pause_seen <= 1'b0;
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
            if (retire_packet.decoded.opcode_id == OPC_CALL_24) begin
              if (!retire_packet.pcc_update_valid ||
                  retire_packet.pcc_update_value.payload.cursor != 48'h0000_0000_5002 ||
                  retire_packet.memory_effect_kind != MEM_EFFECT_RETURN_STACK_PUSH ||
                  !retire_packet.tag_write_valid) begin
                $fatal(1, "integrated control/trap CALL mismatch");
              end
              call_seen <= 1'b1;
            end else if (retire_packet.decoded.opcode_id == OPC_RET_12) begin
              if (!retire_packet.pcc_update_valid ||
                  retire_packet.pcc_update_value.payload.cursor != 48'h0000_0000_5001 ||
                  retire_packet.pcc_update_slot != SLOT_0) begin
                $fatal(1, "integrated control/trap RET mismatch");
              end
              ret_seen <= 1'b1;
            end else if (retire_packet.decoded.opcode_id == OPC_PAUSE_12) begin
              pause_seen <= 1'b1;
              done <= 1'b1;
            end
          end

          1: begin
            if (retire_packet.decoded.opcode_id == OPC_CALLC_24) begin
              if (!retire_packet.pcc_update_valid ||
                  retire_packet.pcc_update_value.payload.cursor != 48'h0000_0000_6100 ||
                  retire_packet.memory_effect_kind != MEM_EFFECT_RETURN_STACK_PUSH) begin
                $fatal(1, "integrated control/trap CALLC mismatch");
              end
              callc_seen <= 1'b1;
            end else if (retire_packet.decoded.opcode_id == OPC_RET_12) begin
              if (!retire_packet.pcc_update_valid ||
                  retire_packet.pcc_update_value.payload.cursor != 48'h0000_0000_6003) begin
                $fatal(1, "integrated control/trap CALLC RET mismatch");
              end
              ret_seen <= 1'b1;
            end else if (retire_packet.decoded.opcode_id == OPC_PAUSE_12) begin
              pause_seen <= 1'b1;
              done <= 1'b1;
            end
          end

          2: begin
            if (retire_packet.decoded.opcode_id == OPC_SYS_12) begin
              if (!retire_packet.fault.valid ||
                  retire_packet.fault.cause != EXC_SYSCALL_TRAP ||
                  !retire_packet.trap_entry_valid ||
                  !retire_packet.epcc_update_valid ||
                  retire_packet.epcc_update_slot != SLOT_1 ||
                  !retire_packet.pcc_update_valid ||
                  retire_packet.pcc_update_value.payload.cursor != 48'h0000_0000_7100) begin
                $fatal(1, "integrated control/trap SYS mismatch");
              end
              sys_seen <= 1'b1;
            end else if (retire_packet.decoded.opcode_id == OPC_IRET_24) begin
              if (!retire_packet.trap_frame_restore_valid ||
                  !retire_packet.pcc_update_valid ||
                  retire_packet.pcc_update_value.payload.cursor != 48'h0000_0000_7000 ||
                  retire_packet.pcc_update_slot != SLOT_1) begin
                $fatal(1, "integrated control/trap IRET mismatch");
              end
              iret_seen <= 1'b1;
            end else if (retire_packet.decoded.opcode_id == OPC_PAUSE_12) begin
              pause_seen <= 1'b1;
              done <= 1'b1;
            end
          end

          3: begin
            if (retire_packet.decoded.opcode_id == OPC_CALLC_24) begin
              if (retire_packet.normal_valid ||
                  !retire_packet.fault.valid ||
                  retire_packet.fault.cause != EXC_CAPABILITY_TAG_FAULT ||
                  retire_packet.fault.capcause != CAPCAUSE_TAG ||
                  retire_packet.fault.fault_cap_idx != FAULT_CAP_IDX_C0) begin
                $fatal(1, "integrated control/trap CALLC tag fault mismatch");
              end
              fault_seen <= 1'b1;
              done <= 1'b1;
            end
          end

          default: begin
            if (retire_packet.decoded.opcode_id == OPC_RET_12) begin
              if (retire_packet.normal_valid ||
                  !retire_packet.fault.valid ||
                  retire_packet.fault.cause != EXC_RETURN_STACK_UNDERFLOW ||
                  retire_packet.fault.capcause != CAPCAUSE_TAG ||
                  retire_packet.fault.fault_cap_idx != FAULT_CAP_IDX_RSC) begin
                $fatal(1, "integrated control/trap RET underflow mismatch");
              end
              fault_seen <= 1'b1;
              done <= 1'b1;
            end
          end
        endcase
      end
    end
  end

  // verilator lint_off UNUSEDSIGNAL
  wire logic unused_ports = &{
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

module cpu_v01_core_control_trap_tb;
  logic clk;
  logic rst_n;

  logic direct_call_seen;
  logic direct_callc_seen;
  logic direct_ret_seen;
  logic direct_sys_seen;
  logic direct_iret_seen;
  logic direct_fault_seen;
  logic direct_pause_seen;
  logic direct_done;

  logic callc_call_seen;
  logic callc_callc_seen;
  logic callc_ret_seen;
  logic callc_sys_seen;
  logic callc_iret_seen;
  logic callc_fault_seen;
  logic callc_pause_seen;
  logic callc_done;

  logic sys_call_seen;
  logic sys_callc_seen;
  logic sys_ret_seen;
  logic sys_sys_seen;
  logic sys_iret_seen;
  logic sys_fault_seen;
  logic sys_pause_seen;
  logic sys_done;

  logic callc_fault_call_seen;
  logic callc_fault_callc_seen;
  logic callc_fault_ret_seen;
  logic callc_fault_sys_seen;
  logic callc_fault_iret_seen;
  logic callc_fault_fault_seen;
  logic callc_fault_pause_seen;
  logic callc_fault_done;

  logic ret_fault_call_seen;
  logic ret_fault_callc_seen;
  logic ret_fault_ret_seen;
  logic ret_fault_sys_seen;
  logic ret_fault_iret_seen;
  logic ret_fault_fault_seen;
  logic ret_fault_pause_seen;
  logic ret_fault_done;

  cpu_v01_core_control_trap_fixture #(
    .MODE(0),
    .RESET_VECTOR(48'h0000_0000_5000)
  ) direct_fixture (
    .clk(clk),
    .rst_n(rst_n),
    .call_seen(direct_call_seen),
    .callc_seen(direct_callc_seen),
    .ret_seen(direct_ret_seen),
    .sys_seen(direct_sys_seen),
    .iret_seen(direct_iret_seen),
    .fault_seen(direct_fault_seen),
    .pause_seen(direct_pause_seen),
    .done(direct_done)
  );

  cpu_v01_core_control_trap_fixture #(
    .MODE(1),
    .RESET_VECTOR(48'h0000_0000_6000)
  ) callc_fixture (
    .clk(clk),
    .rst_n(rst_n),
    .call_seen(callc_call_seen),
    .callc_seen(callc_callc_seen),
    .ret_seen(callc_ret_seen),
    .sys_seen(callc_sys_seen),
    .iret_seen(callc_iret_seen),
    .fault_seen(callc_fault_seen),
    .pause_seen(callc_pause_seen),
    .done(callc_done)
  );

  cpu_v01_core_control_trap_fixture #(
    .MODE(2),
    .RESET_VECTOR(48'h0000_0000_7000)
  ) sys_fixture (
    .clk(clk),
    .rst_n(rst_n),
    .call_seen(sys_call_seen),
    .callc_seen(sys_callc_seen),
    .ret_seen(sys_ret_seen),
    .sys_seen(sys_sys_seen),
    .iret_seen(sys_iret_seen),
    .fault_seen(sys_fault_seen),
    .pause_seen(sys_pause_seen),
    .done(sys_done)
  );

  cpu_v01_core_control_trap_fixture #(
    .MODE(3),
    .RESET_VECTOR(48'h0000_0000_8000)
  ) callc_fault_fixture (
    .clk(clk),
    .rst_n(rst_n),
    .call_seen(callc_fault_call_seen),
    .callc_seen(callc_fault_callc_seen),
    .ret_seen(callc_fault_ret_seen),
    .sys_seen(callc_fault_sys_seen),
    .iret_seen(callc_fault_iret_seen),
    .fault_seen(callc_fault_fault_seen),
    .pause_seen(callc_fault_pause_seen),
    .done(callc_fault_done)
  );

  cpu_v01_core_control_trap_fixture #(
    .MODE(4),
    .RESET_VECTOR(48'h0000_0000_9000)
  ) ret_fault_fixture (
    .clk(clk),
    .rst_n(rst_n),
    .call_seen(ret_fault_call_seen),
    .callc_seen(ret_fault_callc_seen),
    .ret_seen(ret_fault_ret_seen),
    .sys_seen(ret_fault_sys_seen),
    .iret_seen(ret_fault_iret_seen),
    .fault_seen(ret_fault_fault_seen),
    .pause_seen(ret_fault_pause_seen),
    .done(ret_fault_done)
  );

  initial begin
    clk = 1'b0;
    forever #5 clk = ~clk;
  end

  initial begin
    rst_n = 1'b0;
    repeat (2) @(posedge clk);
    rst_n = 1'b1;
    wait (direct_done && callc_done && sys_done && callc_fault_done && ret_fault_done);

    if (!direct_call_seen || !direct_ret_seen || !direct_pause_seen) begin
      $fatal(1, "integrated control/trap direct CALL/RET sequence mismatch");
    end
    if (!callc_callc_seen || !callc_ret_seen || !callc_pause_seen) begin
      $fatal(1, "integrated control/trap CALLC/RET sequence mismatch");
    end
    if (!sys_sys_seen || !sys_iret_seen || !sys_pause_seen) begin
      $fatal(1, "integrated control/trap SYS/IRET sequence mismatch");
    end
    if (!callc_fault_fault_seen || !ret_fault_fault_seen) begin
      $fatal(1, "integrated control/trap fault sequence mismatch");
    end

    $finish;
  end

  // verilator lint_off UNUSEDSIGNAL
  wire logic unused_fixture_outputs = &{
    direct_callc_seen,
    direct_sys_seen,
    direct_iret_seen,
    direct_fault_seen,
    callc_call_seen,
    callc_sys_seen,
    callc_iret_seen,
    callc_fault_seen,
    sys_call_seen,
    sys_callc_seen,
    sys_ret_seen,
    sys_fault_seen,
    callc_fault_call_seen,
    callc_fault_callc_seen,
    callc_fault_ret_seen,
    callc_fault_sys_seen,
    callc_fault_iret_seen,
    callc_fault_pause_seen,
    ret_fault_call_seen,
    ret_fault_callc_seen,
    ret_fault_ret_seen,
    ret_fault_sys_seen,
    ret_fault_iret_seen,
    ret_fault_pause_seen
  };
  // verilator lint_on UNUSEDSIGNAL
endmodule
