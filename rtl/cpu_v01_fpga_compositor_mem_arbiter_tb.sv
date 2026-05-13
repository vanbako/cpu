module cpu_v01_fpga_compositor_mem_arbiter_tb;
  import cpu_v01_pkg::*;

  logic clk;
  logic rst_n;
  logic cpu_req_valid_i;
  logic cpu_req_ready_o;
  logic cpu_req_write_i;
  logic cpu_req_mmio_i;
  addr_t cpu_req_addr_i;
  logic [47:0] cpu_req_wdata_i;
  logic cpu_rsp_valid_o;
  logic [47:0] cpu_rsp_data_o;
  logic cpu_rsp_fault_o;
  logic video_req_valid_i;
  logic video_req_ready_o;
  addr_t video_req_addr_i;
  logic [7:0] video_req_len_cells_i;
  logic video_rsp_valid_o;
  logic [47:0] video_rsp_data_o;
  logic video_rsp_error_o;
  logic descriptor_update_i;
  logic mem_req_valid_o;
  logic mem_req_ready_i;
  logic mem_req_write_o;
  addr_t mem_req_addr_o;
  logic [47:0] mem_req_wdata_o;
  logic [1:0] mem_req_owner_o;
  logic mem_rsp_valid_i;
  logic [47:0] mem_rsp_data_i;
  logic mem_rsp_error_i;
  logic [15:0] cpu_grant_count_o;
  logic [15:0] video_grant_count_o;
  logic [15:0] video_starvation_count_o;
  logic [15:0] video_underflow_count_o;
  logic [15:0] descriptor_update_count_o;
  logic [1:0] last_grant_o;

  // cpu_v01_fpga_compositor_mem_arbiter dut
  cpu_v01_fpga_compositor_mem_arbiter #(
    .VIDEO_STALL_UNDERFLOW_CYCLES(2)
  ) dut (
    .clk(clk),
    .rst_n(rst_n),
    .cpu_req_valid_i(cpu_req_valid_i),
    .cpu_req_ready_o(cpu_req_ready_o),
    .cpu_req_write_i(cpu_req_write_i),
    .cpu_req_mmio_i(cpu_req_mmio_i),
    .cpu_req_addr_i(cpu_req_addr_i),
    .cpu_req_wdata_i(cpu_req_wdata_i),
    .cpu_rsp_valid_o(cpu_rsp_valid_o),
    .cpu_rsp_data_o(cpu_rsp_data_o),
    .cpu_rsp_fault_o(cpu_rsp_fault_o),
    .video_req_valid_i(video_req_valid_i),
    .video_req_ready_o(video_req_ready_o),
    .video_req_addr_i(video_req_addr_i),
    .video_req_len_cells_i(video_req_len_cells_i),
    .video_rsp_valid_o(video_rsp_valid_o),
    .video_rsp_data_o(video_rsp_data_o),
    .video_rsp_error_o(video_rsp_error_o),
    .descriptor_update_i(descriptor_update_i),
    .mem_req_valid_o(mem_req_valid_o),
    .mem_req_ready_i(mem_req_ready_i),
    .mem_req_write_o(mem_req_write_o),
    .mem_req_addr_o(mem_req_addr_o),
    .mem_req_wdata_o(mem_req_wdata_o),
    .mem_req_owner_o(mem_req_owner_o),
    .mem_rsp_valid_i(mem_rsp_valid_i),
    .mem_rsp_data_i(mem_rsp_data_i),
    .mem_rsp_error_i(mem_rsp_error_i),
    .cpu_grant_count_o(cpu_grant_count_o),
    .video_grant_count_o(video_grant_count_o),
    .video_starvation_count_o(video_starvation_count_o),
    .video_underflow_count_o(video_underflow_count_o),
    .descriptor_update_count_o(descriptor_update_count_o),
    .last_grant_o(last_grant_o)
  );

  initial begin
    clk = 1'b0;
    forever #5 clk = ~clk;
  end

  task automatic clear_inputs();
    cpu_req_valid_i = 1'b0;
    cpu_req_write_i = 1'b0;
    cpu_req_mmio_i = 1'b0;
    cpu_req_addr_i = 48'd0;
    cpu_req_wdata_i = 48'd0;
    video_req_valid_i = 1'b0;
    video_req_addr_i = 48'd0;
    video_req_len_cells_i = 8'd1;
    descriptor_update_i = 1'b0;
    mem_req_ready_i = 1'b1;
    mem_rsp_valid_i = 1'b0;
    mem_rsp_data_i = 48'd0;
    mem_rsp_error_i = 1'b0;
  endtask

  task automatic respond(input logic [47:0] data, input logic error);
    mem_rsp_data_i = data;
    mem_rsp_error_i = error;
    mem_rsp_valid_i = 1'b1;
    @(posedge clk);
    #1;
    mem_rsp_valid_i = 1'b0;
    mem_rsp_error_i = 1'b0;
  endtask

  initial begin
    clear_inputs();
    rst_n = 1'b0;
    repeat (3) @(posedge clk);
    rst_n = 1'b1;
    repeat (2) @(posedge clk);

    cpu_req_valid_i = 1'b1;
    cpu_req_write_i = 1'b1;
    cpu_req_addr_i = 48'h0000_0001_0000;
    cpu_req_wdata_i = 48'h0000_0000_1234;
    video_req_valid_i = 1'b1;
    video_req_addr_i = 48'h0000_0110_0000;
    descriptor_update_i = 1'b1;
    #1;
    if (!cpu_req_ready_o || video_req_ready_o || !mem_req_write_o || mem_req_owner_o != 2'd1) begin
      $fatal(1, "compositor arbiter did not grant CPU before video");
    end
    @(posedge clk);
    #1;
    clear_inputs();
    if (descriptor_update_count_o != 16'd1) begin
      $fatal(1, "compositor arbiter did not count descriptor update");
    end
    if (video_starvation_count_o != 16'd1) begin
      $fatal(1, "compositor arbiter did not expose video starvation counter");
    end
    respond(48'h0000_0000_AAAA, 1'b0);
    if (!cpu_rsp_valid_o || cpu_rsp_fault_o) begin
      $fatal(1, "compositor arbiter did not preserve CPU response ordering");
    end

    video_req_valid_i = 1'b1;
    video_req_addr_i = 48'h0000_0110_0000;
    #1;
    if (!video_req_ready_o || mem_req_owner_o != 2'd2 || mem_req_addr_o != 48'h0000_0110_0000) begin
      $fatal(1, "compositor arbiter did not grant pending video scanout read");
    end
    @(posedge clk);
    #1;
    clear_inputs();
    respond(48'h0000_00FF_0000, 1'b0);
    if (!video_rsp_valid_o || video_rsp_data_o != 48'h0000_00FF_0000 || video_rsp_error_o) begin
      $fatal(1, "compositor arbiter did not route video response");
    end

    cpu_req_valid_i = 1'b1;
    cpu_req_mmio_i = 1'b1;
    cpu_req_addr_i = 48'h0000_00F0_0500;
    #1;
    if (!cpu_req_ready_o || mem_req_owner_o != 2'd1) begin
      $fatal(1, "compositor arbiter did not accept CPU MMIO request");
    end
    @(posedge clk);
    #1;
    clear_inputs();
    respond(48'h0000_0000_0000, 1'b1);
    if (!cpu_rsp_valid_o || !cpu_rsp_fault_o) begin
      $fatal(1, "compositor arbiter did not preserve CPU fault response");
    end

    video_req_valid_i = 1'b1;
    video_req_addr_i = 48'h0000_0110_0001;
    mem_req_ready_i = 1'b0;
    @(posedge clk);
    #1;
    @(posedge clk);
    #1;
    if (video_underflow_count_o == 16'd0) begin
      $fatal(1, "compositor arbiter did not report underflow after bounded video stall");
    end

    $finish;
  end

  // verilator lint_off UNUSEDSIGNAL
  wire logic [15:0] unused_cpu_grant_count = cpu_grant_count_o;
  wire logic [15:0] unused_video_grant_count = video_grant_count_o;
  wire logic [1:0] unused_last_grant = last_grant_o;
  // verilator lint_on UNUSEDSIGNAL
endmodule
