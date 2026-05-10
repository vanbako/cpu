module cpu_v01_fpga_top_soc_smoke_tb;
  import cpu_v01_pkg::*;

  localparam addr_t RESET_VECTOR = 48'h0000_0000_1000;
  localparam addr_t UART_BASE = 48'h0000_00F0_0000;
  localparam addr_t TIMER_BASE = 48'h0000_00F0_0100;
  localparam addr_t GPIO_BASE = 48'h0000_00F0_0200;

  logic board_clk_i;
  logic board_reset_n_i;
  logic debug_halt_request_i;
  logic uart_rx_i;
  logic loader_req_valid_i;
  logic loader_req_ready_o;
  logic loader_req_write_i;
  addr_t loader_req_addr_i;
  cell_t loader_req_wdata_i;
  logic loader_req_tag_i;
  logic loader_uart_tx_i;
  logic uart_tx_o;
  logic loader_status_valid_o;
  logic [15:0] loader_status_code_o;
  logic pass_led_o;
  logic fail_led_o;
  logic heartbeat_led_o;
  logic status_reset_observed_o;
  logic status_core_idle_o;
  logic status_retire_valid_o;
  logic status_fault_valid_o;
  logic status_core_port_activity_o;
  logic [15:0] status_fault_code_o;
  logic [31:0] status_retire_count_o;
  logic debug_pcc_valid_o;
  logic [31:0] debug_pcc_cursor_low_o;
  logic [7:0] debug_pcc_permissions_o;
  logic [7:0] debug_sr_low_o;

  int unsigned uart_count_q;
  logic uart_start_bit_seen_q;
  logic timer_interrupt_seen_q;
  logic timer_ack_seen_q;
  logic timer_cleared_after_ack_q;
  logic gpio_pass_seen_q;
  logic sys_seen_q;
  logic iret_seen_q;
  logic pause_after_iret_seen_q;
  logic unexpected_fault_q;
  logic [15:0] unexpected_fault_code_q;

  cpu_v01_fpga_top #(
    .RESET_VECTOR(RESET_VECTOR),
    .ENABLE_FETCH(1'b1),
    .FIRST_TEST_PASS_RETIRE_COUNT(8),
    .UART_STATUS_ENABLE(1'b0),
    .UART_STATUS_CLOCK_HZ(10),
    .UART_STATUS_BAUD(10),
    .UART_STATUS_INTERVAL_CYCLES(2)
  ) dut (
    .board_clk_i(board_clk_i),
    .board_reset_n_i(board_reset_n_i),
    .debug_halt_request_i(debug_halt_request_i),
    .uart_rx_i(uart_rx_i),
    .loader_req_valid_i(loader_req_valid_i),
    .loader_req_ready_o(loader_req_ready_o),
    .loader_req_write_i(loader_req_write_i),
    .loader_req_addr_i(loader_req_addr_i),
    .loader_req_wdata_i(loader_req_wdata_i),
    .loader_req_tag_i(loader_req_tag_i),
    .loader_uart_tx_i(loader_uart_tx_i),
    .uart_tx_o(uart_tx_o),
    .loader_status_valid_o(loader_status_valid_o),
    .loader_status_code_o(loader_status_code_o),
    .pass_led_o(pass_led_o),
    .fail_led_o(fail_led_o),
    .heartbeat_led_o(heartbeat_led_o),
    .status_reset_observed_o(status_reset_observed_o),
    .status_core_idle_o(status_core_idle_o),
    .status_retire_valid_o(status_retire_valid_o),
    .status_fault_valid_o(status_fault_valid_o),
    .status_core_port_activity_o(status_core_port_activity_o),
    .status_fault_code_o(status_fault_code_o),
    .status_retire_count_o(status_retire_count_o),
    .debug_pcc_valid_o(debug_pcc_valid_o),
    .debug_pcc_cursor_low_o(debug_pcc_cursor_low_o),
    .debug_pcc_permissions_o(debug_pcc_permissions_o),
    .debug_sr_low_o(debug_sr_low_o)
  );

  initial begin
    board_clk_i = 1'b0;
    forever #5 board_clk_i = ~board_clk_i;
  end

  function automatic logic [7:0] expected_uart_byte(input int unsigned index);
    unique case (index)
      0: return 8'h49; // I
      1: return 8'h33; // 3
      2: return 8'h30; // 0
      3: return 8'h53; // S
      default: return 8'h00;
    endcase
  endfunction

  function automatic logic smoke_done();
    return uart_count_q == 4 &&
        uart_start_bit_seen_q &&
        timer_interrupt_seen_q &&
        timer_ack_seen_q &&
        timer_cleared_after_ack_q &&
        gpio_pass_seen_q &&
        sys_seen_q &&
        iret_seen_q &&
        pause_after_iret_seen_q &&
        pass_led_o &&
        fail_led_o &&
        heartbeat_led_o &&
        status_fault_valid_o &&
        status_fault_code_o == EXC_SYSCALL_TRAP &&
        !unexpected_fault_q;
  endfunction

  task automatic clear_loader_request();
    loader_req_valid_i = 1'b0;
    loader_req_write_i = 1'b0;
    loader_req_addr_i = '0;
    loader_req_wdata_i = '0;
    loader_req_tag_i = 1'b0;
  endtask

  task automatic seed_rom_fixture();
    dut.instruction_rom.rom_q[0] = 24'h311010; // ST48 C1, D0, D1
    dut.instruction_rom.rom_q[1] = 24'h311020; // ST48 C1, D0, D2
    dut.instruction_rom.rom_q[2] = 24'h311030; // ST48 C1, D0, D3
    dut.instruction_rom.rom_q[3] = 24'h311040; // ST48 C1, D0, D4
    dut.instruction_rom.rom_q[4] = 24'h3127A0; // ST48 C2, D7, D10
    dut.instruction_rom.rom_q[5] = 24'h3128B0; // ST48 C2, D8, D11
    dut.instruction_rom.rom_q[6] = 24'h05B05B; // PAUSE; PAUSE
    dut.instruction_rom.rom_q[7] = 24'h3129C0; // ST48 C2, D9, D12
    dut.instruction_rom.rom_q[8] = 24'h3139D0; // ST48 C3, D9, D13
    dut.instruction_rom.rom_q[9] = 24'h05B056; // SYS; PAUSE
    dut.instruction_rom.rom_q[256] = 24'h570000; // IRET
  endtask

  task automatic seed_core_fixture();
    dut.core.c_regs[1] = '0;
    dut.core.c_regs[1].tag = 1'b1;
    dut.core.c_regs[1].payload.cursor = UART_BASE;
    dut.core.c_regs[1].payload.permissions = 8'h02;
    dut.core.c_regs[1].payload.flags = 2'd1;

    dut.core.c_regs[2] = '0;
    dut.core.c_regs[2].tag = 1'b1;
    dut.core.c_regs[2].payload.cursor = TIMER_BASE;
    dut.core.c_regs[2].payload.permissions = 8'h02;
    dut.core.c_regs[2].payload.flags = 2'd1;

    dut.core.c_regs[3] = '0;
    dut.core.c_regs[3].tag = 1'b1;
    dut.core.c_regs[3].payload.cursor = GPIO_BASE;
    dut.core.c_regs[3].payload.permissions = 8'h02;
    dut.core.c_regs[3].payload.flags = 2'd1;

    dut.core.d_regs[1] = 48'h0000_0000_0049; // I
    dut.core.d_regs[2] = 48'h0000_0000_0033; // 3
    dut.core.d_regs[3] = 48'h0000_0000_0030; // 0
    dut.core.d_regs[4] = 48'h0000_0000_0053; // S
    dut.core.d_regs[7] = 48'd1; // TIMER_COMPARE offset
    dut.core.d_regs[8] = 48'd2; // TIMER_CONTROL offset
    dut.core.d_regs[9] = 48'd3; // TIMER_STATUS and STATUS_LEDS offset
    dut.core.d_regs[10] = 48'd3; // timer compare value
    dut.core.d_regs[11] = 48'd7; // enable, IRQ enable, one-shot
    dut.core.d_regs[12] = 48'd1; // acknowledge pending
    dut.core.d_regs[13] = 48'd5; // pass and heartbeat
  endtask

  always_ff @(posedge board_clk_i or negedge board_reset_n_i) begin
    if (!board_reset_n_i) begin
      uart_count_q <= 0;
      uart_start_bit_seen_q <= 1'b0;
      timer_interrupt_seen_q <= 1'b0;
      timer_ack_seen_q <= 1'b0;
      timer_cleared_after_ack_q <= 1'b0;
      gpio_pass_seen_q <= 1'b0;
      sys_seen_q <= 1'b0;
      iret_seen_q <= 1'b0;
      pause_after_iret_seen_q <= 1'b0;
      unexpected_fault_q <= 1'b0;
      unexpected_fault_code_q <= 16'd0;
    end else begin
      if (uart_tx_o == 1'b0) begin
        uart_start_bit_seen_q <= 1'b1;
      end

      if (dut.uart_req_valid && dut.uart_req_ready && dut.uart_req_write &&
          dut.uart_req_addr == UART_BASE) begin
        if (uart_count_q >= 4 ||
            dut.uart_req_wdata[7:0] != expected_uart_byte(uart_count_q)) begin
          $fatal(1, "FPGA SoC top smoke UART firmware output mismatch");
        end
        uart_count_q <= uart_count_q + 1;
      end

      if (dut.timer_interrupt_pending) begin
        timer_interrupt_seen_q <= 1'b1;
      end
      if (dut.timer_req_valid && dut.timer_req_ready && dut.timer_req_write &&
          dut.timer_req_addr == TIMER_BASE + 48'd3) begin
        if (!timer_interrupt_seen_q && !dut.timer_interrupt_pending) begin
          $fatal(1, "FPGA SoC top smoke acknowledged timer before pending asserted");
        end
        timer_ack_seen_q <= 1'b1;
      end
      if (timer_ack_seen_q && !dut.timer_interrupt_pending) begin
        timer_cleared_after_ack_q <= 1'b1;
      end

      if (dut.gpio_req_valid && dut.gpio_req_ready && dut.gpio_req_write &&
          dut.gpio_req_addr == GPIO_BASE + 48'd3 && dut.gpio_req_wdata[2:0] == 3'b101) begin
        gpio_pass_seen_q <= 1'b1;
      end

      if (dut.retire_valid && dut.retire_packet.fault.valid &&
          dut.retire_packet.decoded.opcode_id != OPC_SYS_12) begin
        unexpected_fault_q <= 1'b1;
        unexpected_fault_code_q <= dut.retire_packet.fault.cause;
      end
      if (dut.retire_valid && dut.retire_packet.decoded.opcode_id == OPC_SYS_12 &&
          dut.retire_packet.trap_entry_valid &&
          dut.retire_packet.fault.cause == EXC_SYSCALL_TRAP) begin
        sys_seen_q <= 1'b1;
      end
      if (dut.retire_valid && dut.retire_packet.decoded.opcode_id == OPC_IRET_24 &&
          dut.retire_packet.trap_frame_restore_valid) begin
        iret_seen_q <= 1'b1;
      end
      if (dut.retire_valid && dut.retire_packet.decoded.opcode_id == OPC_PAUSE_12 &&
          sys_seen_q && iret_seen_q) begin
        pause_after_iret_seen_q <= 1'b1;
      end
    end
  end

  initial begin
    debug_halt_request_i = 1'b0;
    uart_rx_i = 1'b1;
    loader_uart_tx_i = 1'b1;
    clear_loader_request();
    board_reset_n_i = 1'b0;
    #1;
    seed_rom_fixture();
    repeat (3) @(posedge board_clk_i);
    board_reset_n_i = 1'b1;
    wait (dut.core_rst_n === 1'b1);
    #1;
    seed_core_fixture();

    for (int cycle = 0; cycle < 500; cycle++) begin
      @(posedge board_clk_i);
      #1;
      if (smoke_done()) begin
        $finish;
      end
    end

    if (unexpected_fault_q) begin
      $fatal(1, "FPGA SoC top smoke saw unexpected first-failure status");
    end
    if (unexpected_fault_code_q != 16'd0) begin
      $fatal(1, "FPGA SoC top smoke preserved unexpected fault code");
    end
    $fatal(1, "FPGA SoC top smoke did not complete UART timer syscall GPIO checks");
  end

  // verilator lint_off UNUSEDSIGNAL
  wire logic unused_soc_smoke_outputs = &{
    loader_req_ready_o,
    loader_status_valid_o,
    loader_status_code_o,
    status_reset_observed_o,
    status_core_idle_o,
    status_retire_valid_o,
    status_core_port_activity_o,
    status_retire_count_o,
    debug_pcc_valid_o,
    debug_pcc_cursor_low_o,
    debug_pcc_permissions_o,
    debug_sr_low_o
  };
  // verilator lint_on UNUSEDSIGNAL
endmodule
