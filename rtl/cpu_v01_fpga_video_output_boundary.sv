module cpu_v01_fpga_video_output_boundary #(
  parameter int RESET_SYNC_STAGES = 2
) (
  input  logic pixel_clk_i,
  input  logic pixel_reset_n_i,
  input  logic scanout_enable_async_i,
  input  logic output_enable_async_i,
  input  logic [3:0] pattern_select_i,
  input  logic [23:0] bg_color_i,

  output logic [23:0] video_rgb_o,
  output logic video_hsync_o,
  output logic video_vsync_o,
  output logic video_de_o,
  output logic video_vblank_o,
  output logic video_pixel_clk_o,
  output logic video_output_enable_o,
  output logic [47:0] video_frame_count_o
);
  logic [RESET_SYNC_STAGES-1:0] pixel_reset_sync_q;
  logic [1:0] scanout_enable_sync_q;
  logic [1:0] output_enable_sync_q;
  logic pixel_rst_n;

  logic [11:0] timing_pixel_x;
  logic [11:0] timing_pixel_y;
  logic timing_hsync;
  logic timing_vsync;
  logic timing_de;
  logic timing_vblank;
  logic timing_frame_start;
  logic timing_line_start;
  logic [23:0] timing_rgb;
  logic [47:0] timing_frame_count;

  assign pixel_rst_n = pixel_reset_sync_q[RESET_SYNC_STAGES-1];
  assign video_pixel_clk_o = pixel_clk_i;
  assign video_output_enable_o = output_enable_sync_q[1];

  always_ff @(posedge pixel_clk_i or negedge pixel_reset_n_i) begin
    if (!pixel_reset_n_i) begin
      pixel_reset_sync_q <= '0;
    end else begin
      pixel_reset_sync_q <= {pixel_reset_sync_q[RESET_SYNC_STAGES-2:0], 1'b1};
    end
  end

  always_ff @(posedge pixel_clk_i or negedge pixel_rst_n) begin
    if (!pixel_rst_n) begin
      scanout_enable_sync_q <= 2'b00;
      output_enable_sync_q <= 2'b00;
    end else begin
      scanout_enable_sync_q <= {scanout_enable_sync_q[0], scanout_enable_async_i};
      output_enable_sync_q <= {output_enable_sync_q[0], output_enable_async_i};
    end
  end

  cpu_v01_fpga_video_timing u_timing (
    .pixel_clk(pixel_clk_i),
    .rst_n(pixel_rst_n),
    .enable_i(scanout_enable_sync_q[1]),
    .pattern_select_i(pattern_select_i),
    .bg_color_i(bg_color_i),
    .pixel_x_o(timing_pixel_x),
    .pixel_y_o(timing_pixel_y),
    .hsync_o(timing_hsync),
    .vsync_o(timing_vsync),
    .de_o(timing_de),
    .vblank_o(timing_vblank),
    .frame_start_o(timing_frame_start),
    .line_start_o(timing_line_start),
    .rgb_o(timing_rgb),
    .frame_count_o(timing_frame_count)
  );

  always_ff @(posedge pixel_clk_i or negedge pixel_rst_n) begin
    if (!pixel_rst_n) begin
      video_rgb_o <= 24'h000000;
      video_hsync_o <= 1'b0;
      video_vsync_o <= 1'b0;
      video_de_o <= 1'b0;
      video_vblank_o <= 1'b1;
      video_frame_count_o <= 48'd0;
    end else begin
      if (output_enable_sync_q[1]) begin
        video_rgb_o <= timing_de ? timing_rgb : 24'h000000;
        video_de_o <= timing_de;
      end else begin
        video_rgb_o <= 24'h000000;
        video_de_o <= 1'b0;
      end
      video_hsync_o <= timing_hsync;
      video_vsync_o <= timing_vsync;
      video_vblank_o <= timing_vblank;
      video_frame_count_o <= timing_frame_count;
    end
  end
endmodule
