module cpu_v01_fpga_single_plane_fetch_tb;
  import cpu_v01_pkg::*;

  localparam addr_t PLANE_BASE = 48'h0000_0110_0000;
  localparam logic [15:0] PLANE_STRIDE = 16'd16;

  logic clk;
  logic rst_n;
  logic plane_enable_i;
  addr_t plane_base_cell_i;
  logic [15:0] plane_stride_cells_i;
  logic [11:0] plane_width_i;
  logic [11:0] plane_height_i;
  logic [1:0] plane_format_i;
  logic [23:0] background_rgb_i;
  logic line_start_i;
  logic de_i;
  logic [11:0] pixel_x_i;
  logic [11:0] pixel_y_i;
  logic video_rd_req_valid_o;
  logic video_rd_req_ready_i;
  addr_t video_rd_req_addr_o;
  logic [7:0] video_rd_req_len_cells_o;
  logic video_rd_rsp_valid_i;
  logic video_rd_rsp_ready_o;
  logic [47:0] video_rd_rsp_data_i;
  logic video_rd_rsp_error_i;
  logic [23:0] rgb_o;
  logic de_o;
  logic underflow_pulse_o;
  logic busy_o;

  // cpu_v01_fpga_single_plane_fetch dut
  cpu_v01_fpga_single_plane_fetch #(
    .LINE_BUFFER_PIXELS(8)
  ) dut (
    .clk(clk),
    .rst_n(rst_n),
    .plane_enable_i(plane_enable_i),
    .plane_base_cell_i(plane_base_cell_i),
    .plane_stride_cells_i(plane_stride_cells_i),
    .plane_width_i(plane_width_i),
    .plane_height_i(plane_height_i),
    .plane_format_i(plane_format_i),
    .background_rgb_i(background_rgb_i),
    .line_start_i(line_start_i),
    .de_i(de_i),
    .pixel_x_i(pixel_x_i),
    .pixel_y_i(pixel_y_i),
    .video_rd_req_valid_o(video_rd_req_valid_o),
    .video_rd_req_ready_i(video_rd_req_ready_i),
    .video_rd_req_addr_o(video_rd_req_addr_o),
    .video_rd_req_len_cells_o(video_rd_req_len_cells_o),
    .video_rd_rsp_valid_i(video_rd_rsp_valid_i),
    .video_rd_rsp_ready_o(video_rd_rsp_ready_o),
    .video_rd_rsp_data_i(video_rd_rsp_data_i),
    .video_rd_rsp_error_i(video_rd_rsp_error_i),
    .rgb_o(rgb_o),
    .de_o(de_o),
    .underflow_pulse_o(underflow_pulse_o),
    .busy_o(busy_o)
  );

  initial begin
    clk = 1'b0;
    forever #5 clk = ~clk;
  end

  task automatic clear_inputs();
    plane_enable_i = 1'b1;
    plane_base_cell_i = PLANE_BASE;
    plane_stride_cells_i = PLANE_STRIDE;
    plane_width_i = 12'd4;
    plane_height_i = 12'd4;
    plane_format_i = 2'd0;
    background_rgb_i = 24'h102030;
    line_start_i = 1'b0;
    de_i = 1'b0;
    pixel_x_i = 12'd0;
    pixel_y_i = 12'd0;
    video_rd_req_ready_i = 1'b1;
    video_rd_rsp_valid_i = 1'b0;
    video_rd_rsp_data_i = '0;
    video_rd_rsp_error_i = 1'b0;
  endtask

  task automatic start_line(input logic [11:0] y);
    pixel_y_i = y;
    line_start_i = 1'b1;
    @(posedge clk);
    #1;
    line_start_i = 1'b0;
  endtask

  task automatic respond_pixel(input int x, input logic [47:0] data, input bit error);
    if (!video_rd_req_valid_o || video_rd_req_addr_o != PLANE_BASE + addr_t'(pixel_y_i * PLANE_STRIDE) + addr_t'(x)) begin
      $fatal(1, "single-plane fetch request address mismatch");
    end
    if (video_rd_req_len_cells_o != 8'd1) begin
      $fatal(1, "single-plane fetch request length mismatch");
    end
    video_rd_rsp_data_i = data;
    video_rd_rsp_error_i = error;
    video_rd_rsp_valid_i = 1'b1;
    @(posedge clk);
    #1;
    video_rd_rsp_valid_i = 1'b0;
    video_rd_rsp_error_i = 1'b0;
  endtask

  task automatic check_pixel(input logic [11:0] x, input logic [23:0] expected, input string message);
    pixel_x_i = x;
    de_i = 1'b1;
    @(posedge clk);
    #1;
    if (!de_o || rgb_o != expected) begin
      $fatal(1, "%s", message);
    end
    de_i = 1'b0;
  endtask

  initial begin
    clear_inputs();
    rst_n = 1'b0;
    repeat (3) @(posedge clk);
    rst_n = 1'b1;
    repeat (2) @(posedge clk);

    plane_format_i = 2'd0;
    start_line(12'd0);
    respond_pixel(0, 48'h0000_0000_F800, 1'b0);
    respond_pixel(1, 48'h0000_0000_07E0, 1'b0);
    respond_pixel(2, 48'h0000_0000_001F, 1'b0);
    respond_pixel(3, 48'h0000_0000_FFFF, 1'b0);
    repeat (1) @(posedge clk);
    if (busy_o) begin
      $fatal(1, "single-plane fetch did not finish RGB565 line");
    end
    check_pixel(12'd0, 24'hFF0000, "single-plane fetch RGB565 red mismatch");
    check_pixel(12'd1, 24'h00FF00, "single-plane fetch RGB565 green mismatch");
    check_pixel(12'd2, 24'h0000FF, "single-plane fetch RGB565 blue mismatch");
    check_pixel(12'd3, 24'hFFFFFF, "single-plane fetch RGB565 white mismatch");

    plane_format_i = 2'd1;
    start_line(12'd1);
    respond_pixel(0, 48'h0000_0012_3456, 1'b0);
    respond_pixel(1, 48'h0000_00AB_CDEF, 1'b0);
    respond_pixel(2, 48'h0000_0001_0203, 1'b0);
    respond_pixel(3, 48'h0000_0044_5566, 1'b0);
    check_pixel(12'd1, 24'hABCDEF, "single-plane fetch XRGB8888 conversion mismatch");

    start_line(12'd2);
    pixel_x_i = 12'd0;
    de_i = 1'b1;
    @(posedge clk);
    #1;
    if (!underflow_pulse_o || rgb_o != background_rgb_i) begin
      $fatal(1, "single-plane fetch did not report deterministic underflow");
    end
    de_i = 1'b0;
    respond_pixel(0, 48'h0000_0000_F800, 1'b1);
    if (!underflow_pulse_o) begin
      $fatal(1, "single-plane fetch did not report response error underflow");
    end

    $finish;
  end

  // verilator lint_off UNUSEDSIGNAL
  wire logic unused_video_rd_rsp_ready = video_rd_rsp_ready_o;
  // verilator lint_on UNUSEDSIGNAL
endmodule
