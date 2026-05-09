module cpu_v01_fpga_timer_mmio #(
  parameter cpu_v01_pkg::addr_t BASE_CELL = 48'h0000_00F0_0100
) (
  input  logic clk,
  input  logic rst_n,

  input  logic req_valid,
  output logic req_ready,
  input  logic req_write,
  input  cpu_v01_pkg::addr_t req_addr,
  input  logic [2:0] req_len_cells,
  input  cpu_v01_pkg::cell_t req_wdata [cpu_v01_pkg::INTEGER_OBJECT_CELLS],

  output logic rsp_valid,
  output cpu_v01_pkg::cell_t rsp_rdata [cpu_v01_pkg::INTEGER_OBJECT_CELLS],
  output cpu_v01_pkg::fault_packet_t rsp_fault,

  output logic timer_interrupt_o,
  output logic timer_pending_o
);
  import cpu_v01_pkg::*;

  localparam cpu_v01_pkg::addr_t TIMER_VALUE_OFFSET = 48'd0;
  localparam cpu_v01_pkg::addr_t TIMER_COMPARE_OFFSET = 48'd1;
  localparam cpu_v01_pkg::addr_t TIMER_CONTROL_OFFSET = 48'd2;
  localparam cpu_v01_pkg::addr_t TIMER_STATUS_OFFSET = 48'd3;
  localparam cpu_v01_pkg::addr_t TIMER_REGISTER_CELLS = 48'd4;

  localparam logic [3:0] CONTROL_ENABLE = 4'h1;
  localparam logic [3:0] CONTROL_IRQ_ENABLE = 4'h2;
  localparam logic [3:0] CONTROL_ONESHOT = 4'h4;
  localparam logic [3:0] CONTROL_CLEAR_VALUE = 4'h8;
  localparam int CONTROL_ENABLE_BIT = 0;
  localparam int CONTROL_IRQ_ENABLE_BIT = 1;
  localparam int CONTROL_ONESHOT_BIT = 2;
  localparam int CONTROL_CLEAR_VALUE_BIT = 3;

  localparam logic [3:0] STATUS_PENDING = 4'h1;
  localparam logic [3:0] STATUS_OVERFLOW = 4'h2;
  localparam int STATUS_PENDING_BIT = 0;
  localparam int STATUS_OVERFLOW_BIT = 1;

  logic [47:0] timer_value_q;
  logic [47:0] timer_compare_q;
  logic [3:0] control_q;
  logic [3:0] status_q;

  assign req_ready = 1'b1;
  assign timer_pending_o = status_q[STATUS_PENDING_BIT];
  assign timer_interrupt_o = control_q[CONTROL_IRQ_ENABLE_BIT] && status_q[STATUS_PENDING_BIT];

  function automatic logic register_address(input addr_t addr);
    return addr >= BASE_CELL && addr < BASE_CELL + TIMER_REGISTER_CELLS;
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

  function automatic logic [47:0] unpack_timer_value(
      input cell_t low_cell,
      input cell_t high_cell
  );
    return {high_cell, low_cell};
  endfunction

  task automatic pack_timer_value(
      input logic [47:0] value,
      output cell_t cells [INTEGER_OBJECT_CELLS]
  );
    cells[0] = value[23:0];
    cells[1] = value[47:24];
  endtask

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      timer_value_q <= 48'd0;
      timer_compare_q <= 48'd0;
      control_q <= 4'd0;
      status_q <= 4'd0;
      rsp_valid <= 1'b0;
      rsp_fault <= '0;
      for (int i = 0; i < INTEGER_OBJECT_CELLS; i++) begin
        rsp_rdata[i] <= '0;
      end
    end else begin
      automatic addr_t offset;
      offset = register_offset(req_addr);

      rsp_valid <= 1'b0;
      rsp_fault <= '0;
      for (int i = 0; i < INTEGER_OBJECT_CELLS; i++) begin
        rsp_rdata[i] <= '0;
      end

      if (control_q[CONTROL_ENABLE_BIT]) begin
        timer_value_q <= timer_value_q + 48'd1;
        if (timer_value_q == 48'hFFFF_FFFF_FFFF) begin
          status_q[STATUS_OVERFLOW_BIT] <= 1'b1;
        end
        if (timer_value_q + 48'd1 >= timer_compare_q) begin
          status_q[STATUS_PENDING_BIT] <= 1'b1;
          if (control_q[CONTROL_ONESHOT_BIT]) begin
            control_q[CONTROL_ENABLE_BIT] <= 1'b0;
          end
        end
      end

      if (req_valid && req_ready) begin
        if (!register_address(req_addr)) begin
          if (!req_write) begin
            rsp_valid <= 1'b1;
            rsp_fault <= access_fault(req_addr);
          end
        end else if (req_write) begin
          unique case (offset)
            TIMER_COMPARE_OFFSET: begin
              if (req_len_cells >= 3'd2) begin
                timer_compare_q <= unpack_timer_value(req_wdata[0], req_wdata[1]);
              end
            end
            TIMER_CONTROL_OFFSET: begin
              if (req_wdata[0][CONTROL_CLEAR_VALUE_BIT]) begin
                timer_value_q <= 48'd0;
                status_q <= 4'd0;
              end
              control_q <= {1'b0, req_wdata[0][2:0]};
            end
            TIMER_STATUS_OFFSET: begin
              status_q <= status_q & ~req_wdata[0][3:0];
            end
            default: begin
            end
          endcase
        end else begin
          rsp_valid <= 1'b1;
          unique case (offset)
            TIMER_VALUE_OFFSET: begin
              pack_timer_value(timer_value_q, rsp_rdata);
            end
            TIMER_COMPARE_OFFSET: begin
              pack_timer_value(timer_compare_q, rsp_rdata);
            end
            TIMER_CONTROL_OFFSET: begin
              rsp_rdata[0] <= {20'd0, control_q};
            end
            TIMER_STATUS_OFFSET: begin
              rsp_rdata[0] <= {20'd0, status_q};
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
