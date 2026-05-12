module cpu_v01_fpga_video_timing_tb;
  localparam int H_ACTIVE = 1280;
  localparam int H_FRONT = 110;
  localparam int H_SYNC = 40;
  localparam int H_BACK = 220;
  localparam int V_ACTIVE = 720;
  localparam int V_FRONT = 5;
  localparam int V_SYNC = 5;
  localparam int V_BACK = 20;
  localparam int H_TOTAL = H_ACTIVE + H_FRONT + H_SYNC + H_BACK;
  localparam int V_TOTAL = V_ACTIVE + V_FRONT + V_SYNC + V_BACK;
  localparam int FRAME_PIXELS = H_TOTAL * V_TOTAL;

  logic pixel_clk;
  logic rst_n;
  logic enable_i;
  logic [3:0] pattern_select_i;
  logic [23:0] bg_color_i;
  logic [11:0] pixel_x_o;
  logic [11:0] pixel_y_o;
  logic hsync_o;
  logic vsync_o;
  logic de_o;
  logic vblank_o;
  logic frame_start_o;
  logic line_start_o;
  logic [23:0] rgb_o;
  logic [47:0] frame_count_o;

  cpu_v01_fpga_video_timing dut (
    .pixel_clk(pixel_clk),
    .rst_n(rst_n),
    .enable_i(enable_i),
    .pattern_select_i(pattern_select_i),
    .bg_color_i(bg_color_i),
    .pixel_x_o(pixel_x_o),
    .pixel_y_o(pixel_y_o),
    .hsync_o(hsync_o),
    .vsync_o(vsync_o),
    .de_o(de_o),
    .vblank_o(vblank_o),
    .frame_start_o(frame_start_o),
    .line_start_o(line_start_o),
    .rgb_o(rgb_o),
    .frame_count_o(frame_count_o)
  );

  initial begin
    pixel_clk = 1'b0;
    forever #5 pixel_clk = ~pixel_clk;
  end

  initial begin
    int active_pixels;
    int hsync_pixels;
    int vsync_pixels;
    int vblank_pixels;

    rst_n = 1'b0;
    enable_i = 1'b1;
    pattern_select_i = 4'd1;
    bg_color_i = 24'h123456;
    repeat (3) @(posedge pixel_clk);
    rst_n = 1'b1;
    #1;

    if (!de_o || pixel_x_o != 12'd0 || pixel_y_o != 12'd0) begin
      $fatal(1, "FPGA video timing did not start at active pixel 0,0");
    end
    if (rgb_o != 24'hFF0000) begin
      $fatal(1, "COLOR_BAR first pixel mismatch");
    end

    active_pixels = 0;
    hsync_pixels = 0;
    vsync_pixels = 0;
    vblank_pixels = 0;
    for (int i = 0; i < FRAME_PIXELS; i++) begin
      #1;
      if (de_o) begin
        active_pixels++;
      end
      if (hsync_o) begin
        hsync_pixels++;
      end
      if (vsync_o) begin
        vsync_pixels++;
      end
      if (vblank_o) begin
        vblank_pixels++;
      end
      @(posedge pixel_clk);
    end
    #1;

    if (active_pixels != H_ACTIVE * V_ACTIVE) begin
      $fatal(1, "ACTIVE_PIXELS mismatch");
    end
    if (hsync_pixels != H_SYNC * V_TOTAL) begin
      $fatal(1, "HSYNC_PIXELS mismatch");
    end
    if (vsync_pixels != V_SYNC * H_TOTAL) begin
      $fatal(1, "VSYNC_PIXELS mismatch");
    end
    if (vblank_pixels != (V_TOTAL - V_ACTIVE) * H_TOTAL) begin
      $fatal(1, "VBLANK_PIXELS mismatch");
    end
    if (frame_count_o != 48'd1 || pixel_x_o != 12'd0 || pixel_y_o != 12'd0) begin
      $fatal(1, "FRAME_COUNT did not advance");
    end

    pattern_select_i = 4'd2;
    #1;
    if (rgb_o != 24'h000000) begin
      $fatal(1, "CHECKERBOARD origin mismatch");
    end
    repeat (32) @(posedge pixel_clk);
    #1;
    if (rgb_o != 24'hFFFFFF) begin
      $fatal(1, "CHECKERBOARD did not toggle");
    end

    pattern_select_i = 4'd0;
    #1;
    if (rgb_o != bg_color_i) begin
      $fatal(1, "BACKGROUND pattern did not use bg_color_i");
    end

    $finish;
  end
endmodule
