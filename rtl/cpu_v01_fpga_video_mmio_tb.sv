module cpu_v01_fpga_video_mmio_tb;
  import cpu_v01_pkg::*;

  localparam addr_t VIDEO_BASE = 48'h0000_00F0_0500;

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
  logic video_vblank_i;
  logic video_underflow_pulse_i;
  logic [47:0] video_frame_count_i;
  logic [15:0] video_line_count_i;
  logic [15:0] video_pixel_count_i;
  logic [15:0] video_fb_master_status_i;
  logic video_scanout_enable_o;
  logic video_output_enable_o;
  logic [15:0] video_mode_o;
  logic [3:0] video_test_pattern_o;
  logic [23:0] video_bg_color_o;
  logic video_vblank_irq_o;

  cpu_v01_fpga_video_mmio dut (
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
    .video_vblank_i(video_vblank_i),
    .video_underflow_pulse_i(video_underflow_pulse_i),
    .video_frame_count_i(video_frame_count_i),
    .video_line_count_i(video_line_count_i),
    .video_pixel_count_i(video_pixel_count_i),
    .video_fb_master_status_i(video_fb_master_status_i),
    .video_scanout_enable_o(video_scanout_enable_o),
    .video_output_enable_o(video_output_enable_o),
    .video_mode_o(video_mode_o),
    .video_test_pattern_o(video_test_pattern_o),
    .video_bg_color_o(video_bg_color_o),
    .video_vblank_irq_o(video_vblank_irq_o)
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
      $fatal(1, "FPGA video MMIO write request was not ready");
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
      $fatal(1, "FPGA video MMIO read request was not ready");
    end
    @(posedge clk);
    #1;
    req_valid = 1'b0;
    if (!rsp_valid || rsp_fault.valid) begin
      $fatal(1, "FPGA video MMIO read did not return a clean response");
    end
    data = {rsp_rdata[1], rsp_rdata[0]};
    clear_request();
  endtask

  initial begin
    logic [47:0] value;

    clear_request();
    video_vblank_i = 1'b0;
    video_underflow_pulse_i = 1'b0;
    video_frame_count_i = 48'd9;
    video_line_count_i = 16'd720;
    video_pixel_count_i = 16'd1280;
    video_fb_master_status_i = 16'h0005;
    rst_n = 1'b0;
    repeat (3) @(posedge clk);
    rst_n = 1'b1;
    repeat (2) @(posedge clk);

    write_24(VIDEO_BASE + 48'h00, 24'h000003);
    if (!video_scanout_enable_o || !video_output_enable_o) begin
      $fatal(1, "FPGA video MMIO did not enable scanout outputs");
    end

    write_24(VIDEO_BASE + 48'h08, 24'h000002);
    write_24(VIDEO_BASE + 48'h09, 24'h123456);
    if (video_test_pattern_o != 4'd2 || video_bg_color_o != 24'h123456) begin
      $fatal(1, "FPGA video MMIO did not program pattern/color outputs");
    end

    write_24(VIDEO_BASE + 48'h03, 24'h000001);
    video_vblank_i = 1'b1;
    @(posedge clk);
    #1;
    read_register(VIDEO_BASE + 48'h02, 3'd1, value);
    if (!value[1] || !value[4]) begin
      $fatal(1, "FPGA video MMIO did not report vblank status");
    end
    if (!video_vblank_irq_o) begin
      $fatal(1, "FPGA video MMIO did not raise video_vblank_irq_o");
    end

    write_24(VIDEO_BASE + 48'h04, 24'h000001);
    if (video_vblank_irq_o) begin
      $fatal(1, "FPGA video MMIO acknowledgement did not clear vblank IRQ");
    end

    read_register(VIDEO_BASE + 48'h05, 3'd2, value);
    if (value != 48'd9) begin
      $fatal(1, "FPGA video MMIO frame count readback mismatch");
    end
    read_register(VIDEO_BASE + 48'h06, 3'd1, value);
    if (value[15:0] != 16'd720) begin
      $fatal(1, "FPGA video MMIO line count readback mismatch");
    end
    read_register(VIDEO_BASE + 48'h07, 3'd1, value);
    if (value[15:0] != 16'd1280) begin
      $fatal(1, "FPGA video MMIO pixel count readback mismatch");
    end

    video_underflow_pulse_i = 1'b1;
    @(posedge clk);
    #1;
    video_underflow_pulse_i = 1'b0;
    read_register(VIDEO_BASE + 48'h0A, 3'd2, value);
    if (value != 48'd1) begin
      $fatal(1, "FPGA video MMIO underflow count mismatch");
    end
    read_register(VIDEO_BASE + 48'h0B, 3'd1, value);
    if (value[15:0] != 16'h0005) begin
      $fatal(1, "FPGA video MMIO framebuffer status mismatch");
    end

    $finish;
  end

  // verilator lint_off UNUSEDSIGNAL
  wire logic unused_video_mmio_tb_outputs = &{video_mode_o};
  // verilator lint_on UNUSEDSIGNAL
endmodule
