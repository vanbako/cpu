module cpu_v01_smoke_tb;
  import cpu_v01_pkg::*;

  logic clk;
  logic rst_n;
  logic normal_retire_valid;
  logic placement_retire_valid;
  retire_packet_t normal_packet;
  retire_packet_t placement_packet;
  int_reg_t normal_d2;
  int_reg_t placement_d2;
  logic normal_done;
  logic placement_done;

  cpu_v01_smoke_core #(
    .RESET_VECTOR(48'h0000_0000_1000),
    .FORCE_ILLEGAL_SLOT1(1'b0)
  ) normal_core (
    .clk(clk),
    .rst_n(rst_n),
    .retire_valid(normal_retire_valid),
    .retire_packet(normal_packet),
    .d2_value(normal_d2),
    .done(normal_done)
  );

  cpu_v01_smoke_core #(
    .RESET_VECTOR(48'h0000_0000_1700),
    .FORCE_ILLEGAL_SLOT1(1'b1)
  ) placement_core (
    .clk(clk),
    .rst_n(rst_n),
    .retire_valid(placement_retire_valid),
    .retire_packet(placement_packet),
    .d2_value(placement_d2),
    .done(placement_done)
  );

  initial begin
    clk = 1'b0;
    forever #5 clk = ~clk;
  end

  initial begin
    rst_n = 1'b0;
    repeat (2) @(posedge clk);
    rst_n = 1'b1;
    wait (normal_done && placement_done);

    if (!normal_retire_valid || !normal_packet.normal_valid) begin
      $fatal(1, "normal smoke core did not produce a normal retire packet");
    end
    if (normal_packet.\sequence  != 64'd0 ||
        normal_packet.pc_cell != 48'h0000_0000_1000 ||
        normal_packet.slot != SLOT_0 ||
        normal_packet.decoded.opcode_id != OPC_ADD_24 ||
        !normal_packet.integer_write_valid ||
        normal_packet.integer_write_index != 4'd2 ||
        normal_packet.integer_write_value != 48'h0000_0000_0030 ||
        normal_d2 != 48'h0000_0000_0030) begin
      $fatal(1, "normal smoke retire packet did not match golden reset smoke");
    end

    if (!placement_retire_valid ||
        !placement_packet.fault.valid ||
        placement_packet.fault.cause != EXC_ALIGN_FAULT ||
        placement_packet.slot != SLOT_1 ||
        placement_packet.normal_valid) begin
      $fatal(1, "placement smoke core did not produce the expected precise fault");
    end

    $finish;
  end
endmodule
