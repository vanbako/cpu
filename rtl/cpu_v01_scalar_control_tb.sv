module cpu_v01_scalar_control_tb;
  import cpu_v01_pkg::*;

  logic clk;
  logic rst_n;
  logic retire_valid;
  retire_packet_t packet;
  logic scalar_passed;
  logic branch_passed;
  logic csr_passed;
  logic ccsr_passed;
  logic breakpoint_seen;
  logic pause_seen;
  int_reg_t scalar_result;
  cap_t pcc_value;
  cap_t epcc_value;
  logic [15:0] last_fault_cause;
  logic done;

  cpu_v01_scalar_control_core dut (
    .clk(clk),
    .rst_n(rst_n),
    .retire_valid(retire_valid),
    .retire_packet(packet),
    .scalar_passed(scalar_passed),
    .branch_passed(branch_passed),
    .csr_passed(csr_passed),
    .ccsr_passed(ccsr_passed),
    .breakpoint_seen(breakpoint_seen),
    .pause_seen(pause_seen),
    .scalar_result(scalar_result),
    .pcc_value(pcc_value),
    .epcc_value(epcc_value),
    .last_fault_cause(last_fault_cause),
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

    if (!scalar_passed || scalar_result != 48'h0000_0000_0042) begin
      $fatal(1, "scalar integer coverage result mismatch");
    end
    if (!branch_passed ||
        pcc_value.payload.cursor != 48'h0000_0000_1A00 ||
        epcc_value.payload.cursor != 48'h0000_0000_1E20) begin
      $fatal(1, "branch/control coverage result mismatch");
    end
    if (!csr_passed) begin
      $fatal(1, "CSR coverage result mismatch");
    end
    if (!ccsr_passed ||
        !retire_valid ||
        !packet.normal_valid ||
        !packet.ccsr_write_valid ||
        packet.ccsr_write_index != CCSR_DSC ||
        packet.ccsr_write_value.payload.cursor != 48'h0000_0000_2410) begin
      $fatal(1, "CCSR coverage result mismatch");
    end
    if (!breakpoint_seen || last_fault_cause != EXC_BREAKPOINT) begin
      $fatal(1, "BRK breakpoint coverage result mismatch");
    end
    if (!pause_seen) begin
      $fatal(1, "PAUSE retire coverage result mismatch");
    end

    $finish;
  end
endmodule
