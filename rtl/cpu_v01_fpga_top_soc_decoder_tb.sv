module cpu_v01_fpga_top_soc_decoder_tb;
  import cpu_v01_pkg::*;

  localparam addr_t DATA_RAM_BASE = 48'h0000_0001_0000;
  localparam addr_t UART_BASE = 48'h0000_00F0_0000;
  localparam addr_t TIMER_BASE = 48'h0000_00F0_0100;
  localparam addr_t GPIO_BASE = 48'h0000_00F0_0200;
  localparam addr_t IRQ_BASE = 48'h0000_00F0_0300;
  localparam addr_t IDENTITY_BASE = 48'h0000_00F0_0400;
  localparam addr_t RESERVED_MMIO = 48'h0000_00F0_0500;
  localparam logic [95:0] BUILD_ID = 96'h0000_0000_0000_ABCD_EF12_3456;

  logic clk;
  logic rst_n;

  logic core_req_valid;
  logic core_req_ready;
  logic core_req_write;
  addr_t core_req_addr;
  logic [2:0] core_req_len_cells;
  cell_t core_req_wdata [CAPABILITY_OBJECT_CELLS];
  logic core_rsp_valid;
  cell_t core_rsp_rdata [CAPABILITY_OBJECT_CELLS];
  fault_packet_t core_rsp_fault;

  logic ram_req_valid;
  logic ram_req_ready;
  logic ram_req_write;
  addr_t ram_req_addr;
  logic [2:0] ram_req_len_cells;
  cell_t ram_req_wdata [CAPABILITY_OBJECT_CELLS];
  logic ram_rsp_valid;
  cell_t ram_rsp_rdata [CAPABILITY_OBJECT_CELLS];
  fault_packet_t ram_rsp_fault;

  logic uart_req_valid;
  logic uart_req_ready;
  logic uart_req_write;
  addr_t uart_req_addr;
  cell_t uart_req_wdata;
  logic uart_rsp_valid;
  cell_t uart_rsp_rdata;
  fault_packet_t uart_rsp_fault;
  logic uart_tx_o;
  logic uart_rx_ready_irq;
  logic uart_tx_ready_irq;

  logic timer_req_valid;
  logic timer_req_ready;
  logic timer_req_write;
  addr_t timer_req_addr;
  logic [2:0] timer_req_len_cells;
  cell_t timer_req_wdata [INTEGER_OBJECT_CELLS];
  logic timer_rsp_valid;
  cell_t timer_rsp_rdata [INTEGER_OBJECT_CELLS];
  fault_packet_t timer_rsp_fault;
  logic timer_interrupt_o;
  logic timer_pending_o;

  logic gpio_req_valid;
  logic gpio_req_ready;
  logic gpio_req_write;
  addr_t gpio_req_addr;
  cell_t gpio_req_wdata;
  logic gpio_rsp_valid;
  cell_t gpio_rsp_rdata;
  fault_packet_t gpio_rsp_fault;
  logic [15:0] gpio_out_o;
  logic [15:0] gpio_oe_o;
  logic gpio_pass_led_o;
  logic gpio_fail_led_o;
  logic gpio_heartbeat_led_o;
  logic [3:0] status_leds_o;
  logic [7:0] debug_status_select_o;
  logic gpio_status_irq_o;

  logic irq_req_valid;
  logic irq_req_ready;
  logic irq_req_write;
  addr_t irq_req_addr;
  cell_t irq_req_wdata;
  logic irq_rsp_valid;
  cell_t irq_rsp_rdata;
  fault_packet_t irq_rsp_fault;
  logic [15:0] irq_pending_enabled_o;

  logic identity_req_valid;
  logic identity_req_ready;
  logic identity_req_write;
  addr_t identity_req_addr;
  logic [2:0] identity_req_len_cells;
  cell_t identity_req_wdata [CAPABILITY_OBJECT_CELLS];
  logic identity_rsp_valid;
  cell_t identity_rsp_rdata [CAPABILITY_OBJECT_CELLS];
  fault_packet_t identity_rsp_fault;

  cpu_v01_fpga_soc_dmem_decoder #(
    .DATA_RAM_BASE(DATA_RAM_BASE),
    .DATA_RAM_CELLS(64)
  ) dut (
    .clk(clk),
    .rst_n(rst_n),
    .core_req_valid(core_req_valid),
    .core_req_ready(core_req_ready),
    .core_req_write(core_req_write),
    .core_req_addr(core_req_addr),
    .core_req_len_cells(core_req_len_cells),
    .core_req_wdata(core_req_wdata),
    .core_rsp_valid(core_rsp_valid),
    .core_rsp_rdata(core_rsp_rdata),
    .core_rsp_fault(core_rsp_fault),
    .ram_req_valid(ram_req_valid),
    .ram_req_ready(ram_req_ready),
    .ram_req_write(ram_req_write),
    .ram_req_addr(ram_req_addr),
    .ram_req_len_cells(ram_req_len_cells),
    .ram_req_wdata(ram_req_wdata),
    .ram_rsp_valid(ram_rsp_valid),
    .ram_rsp_rdata(ram_rsp_rdata),
    .ram_rsp_fault(ram_rsp_fault),
    .uart_req_valid(uart_req_valid),
    .uart_req_ready(uart_req_ready),
    .uart_req_write(uart_req_write),
    .uart_req_addr(uart_req_addr),
    .uart_req_wdata(uart_req_wdata),
    .uart_rsp_valid(uart_rsp_valid),
    .uart_rsp_rdata(uart_rsp_rdata),
    .uart_rsp_fault(uart_rsp_fault),
    .timer_req_valid(timer_req_valid),
    .timer_req_ready(timer_req_ready),
    .timer_req_write(timer_req_write),
    .timer_req_addr(timer_req_addr),
    .timer_req_len_cells(timer_req_len_cells),
    .timer_req_wdata(timer_req_wdata),
    .timer_rsp_valid(timer_rsp_valid),
    .timer_rsp_rdata(timer_rsp_rdata),
    .timer_rsp_fault(timer_rsp_fault),
    .gpio_req_valid(gpio_req_valid),
    .gpio_req_ready(gpio_req_ready),
    .gpio_req_write(gpio_req_write),
    .gpio_req_addr(gpio_req_addr),
    .gpio_req_wdata(gpio_req_wdata),
    .gpio_rsp_valid(gpio_rsp_valid),
    .gpio_rsp_rdata(gpio_rsp_rdata),
    .gpio_rsp_fault(gpio_rsp_fault),
    .irq_req_valid(irq_req_valid),
    .irq_req_ready(irq_req_ready),
    .irq_req_write(irq_req_write),
    .irq_req_addr(irq_req_addr),
    .irq_req_wdata(irq_req_wdata),
    .irq_rsp_valid(irq_rsp_valid),
    .irq_rsp_rdata(irq_rsp_rdata),
    .irq_rsp_fault(irq_rsp_fault),
    .identity_req_valid(identity_req_valid),
    .identity_req_ready(identity_req_ready),
    .identity_req_write(identity_req_write),
    .identity_req_addr(identity_req_addr),
    .identity_req_len_cells(identity_req_len_cells),
    .identity_req_wdata(identity_req_wdata),
    .identity_rsp_valid(identity_rsp_valid),
    .identity_rsp_rdata(identity_rsp_rdata),
    .identity_rsp_fault(identity_rsp_fault)
  );

  cpu_v01_fpga_data_ram #(
    .BASE_CELL(DATA_RAM_BASE),
    .DEPTH_CELLS(64)
  ) data_ram (
    .clk(clk),
    .rst_n(rst_n),
    .req_valid(ram_req_valid),
    .req_ready(ram_req_ready),
    .req_write(ram_req_write),
    .req_addr(ram_req_addr),
    .req_len_cells(ram_req_len_cells),
    .req_wdata(ram_req_wdata),
    .rsp_valid(ram_rsp_valid),
    .rsp_rdata(ram_rsp_rdata),
    .rsp_fault(ram_rsp_fault)
  );

  cpu_v01_fpga_uart_mmio #(
    .CLOCK_HZ(16),
    .BAUD(1)
  ) uart (
    .clk(clk),
    .rst_n(rst_n),
    .req_valid(uart_req_valid),
    .req_ready(uart_req_ready),
    .req_write(uart_req_write),
    .req_addr(uart_req_addr),
    .req_wdata(uart_req_wdata),
    .rsp_valid(uart_rsp_valid),
    .rsp_rdata(uart_rsp_rdata),
    .rsp_fault(uart_rsp_fault),
    .uart_rx_i(1'b1),
    .uart_tx_o(uart_tx_o),
    .irq_rx_ready_o(uart_rx_ready_irq),
    .irq_tx_ready_o(uart_tx_ready_irq)
  );

  cpu_v01_fpga_timer_mmio timer (
    .clk(clk),
    .rst_n(rst_n),
    .req_valid(timer_req_valid),
    .req_ready(timer_req_ready),
    .req_write(timer_req_write),
    .req_addr(timer_req_addr),
    .req_len_cells(timer_req_len_cells),
    .req_wdata(timer_req_wdata),
    .rsp_valid(timer_rsp_valid),
    .rsp_rdata(timer_rsp_rdata),
    .rsp_fault(timer_rsp_fault),
    .timer_interrupt_o(timer_interrupt_o),
    .timer_pending_o(timer_pending_o)
  );

  cpu_v01_fpga_gpio_status gpio (
    .clk(clk),
    .rst_n(rst_n),
    .req_valid(gpio_req_valid),
    .req_ready(gpio_req_ready),
    .req_write(gpio_req_write),
    .req_addr(gpio_req_addr),
    .req_wdata(gpio_req_wdata),
    .rsp_valid(gpio_rsp_valid),
    .rsp_rdata(gpio_rsp_rdata),
    .rsp_fault(gpio_rsp_fault),
    .board_gpio_i(16'h00F0),
    .gpio_out_o(gpio_out_o),
    .gpio_oe_o(gpio_oe_o),
    .pass_led_o(gpio_pass_led_o),
    .fail_led_o(gpio_fail_led_o),
    .heartbeat_led_o(gpio_heartbeat_led_o),
    .status_leds_o(status_leds_o),
    .debug_status_select_o(debug_status_select_o),
    .gpio_status_irq_o(gpio_status_irq_o)
  );

  cpu_v01_fpga_irq_mmio irq (
    .clk(clk),
    .rst_n(rst_n),
    .req_valid(irq_req_valid),
    .req_ready(irq_req_ready),
    .req_write(irq_req_write),
    .req_addr(irq_req_addr),
    .req_wdata(irq_req_wdata),
    .rsp_valid(irq_rsp_valid),
    .rsp_rdata(irq_rsp_rdata),
    .rsp_fault(irq_rsp_fault),
    .irq_sources_i({12'd0, gpio_status_irq_o, timer_interrupt_o, uart_tx_ready_irq, uart_rx_ready_irq}),
    .irq_pending_enabled_o(irq_pending_enabled_o)
  );

  cpu_v01_fpga_system_identity_mmio #(
    .BUILD_ID(BUILD_ID)
  ) identity (
    .clk(clk),
    .rst_n(rst_n),
    .req_valid(identity_req_valid),
    .req_ready(identity_req_ready),
    .req_write(identity_req_write),
    .req_addr(identity_req_addr),
    .req_len_cells(identity_req_len_cells),
    .req_wdata(identity_req_wdata),
    .rsp_valid(identity_rsp_valid),
    .rsp_rdata(identity_rsp_rdata),
    .rsp_fault(identity_rsp_fault)
  );

  initial begin
    clk = 1'b0;
    forever #5 clk = ~clk;
  end

  task automatic clear_core_request();
    core_req_valid = 1'b0;
    core_req_write = 1'b0;
    core_req_addr = '0;
    core_req_len_cells = 3'd0;
    for (int i = 0; i < CAPABILITY_OBJECT_CELLS; i++) begin
      core_req_wdata[i] = '0;
    end
  endtask

  task automatic write_cells(
      input addr_t addr,
      input logic [2:0] len_cells,
      input cell_t data0,
      input cell_t data1
  );
    clear_core_request();
    core_req_addr = addr;
    core_req_len_cells = len_cells;
    core_req_wdata[0] = data0;
    core_req_wdata[1] = data1;
    core_req_write = 1'b1;
    core_req_valid = 1'b1;
    #1;
    if (!core_req_ready) begin
      $fatal(1, "FPGA SoC top decoder write request was not ready");
    end
    @(posedge clk);
    #1;
    clear_core_request();
  endtask

  task automatic read_cells(
      input addr_t addr,
      input logic [2:0] len_cells,
      output cell_t data0,
      output cell_t data1,
      output logic fault_valid,
      output logic [15:0] fault_cause
  );
    clear_core_request();
    core_req_addr = addr;
    core_req_len_cells = len_cells;
    core_req_write = 1'b0;
    core_req_valid = 1'b1;
    #1;
    if (!core_req_ready) begin
      $fatal(1, "FPGA SoC top decoder read request was not ready");
    end
    @(posedge clk);
    #1;
    core_req_valid = 1'b0;
    if (!core_rsp_valid) begin
      $fatal(1, "FPGA SoC top decoder read did not return a response");
    end
    data0 = core_rsp_rdata[0];
    data1 = core_rsp_rdata[1];
    fault_valid = core_rsp_fault.valid;
    fault_cause = core_rsp_fault.cause;
    clear_core_request();
  endtask

  initial begin
    cell_t data0;
    cell_t data1;
    logic fault_valid;
    logic [15:0] fault_cause;

    clear_core_request();
    rst_n = 1'b0;
    repeat (3) @(posedge clk);
    rst_n = 1'b1;
    repeat (2) @(posedge clk);

    write_cells(DATA_RAM_BASE + 48'd4, 3'd2, 24'h00CAFE, 24'h0BEEF0);
    read_cells(DATA_RAM_BASE + 48'd4, 3'd2, data0, data1, fault_valid, fault_cause);
    if (fault_valid || data0 != 24'h00CAFE || data1 != 24'h0BEEF0) begin
      $fatal(1, "FPGA SoC top decoder did not route RAM read/write traffic");
    end

    core_req_addr = UART_BASE + 48'd2;
    core_req_len_cells = 3'd1;
    core_req_write = 1'b0;
    core_req_valid = 1'b1;
    #1;
    if (!uart_req_valid || ram_req_valid || timer_req_valid || gpio_req_valid) begin
      $fatal(1, "FPGA SoC top decoder did not select only the UART window");
    end
    @(posedge clk);
    #1;
    if (!core_rsp_valid || core_rsp_fault.valid || core_rsp_rdata[0][1:0] != 2'b11) begin
      $fatal(1, "FPGA SoC top decoder UART status read mismatch");
    end
    clear_core_request();

    write_cells(TIMER_BASE + 48'd1, 3'd2, 24'h000003, 24'h000000);
    read_cells(TIMER_BASE + 48'd1, 3'd2, data0, data1, fault_valid, fault_cause);
    if (fault_valid || data0 != 24'h000003 || data1 != 24'h000000) begin
      $fatal(1, "FPGA SoC top decoder timer compare readback mismatch");
    end

    write_cells(GPIO_BASE + 48'd0, 3'd1, 24'h0055AA, '0);
    read_cells(GPIO_BASE + 48'd0, 3'd1, data0, data1, fault_valid, fault_cause);
    if (fault_valid || data0 != 24'h0055AA) begin
      $fatal(1, "FPGA SoC top decoder GPIO/status readback mismatch");
    end

    write_cells(IRQ_BASE + 48'd3, 3'd1, 24'h000005, '0);
    read_cells(IRQ_BASE + 48'd0, 3'd1, data0, data1, fault_valid, fault_cause);
    if (fault_valid || data0[2:0] != 3'b101) begin
      $fatal(1, "FPGA SoC top decoder interrupt-controller pending read mismatch");
    end

    read_cells(IDENTITY_BASE + 48'd0, 3'd1, data0, data1, fault_valid, fault_cause);
    if (fault_valid || data0[15:0] != 16'h0001) begin
      $fatal(1, "FPGA SoC top decoder system identity reset-cause mismatch");
    end
    read_cells(IDENTITY_BASE + 48'd1, 3'd2, data0, data1, fault_valid, fault_cause);
    if (fault_valid || data0 != 24'h123456 || data1 != 24'hABCDEF) begin
      $fatal(1, "FPGA SoC top decoder system identity build-id mismatch");
    end

    read_cells(RESERVED_MMIO, 3'd1, data0, data1, fault_valid, fault_cause);
    if (!fault_valid || fault_cause != EXC_ACCESS_FAULT) begin
      $fatal(1, "FPGA SoC top decoder reserved window did not fault");
    end
    read_cells(DATA_RAM_BASE, 3'd0, data0, data1, fault_valid, fault_cause);
    if (!fault_valid || fault_cause != EXC_ACCESS_FAULT) begin
      $fatal(1, "FPGA SoC top decoder invalid length did not fault");
    end

    $finish;
  end

  // verilator lint_off UNUSEDSIGNAL
  wire logic unused_decoder_tb_outputs = &{
    uart_tx_o,
    uart_rx_ready_irq,
    timer_pending_o,
    gpio_out_o,
    gpio_oe_o,
    gpio_pass_led_o,
    gpio_fail_led_o,
    gpio_heartbeat_led_o,
    status_leds_o,
    debug_status_select_o,
    irq_pending_enabled_o
  };
  // verilator lint_on UNUSEDSIGNAL
endmodule
