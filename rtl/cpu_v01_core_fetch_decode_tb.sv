module cpu_v01_core_fetch_decode_fixture #(
  parameter int MODE = 0,
  parameter cpu_v01_pkg::addr_t RESET_VECTOR = 48'h0000_0000_1000
) (
  input  logic clk,
  input  logic rst_n,
  output logic add24_seen,
  output logic pause12_seen,
  output logic brk_slot1_seen,
  output logic cgetaddr48_seen,
  output logic align_fault_seen,
  output logic illegal_fault_seen,
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
        if (group_addr == 48'h0000_0000_1000) begin
          imem_rsp_cells[0] = 24'h120000;
          imem_rsp_cells[1] = 24'h05B05B;
        end else if (group_addr == 48'h0000_0000_1002) begin
          imem_rsp_cells[0] = 24'h410000;
          imem_rsp_cells[1] = 24'h000000;
        end else begin
          imem_rsp_cells[0] = 24'h000999;
        end
      end

      1: begin
        imem_rsp_cells[0] = 24'h000000;
        imem_rsp_cells[1] = 24'h410000;
      end

      2: begin
        imem_rsp_cells[0] = 24'h12005B;
        imem_rsp_cells[1] = 24'h000000;
      end

      default: begin
        imem_rsp_cells[0] = 24'h000999;
        imem_rsp_cells[1] = 24'h000000;
      end
    endcase
  endtask

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      imem_rsp_valid <= 1'b0;
      rsp_pending_q <= 1'b0;
      pending_addr_q <= '0;
      add24_seen <= 1'b0;
      pause12_seen <= 1'b0;
      brk_slot1_seen <= 1'b0;
      cgetaddr48_seen <= 1'b0;
      align_fault_seen <= 1'b0;
      illegal_fault_seen <= 1'b0;
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

      if (retire_valid) begin
        if (retire_packet.fault.valid && retire_packet.fault.cause == EXC_ALIGN_FAULT) begin
          align_fault_seen <= 1'b1;
          done <= MODE != 0;
        end else if (retire_packet.fault.valid &&
                     retire_packet.fault.cause == EXC_ILLEGAL_INSTRUCTION) begin
          illegal_fault_seen <= 1'b1;
          done <= MODE == 3;
        end else if (retire_packet.decoded.valid &&
                     retire_packet.decoded.opcode_id == OPC_ADD_24 &&
                     retire_packet.decoded.size_bits == 8'd24 &&
                     retire_packet.pc_cell == 48'h0000_0000_1000 &&
                     retire_packet.slot == SLOT_0) begin
          add24_seen <= 1'b1;
        end else if (retire_packet.decoded.valid &&
                     retire_packet.decoded.opcode_id == OPC_PAUSE_12 &&
                     retire_packet.decoded.size_bits == 8'd12 &&
                     retire_packet.pc_cell == 48'h0000_0000_1001 &&
                     retire_packet.slot == SLOT_0) begin
          pause12_seen <= 1'b1;
        end else if (retire_packet.decoded.valid &&
                     retire_packet.decoded.opcode_id == OPC_BRK_12 &&
                     retire_packet.decoded.size_bits == 8'd12 &&
                     retire_packet.pc_cell == 48'h0000_0000_1001 &&
                     retire_packet.slot == SLOT_1) begin
          brk_slot1_seen <= 1'b1;
        end else if (retire_packet.decoded.valid &&
                     retire_packet.decoded.opcode_id == OPC_CGETADDR_48 &&
                     retire_packet.decoded.size_bits == 8'd48 &&
                     retire_packet.instruction_length == 2'd2 &&
                     retire_packet.pc_cell == 48'h0000_0000_1002 &&
                     retire_packet.slot == SLOT_0) begin
          cgetaddr48_seen <= 1'b1;
          done <= MODE == 0;
        end
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

module cpu_v01_core_fetch_decode_tb;
  // verilator lint_off UNUSEDSIGNAL
  logic clk;
  logic rst_n;

  logic legal_add24_seen;
  logic legal_pause12_seen;
  logic legal_brk_slot1_seen;
  logic legal_cgetaddr48_seen;
  logic legal_align_fault_seen;
  logic legal_illegal_fault_seen;
  logic legal_done;

  logic align48_add24_seen;
  logic align48_pause12_seen;
  logic align48_brk_slot1_seen;
  logic align48_cgetaddr48_seen;
  logic align48_align_fault_seen;
  logic align48_illegal_fault_seen;
  logic align48_done;

  logic align24_add24_seen;
  logic align24_pause12_seen;
  logic align24_brk_slot1_seen;
  logic align24_cgetaddr48_seen;
  logic align24_align_fault_seen;
  logic align24_illegal_fault_seen;
  logic align24_done;

  logic illegal_add24_seen;
  logic illegal_pause12_seen;
  logic illegal_brk_slot1_seen;
  logic illegal_cgetaddr48_seen;
  logic illegal_align_fault_seen;
  logic illegal_illegal_fault_seen;
  logic illegal_done;
  // verilator lint_on UNUSEDSIGNAL

  cpu_v01_core_fetch_decode_fixture #(
    .MODE(0),
    .RESET_VECTOR(48'h0000_0000_1000)
  ) legal_fixture (
    .clk(clk),
    .rst_n(rst_n),
    .add24_seen(legal_add24_seen),
    .pause12_seen(legal_pause12_seen),
    .brk_slot1_seen(legal_brk_slot1_seen),
    .cgetaddr48_seen(legal_cgetaddr48_seen),
    .align_fault_seen(legal_align_fault_seen),
    .illegal_fault_seen(legal_illegal_fault_seen),
    .done(legal_done)
  );

  cpu_v01_core_fetch_decode_fixture #(
    .MODE(1),
    .RESET_VECTOR(48'h0000_0000_1001)
  ) align48_fixture (
    .clk(clk),
    .rst_n(rst_n),
    .add24_seen(align48_add24_seen),
    .pause12_seen(align48_pause12_seen),
    .brk_slot1_seen(align48_brk_slot1_seen),
    .cgetaddr48_seen(align48_cgetaddr48_seen),
    .align_fault_seen(align48_align_fault_seen),
    .illegal_fault_seen(align48_illegal_fault_seen),
    .done(align48_done)
  );

  cpu_v01_core_fetch_decode_fixture #(
    .MODE(2),
    .RESET_VECTOR(48'h0000_0000_1000)
  ) align24_fixture (
    .clk(clk),
    .rst_n(rst_n),
    .add24_seen(align24_add24_seen),
    .pause12_seen(align24_pause12_seen),
    .brk_slot1_seen(align24_brk_slot1_seen),
    .cgetaddr48_seen(align24_cgetaddr48_seen),
    .align_fault_seen(align24_align_fault_seen),
    .illegal_fault_seen(align24_illegal_fault_seen),
    .done(align24_done)
  );

  cpu_v01_core_fetch_decode_fixture #(
    .MODE(3),
    .RESET_VECTOR(48'h0000_0000_1000)
  ) illegal_fixture (
    .clk(clk),
    .rst_n(rst_n),
    .add24_seen(illegal_add24_seen),
    .pause12_seen(illegal_pause12_seen),
    .brk_slot1_seen(illegal_brk_slot1_seen),
    .cgetaddr48_seen(illegal_cgetaddr48_seen),
    .align_fault_seen(illegal_align_fault_seen),
    .illegal_fault_seen(illegal_illegal_fault_seen),
    .done(illegal_done)
  );

  initial begin
    clk = 1'b0;
    forever #5 clk = ~clk;
  end

  initial begin
    rst_n = 1'b0;
    repeat (2) @(posedge clk);
    rst_n = 1'b1;
    wait (legal_done && align48_done && align24_done && illegal_done);

    if (!legal_add24_seen ||
        !legal_pause12_seen ||
        !legal_cgetaddr48_seen ||
        legal_align_fault_seen ||
        legal_illegal_fault_seen) begin
      $fatal(1, "integrated core fetch/decode legal sequence mismatch");
    end

    if (!align48_align_fault_seen || align48_cgetaddr48_seen) begin
      $fatal(1, "integrated core did not fault 48-bit instruction at second fetch-group cell");
    end

    if (!align24_pause12_seen || !align24_align_fault_seen) begin
      $fatal(1, "integrated core did not fault 24-bit instruction at slot 1");
    end

    if (!illegal_illegal_fault_seen || illegal_align_fault_seen) begin
      $fatal(1, "integrated core did not fault illegal opcode contents");
    end

    $finish;
  end
endmodule
