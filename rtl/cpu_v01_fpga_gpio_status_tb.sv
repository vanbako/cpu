module cpu_v01_fpga_gpio_status_tb;
  import cpu_v01_pkg::*;

  localparam addr_t GPIO_BASE = 48'h0000_00F0_0200;

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
  logic [15:0] board_gpio_i;
  logic [15:0] gpio_out_o;
  logic [15:0] gpio_oe_o;
  logic pass_led_o;
  logic fail_led_o;
  logic heartbeat_led_o;
  logic [3:0] status_leds_o;
  logic [7:0] debug_status_select_o;
  logic gpio_status_irq_o;

  cpu_v01_fpga_gpio_status #(
    .BASE_CELL(GPIO_BASE),
    .GPIO_WIDTH(16)
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
    .board_gpio_i(board_gpio_i),
    .gpio_out_o(gpio_out_o),
    .gpio_oe_o(gpio_oe_o),
    .pass_led_o(pass_led_o),
    .fail_led_o(fail_led_o),
    .heartbeat_led_o(heartbeat_led_o),
    .status_leds_o(status_leds_o),
    .debug_status_select_o(debug_status_select_o),
    .gpio_status_irq_o(gpio_status_irq_o)
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
      $fatal(1, "FPGA GPIO/status write request was not ready");
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
      $fatal(1, "FPGA GPIO/status read did not return a clean response");
    end
    data = rsp_rdata;
    req_addr = '0;
  endtask

  initial begin
    cell_t value;

    req_valid = 1'b0;
    req_write = 1'b0;
    req_addr = '0;
    req_wdata = '0;
    board_gpio_i = 16'd0;
    rst_n = 1'b0;
    repeat (3) @(posedge clk);
    rst_n = 1'b1;
    repeat (2) @(posedge clk);

    write_cell(GPIO_BASE + 48'd2, 24'h0000FF);
    write_cell(GPIO_BASE + 48'd0, 24'h00A5A5);
    if (gpio_out_o != 16'h00A5 || gpio_oe_o != 16'h00FF) begin
      $fatal(1, "FPGA GPIO/status output mask mismatch");
    end

    write_cell(GPIO_BASE + 48'd3, 24'h000015);
    if (!pass_led_o || fail_led_o || !heartbeat_led_o || status_leds_o != 4'h2) begin
      $fatal(1, "FPGA GPIO/status LEDs did not follow STATUS_LEDS");
    end

    board_gpio_i = 16'h1234;
    repeat (4) @(posedge clk);
    if (!gpio_status_irq_o) begin
      $fatal(1, "FPGA GPIO/status input change did not assert interrupt");
    end
    read_cell(GPIO_BASE + 48'd1, value);
    if (value[15:0] != 16'h1234) begin
      $fatal(1, "FPGA GPIO/status input readback mismatch");
    end
    repeat (1) @(posedge clk);
    if (gpio_status_irq_o) begin
      $fatal(1, "FPGA GPIO/status input read did not clear interrupt");
    end

    write_cell(GPIO_BASE + 48'd4, 24'h000080);
    if (!gpio_status_irq_o || debug_status_select_o != 8'h80) begin
      $fatal(1, "FPGA GPIO/status DEBUG_STATUS_SELECT force did not assert interrupt");
    end
    write_cell(GPIO_BASE + 48'd4, 24'h000000);
    repeat (1) @(posedge clk);
    if (gpio_status_irq_o) begin
      $fatal(1, "FPGA GPIO/status DEBUG_STATUS_SELECT clear did not clear interrupt");
    end

    $finish;
  end
endmodule
