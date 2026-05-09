module cpu_v01_fpga_uart_mmio_tb;
  import cpu_v01_pkg::*;

  localparam addr_t UART_BASE = 48'h0000_00F0_0000;
  localparam int UART_TEST_CLOCK_HZ = 16;
  localparam int UART_TEST_BAUD = 1;
  localparam int UART_TEST_CLKS_PER_BIT = UART_TEST_CLOCK_HZ / UART_TEST_BAUD;

  logic clk;
  logic rst_n;
  logic req_valid;
  logic req_ready;
  logic req_write;
  addr_t req_addr;
  cell_t req_wdata;
  logic rsp_valid;
  cell_t rsp_rdata;
  fault_packet_t rsp_fault;
  logic uart_rx_i;
  logic uart_tx_o;
  logic irq_rx_ready_o;
  logic irq_tx_ready_o;

  cpu_v01_fpga_uart_mmio #(
    .BASE_CELL(UART_BASE),
    .CLOCK_HZ(UART_TEST_CLOCK_HZ),
    .BAUD(UART_TEST_BAUD),
    .TX_FIFO_DEPTH(2),
    .RX_FIFO_DEPTH(2)
  ) dut (
    .clk(clk),
    .rst_n(rst_n),
    .req_valid(req_valid),
    .req_ready(req_ready),
    .req_write(req_write),
    .req_addr(req_addr),
    .req_wdata(req_wdata),
    .rsp_valid(rsp_valid),
    .rsp_rdata(rsp_rdata),
    .rsp_fault(rsp_fault),
    .uart_rx_i(uart_rx_i),
    .uart_tx_o(uart_tx_o),
    .irq_rx_ready_o(irq_rx_ready_o),
    .irq_tx_ready_o(irq_tx_ready_o)
  );

  initial begin
    clk = 1'b0;
    forever #5 clk = ~clk;
  end

  task automatic write_cell(input addr_t addr, input cell_t data);
    req_addr = addr;
    req_wdata = data;
    req_write = 1'b1;
    req_valid = 1'b1;
    @(posedge clk);
    #1;
    if (!req_ready) begin
      $fatal(1, "FPGA UART MMIO write request was not ready");
    end
    req_valid = 1'b0;
    req_write = 1'b0;
    req_addr = '0;
    req_wdata = '0;
  endtask

  task automatic read_cell(input addr_t addr, output cell_t data);
    req_addr = addr;
    req_wdata = '0;
    req_write = 1'b0;
    req_valid = 1'b1;
    @(posedge clk);
    #1;
    req_valid = 1'b0;
    if (!rsp_valid || rsp_fault.valid) begin
      $fatal(1, "FPGA UART MMIO read did not return a clean response");
    end
    data = rsp_rdata;
    req_addr = '0;
  endtask

  task automatic drive_uart_bit(input logic bit_value);
    uart_rx_i = bit_value;
    repeat (UART_TEST_CLKS_PER_BIT) @(posedge clk);
  endtask

  task automatic drive_uart_byte(input logic [7:0] value);
    drive_uart_bit(1'b0);
    for (int i = 0; i < 8; i++) begin
      drive_uart_bit(value[i]);
    end
    drive_uart_bit(1'b1);
    repeat (UART_TEST_CLKS_PER_BIT * 2) @(posedge clk);
  endtask

  initial begin
    cell_t value;

    req_valid = 1'b0;
    req_write = 1'b0;
    req_addr = '0;
    req_wdata = '0;
    uart_rx_i = 1'b1;
    rst_n = 1'b0;
    repeat (3) @(posedge clk);
    rst_n = 1'b1;
    repeat (2) @(posedge clk);

    read_cell(UART_BASE + 48'd2, value);
    if (!value[0] || !value[1] || value[2]) begin
      $fatal(1, "FPGA UART MMIO reset status bits mismatch");
    end

    write_cell(UART_BASE + 48'd3, 24'h000003);
    if (!irq_tx_ready_o) begin
      $fatal(1, "FPGA UART MMIO TX ready interrupt did not assert");
    end

    write_cell(UART_BASE + 48'd0, 24'h000055);
    repeat (4) @(posedge clk);
    if (uart_tx_o !== 1'b0) begin
      $fatal(1, "FPGA UART MMIO TX path did not pull uart_tx_o low");
    end
    repeat (UART_TEST_CLKS_PER_BIT * 12) @(posedge clk);

    drive_uart_byte(8'hA6);
    read_cell(UART_BASE + 48'd2, value);
    if (!value[2] || !irq_rx_ready_o) begin
      $fatal(1, "FPGA UART MMIO RX ready status did not assert");
    end
    read_cell(UART_BASE + 48'd1, value);
    if (value[7:0] != 8'hA6) begin
      $fatal(1, "FPGA UART MMIO RX path did not return injected byte");
    end

    drive_uart_byte(8'h11);
    drive_uart_byte(8'h22);
    drive_uart_byte(8'h33);
    read_cell(UART_BASE + 48'd2, value);
    if (!value[3]) begin
      $fatal(1, "FPGA UART MMIO RX overrun bit did not set");
    end

    write_cell(UART_BASE + 48'd3, 24'h000004);
    read_cell(UART_BASE + 48'd2, value);
    if (value[3]) begin
      $fatal(1, "FPGA UART MMIO clear-errors control did not clear RX overrun");
    end

    $finish;
  end
endmodule
