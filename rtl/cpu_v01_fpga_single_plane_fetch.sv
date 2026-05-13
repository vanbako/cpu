module cpu_v01_fpga_single_plane_fetch #(
  parameter int LINE_BUFFER_PIXELS = 1280
) (
  input  logic clk,
  input  logic rst_n,

  input  logic plane_enable_i,
  input  cpu_v01_pkg::addr_t plane_base_cell_i,
  input  logic [15:0] plane_stride_cells_i,
  input  logic [11:0] plane_width_i,
  input  logic [11:0] plane_height_i,
  input  logic [1:0] plane_format_i,
  input  logic [23:0] background_rgb_i,

  input  logic line_start_i,
  input  logic de_i,
  input  logic [11:0] pixel_x_i,
  input  logic [11:0] pixel_y_i,

  output logic video_rd_req_valid_o,
  input  logic video_rd_req_ready_i,
  output cpu_v01_pkg::addr_t video_rd_req_addr_o,
  output logic [7:0] video_rd_req_len_cells_o,
  input  logic video_rd_rsp_valid_i,
  output logic video_rd_rsp_ready_o,
  input  logic [47:0] video_rd_rsp_data_i,
  input  logic video_rd_rsp_error_i,

  output logic [23:0] rgb_o,
  output logic de_o,
  output logic underflow_pulse_o,
  output logic busy_o
);
  import cpu_v01_pkg::*;

  localparam logic [1:0] FORMAT_RGB565 = 2'd0;
  localparam logic [1:0] FORMAT_XRGB8888 = 2'd1;
  localparam int BUFFER_INDEX_BITS = (LINE_BUFFER_PIXELS <= 2) ? 1 : $clog2(LINE_BUFFER_PIXELS);

  logic fetch_active_q;
  logic [11:0] fetch_x_q;
  logic [11:0] fill_x_q;
  logic [11:0] line_y_q;
  logic [1:0] active_format_q;
  addr_t line_base_cell_q;
  logic [23:0] line_rgb_q [LINE_BUFFER_PIXELS];
  logic line_valid_q [LINE_BUFFER_PIXELS];
  logic [BUFFER_INDEX_BITS-1:0] pixel_index;
  logic [BUFFER_INDEX_BITS-1:0] fill_index;
  logic pixel_in_plane;
  logic pixel_in_buffer;
  logic current_pixel_valid;
  logic [23:0] current_pixel_rgb;

  assign pixel_in_plane =
      plane_enable_i && de_i && pixel_x_i < plane_width_i && pixel_y_i < plane_height_i;
  assign pixel_in_buffer = pixel_x_i < LINE_BUFFER_PIXELS[11:0];
  assign pixel_index = pixel_x_i[BUFFER_INDEX_BITS-1:0];
  assign fill_index = fill_x_q[BUFFER_INDEX_BITS-1:0];
  assign current_pixel_valid = pixel_in_plane && pixel_in_buffer && line_valid_q[pixel_index];
  assign current_pixel_rgb =
      current_pixel_valid ? line_rgb_q[pixel_index] : background_rgb_i;

  assign video_rd_req_valid_o = fetch_active_q;
  assign video_rd_req_addr_o = line_base_cell_q + addr_t'(fetch_x_q);
  assign video_rd_req_len_cells_o = 8'd1;
  assign video_rd_rsp_ready_o = 1'b1;
  assign busy_o = fetch_active_q;

  function automatic logic [23:0] rgb565_to_rgb888(input logic [15:0] value);
    logic [4:0] red;
    logic [5:0] green;
    logic [4:0] blue;
    begin
      red = value[15:11];
      green = value[10:5];
      blue = value[4:0];
      rgb565_to_rgb888 = {
        red, red[4:2],
        green, green[5:4],
        blue, blue[4:2]
      };
    end
  endfunction

  function automatic logic [23:0] xrgb8888_to_rgb888(input logic [31:0] value);
    xrgb8888_to_rgb888 = value[23:0];
  endfunction

  function automatic logic [23:0] convert_pixel(
      input logic [1:0] format,
      input logic [47:0] data,
      input logic [23:0] background
  );
    unique case (format)
      FORMAT_RGB565: convert_pixel = rgb565_to_rgb888(data[15:0]);
      FORMAT_XRGB8888: convert_pixel = xrgb8888_to_rgb888(data[31:0]);
      default: convert_pixel = background;
    endcase
  endfunction

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      fetch_active_q <= 1'b0;
      fetch_x_q <= 12'd0;
      fill_x_q <= 12'd0;
      line_y_q <= 12'd0;
      line_base_cell_q <= '0;
      active_format_q <= FORMAT_RGB565;
      rgb_o <= 24'h000000;
      de_o <= 1'b0;
      underflow_pulse_o <= 1'b0;
      for (int i = 0; i < LINE_BUFFER_PIXELS; i++) begin
        line_rgb_q[i] <= 24'h000000;
        line_valid_q[i] <= 1'b0;
      end
    end else begin
      underflow_pulse_o <= 1'b0;
      de_o <= de_i;
      rgb_o <= current_pixel_rgb;

      if (pixel_in_plane && !current_pixel_valid) begin
        underflow_pulse_o <= 1'b1;
      end

      if (line_start_i) begin
        fetch_active_q <= plane_enable_i && pixel_y_i < plane_height_i;
        fetch_x_q <= 12'd0;
        fill_x_q <= 12'd0;
        line_y_q <= pixel_y_i;
        line_base_cell_q <= plane_base_cell_i + (addr_t'(pixel_y_i) * addr_t'(plane_stride_cells_i));
        active_format_q <= plane_format_i;
        for (int i = 0; i < LINE_BUFFER_PIXELS; i++) begin
          line_rgb_q[i] <= 24'h000000;
          line_valid_q[i] <= 1'b0;
        end
      end else begin
        if (video_rd_req_valid_o && video_rd_req_ready_i) begin
          fetch_x_q <= fetch_x_q + 12'd1;
          if (fetch_x_q + 12'd1 >= plane_width_i || fetch_x_q + 12'd1 >= LINE_BUFFER_PIXELS[11:0]) begin
            fetch_active_q <= 1'b0;
          end
        end

        if (video_rd_rsp_valid_i && video_rd_rsp_ready_o && fill_x_q < LINE_BUFFER_PIXELS[11:0]) begin
          line_rgb_q[fill_index] <= convert_pixel(active_format_q, video_rd_rsp_data_i, background_rgb_i);
          line_valid_q[fill_index] <= !video_rd_rsp_error_i;
          if (video_rd_rsp_error_i) begin
            underflow_pulse_o <= 1'b1;
          end
          fill_x_q <= fill_x_q + 12'd1;
        end
      end
    end
  end

  // verilator lint_off UNUSEDSIGNAL
  wire logic [11:0] unused_line_y = line_y_q;
  // verilator lint_on UNUSEDSIGNAL
endmodule
