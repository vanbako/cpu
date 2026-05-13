module cpu_v01_fpga_compositor_pipeline_tb;
  logic clk;
  logic rst_n;
  logic de_i;
  logic [11:0] pixel_x_i;
  logic [11:0] pixel_y_i;
  logic [23:0] background_rgb_i;
  logic plane0_enable_i;
  logic [11:0] plane0_x_i;
  logic [11:0] plane0_y_i;
  logic [11:0] plane0_width_i;
  logic [11:0] plane0_height_i;
  logic [3:0] plane0_z_i;
  logic [7:0] plane0_alpha_i;
  logic plane0_color_key_enable_i;
  logic [23:0] plane0_color_key_rgb_i;
  logic [23:0] plane0_rgb_i;
  logic plane0_valid_i;
  logic plane1_enable_i;
  logic [11:0] plane1_x_i;
  logic [11:0] plane1_y_i;
  logic [11:0] plane1_width_i;
  logic [11:0] plane1_height_i;
  logic [3:0] plane1_z_i;
  logic [7:0] plane1_alpha_i;
  logic plane1_color_key_enable_i;
  logic [23:0] plane1_color_key_rgb_i;
  logic [23:0] plane1_rgb_i;
  logic plane1_valid_i;
  logic [23:0] rgb_o;
  logic de_o;
  logic [1:0] selected_plane_o;
  logic plane0_sample_o;
  logic plane1_sample_o;

  // cpu_v01_fpga_compositor_pipeline dut
  cpu_v01_fpga_compositor_pipeline dut (
    .clk(clk),
    .rst_n(rst_n),
    .de_i(de_i),
    .pixel_x_i(pixel_x_i),
    .pixel_y_i(pixel_y_i),
    .background_rgb_i(background_rgb_i),
    .plane0_enable_i(plane0_enable_i),
    .plane0_x_i(plane0_x_i),
    .plane0_y_i(plane0_y_i),
    .plane0_width_i(plane0_width_i),
    .plane0_height_i(plane0_height_i),
    .plane0_z_i(plane0_z_i),
    .plane0_alpha_i(plane0_alpha_i),
    .plane0_color_key_enable_i(plane0_color_key_enable_i),
    .plane0_color_key_rgb_i(plane0_color_key_rgb_i),
    .plane0_rgb_i(plane0_rgb_i),
    .plane0_valid_i(plane0_valid_i),
    .plane1_enable_i(plane1_enable_i),
    .plane1_x_i(plane1_x_i),
    .plane1_y_i(plane1_y_i),
    .plane1_width_i(plane1_width_i),
    .plane1_height_i(plane1_height_i),
    .plane1_z_i(plane1_z_i),
    .plane1_alpha_i(plane1_alpha_i),
    .plane1_color_key_enable_i(plane1_color_key_enable_i),
    .plane1_color_key_rgb_i(plane1_color_key_rgb_i),
    .plane1_rgb_i(plane1_rgb_i),
    .plane1_valid_i(plane1_valid_i),
    .rgb_o(rgb_o),
    .de_o(de_o),
    .selected_plane_o(selected_plane_o),
    .plane0_sample_o(plane0_sample_o),
    .plane1_sample_o(plane1_sample_o)
  );

  initial begin
    clk = 1'b0;
    forever #5 clk = ~clk;
  end

  task automatic reset_inputs();
    de_i = 1'b0;
    pixel_x_i = 12'd0;
    pixel_y_i = 12'd0;
    background_rgb_i = 24'h102030;
    plane0_enable_i = 1'b1;
    plane0_x_i = 12'd0;
    plane0_y_i = 12'd0;
    plane0_width_i = 12'd4;
    plane0_height_i = 12'd4;
    plane0_z_i = 4'd0;
    plane0_alpha_i = 8'hFF;
    plane0_color_key_enable_i = 1'b0;
    plane0_color_key_rgb_i = 24'h000000;
    plane0_rgb_i = 24'hFF0000;
    plane0_valid_i = 1'b1;
    plane1_enable_i = 1'b1;
    plane1_x_i = 12'd2;
    plane1_y_i = 12'd0;
    plane1_width_i = 12'd4;
    plane1_height_i = 12'd4;
    plane1_z_i = 4'd1;
    plane1_alpha_i = 8'd128;
    plane1_color_key_enable_i = 1'b0;
    plane1_color_key_rgb_i = 24'h00FF00;
    plane1_rgb_i = 24'h0000FF;
    plane1_valid_i = 1'b1;
  endtask

  task automatic sample_pixel(input logic [11:0] x, input logic [11:0] y);
    pixel_x_i = x;
    pixel_y_i = y;
    de_i = 1'b1;
    @(posedge clk);
    #1;
  endtask

  initial begin
    reset_inputs();
    rst_n = 1'b0;
    repeat (3) @(posedge clk);
    rst_n = 1'b1;
    repeat (2) @(posedge clk);

    sample_pixel(12'd1, 12'd1);
    if (rgb_o != 24'hFF0000 || selected_plane_o != 2'd1 || !plane0_sample_o || plane1_sample_o) begin
      $fatal(1, "compositor pipeline did not select plane0");
    end

    sample_pixel(12'd2, 12'd1);
    if (rgb_o != 24'h7F0080 || selected_plane_o != 2'd2 || !plane0_sample_o || !plane1_sample_o) begin
      $fatal(1, "compositor pipeline did not alpha blend plane1");
    end

    plane1_alpha_i = 8'hFF;
    plane1_color_key_enable_i = 1'b1;
    plane1_rgb_i = 24'h00FF00;
    sample_pixel(12'd2, 12'd1);
    if (rgb_o != 24'hFF0000 || selected_plane_o != 2'd1) begin
      $fatal(1, "compositor pipeline did not honor color key");
    end

    sample_pixel(12'd7, 12'd7);
    if (rgb_o != background_rgb_i || plane0_sample_o || plane1_sample_o) begin
      $fatal(1, "compositor pipeline sampled clipped planes");
    end

    $finish;
  end

  // verilator lint_off UNUSEDSIGNAL
  wire logic unused_de = de_o;
  // verilator lint_on UNUSEDSIGNAL
endmodule
