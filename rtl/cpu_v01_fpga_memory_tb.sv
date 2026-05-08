module cpu_v01_fpga_memory_tb;
  import cpu_v01_pkg::*;

  logic clk;
  logic rst_n;

  logic imem_req_valid;
  logic imem_req_ready;
  addr_t imem_req_addr;
  logic imem_rsp_valid;
  logic imem_rsp_ready;
  cell_t imem_rsp_cells [FETCH_GROUP_CELLS];
  fault_packet_t imem_rsp_fault;

  logic dmem_req_valid;
  logic dmem_req_ready;
  logic dmem_req_write;
  addr_t dmem_req_addr;
  logic [2:0] dmem_req_len_cells;
  cell_t dmem_req_wdata [CAPABILITY_OBJECT_CELLS];
  logic dmem_rsp_valid;
  cell_t dmem_rsp_rdata [CAPABILITY_OBJECT_CELLS];
  fault_packet_t dmem_rsp_fault;

  logic tagmem_req_valid;
  logic tagmem_req_ready;
  logic tagmem_req_write;
  addr_t tagmem_req_slot_addr;
  logic tagmem_req_wtag;
  logic tagmem_rsp_valid;
  logic tagmem_rsp_rtag;

  cpu_v01_fpga_imem_rom instruction_rom (
    .clk(clk),
    .rst_n(rst_n),
    .req_valid(imem_req_valid),
    .req_ready(imem_req_ready),
    .req_addr(imem_req_addr),
    .rsp_valid(imem_rsp_valid),
    .rsp_ready(imem_rsp_ready),
    .rsp_cells(imem_rsp_cells),
    .rsp_fault(imem_rsp_fault)
  );

  cpu_v01_fpga_data_ram data_ram (
    .clk(clk),
    .rst_n(rst_n),
    .req_valid(dmem_req_valid),
    .req_ready(dmem_req_ready),
    .req_write(dmem_req_write),
    .req_addr(dmem_req_addr),
    .req_len_cells(dmem_req_len_cells),
    .req_wdata(dmem_req_wdata),
    .rsp_valid(dmem_rsp_valid),
    .rsp_rdata(dmem_rsp_rdata),
    .rsp_fault(dmem_rsp_fault)
  );

  cpu_v01_fpga_tag_ram tag_ram (
    .clk(clk),
    .rst_n(rst_n),
    .req_valid(tagmem_req_valid),
    .req_ready(tagmem_req_ready),
    .req_write(tagmem_req_write),
    .req_slot_addr(tagmem_req_slot_addr),
    .req_wtag(tagmem_req_wtag),
    .rsp_valid(tagmem_rsp_valid),
    .rsp_rtag(tagmem_rsp_rtag)
  );

  initial begin
    clk = 1'b0;
    forever #5 clk = ~clk;
  end

  task automatic request_instruction(input addr_t addr);
    imem_req_addr = addr;
    imem_req_valid = 1'b1;
    @(posedge clk);
    #1;
    imem_req_valid = 1'b0;
    if (!imem_rsp_valid || imem_rsp_fault.valid) begin
      $fatal(1, "FPGA instruction ROM did not return initialized image data");
    end
  endtask

  task automatic write_data(input addr_t addr, input cell_t cell0, input cell_t cell1);
    dmem_req_addr = addr;
    dmem_req_len_cells = 3'd2;
    dmem_req_wdata[0] = cell0;
    dmem_req_wdata[1] = cell1;
    dmem_req_wdata[2] = '0;
    dmem_req_wdata[3] = '0;
    dmem_req_write = 1'b1;
    dmem_req_valid = 1'b1;
    @(posedge clk);
    #1;
    dmem_req_valid = 1'b0;
    dmem_req_write = 1'b0;
  endtask

  task automatic read_data(input addr_t addr);
    dmem_req_addr = addr;
    dmem_req_len_cells = 3'd2;
    dmem_req_write = 1'b0;
    dmem_req_valid = 1'b1;
    @(posedge clk);
    #1;
    dmem_req_valid = 1'b0;
    if (!dmem_rsp_valid || dmem_rsp_fault.valid) begin
      $fatal(1, "FPGA data RAM did not return a read response");
    end
  endtask

  task automatic write_tag(input addr_t addr, input logic tag);
    tagmem_req_slot_addr = addr;
    tagmem_req_wtag = tag;
    tagmem_req_write = 1'b1;
    tagmem_req_valid = 1'b1;
    @(posedge clk);
    #1;
    tagmem_req_valid = 1'b0;
    tagmem_req_write = 1'b0;
  endtask

  task automatic read_tag(input addr_t addr);
    tagmem_req_slot_addr = addr;
    tagmem_req_write = 1'b0;
    tagmem_req_valid = 1'b1;
    @(posedge clk);
    #1;
    tagmem_req_valid = 1'b0;
    if (!tagmem_rsp_valid) begin
      $fatal(1, "FPGA tag RAM did not return a tag response");
    end
  endtask

  initial begin
    imem_req_valid = 1'b0;
    imem_req_addr = '0;
    imem_rsp_ready = 1'b1;
    dmem_req_valid = 1'b0;
    dmem_req_write = 1'b0;
    dmem_req_addr = '0;
    dmem_req_len_cells = '0;
    tagmem_req_valid = 1'b0;
    tagmem_req_write = 1'b0;
    tagmem_req_slot_addr = '0;
    tagmem_req_wtag = 1'b0;
    for (int i = 0; i < CAPABILITY_OBJECT_CELLS; i++) begin
      dmem_req_wdata[i] = '0;
    end

    rst_n = 1'b0;
    repeat (2) @(posedge clk);
    rst_n = 1'b1;
    @(posedge clk);

    request_instruction(48'h0000_0000_1000);
    if (imem_rsp_cells[0] != 24'h05B05B || imem_rsp_cells[1] != 24'h05B05B) begin
      $fatal(1, "FPGA instruction ROM tiny image contents mismatch");
    end

    write_data(48'h0000_0001_0000, 24'h00CAFE, 24'h0BEEF0);
    read_data(48'h0000_0001_0000);
    if (dmem_rsp_rdata[0] != 24'h00CAFE || dmem_rsp_rdata[1] != 24'h0BEEF0) begin
      $fatal(1, "FPGA data RAM read/write contents mismatch");
    end

    write_tag(48'h0000_0001_0000, 1'b1);
    read_tag(48'h0000_0001_0000);
    if (!tagmem_rsp_rtag) begin
      $fatal(1, "FPGA tag RAM did not preserve CSC-style tag write");
    end

    write_tag(48'h0000_0001_0000, 1'b0);
    read_tag(48'h0000_0001_0000);
    if (tagmem_rsp_rtag) begin
      $fatal(1, "FPGA tag RAM did not clear tag on integer-store clear write");
    end

    $finish;
  end
endmodule
