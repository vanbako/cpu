module cpu_v01_fpga_compositor_pipeline (
  input  logic clk,
  input  logic rst_n,

  input  logic de_i,
  input  logic [11:0] pixel_x_i,
  input  logic [11:0] pixel_y_i,
  input  logic [23:0] background_rgb_i,

  input  logic plane0_enable_i,
  input  logic [11:0] plane0_x_i,
  input  logic [11:0] plane0_y_i,
  input  logic [11:0] plane0_width_i,
  input  logic [11:0] plane0_height_i,
  input  logic [3:0] plane0_z_i,
  input  logic [7:0] plane0_alpha_i,
  input  logic plane0_color_key_enable_i,
  input  logic [23:0] plane0_color_key_rgb_i,
  input  logic [23:0] plane0_rgb_i,
  input  logic plane0_valid_i,

  input  logic plane1_enable_i,
  input  logic [11:0] plane1_x_i,
  input  logic [11:0] plane1_y_i,
  input  logic [11:0] plane1_width_i,
  input  logic [11:0] plane1_height_i,
  input  logic [3:0] plane1_z_i,
  input  logic [7:0] plane1_alpha_i,
  input  logic plane1_color_key_enable_i,
  input  logic [23:0] plane1_color_key_rgb_i,
  input  logic [23:0] plane1_rgb_i,
  input  logic plane1_valid_i,

  output logic [23:0] rgb_o,
  output logic de_o,
  output logic [1:0] selected_plane_o,
  output logic plane0_sample_o,
  output logic plane1_sample_o
);
  localparam logic [1:0] SELECT_BACKGROUND = 2'd0;
  localparam logic [1:0] SELECT_PLANE0 = 2'd1;
  localparam logic [1:0] SELECT_PLANE1 = 2'd2;

  logic plane0_inside;
  logic plane1_inside;
  logic plane0_key_hit;
  logic plane1_key_hit;
  logic plane0_visible;
  logic plane1_visible;
  logic plane1_over_plane0;
  logic [23:0] lower_rgb;
  logic [23:0] composed_rgb;
  logic [1:0] selected_plane;

  assign plane0_inside =
      plane0_enable_i && plane0_valid_i && de_i &&
      pixel_x_i >= plane0_x_i && pixel_x_i < plane0_x_i + plane0_width_i &&
      pixel_y_i >= plane0_y_i && pixel_y_i < plane0_y_i + plane0_height_i;
  assign plane1_inside =
      plane1_enable_i && plane1_valid_i && de_i &&
      pixel_x_i >= plane1_x_i && pixel_x_i < plane1_x_i + plane1_width_i &&
      pixel_y_i >= plane1_y_i && pixel_y_i < plane1_y_i + plane1_height_i;
  assign plane0_key_hit = plane0_color_key_enable_i && plane0_rgb_i == plane0_color_key_rgb_i;
  assign plane1_key_hit = plane1_color_key_enable_i && plane1_rgb_i == plane1_color_key_rgb_i;
  assign plane0_visible = plane0_inside && !plane0_key_hit && plane0_alpha_i != 8'd0;
  assign plane1_visible = plane1_inside && !plane1_key_hit && plane1_alpha_i != 8'd0;
  assign plane1_over_plane0 = plane1_z_i >= plane0_z_i;

  always_comb begin
    composed_rgb = background_rgb_i;
    selected_plane = SELECT_BACKGROUND;
    lower_rgb = background_rgb_i;

    if (plane0_visible && (!plane1_visible || !plane1_over_plane0)) begin
      composed_rgb = alpha_blend(plane0_rgb_i, background_rgb_i, plane0_alpha_i);
      selected_plane = SELECT_PLANE0;
      if (plane1_visible) begin
        composed_rgb = alpha_blend(plane1_rgb_i, composed_rgb, plane1_alpha_i);
        selected_plane = SELECT_PLANE1;
      end
    end else if (plane1_visible) begin
      lower_rgb = background_rgb_i;
      if (plane0_visible) begin
        lower_rgb = alpha_blend(plane0_rgb_i, background_rgb_i, plane0_alpha_i);
      end
      composed_rgb = alpha_blend(plane1_rgb_i, lower_rgb, plane1_alpha_i);
      selected_plane = SELECT_PLANE1;
    end else if (plane0_visible) begin
      composed_rgb = alpha_blend(plane0_rgb_i, background_rgb_i, plane0_alpha_i);
      selected_plane = SELECT_PLANE0;
    end
  end

  function automatic logic [23:0] alpha_blend(
      input logic [23:0] src,
      input logic [23:0] dst,
      input logic [7:0] alpha
  );
    logic [15:0] red;
    logic [15:0] green;
    logic [15:0] blue;
    begin
      if (alpha == 8'd0) begin
        alpha_blend = dst;
      end else if (alpha == 8'hFF) begin
        alpha_blend = src;
      end else begin
        red = (({8'd0, src[23:16]} * {8'd0, alpha}) +
               ({8'd0, dst[23:16]} * {8'd0, 8'hFF - alpha}) + 16'd127) / 16'd255;
        green = (({8'd0, src[15:8]} * {8'd0, alpha}) +
                 ({8'd0, dst[15:8]} * {8'd0, 8'hFF - alpha}) + 16'd127) / 16'd255;
        blue = (({8'd0, src[7:0]} * {8'd0, alpha}) +
                ({8'd0, dst[7:0]} * {8'd0, 8'hFF - alpha}) + 16'd127) / 16'd255;
        alpha_blend = {red[7:0], green[7:0], blue[7:0]};
      end
    end
  endfunction

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      rgb_o <= 24'h000000;
      de_o <= 1'b0;
      selected_plane_o <= SELECT_BACKGROUND;
      plane0_sample_o <= 1'b0;
      plane1_sample_o <= 1'b0;
    end else begin
      rgb_o <= composed_rgb;
      de_o <= de_i;
      selected_plane_o <= selected_plane;
      plane0_sample_o <= plane0_inside;
      plane1_sample_o <= plane1_inside;
    end
  end
endmodule
