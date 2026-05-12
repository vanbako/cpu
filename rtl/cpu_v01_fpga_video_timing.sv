module cpu_v01_fpga_video_timing #(
  parameter int H_ACTIVE = 1280,
  parameter int H_FRONT = 110,
  parameter int H_SYNC = 40,
  parameter int H_BACK = 220,
  parameter int V_ACTIVE = 720,
  parameter int V_FRONT = 5,
  parameter int V_SYNC = 5,
  parameter int V_BACK = 20
) (
  input  logic pixel_clk,
  input  logic rst_n,
  input  logic enable_i,
  input  logic [3:0] pattern_select_i,
  input  logic [23:0] bg_color_i,

  output logic [11:0] pixel_x_o,
  output logic [11:0] pixel_y_o,
  output logic hsync_o,
  output logic vsync_o,
  output logic de_o,
  output logic vblank_o,
  output logic frame_start_o,
  output logic line_start_o,
  output logic [23:0] rgb_o,
  output logic [47:0] frame_count_o
);
  localparam int H_TOTAL = H_ACTIVE + H_FRONT + H_SYNC + H_BACK;
  localparam int V_TOTAL = V_ACTIVE + V_FRONT + V_SYNC + V_BACK;
  localparam int H_SYNC_START = H_ACTIVE + H_FRONT;
  localparam int H_SYNC_END = H_SYNC_START + H_SYNC;
  localparam int V_SYNC_START = V_ACTIVE + V_FRONT;
  localparam int V_SYNC_END = V_SYNC_START + V_SYNC;

  localparam logic [3:0] PATTERN_BACKGROUND = 4'd0;
  localparam logic [3:0] PATTERN_COLOR_BARS = 4'd1;
  localparam logic [3:0] PATTERN_CHECKERBOARD = 4'd2;

  logic [11:0] h_count_q;
  logic [11:0] v_count_q;
  logic active_pixel;
  logic hsync_active;
  logic vsync_active;

  assign active_pixel = (h_count_q < H_ACTIVE[11:0]) && (v_count_q < V_ACTIVE[11:0]);
  assign hsync_active = (h_count_q >= H_SYNC_START[11:0]) && (h_count_q < H_SYNC_END[11:0]);
  assign vsync_active = (v_count_q >= V_SYNC_START[11:0]) && (v_count_q < V_SYNC_END[11:0]);

  assign pixel_x_o = active_pixel ? h_count_q : 12'd0;
  assign pixel_y_o = active_pixel ? v_count_q : 12'd0;
  assign de_o = active_pixel;
  assign hsync_o = hsync_active;
  assign vsync_o = vsync_active;
  assign vblank_o = (v_count_q >= V_ACTIVE[11:0]);
  assign rgb_o = active_pixel ? selected_rgb(h_count_q, v_count_q, pattern_select_i, bg_color_i) : 24'h000000;

  function automatic logic [23:0] color_bar_rgb(input logic [11:0] x);
    automatic int bar;
    bar = (x * 8) / H_ACTIVE;
    unique case (bar[2:0])
      3'd0: color_bar_rgb = 24'hFF0000;
      3'd1: color_bar_rgb = 24'h00FF00;
      3'd2: color_bar_rgb = 24'h0000FF;
      3'd3: color_bar_rgb = 24'hFFFF00;
      3'd4: color_bar_rgb = 24'h00FFFF;
      3'd5: color_bar_rgb = 24'hFF00FF;
      3'd6: color_bar_rgb = 24'hFFFFFF;
      default: color_bar_rgb = 24'h202020;
    endcase
  endfunction

  function automatic logic [23:0] checkerboard_rgb(
      input logic [11:0] x,
      input logic [11:0] y
  );
    checkerboard_rgb = (((x[11:5] ^ y[11:5]) & 7'd1) != 7'd0) ? 24'hFFFFFF : 24'h000000;
  endfunction

  function automatic logic [23:0] selected_rgb(
      input logic [11:0] x,
      input logic [11:0] y,
      input logic [3:0] pattern_select,
      input logic [23:0] bg_color
  );
    unique case (pattern_select)
      PATTERN_BACKGROUND: selected_rgb = bg_color;
      PATTERN_COLOR_BARS: selected_rgb = color_bar_rgb(x);
      PATTERN_CHECKERBOARD: selected_rgb = checkerboard_rgb(x, y);
      default: selected_rgb = bg_color;
    endcase
  endfunction

  always_ff @(posedge pixel_clk or negedge rst_n) begin
    if (!rst_n) begin
      h_count_q <= 12'd0;
      v_count_q <= 12'd0;
      frame_count_o <= 48'd0;
      frame_start_o <= 1'b0;
      line_start_o <= 1'b0;
    end else begin
      frame_start_o <= 1'b0;
      line_start_o <= 1'b0;

      if (enable_i) begin
        if (h_count_q == H_TOTAL[11:0] - 12'd1) begin
          h_count_q <= 12'd0;
          line_start_o <= 1'b1;
          if (v_count_q == V_TOTAL[11:0] - 12'd1) begin
            v_count_q <= 12'd0;
            frame_count_o <= frame_count_o + 48'd1;
            frame_start_o <= 1'b1;
          end else begin
            v_count_q <= v_count_q + 12'd1;
          end
        end else begin
          h_count_q <= h_count_q + 12'd1;
        end
      end
    end
  end
endmodule
