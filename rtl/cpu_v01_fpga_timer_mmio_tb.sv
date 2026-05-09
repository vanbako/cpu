module cpu_v01_fpga_timer_mmio_tb;
  import cpu_v01_pkg::*;

  localparam addr_t TIMER_BASE = 48'h0000_00F0_0100;

  logic clk;
  logic rst_n;
  logic req_valid;
  logic req_ready;
  logic req_write;
  addr_t req_addr;
  logic [2:0] req_len_cells;
  cell_t req_wdata [INTEGER_OBJECT_CELLS];
  logic rsp_valid;
  cell_t rsp_rdata [INTEGER_OBJECT_CELLS];
  fault_packet_t rsp_fault;
  logic timer_interrupt_o;
  logic timer_pending_o;

  cpu_v01_fpga_timer_mmio #(
    .BASE_CELL(TIMER_BASE)
  ) dut (
    .clk(clk),
    .rst_n(rst_n),
    .req_valid(req_valid),
    .req_ready(req_ready),
    .req_write(req_write),
    .req_addr(req_addr),
    .req_len_cells(req_len_cells),
    .req_wdata(req_wdata),
    .rsp_valid(rsp_valid),
    .rsp_rdata(rsp_rdata),
    .rsp_fault(rsp_fault),
    .timer_interrupt_o(timer_interrupt_o),
    .timer_pending_o(timer_pending_o)
  );

  initial begin
    clk = 1'b0;
    forever #5 clk = ~clk;
  end

  task automatic write_24(input addr_t addr, input cell_t data);
    req_addr = addr;
    req_wdata[0] = data;
    req_wdata[1] = '0;
    req_len_cells = 3'd1;
    req_write = 1'b1;
    req_valid = 1'b1;
    @(posedge clk);
    #1;
    if (!req_ready) begin
      $fatal(1, "FPGA timer MMIO write request was not ready");
    end
    req_valid = 1'b0;
    req_write = 1'b0;
    req_addr = '0;
    req_len_cells = '0;
    req_wdata[0] = '0;
    req_wdata[1] = '0;
  endtask

  task automatic write_48(input addr_t addr, input logic [47:0] data);
    req_addr = addr;
    req_wdata[0] = data[23:0];
    req_wdata[1] = data[47:24];
    req_len_cells = 3'd2;
    req_write = 1'b1;
    req_valid = 1'b1;
    @(posedge clk);
    #1;
    if (!req_ready) begin
      $fatal(1, "FPGA timer MMIO write request was not ready");
    end
    req_valid = 1'b0;
    req_write = 1'b0;
    req_addr = '0;
    req_len_cells = '0;
    req_wdata[0] = '0;
    req_wdata[1] = '0;
  endtask

  task automatic read_register(input addr_t addr, input logic [2:0] len, output logic [47:0] data);
    req_addr = addr;
    req_wdata[0] = '0;
    req_wdata[1] = '0;
    req_len_cells = len;
    req_write = 1'b0;
    req_valid = 1'b1;
    @(posedge clk);
    #1;
    req_valid = 1'b0;
    if (!rsp_valid || rsp_fault.valid) begin
      $fatal(1, "FPGA timer MMIO read did not return a clean response");
    end
    data = {rsp_rdata[1], rsp_rdata[0]};
    req_addr = '0;
    req_len_cells = '0;
  endtask

  initial begin
    logic [47:0] value;

    req_valid = 1'b0;
    req_write = 1'b0;
    req_addr = '0;
    req_len_cells = '0;
    req_wdata[0] = '0;
    req_wdata[1] = '0;
    rst_n = 1'b0;
    repeat (3) @(posedge clk);
    rst_n = 1'b1;
    repeat (2) @(posedge clk);

    write_48(TIMER_BASE + 48'd1, 48'd3);
    write_24(TIMER_BASE + 48'd2, 24'h000003);
    repeat (3) @(posedge clk);
    if (!timer_interrupt_o || !timer_pending_o) begin
      $fatal(1, "FPGA timer MMIO did not raise timer_interrupt_o");
    end

    write_24(TIMER_BASE + 48'd3, 24'h000001);
    repeat (1) @(posedge clk);
    if (timer_interrupt_o || timer_pending_o) begin
      $fatal(1, "FPGA timer MMIO acknowledgement did not clear interrupt");
    end

    read_register(TIMER_BASE + 48'd0, 3'd2, value);
    if (value < 48'd3) begin
      $fatal(1, "FPGA timer MMIO value did not advance");
    end

    write_24(TIMER_BASE + 48'd2, 24'h000008);
    read_register(TIMER_BASE + 48'd0, 3'd2, value);
    if (value != 48'd0 || timer_pending_o) begin
      $fatal(1, "FPGA timer MMIO clear-value control did not reset value");
    end

    write_48(TIMER_BASE + 48'd1, 48'd2);
    write_24(TIMER_BASE + 48'd2, 24'h000007);
    repeat (2) @(posedge clk);
    if (!timer_pending_o) begin
      $fatal(1, "FPGA timer MMIO one-shot did not set pending");
    end
    repeat (2) @(posedge clk);
    read_register(TIMER_BASE + 48'd2, 3'd1, value);
    if (value[0]) begin
      $fatal(1, "FPGA timer MMIO one-shot did not clear enable");
    end

    $finish;
  end
endmodule
