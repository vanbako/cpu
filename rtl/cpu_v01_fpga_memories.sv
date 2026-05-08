module cpu_v01_fpga_imem_rom #(
  parameter cpu_v01_pkg::addr_t BASE_CELL = 48'h0000_0000_1000,
  parameter int DEPTH_CELLS = 1024,
  parameter bit USE_INIT_FILE = 1'b0,
  parameter string INIT_FILE = ""
) (
  input  logic clk,
  input  logic rst_n,

  input  logic req_valid,
  output logic req_ready,
  input  cpu_v01_pkg::addr_t req_addr,

  output logic rsp_valid,
  input  logic rsp_ready,
  output cpu_v01_pkg::cell_t rsp_cells [cpu_v01_pkg::FETCH_GROUP_CELLS],
  output cpu_v01_pkg::fault_packet_t rsp_fault
);
  import cpu_v01_pkg::*;

  cell_t rom_q [DEPTH_CELLS];

  assign req_ready = !rsp_valid || rsp_ready;

  initial begin
    for (int i = 0; i < DEPTH_CELLS; i++) begin
      rom_q[i] = '0;
    end

    rom_q[0] = 24'h05B05B;
    rom_q[1] = 24'h05B05B;
    rom_q[2] = 24'h05B05B;
    rom_q[3] = 24'h05B05B;

    if (USE_INIT_FILE && INIT_FILE != "") begin
      $readmemh(INIT_FILE, rom_q);
    end
  end

  function automatic logic fetch_in_range(input addr_t addr);
    addr_t last_cell;
    last_cell = addr + addr_t'(FETCH_GROUP_CELLS) - 48'd1;
    return addr >= BASE_CELL && last_cell < BASE_CELL + addr_t'(DEPTH_CELLS);
  endfunction

  function automatic int unsigned rom_offset(input addr_t addr);
    return int'(addr - BASE_CELL);
  endfunction

  function automatic fault_packet_t access_fault(input addr_t addr);
    fault_packet_t fault;
    fault = '0;
    fault.valid = 1'b1;
    fault.cause = EXC_ACCESS_FAULT;
    fault.tval = addr;
    fault.fault_cap_idx = FAULT_CAP_IDX_PCC;
    return fault;
  endfunction

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      rsp_valid <= 1'b0;
      rsp_fault <= '0;
      for (int i = 0; i < FETCH_GROUP_CELLS; i++) begin
        rsp_cells[i] <= '0;
      end
    end else if (req_valid && req_ready) begin
      automatic int unsigned offset;
      offset = rom_offset(req_addr);
      rsp_valid <= 1'b1;
      if (fetch_in_range(req_addr)) begin
        rsp_fault <= '0;
        for (int i = 0; i < FETCH_GROUP_CELLS; i++) begin
          rsp_cells[i] <= rom_q[offset + i];
        end
      end else begin
        rsp_fault <= access_fault(req_addr);
        for (int i = 0; i < FETCH_GROUP_CELLS; i++) begin
          rsp_cells[i] <= '0;
        end
      end
    end else if (rsp_ready) begin
      rsp_valid <= 1'b0;
      rsp_fault <= '0;
    end
  end
endmodule

module cpu_v01_fpga_data_ram #(
  parameter cpu_v01_pkg::addr_t BASE_CELL = 48'h0000_0001_0000,
  parameter int DEPTH_CELLS = 4096,
  parameter bit USE_INIT_FILE = 1'b0,
  parameter string INIT_FILE = ""
) (
  input  logic clk,
  input  logic rst_n,

  input  logic req_valid,
  output logic req_ready,
  input  logic req_write,
  input  cpu_v01_pkg::addr_t req_addr,
  input  logic [2:0] req_len_cells,
  input  cpu_v01_pkg::cell_t req_wdata [cpu_v01_pkg::CAPABILITY_OBJECT_CELLS],

  output logic rsp_valid,
  output cpu_v01_pkg::cell_t rsp_rdata [cpu_v01_pkg::CAPABILITY_OBJECT_CELLS],
  output cpu_v01_pkg::fault_packet_t rsp_fault
);
  import cpu_v01_pkg::*;

  cell_t ram_q [DEPTH_CELLS];

  assign req_ready = 1'b1;

  initial begin
    for (int i = 0; i < DEPTH_CELLS; i++) begin
      ram_q[i] = '0;
    end

    if (USE_INIT_FILE && INIT_FILE != "") begin
      $readmemh(INIT_FILE, ram_q);
    end
  end

  function automatic logic transfer_in_range(input addr_t addr, input logic [2:0] len_cells);
    addr_t last_cell;
    last_cell = addr + addr_t'(len_cells) - 48'd1;
    return len_cells != 3'd0 &&
        addr >= BASE_CELL &&
        last_cell < BASE_CELL + addr_t'(DEPTH_CELLS);
  endfunction

  function automatic int unsigned ram_offset(input addr_t addr);
    return int'(addr - BASE_CELL);
  endfunction

  function automatic fault_packet_t access_fault(input addr_t addr);
    fault_packet_t fault;
    fault = '0;
    fault.valid = 1'b1;
    fault.cause = EXC_ACCESS_FAULT;
    fault.tval = addr;
    return fault;
  endfunction

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      rsp_valid <= 1'b0;
      rsp_fault <= '0;
      for (int i = 0; i < CAPABILITY_OBJECT_CELLS; i++) begin
        rsp_rdata[i] <= '0;
      end
    end else begin
      rsp_valid <= 1'b0;
      rsp_fault <= '0;

      if (req_valid && req_ready) begin
        automatic int unsigned offset;
        offset = ram_offset(req_addr);
        if (transfer_in_range(req_addr, req_len_cells)) begin
          if (req_write) begin
            if (req_len_cells >= 3'd1) begin
              ram_q[offset] <= req_wdata[0];
            end
            if (req_len_cells >= 3'd2) begin
              ram_q[offset + 1] <= req_wdata[1];
            end
            if (req_len_cells >= 3'd3) begin
              ram_q[offset + 2] <= req_wdata[2];
            end
            if (req_len_cells >= 3'd4) begin
              ram_q[offset + 3] <= req_wdata[3];
            end
          end else begin
            rsp_valid <= 1'b1;
            rsp_rdata[0] <= req_len_cells >= 3'd1 ? ram_q[offset] : '0;
            rsp_rdata[1] <= req_len_cells >= 3'd2 ? ram_q[offset + 1] : '0;
            rsp_rdata[2] <= req_len_cells >= 3'd3 ? ram_q[offset + 2] : '0;
            rsp_rdata[3] <= req_len_cells >= 3'd4 ? ram_q[offset + 3] : '0;
          end
        end else if (!req_write) begin
          rsp_valid <= 1'b1;
          rsp_fault <= access_fault(req_addr);
          for (int i = 0; i < CAPABILITY_OBJECT_CELLS; i++) begin
            rsp_rdata[i] <= '0;
          end
        end
      end
    end
  end
endmodule

module cpu_v01_fpga_tag_ram #(
  parameter cpu_v01_pkg::addr_t BASE_CELL = 48'h0000_0001_0000,
  parameter int DEPTH_ENTRIES = 4096
) (
  input  logic clk,
  input  logic rst_n,

  input  logic req_valid,
  output logic req_ready,
  input  logic req_write,
  input  cpu_v01_pkg::addr_t req_slot_addr,
  input  logic req_wtag,

  output logic rsp_valid,
  output logic rsp_rtag
);
  import cpu_v01_pkg::*;

  logic tag_q [DEPTH_ENTRIES];

  assign req_ready = 1'b1;

  initial begin
    for (int i = 0; i < DEPTH_ENTRIES; i++) begin
      tag_q[i] = 1'b0;
    end
  end

  function automatic logic tag_in_range(input addr_t addr);
    return addr >= BASE_CELL && addr < BASE_CELL + addr_t'(DEPTH_ENTRIES);
  endfunction

  function automatic int unsigned tag_offset(input addr_t addr);
    return int'(addr - BASE_CELL);
  endfunction

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      rsp_valid <= 1'b0;
      rsp_rtag <= 1'b0;
    end else begin
      rsp_valid <= 1'b0;
      if (req_valid && req_ready) begin
        automatic int unsigned offset;
        offset = tag_offset(req_slot_addr);
        if (tag_in_range(req_slot_addr)) begin
          if (req_write) begin
            tag_q[offset] <= req_wtag;
          end else begin
            rsp_valid <= 1'b1;
            rsp_rtag <= tag_q[offset];
          end
        end else if (!req_write) begin
          rsp_valid <= 1'b1;
          rsp_rtag <= 1'b0;
        end
      end
    end
  end
endmodule
