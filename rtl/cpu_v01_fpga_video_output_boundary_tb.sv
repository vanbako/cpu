module cpu_v01_fpga_video_output_boundary_tb;
  logic pixel_clk_i;
  logic pixel_reset_n_i;
  logic scanout_enable_async_i;
  logic output_enable_async_i;
  logic [3:0] pattern_select_i;
  logic [23:0] bg_color_i;

  logic [23:0] video_rgb_o;
  logic video_hsync_o;
  logic video_vsync_o;
  logic video_de_o;
  logic video_vblank_o;
  logic video_pixel_clk_o;
  logic video_output_enable_o;
  logic [47:0] video_frame_count_o;

  cpu_v01_fpga_video_output_boundary dut (
    .pixel_clk_i(pixel_clk_i),
    .pixel_reset_n_i(pixel_reset_n_i),
    .scanout_enable_async_i(scanout_enable_async_i),
    .output_enable_async_i(output_enable_async_i),
    .pattern_select_i(pattern_select_i),
    .bg_color_i(bg_color_i),
    .video_rgb_o(video_rgb_o),
    .video_hsync_o(video_hsync_o),
    .video_vsync_o(video_vsync_o),
    .video_de_o(video_de_o),
    .video_vblank_o(video_vblank_o),
    .video_pixel_clk_o(video_pixel_clk_o),
    .video_output_enable_o(video_output_enable_o),
    .video_frame_count_o(video_frame_count_o)
  );

  initial begin
    pixel_clk_i = 1'b0;
    forever #5 pixel_clk_i = ~pixel_clk_i;
  end

  initial begin
    bit saw_active_video;
    bit saw_hsync;

    pixel_reset_n_i = 1'b0;
    scanout_enable_async_i = 1'b0;
    output_enable_async_i = 1'b0;
    pattern_select_i = 4'd1;
    bg_color_i = 24'h204080;

    repeat (4) @(posedge pixel_clk_i);
    #1;
    if (video_rgb_o != 24'h000000 || video_de_o || !video_vblank_o) begin
      $fatal(1, "VIDEO output reset did not hold outputs blank");
    end
    if (video_pixel_clk_o !== pixel_clk_i) begin
      $fatal(1, "VIDEO output did not expose pixel clock");
    end

    pixel_reset_n_i = 1'b1;
    scanout_enable_async_i = 1'b1;
    output_enable_async_i = 1'b1;
    repeat (6) @(posedge pixel_clk_i);

    saw_active_video = 1'b0;
    for (int i = 0; i < 32; i++) begin
      @(posedge pixel_clk_i);
      #1;
      if (video_de_o && video_rgb_o != 24'h000000) begin
        saw_active_video = 1'b1;
      end
    end
    if (!saw_active_video) begin
      $fatal(1, "VIDEO output did not drive active RGB");
    end

    saw_hsync = 1'b0;
    for (int i = 0; i < 1700; i++) begin
      @(posedge pixel_clk_i);
      #1;
      if (video_hsync_o) begin
        saw_hsync = 1'b1;
      end
    end
    if (!saw_hsync) begin
      $fatal(1, "VIDEO output did not forward hsync");
    end

    output_enable_async_i = 1'b0;
    repeat (4) @(posedge pixel_clk_i);
    #1;
    if (video_rgb_o != 24'h000000 || video_de_o || video_output_enable_o) begin
      $fatal(1, "VIDEO output enable did not blank RGB");
    end

    $finish;
  end
endmodule
