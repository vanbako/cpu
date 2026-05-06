module cpu_v01_cap_mem_tb;
  import cpu_v01_pkg::*;

  logic clk;
  logic rst_n;
  logic retire_valid;
  retire_packet_t packet;
  cap_t c2_value;
  cap_t c3_value;
  cap_t c4_value;
  cap_t c5_value;
  cap_t c6_value;
  int_reg_t d3_value;
  int_reg_t d8_value;
  logic memory_tag_value;
  logic done;

  cpu_v01_cap_mem_core dut (
    .clk(clk),
    .rst_n(rst_n),
    .retire_valid(retire_valid),
    .retire_packet(packet),
    .c2_value(c2_value),
    .c3_value(c3_value),
    .c4_value(c4_value),
    .c5_value(c5_value),
    .c6_value(c6_value),
    .d3_value(d3_value),
    .d8_value(d8_value),
    .memory_tag_value(memory_tag_value),
    .done(done)
  );

  initial begin
    clk = 1'b0;
    forever #5 clk = ~clk;
  end

  initial begin
    rst_n = 1'b0;
    repeat (2) @(posedge clk);
    rst_n = 1'b1;
    wait (done);

    if (d3_value != 48'h0000_0000_2200 || !c2_value.tag) begin
      $fatal(1, "CMOVE/CGETADDR smoke result mismatch");
    end
    if (c4_value.payload.cursor != 48'h0000_0000_2080 ||
        c5_value.payload.permissions != 8'h01) begin
      $fatal(1, "CSETADDR/CANDPERM smoke result mismatch");
    end
    if (!c6_value.tag || c6_value.payload.cursor != 48'h0000_0000_2100) begin
      $fatal(1, "CLC smoke result mismatch");
    end
    if (d8_value != 48'h1234_5678_9ABC || memory_tag_value != 1'b0) begin
      $fatal(1, "ST48/LD48 tag-clear smoke result mismatch");
    end
    if (!retire_valid ||
        packet.normal_valid ||
        !packet.fault.valid ||
        packet.fault.cause != EXC_CAPABILITY_TAG_FAULT ||
        packet.fault.capcause != CAPCAUSE_TAG ||
        packet.fault.fault_cap_idx != FAULT_CAP_IDX_C1) begin
      $fatal(1, "invalid-tag fault smoke result mismatch");
    end

    $finish;
  end
endmodule
