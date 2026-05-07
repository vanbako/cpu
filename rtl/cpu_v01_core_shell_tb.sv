module cpu_v01_core_shell_tb;
  import cpu_v01_pkg::*;

  logic clk;
  logic rst_n;

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

  logic timer_interrupt_pending;
  logic software_interrupt_pending;
  logic external_interrupt_pending;
  logic external_event_valid;
  logic [15:0] external_event_cause;
  logic debug_halt_request;

  logic retire_valid;
  logic retire_ready;
  retire_packet_t retire_packet;

  logic core_idle;
  logic reset_observed;
  cap_t debug_pcc;
  logic debug_pcc_slot;
  int_reg_t debug_sr;
  logic [RETIRE_SEQUENCE_BITS-1:0] debug_retire_sequence;

  cpu_v01_core #(
    .RESET_VECTOR(48'h0000_0000_1000)
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
    .timer_interrupt_pending(timer_interrupt_pending),
    .software_interrupt_pending(software_interrupt_pending),
    .external_interrupt_pending(external_interrupt_pending),
    .external_event_valid(external_event_valid),
    .external_event_cause(external_event_cause),
    .debug_halt_request(debug_halt_request),
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

  initial begin
    clk = 1'b0;
    forever #5 clk = ~clk;
  end

  initial begin
    imem_req_ready = 1'b1;
    imem_rsp_valid = 1'b0;
    imem_rsp_fault = '0;
    dmem_req_ready = 1'b1;
    dmem_rsp_valid = 1'b0;
    dmem_rsp_fault = '0;
    tagmem_req_ready = 1'b1;
    tagmem_rsp_valid = 1'b0;
    tagmem_rsp_rtag = 1'b0;
    timer_interrupt_pending = 1'b0;
    software_interrupt_pending = 1'b0;
    external_interrupt_pending = 1'b0;
    external_event_valid = 1'b0;
    external_event_cause = '0;
    debug_halt_request = 1'b0;
    retire_ready = 1'b1;
    for (int i = 0; i < FETCH_GROUP_CELLS; i++) begin
      imem_rsp_cells[i] = '0;
    end
    for (int i = 0; i < CAPABILITY_OBJECT_CELLS; i++) begin
      dmem_rsp_rdata[i] = '0;
    end

    rst_n = 1'b0;
    repeat (2) @(posedge clk);
    rst_n = 1'b1;
    repeat (2) @(posedge clk);

    if (!reset_observed || !core_idle) begin
      $fatal(1, "integrated core shell did not expose idle reset observation");
    end
    if (imem_req_valid || imem_rsp_ready ||
        dmem_req_valid || dmem_req_write ||
        tagmem_req_valid || tagmem_req_write ||
        retire_valid || retire_packet.valid) begin
      $fatal(1, "integrated core shell did not keep all request and retire ports idle");
    end
    if (imem_req_addr != 48'h0000_0000_1000 ||
        debug_pcc.payload.cursor != 48'h0000_0000_1000 ||
        debug_pcc.payload.permissions != 8'd4 ||
        debug_pcc.payload.otype != 8'd0 ||
        debug_pcc.payload.flags != 2'd1 ||
        !debug_pcc.tag ||
        debug_pcc_slot != SLOT_0 ||
        debug_sr != 48'h0000_0000_00C0 ||
        debug_retire_sequence != 64'd0) begin
      $fatal(1, "integrated core shell reset PCC/SR observation mismatch");
    end

    $finish;
  end
endmodule
