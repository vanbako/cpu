module cpu_v01_fpga_compositor_descriptor_latch_tb;
  logic clk;
  logic rst_n;
  logic vblank_i;
  logic cfg_write_i;
  logic cfg_plane_i;
  logic [2:0] cfg_field_i;
  logic [47:0] cfg_wdata_i;
  logic descriptor_pending_o;
  logic descriptor_applied_pulse_o;
  logic [15:0] applied_count_o;
  logic active_plane0_enable_o;
  logic [47:0] active_plane0_base_o;
  logic [15:0] active_plane0_stride_o;
  logic [11:0] active_plane0_x_o;
  logic [11:0] active_plane0_y_o;
  logic [11:0] active_plane0_width_o;
  logic [11:0] active_plane0_height_o;
  logic [3:0] active_plane0_format_o;
  logic [3:0] active_plane0_z_o;
  logic [7:0] active_plane0_alpha_o;
  logic active_plane0_color_key_enable_o;
  logic [23:0] active_plane0_color_key_rgb_o;
  logic active_plane1_enable_o;
  logic [47:0] active_plane1_base_o;
  logic [15:0] active_plane1_stride_o;
  logic [11:0] active_plane1_x_o;
  logic [11:0] active_plane1_y_o;
  logic [11:0] active_plane1_width_o;
  logic [11:0] active_plane1_height_o;
  logic [3:0] active_plane1_format_o;
  logic [3:0] active_plane1_z_o;
  logic [7:0] active_plane1_alpha_o;
  logic active_plane1_color_key_enable_o;
  logic [23:0] active_plane1_color_key_rgb_o;

  // cpu_v01_fpga_compositor_descriptor_latch dut
  cpu_v01_fpga_compositor_descriptor_latch dut (
    .clk(clk),
    .rst_n(rst_n),
    .vblank_i(vblank_i),
    .cfg_write_i(cfg_write_i),
    .cfg_plane_i(cfg_plane_i),
    .cfg_field_i(cfg_field_i),
    .cfg_wdata_i(cfg_wdata_i),
    .descriptor_pending_o(descriptor_pending_o),
    .descriptor_applied_pulse_o(descriptor_applied_pulse_o),
    .applied_count_o(applied_count_o),
    .active_plane0_enable_o(active_plane0_enable_o),
    .active_plane0_base_o(active_plane0_base_o),
    .active_plane0_stride_o(active_plane0_stride_o),
    .active_plane0_x_o(active_plane0_x_o),
    .active_plane0_y_o(active_plane0_y_o),
    .active_plane0_width_o(active_plane0_width_o),
    .active_plane0_height_o(active_plane0_height_o),
    .active_plane0_format_o(active_plane0_format_o),
    .active_plane0_z_o(active_plane0_z_o),
    .active_plane0_alpha_o(active_plane0_alpha_o),
    .active_plane0_color_key_enable_o(active_plane0_color_key_enable_o),
    .active_plane0_color_key_rgb_o(active_plane0_color_key_rgb_o),
    .active_plane1_enable_o(active_plane1_enable_o),
    .active_plane1_base_o(active_plane1_base_o),
    .active_plane1_stride_o(active_plane1_stride_o),
    .active_plane1_x_o(active_plane1_x_o),
    .active_plane1_y_o(active_plane1_y_o),
    .active_plane1_width_o(active_plane1_width_o),
    .active_plane1_height_o(active_plane1_height_o),
    .active_plane1_format_o(active_plane1_format_o),
    .active_plane1_z_o(active_plane1_z_o),
    .active_plane1_alpha_o(active_plane1_alpha_o),
    .active_plane1_color_key_enable_o(active_plane1_color_key_enable_o),
    .active_plane1_color_key_rgb_o(active_plane1_color_key_rgb_o)
  );

  initial begin
    clk = 1'b0;
    forever #5 clk = ~clk;
  end

  task automatic clear_cfg();
    cfg_write_i = 1'b0;
    cfg_plane_i = 1'b0;
    cfg_field_i = 3'd0;
    cfg_wdata_i = 48'd0;
  endtask

  task automatic write_field(input logic plane, input logic [2:0] field, input logic [47:0] data);
    cfg_plane_i = plane;
    cfg_field_i = field;
    cfg_wdata_i = data;
    cfg_write_i = 1'b1;
    @(posedge clk);
    #1;
    clear_cfg();
  endtask

  initial begin
    clear_cfg();
    vblank_i = 1'b0;
    rst_n = 1'b0;
    repeat (3) @(posedge clk);
    rst_n = 1'b1;
    repeat (2) @(posedge clk);

    write_field(1'b0, 3'd1, 48'h0000_0110_0000);
    write_field(1'b0, 3'd2, 48'd16);
    write_field(1'b0, 3'd3, 48'h0000_000A_0014);
    write_field(1'b0, 3'd4, 48'h0000_0080_0040);
    write_field(1'b0, 3'd5, 48'h0000_00FF_0100);
    write_field(1'b0, 3'd6, 48'h0000_0000_FF00);
    write_field(1'b0, 3'd0, 48'h3);

    if (!descriptor_pending_o) begin
      $fatal(1, "descriptor latch did not expose pending status");
    end
    if (active_plane0_base_o != 48'd0 || active_plane0_enable_o) begin
      $fatal(1, "descriptor latch active base changed before vblank");
    end

    vblank_i = 1'b1;
    @(posedge clk);
    #1;
    if (!descriptor_applied_pulse_o || descriptor_pending_o || applied_count_o != 16'd1) begin
      $fatal(1, "descriptor latch did not apply on vblank");
    end
    if (!active_plane0_enable_o || active_plane0_base_o != 48'h0000_0110_0000) begin
      $fatal(1, "descriptor latch active descriptor mismatch");
    end
    if (active_plane0_x_o != 12'h014 || active_plane0_y_o != 12'h00A) begin
      $fatal(1, "descriptor latch position mismatch");
    end
    if (active_plane0_width_o != 12'h040 || active_plane0_height_o != 12'h080) begin
      $fatal(1, "descriptor latch size mismatch");
    end
    if (active_plane0_format_o != 4'd0 || active_plane0_z_o != 4'd1 || active_plane0_alpha_o != 8'hFF) begin
      $fatal(1, "descriptor latch format/z/alpha mismatch");
    end
    if (!active_plane0_color_key_enable_o || active_plane0_color_key_rgb_o != 24'h00FF00) begin
      $fatal(1, "descriptor latch color key mismatch");
    end

    $finish;
  end

  // verilator lint_off UNUSEDSIGNAL
  wire logic unused_plane1 = &{
    active_plane1_enable_o,
    active_plane1_base_o[0],
    active_plane1_stride_o[0],
    active_plane1_x_o[0],
    active_plane1_y_o[0],
    active_plane1_width_o[0],
    active_plane1_height_o[0],
    active_plane1_format_o[0],
    active_plane1_z_o[0],
    active_plane1_alpha_o[0],
    active_plane1_color_key_enable_o,
    active_plane1_color_key_rgb_o[0]
  };
  // verilator lint_on UNUSEDSIGNAL
endmodule
