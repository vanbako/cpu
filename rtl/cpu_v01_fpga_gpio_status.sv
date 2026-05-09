module cpu_v01_fpga_gpio_status #(
  parameter cpu_v01_pkg::addr_t BASE_CELL = 48'h0000_00F0_0200,
  parameter int GPIO_WIDTH = 16
) (
  input  logic clk,
  input  logic rst_n,

  input  logic req_valid,
  output logic req_ready,
  input  logic req_write,
  input  cpu_v01_pkg::addr_t req_addr,
  input  cpu_v01_pkg::cell_t req_wdata,

  output logic rsp_valid,
  output cpu_v01_pkg::cell_t rsp_rdata,
  output cpu_v01_pkg::fault_packet_t rsp_fault,

  input  logic [GPIO_WIDTH-1:0] board_gpio_i,
  output logic [GPIO_WIDTH-1:0] gpio_out_o,
  output logic [GPIO_WIDTH-1:0] gpio_oe_o,
  output logic pass_led_o,
  output logic fail_led_o,
  output logic heartbeat_led_o,
  output logic [3:0] status_leds_o,
  output logic [7:0] debug_status_select_o,
  output logic gpio_status_irq_o
);
  import cpu_v01_pkg::*;

  localparam cpu_v01_pkg::addr_t GPIO_OUT_OFFSET = 48'd0;
  localparam cpu_v01_pkg::addr_t GPIO_IN_OFFSET = 48'd1;
  localparam cpu_v01_pkg::addr_t GPIO_DIR_OFFSET = 48'd2;
  localparam cpu_v01_pkg::addr_t STATUS_LEDS_OFFSET = 48'd3;
  localparam cpu_v01_pkg::addr_t DEBUG_STATUS_SELECT_OFFSET = 48'd4;
  localparam cpu_v01_pkg::addr_t GPIO_REGISTER_CELLS = 48'd5;

  localparam logic [7:0] STATUS_LED_PASS = 8'h01;
  localparam logic [7:0] STATUS_LED_FAIL = 8'h02;
  localparam logic [7:0] STATUS_LED_HEARTBEAT = 8'h04;
  localparam int DEBUG_SELECT_FORCE_IRQ_BIT = 7;

  logic [GPIO_WIDTH-1:0] gpio_out_q;
  logic [GPIO_WIDTH-1:0] gpio_dir_q;
  logic [GPIO_WIDTH-1:0] gpio_meta_q;
  logic [GPIO_WIDTH-1:0] gpio_in_q;
  logic [GPIO_WIDTH-1:0] gpio_prev_q;
  logic [7:0] status_leds_q;
  logic [7:0] debug_status_select_q;
  logic gpio_changed_q;

  assign req_ready = 1'b1;
  assign gpio_out_o = gpio_out_q & gpio_dir_q;
  assign gpio_oe_o = gpio_dir_q;
  assign pass_led_o = status_leds_q[0];
  assign fail_led_o = status_leds_q[1];
  assign heartbeat_led_o = status_leds_q[2];
  assign status_leds_o = status_leds_q[6:3];
  assign debug_status_select_o = debug_status_select_q;
  assign gpio_status_irq_o = gpio_changed_q || debug_status_select_q[DEBUG_SELECT_FORCE_IRQ_BIT];

  function automatic logic register_address(input addr_t addr);
    return addr >= BASE_CELL && addr < BASE_CELL + GPIO_REGISTER_CELLS;
  endfunction

  function automatic addr_t register_offset(input addr_t addr);
    return addr - BASE_CELL;
  endfunction

  function automatic fault_packet_t access_fault(input addr_t addr);
    fault_packet_t fault;
    fault = '0;
    fault.valid = 1'b1;
    fault.cause = EXC_ACCESS_FAULT;
    fault.tval = addr;
    return fault;
  endfunction

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      gpio_out_q <= '0;
      gpio_dir_q <= '0;
      gpio_meta_q <= '0;
      gpio_in_q <= '0;
      gpio_prev_q <= '0;
      status_leds_q <= 8'd0;
      debug_status_select_q <= 8'd0;
      gpio_changed_q <= 1'b0;
      rsp_valid <= 1'b0;
      rsp_rdata <= '0;
      rsp_fault <= '0;
    end else begin
      automatic addr_t offset;
      offset = register_offset(req_addr);

      rsp_valid <= 1'b0;
      rsp_rdata <= '0;
      rsp_fault <= '0;

      gpio_meta_q <= board_gpio_i;
      gpio_in_q <= gpio_meta_q;
      gpio_prev_q <= gpio_in_q;
      if (gpio_in_q != gpio_prev_q) begin
        gpio_changed_q <= 1'b1;
      end

      if (req_valid && req_ready) begin
        if (!register_address(req_addr)) begin
          if (!req_write) begin
            rsp_valid <= 1'b1;
            rsp_fault <= access_fault(req_addr);
          end
        end else if (req_write) begin
          unique case (offset)
            GPIO_OUT_OFFSET: begin
              gpio_out_q <= req_wdata[GPIO_WIDTH-1:0];
            end
            GPIO_DIR_OFFSET: begin
              gpio_dir_q <= req_wdata[GPIO_WIDTH-1:0];
            end
            STATUS_LEDS_OFFSET: begin
              status_leds_q <= req_wdata[7:0];
            end
            DEBUG_STATUS_SELECT_OFFSET: begin
              debug_status_select_q <= req_wdata[7:0];
            end
            default: begin
            end
          endcase
        end else begin
          rsp_valid <= 1'b1;
          unique case (offset)
            GPIO_OUT_OFFSET: begin
              rsp_rdata <= cell_t'(gpio_out_q);
            end
            GPIO_IN_OFFSET: begin
              rsp_rdata <= cell_t'(gpio_in_q);
              gpio_changed_q <= 1'b0;
            end
            GPIO_DIR_OFFSET: begin
              rsp_rdata <= cell_t'(gpio_dir_q);
            end
            STATUS_LEDS_OFFSET: begin
              rsp_rdata <= {16'd0, status_leds_q};
            end
            DEBUG_STATUS_SELECT_OFFSET: begin
              rsp_rdata <= {16'd0, debug_status_select_q};
            end
            default: begin
              rsp_fault <= access_fault(req_addr);
            end
          endcase
        end
      end
    end
  end
endmodule
