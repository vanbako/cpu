module cpu_v01_fpga_compositor_descriptor_latch (
  input  logic clk,
  input  logic rst_n,
  input  logic vblank_i,

  input  logic cfg_write_i,
  input  logic cfg_plane_i,
  input  logic [2:0] cfg_field_i,
  input  logic [47:0] cfg_wdata_i,

  output logic descriptor_pending_o,
  output logic descriptor_applied_pulse_o,
  output logic [15:0] applied_count_o,

  output logic active_plane0_enable_o,
  output logic [47:0] active_plane0_base_o,
  output logic [15:0] active_plane0_stride_o,
  output logic [11:0] active_plane0_x_o,
  output logic [11:0] active_plane0_y_o,
  output logic [11:0] active_plane0_width_o,
  output logic [11:0] active_plane0_height_o,
  output logic [3:0] active_plane0_format_o,
  output logic [3:0] active_plane0_z_o,
  output logic [7:0] active_plane0_alpha_o,
  output logic active_plane0_color_key_enable_o,
  output logic [23:0] active_plane0_color_key_rgb_o,

  output logic active_plane1_enable_o,
  output logic [47:0] active_plane1_base_o,
  output logic [15:0] active_plane1_stride_o,
  output logic [11:0] active_plane1_x_o,
  output logic [11:0] active_plane1_y_o,
  output logic [11:0] active_plane1_width_o,
  output logic [11:0] active_plane1_height_o,
  output logic [3:0] active_plane1_format_o,
  output logic [3:0] active_plane1_z_o,
  output logic [7:0] active_plane1_alpha_o,
  output logic active_plane1_color_key_enable_o,
  output logic [23:0] active_plane1_color_key_rgb_o
);
  localparam logic [2:0] FIELD_CONTROL = 3'd0;
  localparam logic [2:0] FIELD_BASE = 3'd1;
  localparam logic [2:0] FIELD_STRIDE = 3'd2;
  localparam logic [2:0] FIELD_POSITION = 3'd3;
  localparam logic [2:0] FIELD_SIZE = 3'd4;
  localparam logic [2:0] FIELD_FORMAT_Z_ALPHA = 3'd5;
  localparam logic [2:0] FIELD_COLOR_KEY = 3'd6;

  logic vblank_q;
  logic shadow_plane0_enable_q;
  logic [47:0] shadow_plane0_base_q;
  logic [15:0] shadow_plane0_stride_q;
  logic [11:0] shadow_plane0_x_q;
  logic [11:0] shadow_plane0_y_q;
  logic [11:0] shadow_plane0_width_q;
  logic [11:0] shadow_plane0_height_q;
  logic [3:0] shadow_plane0_format_q;
  logic [3:0] shadow_plane0_z_q;
  logic [7:0] shadow_plane0_alpha_q;
  logic shadow_plane0_color_key_enable_q;
  logic [23:0] shadow_plane0_color_key_rgb_q;

  logic shadow_plane1_enable_q;
  logic [47:0] shadow_plane1_base_q;
  logic [15:0] shadow_plane1_stride_q;
  logic [11:0] shadow_plane1_x_q;
  logic [11:0] shadow_plane1_y_q;
  logic [11:0] shadow_plane1_width_q;
  logic [11:0] shadow_plane1_height_q;
  logic [3:0] shadow_plane1_format_q;
  logic [3:0] shadow_plane1_z_q;
  logic [7:0] shadow_plane1_alpha_q;
  logic shadow_plane1_color_key_enable_q;
  logic [23:0] shadow_plane1_color_key_rgb_q;

  logic active_plane0_enable_q;
  logic [47:0] active_plane0_base_q;
  logic [15:0] active_plane0_stride_q;
  logic [11:0] active_plane0_x_q;
  logic [11:0] active_plane0_y_q;
  logic [11:0] active_plane0_width_q;
  logic [11:0] active_plane0_height_q;
  logic [3:0] active_plane0_format_q;
  logic [3:0] active_plane0_z_q;
  logic [7:0] active_plane0_alpha_q;
  logic active_plane0_color_key_enable_q;
  logic [23:0] active_plane0_color_key_rgb_q;

  logic active_plane1_enable_q;
  logic [47:0] active_plane1_base_q;
  logic [15:0] active_plane1_stride_q;
  logic [11:0] active_plane1_x_q;
  logic [11:0] active_plane1_y_q;
  logic [11:0] active_plane1_width_q;
  logic [11:0] active_plane1_height_q;
  logic [3:0] active_plane1_format_q;
  logic [3:0] active_plane1_z_q;
  logic [7:0] active_plane1_alpha_q;
  logic active_plane1_color_key_enable_q;
  logic [23:0] active_plane1_color_key_rgb_q;

  assign active_plane0_enable_o = active_plane0_enable_q;
  assign active_plane0_base_o = active_plane0_base_q;
  assign active_plane0_stride_o = active_plane0_stride_q;
  assign active_plane0_x_o = active_plane0_x_q;
  assign active_plane0_y_o = active_plane0_y_q;
  assign active_plane0_width_o = active_plane0_width_q;
  assign active_plane0_height_o = active_plane0_height_q;
  assign active_plane0_format_o = active_plane0_format_q;
  assign active_plane0_z_o = active_plane0_z_q;
  assign active_plane0_alpha_o = active_plane0_alpha_q;
  assign active_plane0_color_key_enable_o = active_plane0_color_key_enable_q;
  assign active_plane0_color_key_rgb_o = active_plane0_color_key_rgb_q;
  assign active_plane1_enable_o = active_plane1_enable_q;
  assign active_plane1_base_o = active_plane1_base_q;
  assign active_plane1_stride_o = active_plane1_stride_q;
  assign active_plane1_x_o = active_plane1_x_q;
  assign active_plane1_y_o = active_plane1_y_q;
  assign active_plane1_width_o = active_plane1_width_q;
  assign active_plane1_height_o = active_plane1_height_q;
  assign active_plane1_format_o = active_plane1_format_q;
  assign active_plane1_z_o = active_plane1_z_q;
  assign active_plane1_alpha_o = active_plane1_alpha_q;
  assign active_plane1_color_key_enable_o = active_plane1_color_key_enable_q;
  assign active_plane1_color_key_rgb_o = active_plane1_color_key_rgb_q;

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      vblank_q <= 1'b0;
      descriptor_pending_o <= 1'b0;
      descriptor_applied_pulse_o <= 1'b0;
      applied_count_o <= 16'd0;
      shadow_plane0_enable_q <= 1'b0;
      shadow_plane0_base_q <= 48'd0;
      shadow_plane0_stride_q <= 16'd0;
      shadow_plane0_x_q <= 12'd0;
      shadow_plane0_y_q <= 12'd0;
      shadow_plane0_width_q <= 12'd0;
      shadow_plane0_height_q <= 12'd0;
      shadow_plane0_format_q <= 4'd0;
      shadow_plane0_z_q <= 4'd0;
      shadow_plane0_alpha_q <= 8'hFF;
      shadow_plane0_color_key_enable_q <= 1'b0;
      shadow_plane0_color_key_rgb_q <= 24'd0;
      shadow_plane1_enable_q <= 1'b0;
      shadow_plane1_base_q <= 48'd0;
      shadow_plane1_stride_q <= 16'd0;
      shadow_plane1_x_q <= 12'd0;
      shadow_plane1_y_q <= 12'd0;
      shadow_plane1_width_q <= 12'd0;
      shadow_plane1_height_q <= 12'd0;
      shadow_plane1_format_q <= 4'd0;
      shadow_plane1_z_q <= 4'd0;
      shadow_plane1_alpha_q <= 8'hFF;
      shadow_plane1_color_key_enable_q <= 1'b0;
      shadow_plane1_color_key_rgb_q <= 24'd0;
      active_plane0_enable_q <= 1'b0;
      active_plane0_base_q <= 48'd0;
      active_plane0_stride_q <= 16'd0;
      active_plane0_x_q <= 12'd0;
      active_plane0_y_q <= 12'd0;
      active_plane0_width_q <= 12'd0;
      active_plane0_height_q <= 12'd0;
      active_plane0_format_q <= 4'd0;
      active_plane0_z_q <= 4'd0;
      active_plane0_alpha_q <= 8'hFF;
      active_plane0_color_key_enable_q <= 1'b0;
      active_plane0_color_key_rgb_q <= 24'd0;
      active_plane1_enable_q <= 1'b0;
      active_plane1_base_q <= 48'd0;
      active_plane1_stride_q <= 16'd0;
      active_plane1_x_q <= 12'd0;
      active_plane1_y_q <= 12'd0;
      active_plane1_width_q <= 12'd0;
      active_plane1_height_q <= 12'd0;
      active_plane1_format_q <= 4'd0;
      active_plane1_z_q <= 4'd0;
      active_plane1_alpha_q <= 8'hFF;
      active_plane1_color_key_enable_q <= 1'b0;
      active_plane1_color_key_rgb_q <= 24'd0;
    end else begin
      vblank_q <= vblank_i;
      descriptor_applied_pulse_o <= 1'b0;

      if (cfg_write_i) begin
        descriptor_pending_o <= 1'b1;
        if (!cfg_plane_i) begin
          unique case (cfg_field_i)
            FIELD_CONTROL: begin
              shadow_plane0_enable_q <= cfg_wdata_i[0];
              shadow_plane0_color_key_enable_q <= cfg_wdata_i[1];
            end
            FIELD_BASE: shadow_plane0_base_q <= cfg_wdata_i;
            FIELD_STRIDE: shadow_plane0_stride_q <= cfg_wdata_i[15:0];
            FIELD_POSITION: begin
              shadow_plane0_x_q <= cfg_wdata_i[11:0];
              shadow_plane0_y_q <= cfg_wdata_i[27:16];
            end
            FIELD_SIZE: begin
              shadow_plane0_width_q <= cfg_wdata_i[11:0];
              shadow_plane0_height_q <= cfg_wdata_i[27:16];
            end
            FIELD_FORMAT_Z_ALPHA: begin
              shadow_plane0_format_q <= cfg_wdata_i[3:0];
              shadow_plane0_z_q <= cfg_wdata_i[11:8];
              shadow_plane0_alpha_q <= cfg_wdata_i[23:16];
            end
            FIELD_COLOR_KEY: shadow_plane0_color_key_rgb_q <= cfg_wdata_i[23:0];
            default: begin
            end
          endcase
        end else begin
          unique case (cfg_field_i)
            FIELD_CONTROL: begin
              shadow_plane1_enable_q <= cfg_wdata_i[0];
              shadow_plane1_color_key_enable_q <= cfg_wdata_i[1];
            end
            FIELD_BASE: shadow_plane1_base_q <= cfg_wdata_i;
            FIELD_STRIDE: shadow_plane1_stride_q <= cfg_wdata_i[15:0];
            FIELD_POSITION: begin
              shadow_plane1_x_q <= cfg_wdata_i[11:0];
              shadow_plane1_y_q <= cfg_wdata_i[27:16];
            end
            FIELD_SIZE: begin
              shadow_plane1_width_q <= cfg_wdata_i[11:0];
              shadow_plane1_height_q <= cfg_wdata_i[27:16];
            end
            FIELD_FORMAT_Z_ALPHA: begin
              shadow_plane1_format_q <= cfg_wdata_i[3:0];
              shadow_plane1_z_q <= cfg_wdata_i[11:8];
              shadow_plane1_alpha_q <= cfg_wdata_i[23:16];
            end
            FIELD_COLOR_KEY: shadow_plane1_color_key_rgb_q <= cfg_wdata_i[23:0];
            default: begin
            end
          endcase
        end
      end

      if (vblank_i && !vblank_q && descriptor_pending_o) begin
        active_plane0_enable_q <= shadow_plane0_enable_q;
        active_plane0_base_q <= shadow_plane0_base_q;
        active_plane0_stride_q <= shadow_plane0_stride_q;
        active_plane0_x_q <= shadow_plane0_x_q;
        active_plane0_y_q <= shadow_plane0_y_q;
        active_plane0_width_q <= shadow_plane0_width_q;
        active_plane0_height_q <= shadow_plane0_height_q;
        active_plane0_format_q <= shadow_plane0_format_q;
        active_plane0_z_q <= shadow_plane0_z_q;
        active_plane0_alpha_q <= shadow_plane0_alpha_q;
        active_plane0_color_key_enable_q <= shadow_plane0_color_key_enable_q;
        active_plane0_color_key_rgb_q <= shadow_plane0_color_key_rgb_q;
        active_plane1_enable_q <= shadow_plane1_enable_q;
        active_plane1_base_q <= shadow_plane1_base_q;
        active_plane1_stride_q <= shadow_plane1_stride_q;
        active_plane1_x_q <= shadow_plane1_x_q;
        active_plane1_y_q <= shadow_plane1_y_q;
        active_plane1_width_q <= shadow_plane1_width_q;
        active_plane1_height_q <= shadow_plane1_height_q;
        active_plane1_format_q <= shadow_plane1_format_q;
        active_plane1_z_q <= shadow_plane1_z_q;
        active_plane1_alpha_q <= shadow_plane1_alpha_q;
        active_plane1_color_key_enable_q <= shadow_plane1_color_key_enable_q;
        active_plane1_color_key_rgb_q <= shadow_plane1_color_key_rgb_q;
        descriptor_pending_o <= 1'b0;
        descriptor_applied_pulse_o <= 1'b1;
        applied_count_o <= applied_count_o + 16'd1;
      end
    end
  end
endmodule
