module cpu_v01_fpga_uart_mmio #(
  parameter cpu_v01_pkg::addr_t BASE_CELL = 48'h0000_00F0_0000,
  parameter int CLOCK_HZ = 25_000_000,
  parameter int BAUD = 115_200,
  parameter int TX_FIFO_DEPTH = 4,
  parameter int RX_FIFO_DEPTH = 4
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

  input  logic uart_rx_i,
  output logic uart_tx_o,
  output logic irq_rx_ready_o,
  output logic irq_tx_ready_o
);
  import cpu_v01_pkg::*;

  localparam cpu_v01_pkg::addr_t UART_TXDATA_OFFSET = 48'd0;
  localparam cpu_v01_pkg::addr_t UART_RXDATA_OFFSET = 48'd1;
  localparam cpu_v01_pkg::addr_t UART_STATUS_OFFSET = 48'd2;
  localparam cpu_v01_pkg::addr_t UART_CONTROL_OFFSET = 48'd3;
  localparam cpu_v01_pkg::addr_t UART_BAUD_DIV_OFFSET = 48'd4;
  localparam cpu_v01_pkg::addr_t UART_REGISTER_CELLS = 48'd5;

  localparam logic [7:0] STATUS_TX_READY = 8'h01;
  localparam logic [7:0] STATUS_TX_EMPTY = 8'h02;
  localparam logic [7:0] STATUS_RX_VALID = 8'h04;
  localparam logic [7:0] STATUS_RX_OVERRUN = 8'h08;
  localparam logic [7:0] STATUS_FRAME_ERROR = 8'h10;
  localparam logic [7:0] STATUS_TX_IRQ_PENDING = 8'h20;
  localparam logic [7:0] STATUS_RX_IRQ_PENDING = 8'h40;
  localparam logic [7:0] STATUS_TX_OVERRUN = 8'h80;

  localparam int CONTROL_TX_IRQ_ENABLE_BIT = 0;
  localparam int CONTROL_RX_IRQ_ENABLE_BIT = 1;
  localparam int CONTROL_CLEAR_ERRORS_BIT = 2;

  localparam int DEFAULT_BAUD_DIVISOR = (CLOCK_HZ + (BAUD / 2)) / BAUD;
  localparam int EFFECTIVE_BAUD_DIVISOR =
      (DEFAULT_BAUD_DIVISOR < 1) ? 1 : DEFAULT_BAUD_DIVISOR;
  localparam int TX_COUNT_BITS = (TX_FIFO_DEPTH < 2) ? 1 : $clog2(TX_FIFO_DEPTH + 1);
  localparam int TX_PTR_BITS = (TX_FIFO_DEPTH < 2) ? 1 : $clog2(TX_FIFO_DEPTH);
  localparam int RX_COUNT_BITS = (RX_FIFO_DEPTH < 2) ? 1 : $clog2(RX_FIFO_DEPTH + 1);
  localparam int RX_PTR_BITS = (RX_FIFO_DEPTH < 2) ? 1 : $clog2(RX_FIFO_DEPTH);

  logic [7:0] tx_fifo_q [TX_FIFO_DEPTH];
  logic [7:0] rx_fifo_q [RX_FIFO_DEPTH];
  logic [TX_COUNT_BITS-1:0] tx_count_q;
  logic [TX_PTR_BITS-1:0] tx_rd_ptr_q;
  logic [TX_PTR_BITS-1:0] tx_wr_ptr_q;
  logic [RX_COUNT_BITS-1:0] rx_count_q;
  logic [RX_PTR_BITS-1:0] rx_rd_ptr_q;
  logic [RX_PTR_BITS-1:0] rx_wr_ptr_q;

  logic [7:0] control_q;
  logic [23:0] baud_div_q;
  logic rx_overrun_q;
  logic frame_error_q;
  logic tx_overrun_q;

  logic tx_busy_q;
  logic [9:0] tx_shift_q;
  logic [3:0] tx_bit_count_q;
  logic [23:0] tx_baud_count_q;

  logic uart_rx_meta_q;
  logic uart_rx_sync_q;
  logic rx_busy_q;
  logic [7:0] rx_shift_q;
  logic [3:0] rx_bit_index_q;
  logic [23:0] rx_baud_count_q;

  assign req_ready = 1'b1;
  assign uart_tx_o = !tx_busy_q ? 1'b1 : tx_shift_q[0];
  assign irq_rx_ready_o = control_q[CONTROL_RX_IRQ_ENABLE_BIT] && (rx_count_q != '0);
  assign irq_tx_ready_o = control_q[CONTROL_TX_IRQ_ENABLE_BIT] && (tx_count_q < TX_COUNT_BITS'(TX_FIFO_DEPTH));

  function automatic logic [TX_PTR_BITS-1:0] tx_ptr_next(input logic [TX_PTR_BITS-1:0] ptr);
    if (int'(ptr) == TX_FIFO_DEPTH - 1) begin
      return '0;
    end
    return ptr + TX_PTR_BITS'(1);
  endfunction

  function automatic logic [RX_PTR_BITS-1:0] rx_ptr_next(input logic [RX_PTR_BITS-1:0] ptr);
    if (int'(ptr) == RX_FIFO_DEPTH - 1) begin
      return '0;
    end
    return ptr + RX_PTR_BITS'(1);
  endfunction

  function automatic logic register_address(input addr_t addr);
    return addr >= BASE_CELL && addr < BASE_CELL + UART_REGISTER_CELLS;
  endfunction

  function automatic addr_t register_offset(input addr_t addr);
    return addr - BASE_CELL;
  endfunction

  function automatic logic [23:0] baud_reload();
    if (baud_div_q <= 24'd1) begin
      return 24'd0;
    end
    return baud_div_q - 24'd1;
  endfunction

  function automatic logic [23:0] rx_start_reload();
    logic [24:0] start_count;
    start_count = {1'b0, baud_div_q} + ({1'b0, baud_div_q} >> 1);
    if (start_count <= 25'd1) begin
      return 24'd0;
    end
    return start_count[23:0] - 24'd1;
  endfunction

  function automatic cell_t status_cell(
      input logic [TX_COUNT_BITS-1:0] tx_count,
      input logic tx_busy,
      input logic [RX_COUNT_BITS-1:0] rx_count
  );
    cell_t status;
    status = '0;
    if (tx_count < TX_COUNT_BITS'(TX_FIFO_DEPTH)) begin
      status[7:0] = status[7:0] | STATUS_TX_READY;
    end
    if (tx_count == '0 && !tx_busy) begin
      status[7:0] = status[7:0] | STATUS_TX_EMPTY;
    end
    if (rx_count != '0) begin
      status[7:0] = status[7:0] | STATUS_RX_VALID;
    end
    if (rx_overrun_q) begin
      status[7:0] = status[7:0] | STATUS_RX_OVERRUN;
    end
    if (frame_error_q) begin
      status[7:0] = status[7:0] | STATUS_FRAME_ERROR;
    end
    if (control_q[CONTROL_TX_IRQ_ENABLE_BIT] && (tx_count < TX_COUNT_BITS'(TX_FIFO_DEPTH))) begin
      status[7:0] = status[7:0] | STATUS_TX_IRQ_PENDING;
    end
    if (control_q[CONTROL_RX_IRQ_ENABLE_BIT] && (rx_count != '0)) begin
      status[7:0] = status[7:0] | STATUS_RX_IRQ_PENDING;
    end
    if (tx_overrun_q) begin
      status[7:0] = status[7:0] | STATUS_TX_OVERRUN;
    end
    return status;
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
      tx_count_q <= '0;
      tx_rd_ptr_q <= '0;
      tx_wr_ptr_q <= '0;
      rx_count_q <= '0;
      rx_rd_ptr_q <= '0;
      rx_wr_ptr_q <= '0;
      control_q <= 8'd0;
      baud_div_q <= 24'(EFFECTIVE_BAUD_DIVISOR);
      rx_overrun_q <= 1'b0;
      frame_error_q <= 1'b0;
      tx_overrun_q <= 1'b0;
      tx_busy_q <= 1'b0;
      tx_shift_q <= 10'h3FF;
      tx_bit_count_q <= 4'd0;
      tx_baud_count_q <= 24'd0;
      uart_rx_meta_q <= 1'b1;
      uart_rx_sync_q <= 1'b1;
      rx_busy_q <= 1'b0;
      rx_shift_q <= 8'd0;
      rx_bit_index_q <= 4'd0;
      rx_baud_count_q <= 24'd0;
      rsp_valid <= 1'b0;
      rsp_rdata <= '0;
      rsp_fault <= '0;
      for (int i = 0; i < TX_FIFO_DEPTH; i++) begin
        tx_fifo_q[i] <= 8'd0;
      end
      for (int i = 0; i < RX_FIFO_DEPTH; i++) begin
        rx_fifo_q[i] <= 8'd0;
      end
    end else begin
      automatic logic [TX_COUNT_BITS-1:0] tx_count_next;
      automatic logic [RX_COUNT_BITS-1:0] rx_count_next;
      automatic addr_t offset;
      tx_count_next = tx_count_q;
      rx_count_next = rx_count_q;
      offset = register_offset(req_addr);

      rsp_valid <= 1'b0;
      rsp_rdata <= '0;
      rsp_fault <= '0;
      uart_rx_meta_q <= uart_rx_i;
      uart_rx_sync_q <= uart_rx_meta_q;

      if (tx_busy_q) begin
        if (tx_baud_count_q != 24'd0) begin
          tx_baud_count_q <= tx_baud_count_q - 24'd1;
        end else if (tx_bit_count_q == 4'd9) begin
          tx_busy_q <= 1'b0;
          tx_shift_q <= 10'h3FF;
        end else begin
          tx_shift_q <= {1'b1, tx_shift_q[9:1]};
          tx_bit_count_q <= tx_bit_count_q + 4'd1;
          tx_baud_count_q <= baud_reload();
        end
      end else if (tx_count_q != '0) begin
        tx_shift_q <= {1'b1, tx_fifo_q[tx_rd_ptr_q], 1'b0};
        tx_rd_ptr_q <= tx_ptr_next(tx_rd_ptr_q);
        tx_count_next = tx_count_next - TX_COUNT_BITS'(1);
        tx_busy_q <= 1'b1;
        tx_bit_count_q <= 4'd0;
        tx_baud_count_q <= baud_reload();
      end

      if (req_valid && req_ready) begin
        if (!register_address(req_addr)) begin
          if (!req_write) begin
            rsp_valid <= 1'b1;
            rsp_fault <= access_fault(req_addr);
          end
        end else if (req_write) begin
          unique case (offset)
            UART_TXDATA_OFFSET: begin
              if (tx_count_next < TX_COUNT_BITS'(TX_FIFO_DEPTH)) begin
                tx_fifo_q[tx_wr_ptr_q] <= req_wdata[7:0];
                tx_wr_ptr_q <= tx_ptr_next(tx_wr_ptr_q);
                tx_count_next = tx_count_next + TX_COUNT_BITS'(1);
              end else begin
                tx_overrun_q <= 1'b1;
              end
            end
            UART_CONTROL_OFFSET: begin
              if (req_wdata[CONTROL_CLEAR_ERRORS_BIT]) begin
                rx_overrun_q <= 1'b0;
                frame_error_q <= 1'b0;
                tx_overrun_q <= 1'b0;
              end
              control_q <= {6'd0, req_wdata[1:0]};
            end
            UART_BAUD_DIV_OFFSET: begin
              baud_div_q <= (req_wdata == '0) ? 24'd1 : req_wdata;
            end
            default: begin
            end
          endcase
        end else begin
          rsp_valid <= 1'b1;
          unique case (offset)
            UART_RXDATA_OFFSET: begin
              if (rx_count_next != '0) begin
                rsp_rdata <= {16'd0, rx_fifo_q[rx_rd_ptr_q]};
                rx_rd_ptr_q <= rx_ptr_next(rx_rd_ptr_q);
                rx_count_next = rx_count_next - RX_COUNT_BITS'(1);
              end else begin
                rsp_rdata <= '0;
              end
            end
            UART_STATUS_OFFSET: begin
              rsp_rdata <= status_cell(tx_count_next, tx_busy_q, rx_count_next);
            end
            UART_CONTROL_OFFSET: begin
              rsp_rdata <= {16'd0, control_q};
            end
            UART_BAUD_DIV_OFFSET: begin
              rsp_rdata <= cell_t'(baud_div_q);
            end
            default: begin
              rsp_fault <= access_fault(req_addr);
              rsp_rdata <= '0;
            end
          endcase
        end
      end

      if (rx_busy_q) begin
        if (rx_baud_count_q != 24'd0) begin
          rx_baud_count_q <= rx_baud_count_q - 24'd1;
        end else if (rx_bit_index_q < 4'd8) begin
          rx_shift_q[rx_bit_index_q[2:0]] <= uart_rx_sync_q;
          rx_bit_index_q <= rx_bit_index_q + 4'd1;
          rx_baud_count_q <= baud_reload();
        end else begin
          rx_busy_q <= 1'b0;
          if (!uart_rx_sync_q) begin
            frame_error_q <= 1'b1;
          end else if (rx_count_next < RX_COUNT_BITS'(RX_FIFO_DEPTH)) begin
            rx_fifo_q[rx_wr_ptr_q] <= rx_shift_q;
            rx_wr_ptr_q <= rx_ptr_next(rx_wr_ptr_q);
            rx_count_next = rx_count_next + RX_COUNT_BITS'(1);
          end else begin
            rx_overrun_q <= 1'b1;
          end
        end
      end else if (!uart_rx_sync_q) begin
        rx_busy_q <= 1'b1;
        rx_shift_q <= 8'd0;
        rx_bit_index_q <= 4'd0;
        rx_baud_count_q <= rx_start_reload();
      end

      tx_count_q <= tx_count_next;
      rx_count_q <= rx_count_next;
    end
  end
endmodule
