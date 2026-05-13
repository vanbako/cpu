module cpu_v01_fpga_video_scanout_gate_tb;
  import cpu_v01_pkg::*;

  localparam addr_t VIDEO_BASE = 48'h0000_00F0_0500;
  localparam int VBLANK_START_CYCLES = 720 * 1650;
  localparam int FULL_FRAME_CYCLES = 750 * 1650;

  logic clk;
  logic rst_n;
  logic req_valid;
  logic req_ready;
  logic req_write;
  addr_t req_addr;
  logic [2:0] req_len_cells;
  cell_t req_wdata [INTEGER_OBJECT_CELLS];
  logic rsp_valid;
  cell_t rsp_rdata [INTEGER_OBJECT_CELLS];
  fault_packet_t rsp_fault;

  logic video_scanout_enable;
  logic video_output_enable;
  logic [15:0] video_mode;
  logic [3:0] video_test_pattern;
  logic [23:0] video_bg_color;
  logic video_vblank_irq;

  logic [23:0] video_rgb;
  logic video_hsync;
  logic video_vsync;
  logic video_de;
  logic video_vblank;
  logic video_pixel_clk;
  logic video_output_enable_sync;
  logic [47:0] video_frame_count;

  cpu_v01_fpga_video_output_boundary video_output (
    .pixel_clk_i(clk),
    .pixel_reset_n_i(rst_n),
    .scanout_enable_async_i(video_scanout_enable),
    .output_enable_async_i(video_output_enable),
    .pattern_select_i(video_test_pattern),
    .bg_color_i(video_bg_color),
    .video_rgb_o(video_rgb),
    .video_hsync_o(video_hsync),
    .video_vsync_o(video_vsync),
    .video_de_o(video_de),
    .video_vblank_o(video_vblank),
    .video_pixel_clk_o(video_pixel_clk),
    .video_output_enable_o(video_output_enable_sync),
    .video_frame_count_o(video_frame_count)
  );

  cpu_v01_fpga_video_mmio video_mmio (
    .clk(clk),
    .rst_n(rst_n),
    .req_valid(req_valid),
    .req_ready(req_ready),
    .req_write(req_write),
    .req_addr(req_addr),
    .req_len_cells(req_len_cells),
    .req_wdata(req_wdata),
    .rsp_valid(rsp_valid),
    .rsp_rdata(rsp_rdata),
    .rsp_fault(rsp_fault),
    .video_vblank_i(video_vblank),
    .video_underflow_pulse_i(1'b0),
    .video_frame_count_i(video_frame_count),
    .video_line_count_i(16'd0),
    .video_pixel_count_i(16'd0),
    .video_fb_master_status_i(16'd1),
    .video_scanout_enable_o(video_scanout_enable),
    .video_output_enable_o(video_output_enable),
    .video_mode_o(video_mode),
    .video_test_pattern_o(video_test_pattern),
    .video_bg_color_o(video_bg_color),
    .video_vblank_irq_o(video_vblank_irq)
  );

  initial begin
    clk = 1'b0;
    forever #5 clk = ~clk;
  end

  task automatic clear_request();
    req_valid = 1'b0;
    req_write = 1'b0;
    req_addr = '0;
    req_len_cells = 3'd0;
    for (int i = 0; i < INTEGER_OBJECT_CELLS; i++) begin
      req_wdata[i] = '0;
    end
  endtask

  task automatic write_24(input addr_t addr, input cell_t data);
    clear_request();
    req_addr = addr;
    req_len_cells = 3'd1;
    req_wdata[0] = data;
    req_write = 1'b1;
    req_valid = 1'b1;
    #1;
    if (!req_ready) begin
      $fatal(1, "FPGA video scanout gate write request was not ready");
    end
    @(posedge clk);
    #1;
    clear_request();
  endtask

  task automatic read_register(input addr_t addr, input logic [2:0] len, output logic [47:0] data);
    clear_request();
    req_addr = addr;
    req_len_cells = len;
    req_write = 1'b0;
    req_valid = 1'b1;
    #1;
    if (!req_ready) begin
      $fatal(1, "FPGA video scanout gate read request was not ready");
    end
    @(posedge clk);
    #1;
    req_valid = 1'b0;
    if (!rsp_valid || rsp_fault.valid) begin
      $fatal(1, "FPGA video scanout gate read did not return a clean response");
    end
    data = {rsp_rdata[1], rsp_rdata[0]};
    clear_request();
  endtask

  initial begin
    logic [47:0] value;
    bit saw_active_rgb;
    int vblank_guard;
    int frame_guard;

    clear_request();
    rst_n = 1'b0;
    repeat (4) @(posedge clk);
    rst_n = 1'b1;
    repeat (4) @(posedge clk);

    write_24(VIDEO_BASE + 48'h00, 24'h000003);
    write_24(VIDEO_BASE + 48'h08, 24'h000001);
    write_24(VIDEO_BASE + 48'h09, 24'h123456);
    write_24(VIDEO_BASE + 48'h03, 24'h000001);
    write_24(VIDEO_BASE + 48'h04, 24'h000001);

    repeat (8) @(posedge clk);
    if (!video_output_enable_sync) begin
      $fatal(1, "FPGA video scanout gate did not synchronize output enable");
    end

    saw_active_rgb = 1'b0;
    for (int i = 0; i < 64; i++) begin
      @(posedge clk);
      #1;
      if (video_de && video_rgb != 24'h000000) begin
        saw_active_rgb = 1'b1;
      end
    end
    if (!saw_active_rgb) begin
      $fatal(1, "FPGA video scanout gate did not drive active RGB");
    end
    if (video_pixel_clk !== clk) begin
      $fatal(1, "FPGA video scanout gate did not expose pixel clock");
    end

    vblank_guard = 0;
    while (!video_vblank && vblank_guard < (VBLANK_START_CYCLES + 128)) begin
      @(posedge clk);
      #1;
      vblank_guard++;
    end
    if (!video_vblank) begin
      $fatal(1, "FPGA video scanout gate did not reach vblank");
    end
    if (!video_vblank_irq) begin
      $fatal(1, "FPGA video scanout gate did not raise vblank IRQ");
    end
    read_register(VIDEO_BASE + 48'h02, 3'd1, value);
    if (!value[1] || !value[4]) begin
      $fatal(1, "FPGA video scanout gate vblank status readback mismatch");
    end

    write_24(VIDEO_BASE + 48'h04, 24'h000001);
    if (video_vblank_irq) begin
      $fatal(1, "FPGA video scanout gate did not clear vblank IRQ");
    end

    frame_guard = 0;
    while (video_frame_count != 48'd1 && frame_guard < (FULL_FRAME_CYCLES - VBLANK_START_CYCLES + 128)) begin
      @(posedge clk);
      #1;
      frame_guard++;
    end
    if (video_frame_count != 48'd1) begin
      $fatal(1, "FPGA video scanout gate did not finish one frame");
    end
    read_register(VIDEO_BASE + 48'h05, 3'd2, value);
    if (value != 48'd1) begin
      $fatal(1, "FPGA video scanout gate frame count readback mismatch");
    end
    read_register(VIDEO_BASE + 48'h0A, 3'd2, value);
    if (value != 48'd0) begin
      $fatal(1, "FPGA video scanout gate unexpected underflow count");
    end

    $finish;
  end

  // verilator lint_off UNUSEDSIGNAL
  wire logic unused_video_scanout_gate_outputs = &{video_mode, video_hsync, video_vsync};
  // verilator lint_on UNUSEDSIGNAL
endmodule
