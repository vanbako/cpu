module cpu_v01_fpga_compositor_mem_arbiter #(
  parameter int VIDEO_STALL_UNDERFLOW_CYCLES = 2
) (
  input  logic clk,
  input  logic rst_n,

  input  logic cpu_req_valid_i,
  output logic cpu_req_ready_o,
  input  logic cpu_req_write_i,
  input  logic cpu_req_mmio_i,
  input  cpu_v01_pkg::addr_t cpu_req_addr_i,
  input  logic [47:0] cpu_req_wdata_i,
  output logic cpu_rsp_valid_o,
  output logic [47:0] cpu_rsp_data_o,
  output logic cpu_rsp_fault_o,

  input  logic video_req_valid_i,
  output logic video_req_ready_o,
  input  cpu_v01_pkg::addr_t video_req_addr_i,
  input  logic [7:0] video_req_len_cells_i,
  output logic video_rsp_valid_o,
  output logic [47:0] video_rsp_data_o,
  output logic video_rsp_error_o,

  input  logic descriptor_update_i,

  output logic mem_req_valid_o,
  input  logic mem_req_ready_i,
  output logic mem_req_write_o,
  output cpu_v01_pkg::addr_t mem_req_addr_o,
  output logic [47:0] mem_req_wdata_o,
  output logic [1:0] mem_req_owner_o,
  input  logic mem_rsp_valid_i,
  input  logic [47:0] mem_rsp_data_i,
  input  logic mem_rsp_error_i,

  output logic [15:0] cpu_grant_count_o,
  output logic [15:0] video_grant_count_o,
  output logic [15:0] video_starvation_count_o,
  output logic [15:0] video_underflow_count_o,
  output logic [15:0] descriptor_update_count_o,
  output logic [1:0] last_grant_o
);
  import cpu_v01_pkg::*;

  localparam logic [1:0] OWNER_NONE = 2'd0;
  localparam logic [1:0] OWNER_CPU = 2'd1;
  localparam logic [1:0] OWNER_VIDEO = 2'd2;
  localparam logic [15:0] VIDEO_STALL_UNDERFLOW_LIMIT = 16'(VIDEO_STALL_UNDERFLOW_CYCLES);
  // CPU_FIRST_SINGLE_OUTSTANDING policy: CPU data/MMIO wins same-cycle contention.

  logic outstanding_q;
  logic [1:0] outstanding_owner_q;
  logic [15:0] video_wait_count_q;
  logic grant_cpu;
  logic grant_video;
  logic [15:0] next_video_wait_count;

  assign grant_cpu = !outstanding_q && cpu_req_valid_i && mem_req_ready_i;
  assign grant_video = !outstanding_q && !cpu_req_valid_i && video_req_valid_i && mem_req_ready_i;
  assign cpu_req_ready_o = grant_cpu;
  assign video_req_ready_o = grant_video;
  assign mem_req_valid_o = !outstanding_q && (cpu_req_valid_i || video_req_valid_i);
  assign mem_req_write_o = cpu_req_valid_i ? cpu_req_write_i : 1'b0;
  assign mem_req_addr_o = cpu_req_valid_i ? cpu_req_addr_i : video_req_addr_i;
  assign mem_req_wdata_o = cpu_req_valid_i ? cpu_req_wdata_i : 48'd0;
  assign mem_req_owner_o = cpu_req_valid_i ? OWNER_CPU : (video_req_valid_i ? OWNER_VIDEO : OWNER_NONE);
  assign next_video_wait_count = video_wait_count_q + 16'd1;

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      outstanding_q <= 1'b0;
      outstanding_owner_q <= OWNER_NONE;
      video_wait_count_q <= 16'd0;
      cpu_rsp_valid_o <= 1'b0;
      cpu_rsp_data_o <= 48'd0;
      cpu_rsp_fault_o <= 1'b0;
      video_rsp_valid_o <= 1'b0;
      video_rsp_data_o <= 48'd0;
      video_rsp_error_o <= 1'b0;
      cpu_grant_count_o <= 16'd0;
      video_grant_count_o <= 16'd0;
      video_starvation_count_o <= 16'd0;
      video_underflow_count_o <= 16'd0;
      descriptor_update_count_o <= 16'd0;
      last_grant_o <= OWNER_NONE;
    end else begin
      cpu_rsp_valid_o <= 1'b0;
      cpu_rsp_fault_o <= 1'b0;
      video_rsp_valid_o <= 1'b0;
      video_rsp_error_o <= 1'b0;

      if (descriptor_update_i) begin
        descriptor_update_count_o <= descriptor_update_count_o + 16'd1;
      end

      if (grant_cpu) begin
        outstanding_q <= 1'b1;
        outstanding_owner_q <= OWNER_CPU;
        cpu_grant_count_o <= cpu_grant_count_o + 16'd1;
        last_grant_o <= OWNER_CPU;
      end else if (grant_video) begin
        outstanding_q <= 1'b1;
        outstanding_owner_q <= OWNER_VIDEO;
        video_grant_count_o <= video_grant_count_o + 16'd1;
        last_grant_o <= OWNER_VIDEO;
      end

      if (video_req_valid_i && !video_req_ready_o) begin
        video_starvation_count_o <= video_starvation_count_o + 16'd1;
        video_wait_count_q <= next_video_wait_count;
        if (next_video_wait_count >= VIDEO_STALL_UNDERFLOW_LIMIT) begin
          video_underflow_count_o <= video_underflow_count_o + 16'd1;
          video_wait_count_q <= 16'd0;
        end
      end else if (video_req_ready_o) begin
        video_wait_count_q <= 16'd0;
      end

      if (mem_rsp_valid_i && outstanding_q) begin
        outstanding_q <= 1'b0;
        if (outstanding_owner_q == OWNER_CPU) begin
          cpu_rsp_valid_o <= 1'b1;
          cpu_rsp_data_o <= mem_rsp_data_i;
          cpu_rsp_fault_o <= mem_rsp_error_i; // EXC_ACCESS_FAULT handoff stays CPU-owned
        end else if (outstanding_owner_q == OWNER_VIDEO) begin
          video_rsp_valid_o <= 1'b1;
          video_rsp_data_o <= mem_rsp_data_i;
          video_rsp_error_o <= mem_rsp_error_i;
          if (mem_rsp_error_i) begin
            video_underflow_count_o <= video_underflow_count_o + 16'd1;
          end
        end
        outstanding_owner_q <= OWNER_NONE;
      end
    end
  end

  // verilator lint_off UNUSEDSIGNAL
  wire logic unused_cpu_req_mmio = cpu_req_mmio_i;
  wire logic [7:0] unused_video_len = video_req_len_cells_i;
  // verilator lint_on UNUSEDSIGNAL
endmodule
