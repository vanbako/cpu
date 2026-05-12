module cpu_v01_fpga_top #(
  parameter cpu_v01_pkg::addr_t RESET_VECTOR = 48'h0000_0000_1000,
  parameter int RESET_SYNC_STAGES = 2,
  parameter bit ENABLE_FETCH = 1'b1,
  parameter int FIRST_TEST_PASS_RETIRE_COUNT = 8,
  parameter cpu_v01_pkg::addr_t DATA_RAM_BASE = 48'h0000_0001_0000,
  parameter int INSTRUCTION_ROM_CELLS = 1024,
  parameter int DATA_RAM_CELLS = 4096,
  parameter bit USE_ROM_INIT_FILE = 1'b0,
  parameter string ROM_INIT_FILE = "",
  parameter bit USE_DATA_INIT_FILE = 1'b0,
  parameter string DATA_INIT_FILE = "",
  parameter bit UART_STATUS_ENABLE = 1'b1,
  parameter int UART_STATUS_CLOCK_HZ = 25_000_000,
  parameter int UART_STATUS_BAUD = 115_200,
  parameter int UART_STATUS_INTERVAL_CYCLES = 25_000,
  parameter logic [31:0] DEBUG_BUILD_ID = 32'h2501_C0DE,
  parameter logic [255:0] IMAGE_SHA256 = 256'd0
) (
  input  logic board_clk_i,
  input  logic board_reset_n_i,
  input  logic debug_halt_request_i,
  input  logic uart_rx_i,
  input  logic loader_req_valid_i,
  output logic loader_req_ready_o,
  input  logic loader_req_write_i,
  input  cpu_v01_pkg::addr_t loader_req_addr_i,
  input  cpu_v01_pkg::cell_t loader_req_wdata_i,
  input  logic loader_req_tag_i,
  input  logic loader_uart_tx_i,

  output logic uart_tx_o,
  output logic loader_status_valid_o,
  output logic [15:0] loader_status_code_o,
  output logic pass_led_o,
  output logic fail_led_o,
  output logic heartbeat_led_o,
  output logic status_reset_observed_o,
  output logic status_core_idle_o,
  output logic status_retire_valid_o,
  output logic status_fault_valid_o,
  output logic status_core_port_activity_o,
  output logic [15:0] status_fault_code_o,
  output logic [31:0] status_retire_count_o,
  output logic debug_pcc_valid_o,
  output logic [31:0] debug_pcc_cursor_low_o,
  output logic [7:0] debug_pcc_permissions_o,
  output logic [7:0] debug_sr_low_o
);
  import cpu_v01_pkg::*;

  localparam logic [RETIRE_SEQUENCE_BITS-1:0] FIRST_TEST_PASS_THRESHOLD =
      RETIRE_SEQUENCE_BITS'(FIRST_TEST_PASS_RETIRE_COUNT - 1);
  localparam logic [15:0] STATUS_PACKET_MAGIC = 16'hC501;
  localparam logic [7:0] STATUS_PACKET_VERSION = 8'd1;
  localparam logic [7:0] STATUS_PACKET_SIZE_BYTES = 8'd32;
  localparam int STATUS_PACKET_BITS = 256;

  logic [RESET_SYNC_STAGES-1:0] reset_sync_q;
  logic core_rst_n;

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

  logic ram_req_valid;
  logic ram_req_ready;
  logic ram_req_write;
  addr_t ram_req_addr;
  logic [2:0] ram_req_len_cells;
  cell_t ram_req_wdata [CAPABILITY_OBJECT_CELLS];
  logic ram_rsp_valid;
  cell_t ram_rsp_rdata [CAPABILITY_OBJECT_CELLS];
  fault_packet_t ram_rsp_fault;
  logic loader_ram_req_valid;
  addr_t loader_ram_req_addr;
  cell_t loader_ram_req_wdata;
  cell_t loader_ram_req_wdata_cells [CAPABILITY_OBJECT_CELLS];
  cell_t data_ram_req_wdata [CAPABILITY_OBJECT_CELLS];
  logic loader_tag_clear_valid;
  addr_t loader_tag_clear_addr;
  logic loader_status_pulse;
  logic [15:0] loader_status_code;
  logic loader_status_valid_q;
  logic [15:0] loader_status_code_q;
  logic core_tagram_req_valid;
  logic tagram_req_write;
  addr_t tagram_req_slot_addr;
  logic tagram_req_wtag;

  logic uart_req_valid;
  logic uart_req_ready;
  logic uart_req_write;
  addr_t uart_req_addr;
  cell_t uart_req_wdata;
  logic uart_rsp_valid;
  cell_t uart_rsp_rdata;
  fault_packet_t uart_rsp_fault;

  logic timer_req_valid;
  logic timer_req_ready;
  logic timer_req_write;
  addr_t timer_req_addr;
  logic [2:0] timer_req_len_cells;
  cell_t timer_req_wdata [INTEGER_OBJECT_CELLS];
  logic timer_rsp_valid;
  cell_t timer_rsp_rdata [INTEGER_OBJECT_CELLS];
  fault_packet_t timer_rsp_fault;

  logic gpio_req_valid;
  logic gpio_req_ready;
  logic gpio_req_write;
  addr_t gpio_req_addr;
  cell_t gpio_req_wdata;
  logic gpio_rsp_valid;
  cell_t gpio_rsp_rdata;
  fault_packet_t gpio_rsp_fault;

  logic video_req_valid;
  logic video_req_ready;
  logic video_req_write;
  addr_t video_req_addr;
  logic [2:0] video_req_len_cells;
  cell_t video_req_wdata [INTEGER_OBJECT_CELLS];
  logic video_rsp_valid;
  cell_t video_rsp_rdata [INTEGER_OBJECT_CELLS];
  fault_packet_t video_rsp_fault;

  logic irq_req_valid;
  logic irq_req_ready;
  logic irq_req_write;
  addr_t irq_req_addr;
  cell_t irq_req_wdata;
  logic irq_rsp_valid;
  cell_t irq_rsp_rdata;
  fault_packet_t irq_rsp_fault;

  logic identity_req_valid;
  logic identity_req_ready;
  logic identity_req_write;
  addr_t identity_req_addr;
  logic [2:0] identity_req_len_cells;
  cell_t identity_req_wdata [CAPABILITY_OBJECT_CELLS];
  logic identity_rsp_valid;
  cell_t identity_rsp_rdata [CAPABILITY_OBJECT_CELLS];
  fault_packet_t identity_rsp_fault;

  logic tagmem_req_valid;
  logic tagmem_req_ready;
  logic tagmem_req_write;
  addr_t tagmem_req_slot_addr;
  logic tagmem_req_wtag;
  logic tagmem_rsp_valid;
  logic tagmem_rsp_rtag;
  logic tagmem_req_in_data_ram;
  logic tagram_req_valid;
  logic tagram_req_ready;
  logic tagram_rsp_valid;
  logic tagram_rsp_rtag;
  logic tagmem_bypass_rsp_valid_q;

  logic retire_valid;
  retire_packet_t retire_packet;
  logic core_idle;
  logic reset_observed;
  cap_t debug_pcc;
  logic debug_pcc_slot;
  int_reg_t debug_sr;
  logic [RETIRE_SEQUENCE_BITS-1:0] debug_retire_sequence;
  logic pass_sticky_q;
  logic fault_sticky_q;
  logic [15:0] fault_code_q;
  logic core_port_activity;
  logic [15:0] uart_status_flags;
  logic [7:0] uart_status_pass_fail_state;
  logic [STATUS_PACKET_BITS-1:0] uart_status_packet;
  logic [31:0] uart_status_sequence_q;
  logic uart_status_packet_started;
  logic status_uart_tx;
  logic uart_mmio_tx;
  logic uart_rx_ready_irq;
  logic uart_tx_ready_irq;
  logic timer_compare_irq;
  logic timer_interrupt_pending;
  logic external_interrupt_pending;
  logic timer_pending;
  logic [15:0] gpio_out;
  logic [15:0] gpio_oe;
  logic gpio_pass_led;
  logic gpio_fail_led;
  logic gpio_heartbeat_led;
  logic [3:0] gpio_status_leds;
  logic [7:0] gpio_debug_status_select;
  logic gpio_status_irq;
  logic video_scanout_enable;
  logic video_output_enable;
  logic [15:0] video_mode;
  logic [3:0] video_test_pattern;
  logic [23:0] video_bg_color;
  logic video_vblank_source;
  logic [47:0] video_frame_count_source;
  logic [15:0] video_line_count_source;
  logic [15:0] video_pixel_count_source;
  logic video_underflow_pulse_source;
  logic [15:0] video_fb_master_status_source;
  logic video_vblank_irq;
  logic [15:0] irq_sources;
  logic [15:0] irq_pending_enabled;

  assign core_rst_n = reset_sync_q[RESET_SYNC_STAGES-1];

  assign uart_tx_o = uart_mmio_tx & status_uart_tx & loader_uart_tx_i;
  assign loader_status_valid_o = loader_status_valid_q;
  assign loader_status_code_o = loader_status_code_q;
  assign pass_led_o = pass_sticky_q && !fault_sticky_q || gpio_pass_led;
  assign fail_led_o = fault_sticky_q || gpio_fail_led;
  assign heartbeat_led_o = debug_retire_sequence[0] || gpio_heartbeat_led;
  assign status_reset_observed_o = reset_observed;
  assign status_core_idle_o = core_idle;
  assign status_retire_valid_o = retire_valid;
  assign status_fault_valid_o =
      fault_sticky_q || (loader_status_valid_q && loader_status_code_q != 16'h0000);
  assign status_core_port_activity_o = core_port_activity;
  assign status_fault_code_o =
      (loader_status_valid_q && loader_status_code_q != 16'h0000)
          ? loader_status_code_q : fault_code_q;
  assign status_retire_count_o = debug_retire_sequence[31:0];
  assign debug_pcc_valid_o = debug_pcc.tag && !debug_pcc_slot;
  assign debug_pcc_cursor_low_o = debug_pcc.payload.cursor[31:0];
  assign debug_pcc_permissions_o = debug_pcc.payload.permissions;
  assign debug_sr_low_o = debug_sr[7:0];
  assign video_vblank_source = 1'b0;
  assign video_frame_count_source = 48'd0;
  assign video_line_count_source = 16'd0;
  assign video_pixel_count_source = 16'd0;
  assign video_underflow_pulse_source = 1'b0;
  assign video_fb_master_status_source = 16'd0;
  assign irq_sources = {
    11'd0,
    video_vblank_irq,
    gpio_status_irq,
    timer_compare_irq,
    uart_tx_ready_irq,
    uart_rx_ready_irq
  };
  assign timer_interrupt_pending = timer_compare_irq;
  assign external_interrupt_pending = |(irq_pending_enabled & 16'h001B);
  assign tagmem_req_in_data_ram =
      tagmem_req_slot_addr >= DATA_RAM_BASE &&
      tagmem_req_slot_addr < DATA_RAM_BASE + addr_t'(DATA_RAM_CELLS);
  assign tagmem_req_ready = tagmem_req_in_data_ram ? tagram_req_ready : 1'b1;
  assign tagmem_rsp_valid = tagram_rsp_valid || tagmem_bypass_rsp_valid_q;
  assign tagmem_rsp_rtag = tagram_rsp_valid ? tagram_rsp_rtag : 1'b0;

  always_comb begin
    uart_status_flags = 16'd0;
    uart_status_flags[0] = !core_rst_n;
    uart_status_flags[1] = reset_observed;
    uart_status_flags[2] = core_idle;
    uart_status_flags[3] = retire_valid;
    uart_status_flags[4] = fault_sticky_q ||
        (loader_status_valid_q && loader_status_code_q != 16'h0000);
    uart_status_flags[5] = pass_led_o;
    uart_status_flags[6] = fail_led_o;
    uart_status_flags[7] = heartbeat_led_o;

    if (!core_rst_n) begin
      uart_status_pass_fail_state = 8'd0;
    end else if (fault_sticky_q) begin
      uart_status_pass_fail_state = 8'd3;
    end else if (pass_led_o) begin
      uart_status_pass_fail_state = 8'd2;
    end else if (core_idle) begin
      uart_status_pass_fail_state = 8'd0;
    end else begin
      uart_status_pass_fail_state = 8'd1;
    end

    uart_status_packet = '0;
    uart_status_packet[0 +: 16] = STATUS_PACKET_MAGIC;
    uart_status_packet[16 +: 8] = STATUS_PACKET_VERSION;
    uart_status_packet[24 +: 8] = STATUS_PACKET_SIZE_BYTES;
    uart_status_packet[32 +: 16] = uart_status_flags;
    uart_status_packet[48 +: 8] = {7'd0, retire_packet.slot};
    uart_status_packet[56 +: 8] = uart_status_pass_fail_state;
    uart_status_packet[64 +: 64] =
        {16'd0, (retire_valid ? retire_packet.pc_cell : debug_pcc.payload.cursor)};
    uart_status_packet[128 +: 32] = debug_retire_sequence[31:0];
    uart_status_packet[160 +: 16] =
        (loader_status_valid_q && loader_status_code_q != 16'h0000)
            ? loader_status_code_q : fault_code_q;
    uart_status_packet[176 +: 16] =
        retire_packet.fault.valid ? retire_packet.fault.cause : 16'd0;
    uart_status_packet[192 +: 32] = DEBUG_BUILD_ID;
    uart_status_packet[224 +: 32] = uart_status_sequence_q;
  end

  always_ff @(posedge board_clk_i or negedge board_reset_n_i) begin
    if (!board_reset_n_i) begin
      reset_sync_q <= '0;
    end else begin
      reset_sync_q <= {reset_sync_q[RESET_SYNC_STAGES-2:0], 1'b1};
    end
  end

  always_ff @(posedge board_clk_i or negedge core_rst_n) begin
    if (!core_rst_n) begin
      uart_status_sequence_q <= 32'd0;
    end else if (uart_status_packet_started) begin
      uart_status_sequence_q <= uart_status_sequence_q + 32'd1;
    end
  end

  always_ff @(posedge board_clk_i or negedge core_rst_n) begin
    if (!core_rst_n) begin
      pass_sticky_q <= 1'b0;
      fault_sticky_q <= 1'b0;
      fault_code_q <= 16'd0;
    end else if (retire_packet.fault.valid) begin
      fault_sticky_q <= 1'b1;
      fault_code_q <= retire_packet.fault.cause;
    end else if (retire_valid && debug_retire_sequence >= FIRST_TEST_PASS_THRESHOLD) begin
      pass_sticky_q <= 1'b1;
    end
  end

  always_ff @(posedge board_clk_i or negedge core_rst_n) begin
    if (!core_rst_n) begin
      loader_status_valid_q <= 1'b0;
      loader_status_code_q <= 16'd0;
    end else if (loader_status_pulse) begin
      loader_status_valid_q <= 1'b1;
      loader_status_code_q <= loader_status_code;
    end
  end

  always_ff @(posedge board_clk_i or negedge core_rst_n) begin
    if (!core_rst_n) begin
      tagmem_bypass_rsp_valid_q <= 1'b0;
    end else begin
      tagmem_bypass_rsp_valid_q <=
          tagmem_req_valid && tagmem_req_ready && !tagmem_req_write && !tagmem_req_in_data_ram;
    end
  end

  always_comb begin
    core_port_activity =
        imem_req_valid || imem_rsp_ready || (imem_req_valid && (|imem_req_addr)) ||
        dmem_req_valid || dmem_req_write || (dmem_req_valid && (|dmem_req_addr)) ||
        (dmem_req_valid && (|dmem_req_len_cells)) ||
        tagmem_req_valid || tagmem_req_write ||
        (tagmem_req_valid && (|tagmem_req_slot_addr)) ||
        tagmem_req_wtag || loader_req_valid_i || loader_status_valid_q || retire_valid;
    for (int i = 0; i < CAPABILITY_OBJECT_CELLS; i++) begin
      core_port_activity = core_port_activity || (dmem_req_valid && (|dmem_req_wdata[i]));
    end
  end

  cpu_v01_fpga_imem_rom #(
    .BASE_CELL(RESET_VECTOR),
    .DEPTH_CELLS(INSTRUCTION_ROM_CELLS),
    .USE_INIT_FILE(USE_ROM_INIT_FILE),
    .INIT_FILE(ROM_INIT_FILE)
  ) instruction_rom (
    .clk(board_clk_i),
    .rst_n(core_rst_n),
    .req_valid(imem_req_valid),
    .req_ready(imem_req_ready),
    .req_addr(imem_req_addr),
    .rsp_valid(imem_rsp_valid),
    .rsp_ready(imem_rsp_ready),
    .rsp_cells(imem_rsp_cells),
    .rsp_fault(imem_rsp_fault)
  );

  cpu_v01_fpga_data_ram #(
    .BASE_CELL(DATA_RAM_BASE),
    .DEPTH_CELLS(DATA_RAM_CELLS),
    .USE_INIT_FILE(USE_DATA_INIT_FILE),
    .INIT_FILE(DATA_INIT_FILE)
  ) data_ram (
    .clk(board_clk_i),
    .rst_n(core_rst_n),
    .req_valid(loader_ram_req_valid || ram_req_valid),
    .req_ready(ram_req_ready),
    .req_write(loader_ram_req_valid ? 1'b1 : ram_req_write),
    .req_addr(loader_ram_req_valid ? loader_ram_req_addr : ram_req_addr),
    .req_len_cells(loader_ram_req_valid ? 3'd1 : ram_req_len_cells),
    .req_wdata(data_ram_req_wdata),
    .rsp_valid(ram_rsp_valid),
    .rsp_rdata(ram_rsp_rdata),
    .rsp_fault(ram_rsp_fault)
  );

  always_comb begin
    for (int i = 0; i < CAPABILITY_OBJECT_CELLS; i++) begin
      loader_ram_req_wdata_cells[i] = '0;
      data_ram_req_wdata[i] =
          loader_ram_req_valid ? loader_ram_req_wdata_cells[i] : ram_req_wdata[i];
    end
    loader_ram_req_wdata_cells[0] = loader_ram_req_wdata;
    data_ram_req_wdata[0] = loader_ram_req_valid ? loader_ram_req_wdata : ram_req_wdata[0];
  end

  cpu_v01_fpga_soc_dmem_decoder #(
    .DATA_RAM_BASE(DATA_RAM_BASE),
    .DATA_RAM_CELLS(DATA_RAM_CELLS)
  ) soc_dmem_decoder (
    .clk(board_clk_i),
    .rst_n(core_rst_n),
    .core_req_valid(dmem_req_valid),
    .core_req_ready(dmem_req_ready),
    .core_req_write(dmem_req_write),
    .core_req_addr(dmem_req_addr),
    .core_req_len_cells(dmem_req_len_cells),
    .core_req_wdata(dmem_req_wdata),
    .core_rsp_valid(dmem_rsp_valid),
    .core_rsp_rdata(dmem_rsp_rdata),
    .core_rsp_fault(dmem_rsp_fault),
    .ram_req_valid(ram_req_valid),
    .ram_req_ready(ram_req_ready),
    .ram_req_write(ram_req_write),
    .ram_req_addr(ram_req_addr),
    .ram_req_len_cells(ram_req_len_cells),
    .ram_req_wdata(ram_req_wdata),
    .ram_rsp_valid(ram_rsp_valid),
    .ram_rsp_rdata(ram_rsp_rdata),
    .ram_rsp_fault(ram_rsp_fault),
    .uart_req_valid(uart_req_valid),
    .uart_req_ready(uart_req_ready),
    .uart_req_write(uart_req_write),
    .uart_req_addr(uart_req_addr),
    .uart_req_wdata(uart_req_wdata),
    .uart_rsp_valid(uart_rsp_valid),
    .uart_rsp_rdata(uart_rsp_rdata),
    .uart_rsp_fault(uart_rsp_fault),
    .timer_req_valid(timer_req_valid),
    .timer_req_ready(timer_req_ready),
    .timer_req_write(timer_req_write),
    .timer_req_addr(timer_req_addr),
    .timer_req_len_cells(timer_req_len_cells),
    .timer_req_wdata(timer_req_wdata),
    .timer_rsp_valid(timer_rsp_valid),
    .timer_rsp_rdata(timer_rsp_rdata),
    .timer_rsp_fault(timer_rsp_fault),
    .gpio_req_valid(gpio_req_valid),
    .gpio_req_ready(gpio_req_ready),
    .gpio_req_write(gpio_req_write),
    .gpio_req_addr(gpio_req_addr),
    .gpio_req_wdata(gpio_req_wdata),
    .gpio_rsp_valid(gpio_rsp_valid),
    .gpio_rsp_rdata(gpio_rsp_rdata),
    .gpio_rsp_fault(gpio_rsp_fault),
    .video_req_valid(video_req_valid),
    .video_req_ready(video_req_ready),
    .video_req_write(video_req_write),
    .video_req_addr(video_req_addr),
    .video_req_len_cells(video_req_len_cells),
    .video_req_wdata(video_req_wdata),
    .video_rsp_valid(video_rsp_valid),
    .video_rsp_rdata(video_rsp_rdata),
    .video_rsp_fault(video_rsp_fault),
    .irq_req_valid(irq_req_valid),
    .irq_req_ready(irq_req_ready),
    .irq_req_write(irq_req_write),
    .irq_req_addr(irq_req_addr),
    .irq_req_wdata(irq_req_wdata),
    .irq_rsp_valid(irq_rsp_valid),
    .irq_rsp_rdata(irq_rsp_rdata),
    .irq_rsp_fault(irq_rsp_fault),
    .identity_req_valid(identity_req_valid),
    .identity_req_ready(identity_req_ready),
    .identity_req_write(identity_req_write),
    .identity_req_addr(identity_req_addr),
    .identity_req_len_cells(identity_req_len_cells),
    .identity_req_wdata(identity_req_wdata),
    .identity_rsp_valid(identity_rsp_valid),
    .identity_rsp_rdata(identity_rsp_rdata),
    .identity_rsp_fault(identity_rsp_fault)
  );

  cpu_v01_fpga_uart_mmio #(
    .CLOCK_HZ(UART_STATUS_CLOCK_HZ),
    .BAUD(UART_STATUS_BAUD)
  ) firmware_uart (
    .clk(board_clk_i),
    .rst_n(core_rst_n),
    .req_valid(uart_req_valid),
    .req_ready(uart_req_ready),
    .req_write(uart_req_write),
    .req_addr(uart_req_addr),
    .req_wdata(uart_req_wdata),
    .rsp_valid(uart_rsp_valid),
    .rsp_rdata(uart_rsp_rdata),
    .rsp_fault(uart_rsp_fault),
    .uart_rx_i(uart_rx_i),
    .uart_tx_o(uart_mmio_tx),
    .irq_rx_ready_o(uart_rx_ready_irq),
    .irq_tx_ready_o(uart_tx_ready_irq)
  );

  cpu_v01_fpga_timer_mmio firmware_timer (
    .clk(board_clk_i),
    .rst_n(core_rst_n),
    .req_valid(timer_req_valid),
    .req_ready(timer_req_ready),
    .req_write(timer_req_write),
    .req_addr(timer_req_addr),
    .req_len_cells(timer_req_len_cells),
    .req_wdata(timer_req_wdata),
    .rsp_valid(timer_rsp_valid),
    .rsp_rdata(timer_rsp_rdata),
    .rsp_fault(timer_rsp_fault),
    .timer_interrupt_o(timer_compare_irq),
    .timer_pending_o(timer_pending)
  );

  cpu_v01_fpga_gpio_status firmware_gpio_status (
    .clk(board_clk_i),
    .rst_n(core_rst_n),
    .req_valid(gpio_req_valid),
    .req_ready(gpio_req_ready),
    .req_write(gpio_req_write),
    .req_addr(gpio_req_addr),
    .req_wdata(gpio_req_wdata),
    .rsp_valid(gpio_rsp_valid),
    .rsp_rdata(gpio_rsp_rdata),
    .rsp_fault(gpio_rsp_fault),
    .board_gpio_i(16'd0),
    .gpio_out_o(gpio_out),
    .gpio_oe_o(gpio_oe),
    .pass_led_o(gpio_pass_led),
    .fail_led_o(gpio_fail_led),
    .heartbeat_led_o(gpio_heartbeat_led),
    .status_leds_o(gpio_status_leds),
    .debug_status_select_o(gpio_debug_status_select),
    .gpio_status_irq_o(gpio_status_irq)
  );

  cpu_v01_fpga_video_mmio firmware_video (
    .clk(board_clk_i),
    .rst_n(core_rst_n),
    .req_valid(video_req_valid),
    .req_ready(video_req_ready),
    .req_write(video_req_write),
    .req_addr(video_req_addr),
    .req_len_cells(video_req_len_cells),
    .req_wdata(video_req_wdata),
    .rsp_valid(video_rsp_valid),
    .rsp_rdata(video_rsp_rdata),
    .rsp_fault(video_rsp_fault),
    .video_vblank_i(video_vblank_source),
    .video_underflow_pulse_i(video_underflow_pulse_source),
    .video_frame_count_i(video_frame_count_source),
    .video_line_count_i(video_line_count_source),
    .video_pixel_count_i(video_pixel_count_source),
    .video_fb_master_status_i(video_fb_master_status_source),
    .video_scanout_enable_o(video_scanout_enable),
    .video_output_enable_o(video_output_enable),
    .video_mode_o(video_mode),
    .video_test_pattern_o(video_test_pattern),
    .video_bg_color_o(video_bg_color),
    .video_vblank_irq_o(video_vblank_irq)
  );

  cpu_v01_fpga_irq_mmio firmware_irq (
    .clk(board_clk_i),
    .rst_n(core_rst_n),
    .req_valid(irq_req_valid),
    .req_ready(irq_req_ready),
    .req_write(irq_req_write),
    .req_addr(irq_req_addr),
    .req_wdata(irq_req_wdata),
    .rsp_valid(irq_rsp_valid),
    .rsp_rdata(irq_rsp_rdata),
    .rsp_fault(irq_rsp_fault),
    .irq_sources_i(irq_sources),
    .irq_pending_enabled_o(irq_pending_enabled)
  );

  cpu_v01_fpga_system_identity_mmio #(
    .BUILD_ID({64'd0, DEBUG_BUILD_ID}),
    .IMAGE_SHA256(IMAGE_SHA256)
  ) system_identity (
    .clk(board_clk_i),
    .rst_n(core_rst_n),
    .req_valid(identity_req_valid),
    .req_ready(identity_req_ready),
    .req_write(identity_req_write),
    .req_addr(identity_req_addr),
    .req_len_cells(identity_req_len_cells),
    .req_wdata(identity_req_wdata),
    .rsp_valid(identity_rsp_valid),
    .rsp_rdata(identity_rsp_rdata),
    .rsp_fault(identity_rsp_fault)
  );

  cpu_v01_fpga_tag_ram #(
    .BASE_CELL(DATA_RAM_BASE),
    .DEPTH_ENTRIES(DATA_RAM_CELLS)
  ) tag_ram (
    .clk(board_clk_i),
    .rst_n(core_rst_n),
    .req_valid(tagram_req_valid),
    .req_ready(tagram_req_ready),
    .req_write(tagram_req_write),
    .req_slot_addr(tagram_req_slot_addr),
    .req_wtag(tagram_req_wtag),
    .rsp_valid(tagram_rsp_valid),
    .rsp_rtag(tagram_rsp_rtag)
  );
  assign core_tagram_req_valid = tagmem_req_valid && tagmem_req_in_data_ram;
  assign tagram_req_valid = loader_tag_clear_valid || core_tagram_req_valid;
  assign tagram_req_write = loader_tag_clear_valid ? 1'b1 : tagmem_req_write;
  assign tagram_req_slot_addr =
      loader_tag_clear_valid ? loader_tag_clear_addr : tagmem_req_slot_addr;
  assign tagram_req_wtag = loader_tag_clear_valid ? 1'b0 : tagmem_req_wtag;

  cpu_v01_fpga_soc_loader_handoff #(
    .DATA_RAM_BASE(DATA_RAM_BASE),
    .DATA_RAM_CELLS(DATA_RAM_CELLS)
  ) loader_handoff (
    .clk(board_clk_i),
    .rst_n(core_rst_n),
    .loader_req_valid(loader_req_valid_i),
    .loader_req_ready(loader_req_ready_o),
    .loader_req_write(loader_req_write_i),
    .loader_req_addr(loader_req_addr_i),
    .loader_req_wdata(loader_req_wdata_i),
    .loader_req_tag(loader_req_tag_i),
    .loader_path_ready(!ram_req_valid && !core_tagram_req_valid),
    .ram_req_valid(loader_ram_req_valid),
    .ram_req_addr(loader_ram_req_addr),
    .ram_req_wdata(loader_ram_req_wdata),
    .tag_clear_valid(loader_tag_clear_valid),
    .tag_clear_addr(loader_tag_clear_addr),
    .status_valid(loader_status_pulse),
    .status_code(loader_status_code)
  );

  cpu_v01_fpga_uart_status_streamer #(
    .ENABLE(UART_STATUS_ENABLE),
    .CLOCK_HZ(UART_STATUS_CLOCK_HZ),
    .BAUD(UART_STATUS_BAUD),
    .STATUS_INTERVAL_CYCLES(UART_STATUS_INTERVAL_CYCLES)
  ) status_uart (
    .clk(board_clk_i),
    .rst_n(core_rst_n),
    .packet_i(uart_status_packet),
    .packet_started_o(uart_status_packet_started),
    .uart_tx_o(status_uart_tx)
  );

  // verilator lint_off UNUSEDSIGNAL
  wire logic unused_i30_s02_outputs = &{
    timer_pending,
    gpio_out,
    gpio_oe,
    gpio_status_leds,
    gpio_debug_status_select
  };
  // verilator lint_on UNUSEDSIGNAL

  cpu_v01_core #(
    .RESET_VECTOR(RESET_VECTOR),
    .ENABLE_FETCH(ENABLE_FETCH)
  ) core (
    .clk(board_clk_i),
    .rst_n(core_rst_n),
    .imem_req_valid(imem_req_valid),
    .imem_req_ready(imem_req_ready),
    .imem_req_addr(imem_req_addr),
    .imem_rsp_valid(imem_rsp_valid),
    .imem_rsp_ready(imem_rsp_ready),
    .imem_rsp_cells(imem_rsp_cells),
    .imem_rsp_fault(imem_rsp_fault),
    .dmem_req_valid(dmem_req_valid),
    .dmem_req_ready(dmem_req_ready),
    .dmem_req_write(dmem_req_write),
    .dmem_req_addr(dmem_req_addr),
    .dmem_req_len_cells(dmem_req_len_cells),
    .dmem_req_wdata(dmem_req_wdata),
    .dmem_rsp_valid(dmem_rsp_valid),
    .dmem_rsp_rdata(dmem_rsp_rdata),
    .dmem_rsp_fault(dmem_rsp_fault),
    .tagmem_req_valid(tagmem_req_valid),
    .tagmem_req_ready(tagmem_req_ready),
    .tagmem_req_write(tagmem_req_write),
    .tagmem_req_slot_addr(tagmem_req_slot_addr),
    .tagmem_req_wtag(tagmem_req_wtag),
    .tagmem_rsp_valid(tagmem_rsp_valid),
    .tagmem_rsp_rtag(tagmem_rsp_rtag),
    .timer_interrupt_pending(timer_interrupt_pending),
    .software_interrupt_pending(1'b0),
    .external_interrupt_pending(external_interrupt_pending),
    .external_event_valid(1'b0),
    .external_event_cause(16'd0),
    .debug_halt_request(debug_halt_request_i),
    .retire_valid(retire_valid),
    .retire_ready(1'b1),
    .retire_packet(retire_packet),
    .core_idle(core_idle),
    .reset_observed(reset_observed),
    .debug_pcc(debug_pcc),
    .debug_pcc_slot(debug_pcc_slot),
    .debug_sr(debug_sr),
    .debug_retire_sequence(debug_retire_sequence)
  );
endmodule

module cpu_v01_fpga_soc_loader_handoff #(
  parameter cpu_v01_pkg::addr_t DATA_RAM_BASE = 48'h0000_0001_0000,
  parameter int DATA_RAM_CELLS = 4096
) (
  input  logic clk,
  input  logic rst_n,

  input  logic loader_req_valid,
  output logic loader_req_ready,
  input  logic loader_req_write,
  input  cpu_v01_pkg::addr_t loader_req_addr,
  input  cpu_v01_pkg::cell_t loader_req_wdata,
  input  logic loader_req_tag,
  input  logic loader_path_ready,

  output logic ram_req_valid,
  output cpu_v01_pkg::addr_t ram_req_addr,
  output cpu_v01_pkg::cell_t ram_req_wdata,
  output logic tag_clear_valid,
  output cpu_v01_pkg::addr_t tag_clear_addr,

  output logic status_valid,
  output logic [15:0] status_code
);
  import cpu_v01_pkg::*;

  localparam logic [15:0] LOAD_STATUS_OK = 16'h0000;
  localparam logic [15:0] LOAD_STATUS_BAD_TARGET = 16'h2603;
  localparam logic [15:0] LOAD_STATUS_TAG_POLICY = 16'h2605;
  localparam logic [15:0] LOAD_STATUS_MALFORMED = 16'h2607;

  logic request_accepted;
  logic request_allowed;
  logic target_in_data_ram;
  logic [15:0] next_status_code;

  assign loader_req_ready = loader_path_ready;
  assign request_accepted = loader_req_valid && loader_req_ready;
  assign target_in_data_ram =
      loader_req_addr >= DATA_RAM_BASE &&
      loader_req_addr < DATA_RAM_BASE + addr_t'(DATA_RAM_CELLS);
  assign request_allowed = loader_req_write && target_in_data_ram && !loader_req_tag;
  assign ram_req_valid = request_accepted && request_allowed;
  assign ram_req_addr = loader_req_addr;
  assign ram_req_wdata = loader_req_wdata;
  assign tag_clear_valid = request_accepted && request_allowed;
  assign tag_clear_addr = loader_req_addr;

  always_comb begin
    if (!loader_req_write) begin
      next_status_code = LOAD_STATUS_MALFORMED;
    end else if (!target_in_data_ram) begin
      next_status_code = LOAD_STATUS_BAD_TARGET;
    end else if (loader_req_tag) begin
      next_status_code = LOAD_STATUS_TAG_POLICY;
    end else begin
      next_status_code = LOAD_STATUS_OK;
    end
  end

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      status_valid <= 1'b0;
      status_code <= LOAD_STATUS_OK;
    end else begin
      status_valid <= request_accepted;
      if (request_accepted) begin
        status_code <= next_status_code;
      end
    end
  end
endmodule

module cpu_v01_fpga_soc_dmem_decoder #(
  parameter cpu_v01_pkg::addr_t DATA_RAM_BASE = 48'h0000_0001_0000,
  parameter int DATA_RAM_CELLS = 4096,
  parameter cpu_v01_pkg::addr_t UART_BASE = 48'h0000_00F0_0000,
  parameter cpu_v01_pkg::addr_t TIMER_BASE = 48'h0000_00F0_0100,
  parameter cpu_v01_pkg::addr_t GPIO_STATUS_BASE = 48'h0000_00F0_0200,
  parameter cpu_v01_pkg::addr_t IRQ_BASE = 48'h0000_00F0_0300,
  parameter cpu_v01_pkg::addr_t SYSTEM_IDENTITY_BASE = 48'h0000_00F0_0400,
  parameter cpu_v01_pkg::addr_t VIDEO_BASE = 48'h0000_00F0_0500,
  parameter int SOC_PERIPHERAL_CELLS = 256
) (
  input  logic clk,
  input  logic rst_n,

  input  logic core_req_valid,
  output logic core_req_ready,
  input  logic core_req_write,
  input  cpu_v01_pkg::addr_t core_req_addr,
  input  logic [2:0] core_req_len_cells,
  input  cpu_v01_pkg::cell_t core_req_wdata [cpu_v01_pkg::CAPABILITY_OBJECT_CELLS],

  output logic core_rsp_valid,
  output cpu_v01_pkg::cell_t core_rsp_rdata [cpu_v01_pkg::CAPABILITY_OBJECT_CELLS],
  output cpu_v01_pkg::fault_packet_t core_rsp_fault,

  output logic ram_req_valid,
  input  logic ram_req_ready,
  output logic ram_req_write,
  output cpu_v01_pkg::addr_t ram_req_addr,
  output logic [2:0] ram_req_len_cells,
  output cpu_v01_pkg::cell_t ram_req_wdata [cpu_v01_pkg::CAPABILITY_OBJECT_CELLS],
  input  logic ram_rsp_valid,
  input  cpu_v01_pkg::cell_t ram_rsp_rdata [cpu_v01_pkg::CAPABILITY_OBJECT_CELLS],
  input  cpu_v01_pkg::fault_packet_t ram_rsp_fault,

  output logic uart_req_valid,
  input  logic uart_req_ready,
  output logic uart_req_write,
  output cpu_v01_pkg::addr_t uart_req_addr,
  output cpu_v01_pkg::cell_t uart_req_wdata,
  input  logic uart_rsp_valid,
  input  cpu_v01_pkg::cell_t uart_rsp_rdata,
  input  cpu_v01_pkg::fault_packet_t uart_rsp_fault,

  output logic timer_req_valid,
  input  logic timer_req_ready,
  output logic timer_req_write,
  output cpu_v01_pkg::addr_t timer_req_addr,
  output logic [2:0] timer_req_len_cells,
  output cpu_v01_pkg::cell_t timer_req_wdata [cpu_v01_pkg::INTEGER_OBJECT_CELLS],
  input  logic timer_rsp_valid,
  input  cpu_v01_pkg::cell_t timer_rsp_rdata [cpu_v01_pkg::INTEGER_OBJECT_CELLS],
  input  cpu_v01_pkg::fault_packet_t timer_rsp_fault,

  output logic gpio_req_valid,
  input  logic gpio_req_ready,
  output logic gpio_req_write,
  output cpu_v01_pkg::addr_t gpio_req_addr,
  output cpu_v01_pkg::cell_t gpio_req_wdata,
  input  logic gpio_rsp_valid,
  input  cpu_v01_pkg::cell_t gpio_rsp_rdata,
  input  cpu_v01_pkg::fault_packet_t gpio_rsp_fault,

  output logic video_req_valid,
  input  logic video_req_ready,
  output logic video_req_write,
  output cpu_v01_pkg::addr_t video_req_addr,
  output logic [2:0] video_req_len_cells,
  output cpu_v01_pkg::cell_t video_req_wdata [cpu_v01_pkg::INTEGER_OBJECT_CELLS],
  input  logic video_rsp_valid,
  input  cpu_v01_pkg::cell_t video_rsp_rdata [cpu_v01_pkg::INTEGER_OBJECT_CELLS],
  input  cpu_v01_pkg::fault_packet_t video_rsp_fault,

  output logic irq_req_valid,
  input  logic irq_req_ready,
  output logic irq_req_write,
  output cpu_v01_pkg::addr_t irq_req_addr,
  output cpu_v01_pkg::cell_t irq_req_wdata,
  input  logic irq_rsp_valid,
  input  cpu_v01_pkg::cell_t irq_rsp_rdata,
  input  cpu_v01_pkg::fault_packet_t irq_rsp_fault,

  output logic identity_req_valid,
  input  logic identity_req_ready,
  output logic identity_req_write,
  output cpu_v01_pkg::addr_t identity_req_addr,
  output logic [2:0] identity_req_len_cells,
  output cpu_v01_pkg::cell_t identity_req_wdata [cpu_v01_pkg::CAPABILITY_OBJECT_CELLS],
  input  logic identity_rsp_valid,
  input  cpu_v01_pkg::cell_t identity_rsp_rdata [cpu_v01_pkg::CAPABILITY_OBJECT_CELLS],
  input  cpu_v01_pkg::fault_packet_t identity_rsp_fault
);
  import cpu_v01_pkg::*;

  typedef enum logic [2:0] {
    TARGET_FAULT = 3'd0,
    TARGET_RAM = 3'd1,
    TARGET_UART = 3'd2,
    TARGET_TIMER = 3'd3,
    TARGET_GPIO = 3'd4,
    TARGET_IRQ = 3'd5,
    TARGET_IDENTITY = 3'd6,
    TARGET_VIDEO = 3'd7
  } dmem_target_t;

  dmem_target_t selected_target;
  logic invalid_len;
  logic fault_rsp_valid_q;
  fault_packet_t fault_rsp_fault_q;

  assign invalid_len = core_req_len_cells == 3'd0 || core_req_len_cells > 3'd4;
  assign selected_target = target_for(core_req_addr);

  assign ram_req_valid =
      core_req_valid && !invalid_len && selected_target == TARGET_RAM;
  assign uart_req_valid =
      core_req_valid && !invalid_len && selected_target == TARGET_UART;
  assign timer_req_valid =
      core_req_valid && !invalid_len && selected_target == TARGET_TIMER;
  assign gpio_req_valid =
      core_req_valid && !invalid_len && selected_target == TARGET_GPIO;
  assign video_req_valid =
      core_req_valid && !invalid_len && selected_target == TARGET_VIDEO;
  assign irq_req_valid =
      core_req_valid && !invalid_len && selected_target == TARGET_IRQ;
  assign identity_req_valid =
      core_req_valid && !invalid_len && selected_target == TARGET_IDENTITY;

  assign ram_req_write = core_req_write;
  assign ram_req_addr = core_req_addr;
  assign ram_req_len_cells = core_req_len_cells;
  assign uart_req_write = core_req_write;
  assign uart_req_addr = core_req_addr;
  assign uart_req_wdata = core_req_wdata[0];
  assign timer_req_write = core_req_write;
  assign timer_req_addr = core_req_addr;
  assign timer_req_len_cells = core_req_len_cells;
  assign gpio_req_write = core_req_write;
  assign gpio_req_addr = core_req_addr;
  assign gpio_req_wdata = core_req_wdata[0];
  assign video_req_write = core_req_write;
  assign video_req_addr = core_req_addr;
  assign video_req_len_cells = core_req_len_cells;
  assign irq_req_write = core_req_write;
  assign irq_req_addr = core_req_addr;
  assign irq_req_wdata = core_req_wdata[0];
  assign identity_req_write = core_req_write;
  assign identity_req_addr = core_req_addr;
  assign identity_req_len_cells = core_req_len_cells;

  function automatic logic window_contains(
      input addr_t addr,
      input addr_t base,
      input int cells
  );
    return addr >= base && addr < base + addr_t'(cells);
  endfunction

  function automatic dmem_target_t target_for(input addr_t addr);
    if (window_contains(addr, DATA_RAM_BASE, DATA_RAM_CELLS)) begin
      return TARGET_RAM;
    end
    if (window_contains(addr, UART_BASE, SOC_PERIPHERAL_CELLS)) begin
      return TARGET_UART;
    end
    if (window_contains(addr, TIMER_BASE, SOC_PERIPHERAL_CELLS)) begin
      return TARGET_TIMER;
    end
    if (window_contains(addr, GPIO_STATUS_BASE, SOC_PERIPHERAL_CELLS)) begin
      return TARGET_GPIO;
    end
    if (window_contains(addr, IRQ_BASE, SOC_PERIPHERAL_CELLS)) begin
      return TARGET_IRQ;
    end
    if (window_contains(addr, SYSTEM_IDENTITY_BASE, SOC_PERIPHERAL_CELLS)) begin
      return TARGET_IDENTITY;
    end
    if (window_contains(addr, VIDEO_BASE, SOC_PERIPHERAL_CELLS)) begin
      return TARGET_VIDEO;
    end
    return TARGET_FAULT;
  endfunction

  function automatic fault_packet_t access_fault(input addr_t addr);
    fault_packet_t fault;
    fault = '0;
    fault.valid = 1'b1;
    fault.cause = EXC_ACCESS_FAULT;
    fault.tval = addr;
    return fault;
  endfunction

  always_comb begin
    unique case (selected_target)
      TARGET_RAM: core_req_ready = invalid_len ? 1'b1 : ram_req_ready;
      TARGET_UART: core_req_ready = invalid_len ? 1'b1 : uart_req_ready;
      TARGET_TIMER: core_req_ready = invalid_len ? 1'b1 : timer_req_ready;
      TARGET_GPIO: core_req_ready = invalid_len ? 1'b1 : gpio_req_ready;
      TARGET_VIDEO: core_req_ready = invalid_len ? 1'b1 : video_req_ready;
      TARGET_IRQ: core_req_ready = invalid_len ? 1'b1 : irq_req_ready;
      TARGET_IDENTITY: core_req_ready = invalid_len ? 1'b1 : identity_req_ready;
      default: core_req_ready = 1'b1;
    endcase
  end

  always_comb begin
    for (int i = 0; i < CAPABILITY_OBJECT_CELLS; i++) begin
      ram_req_wdata[i] = core_req_wdata[i];
      identity_req_wdata[i] = core_req_wdata[i];
      core_rsp_rdata[i] = '0;
    end
    for (int i = 0; i < INTEGER_OBJECT_CELLS; i++) begin
      timer_req_wdata[i] = core_req_wdata[i];
      video_req_wdata[i] = core_req_wdata[i];
    end

    core_rsp_valid = 1'b0;
    core_rsp_fault = '0;

    if (ram_rsp_valid) begin
      core_rsp_valid = 1'b1;
      core_rsp_fault = ram_rsp_fault;
      for (int i = 0; i < CAPABILITY_OBJECT_CELLS; i++) begin
        core_rsp_rdata[i] = ram_rsp_rdata[i];
      end
    end else if (uart_rsp_valid) begin
      core_rsp_valid = 1'b1;
      core_rsp_fault = uart_rsp_fault;
      core_rsp_rdata[0] = uart_rsp_rdata;
    end else if (timer_rsp_valid) begin
      core_rsp_valid = 1'b1;
      core_rsp_fault = timer_rsp_fault;
      for (int i = 0; i < INTEGER_OBJECT_CELLS; i++) begin
        core_rsp_rdata[i] = timer_rsp_rdata[i];
      end
    end else if (gpio_rsp_valid) begin
      core_rsp_valid = 1'b1;
      core_rsp_fault = gpio_rsp_fault;
      core_rsp_rdata[0] = gpio_rsp_rdata;
    end else if (video_rsp_valid) begin
      core_rsp_valid = 1'b1;
      core_rsp_fault = video_rsp_fault;
      for (int i = 0; i < INTEGER_OBJECT_CELLS; i++) begin
        core_rsp_rdata[i] = video_rsp_rdata[i];
      end
    end else if (irq_rsp_valid) begin
      core_rsp_valid = 1'b1;
      core_rsp_fault = irq_rsp_fault;
      core_rsp_rdata[0] = irq_rsp_rdata;
    end else if (identity_rsp_valid) begin
      core_rsp_valid = 1'b1;
      core_rsp_fault = identity_rsp_fault;
      for (int i = 0; i < CAPABILITY_OBJECT_CELLS; i++) begin
        core_rsp_rdata[i] = identity_rsp_rdata[i];
      end
    end else if (fault_rsp_valid_q) begin
      core_rsp_valid = 1'b1;
      core_rsp_fault = fault_rsp_fault_q;
    end
  end

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      fault_rsp_valid_q <= 1'b0;
      fault_rsp_fault_q <= '0;
    end else begin
      fault_rsp_valid_q <=
          core_req_valid && core_req_ready && !core_req_write &&
          (invalid_len || selected_target == TARGET_FAULT);
      if (core_req_valid && core_req_ready && !core_req_write &&
          (invalid_len || selected_target == TARGET_FAULT)) begin
        fault_rsp_fault_q <= access_fault(core_req_addr);
      end else if (fault_rsp_valid_q) begin
        fault_rsp_fault_q <= '0;
      end
    end
  end
endmodule

module cpu_v01_fpga_video_mmio #(
  parameter cpu_v01_pkg::addr_t BASE_CELL = 48'h0000_00F0_0500
) (
  input  logic clk,
  input  logic rst_n,

  input  logic req_valid,
  output logic req_ready,
  input  logic req_write,
  input  cpu_v01_pkg::addr_t req_addr,
  input  logic [2:0] req_len_cells,
  input  cpu_v01_pkg::cell_t req_wdata [cpu_v01_pkg::INTEGER_OBJECT_CELLS],

  output logic rsp_valid,
  output cpu_v01_pkg::cell_t rsp_rdata [cpu_v01_pkg::INTEGER_OBJECT_CELLS],
  output cpu_v01_pkg::fault_packet_t rsp_fault,

  input  logic video_vblank_i,
  input  logic video_underflow_pulse_i,
  input  logic [47:0] video_frame_count_i,
  input  logic [15:0] video_line_count_i,
  input  logic [15:0] video_pixel_count_i,
  input  logic [15:0] video_fb_master_status_i,

  output logic video_scanout_enable_o,
  output logic video_output_enable_o,
  output logic [15:0] video_mode_o,
  output logic [3:0] video_test_pattern_o,
  output logic [23:0] video_bg_color_o,
  output logic video_vblank_irq_o
);
  import cpu_v01_pkg::*;

  localparam addr_t VIDEO_CONTROL_OFFSET = 48'h00;
  localparam addr_t VIDEO_MODE_OFFSET = 48'h01;
  localparam addr_t VIDEO_STATUS_OFFSET = 48'h02;
  localparam addr_t VIDEO_IRQ_ENABLE_OFFSET = 48'h03;
  localparam addr_t VIDEO_IRQ_ACK_OFFSET = 48'h04;
  localparam addr_t VIDEO_FRAME_COUNT_OFFSET = 48'h05;
  localparam addr_t VIDEO_LINE_COUNT_OFFSET = 48'h06;
  localparam addr_t VIDEO_PIXEL_COUNT_OFFSET = 48'h07;
  localparam addr_t VIDEO_TEST_PATTERN_OFFSET = 48'h08;
  localparam addr_t VIDEO_BG_COLOR_OFFSET = 48'h09;
  localparam addr_t VIDEO_UNDERFLOW_COUNT_OFFSET = 48'h0A;
  localparam addr_t VIDEO_FB_MASTER_STATUS_OFFSET = 48'h0B;
  localparam addr_t VIDEO_REGISTER_CELLS = 48'h0C;

  localparam logic [15:0] VIDEO_CONTROL_SCANOUT_ENABLE = 16'h0001;
  localparam logic [15:0] VIDEO_CONTROL_OUTPUT_ENABLE = 16'h0002;
  localparam logic [15:0] VIDEO_STATUS_SCANOUT_ENABLED = 16'h0001;
  localparam logic [15:0] VIDEO_STATUS_IN_VBLANK = 16'h0002;
  localparam logic [15:0] VIDEO_STATUS_UNDERFLOW_PENDING = 16'h0004;
  localparam logic [15:0] VIDEO_STATUS_MODE_VALID = 16'h0008;
  localparam logic [15:0] VIDEO_STATUS_VBLANK_PENDING = 16'h0010;
  localparam logic [15:0] VIDEO_IRQ_VBLANK = 16'h0001;
  localparam logic [15:0] VIDEO_IRQ_UNDERFLOW = 16'h0002;

  logic [15:0] control_q;
  logic [15:0] mode_q;
  logic [15:0] irq_enable_q;
  logic [15:0] irq_pending_q;
  logic [3:0] test_pattern_q;
  logic [23:0] bg_color_q;
  logic [47:0] underflow_count_q;
  logic vblank_q;
  logic vblank_pending_q;
  logic underflow_pending_q;
  logic mode_valid;
  logic [15:0] video_status;

  assign req_ready = 1'b1;
  assign vblank_pending_q = irq_pending_q[0];
  assign underflow_pending_q = irq_pending_q[1];
  assign mode_valid = mode_q == 16'd0;
  assign video_scanout_enable_o = control_q[0];
  assign video_output_enable_o = control_q[1];
  assign video_mode_o = mode_q;
  assign video_test_pattern_o = test_pattern_q;
  assign video_bg_color_o = bg_color_q;
  assign video_vblank_irq_o = |(irq_enable_q & irq_pending_q);
  assign video_status =
      (control_q[0] ? VIDEO_STATUS_SCANOUT_ENABLED : 16'd0) |
      (video_vblank_i ? VIDEO_STATUS_IN_VBLANK : 16'd0) |
      (underflow_pending_q ? VIDEO_STATUS_UNDERFLOW_PENDING : 16'd0) |
      (mode_valid ? VIDEO_STATUS_MODE_VALID : 16'd0) |
      (vblank_pending_q ? VIDEO_STATUS_VBLANK_PENDING : 16'd0);

  function automatic logic register_address(input addr_t addr);
    return addr >= BASE_CELL && addr < BASE_CELL + VIDEO_REGISTER_CELLS;
  endfunction

  function automatic addr_t register_offset(input addr_t addr);
    return addr - BASE_CELL;
  endfunction

  function automatic fault_packet_t access_fault(input addr_t addr);
    fault_packet_t fault;
    fault = '0;
    fault.valid = 1'b1;
    fault.cause = EXC_ACCESS_FAULT;
    fault.tval = addr;
    return fault;
  endfunction

  task automatic pack_48(
      input logic [47:0] value,
      output cell_t cells [INTEGER_OBJECT_CELLS]
  );
    cells[0] = value[23:0];
    cells[1] = value[47:24];
  endtask

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      control_q <= 16'd0;
      mode_q <= 16'd0;
      irq_enable_q <= 16'd0;
      irq_pending_q <= 16'd0;
      test_pattern_q <= 4'd1;
      bg_color_q <= 24'h000000;
      underflow_count_q <= 48'd0;
      vblank_q <= 1'b0;
      rsp_valid <= 1'b0;
      rsp_fault <= '0;
      for (int i = 0; i < INTEGER_OBJECT_CELLS; i++) begin
        rsp_rdata[i] <= '0;
      end
    end else begin
      automatic addr_t offset;
      offset = register_offset(req_addr);
      vblank_q <= video_vblank_i;
      rsp_valid <= 1'b0;
      rsp_fault <= '0;
      for (int i = 0; i < INTEGER_OBJECT_CELLS; i++) begin
        rsp_rdata[i] <= '0;
      end

      if (video_vblank_i && !vblank_q) begin
        irq_pending_q <= irq_pending_q | VIDEO_IRQ_VBLANK;
      end
      if (video_underflow_pulse_i) begin
        irq_pending_q <= irq_pending_q | VIDEO_IRQ_UNDERFLOW;
        underflow_count_q <= underflow_count_q + 48'd1;
      end

      if (req_valid && req_ready) begin
        if (!register_address(req_addr) || req_len_cells == 3'd0) begin
          if (!req_write) begin
            rsp_valid <= 1'b1;
            rsp_fault <= access_fault(req_addr);
          end
        end else if (req_write) begin
          unique case (offset)
            VIDEO_CONTROL_OFFSET: control_q <= req_wdata[0][15:0];
            VIDEO_MODE_OFFSET: mode_q <= req_wdata[0][15:0];
            VIDEO_IRQ_ENABLE_OFFSET: irq_enable_q <= req_wdata[0][15:0];
            VIDEO_IRQ_ACK_OFFSET: irq_pending_q <= irq_pending_q & ~req_wdata[0][15:0];
            VIDEO_TEST_PATTERN_OFFSET: test_pattern_q <= req_wdata[0][3:0];
            VIDEO_BG_COLOR_OFFSET: bg_color_q <= req_wdata[0][23:0];
            default: begin
            end
          endcase
        end else begin
          rsp_valid <= 1'b1;
          unique case (offset)
            VIDEO_CONTROL_OFFSET: rsp_rdata[0] <= {8'd0, control_q};
            VIDEO_MODE_OFFSET: rsp_rdata[0] <= {8'd0, mode_q};
            VIDEO_STATUS_OFFSET: rsp_rdata[0] <= {8'd0, video_status};
            VIDEO_IRQ_ENABLE_OFFSET: rsp_rdata[0] <= {8'd0, irq_enable_q};
            VIDEO_IRQ_ACK_OFFSET: rsp_rdata[0] <= {8'd0, irq_pending_q};
            VIDEO_FRAME_COUNT_OFFSET: pack_48(video_frame_count_i, rsp_rdata);
            VIDEO_LINE_COUNT_OFFSET: rsp_rdata[0] <= {8'd0, video_line_count_i};
            VIDEO_PIXEL_COUNT_OFFSET: rsp_rdata[0] <= {8'd0, video_pixel_count_i};
            VIDEO_TEST_PATTERN_OFFSET: rsp_rdata[0] <= {20'd0, test_pattern_q};
            VIDEO_BG_COLOR_OFFSET: rsp_rdata[0] <= bg_color_q;
            VIDEO_UNDERFLOW_COUNT_OFFSET: pack_48(underflow_count_q, rsp_rdata);
            VIDEO_FB_MASTER_STATUS_OFFSET: rsp_rdata[0] <= {8'd0, video_fb_master_status_i};
            default: begin
              rsp_fault <= access_fault(req_addr);
            end
          endcase
        end
      end
    end
  end

  // verilator lint_off UNUSEDSIGNAL
  wire logic unused_control_constants = &{
    VIDEO_CONTROL_SCANOUT_ENABLE,
    VIDEO_CONTROL_OUTPUT_ENABLE
  };
  // verilator lint_on UNUSEDSIGNAL
endmodule

module cpu_v01_fpga_irq_mmio #(
  parameter cpu_v01_pkg::addr_t BASE_CELL = 48'h0000_00F0_0300
) (
  input  logic clk,
  input  logic rst_n,

  input  logic req_valid,
  output logic req_ready,
  input  logic req_write,
  input  cpu_v01_pkg::addr_t req_addr,
  input  cpu_v01_pkg::cell_t req_wdata,

  output logic rsp_valid,
  output cpu_v01_pkg::cell_t rsp_rdata,
  output cpu_v01_pkg::fault_packet_t rsp_fault,

  input  logic [15:0] irq_sources_i,
  output logic [15:0] irq_pending_enabled_o
);
  import cpu_v01_pkg::*;

  localparam addr_t IRQ_PENDING_OFFSET = 48'd0;
  localparam addr_t IRQ_ENABLE_OFFSET = 48'd1;
  localparam addr_t IRQ_ACK_OFFSET = 48'd2;
  localparam addr_t IRQ_FORCE_OFFSET = 48'd3;
  localparam addr_t IRQ_REGISTER_CELLS = 48'd4;

  logic [15:0] irq_enable_q;
  logic [15:0] irq_force_q;
  logic [15:0] irq_pending_raw;

  assign req_ready = 1'b1;
  assign irq_pending_raw = irq_sources_i | irq_force_q;
  assign irq_pending_enabled_o = irq_pending_raw & irq_enable_q;

  function automatic logic register_address(input addr_t addr);
    return addr >= BASE_CELL && addr < BASE_CELL + IRQ_REGISTER_CELLS;
  endfunction

  function automatic addr_t register_offset(input addr_t addr);
    return addr - BASE_CELL;
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
      irq_enable_q <= 16'd0;
      irq_force_q <= 16'd0;
      rsp_valid <= 1'b0;
      rsp_rdata <= '0;
      rsp_fault <= '0;
    end else begin
      automatic addr_t offset;
      offset = register_offset(req_addr);
      rsp_valid <= 1'b0;
      rsp_rdata <= '0;
      rsp_fault <= '0;

      if (req_valid && req_ready) begin
        if (!register_address(req_addr)) begin
          if (!req_write) begin
            rsp_valid <= 1'b1;
            rsp_fault <= access_fault(req_addr);
          end
        end else if (req_write) begin
          unique case (offset)
            IRQ_ENABLE_OFFSET: irq_enable_q <= req_wdata[15:0];
            IRQ_ACK_OFFSET: irq_force_q <= irq_force_q & ~req_wdata[15:0];
            IRQ_FORCE_OFFSET: irq_force_q <= irq_force_q | req_wdata[15:0];
            default: begin
            end
          endcase
        end else begin
          rsp_valid <= 1'b1;
          unique case (offset)
            IRQ_PENDING_OFFSET: rsp_rdata <= {8'd0, irq_pending_raw};
            IRQ_ENABLE_OFFSET: rsp_rdata <= {8'd0, irq_enable_q};
            IRQ_ACK_OFFSET: rsp_rdata <= '0;
            IRQ_FORCE_OFFSET: rsp_rdata <= {8'd0, irq_force_q};
            default: begin
              rsp_fault <= access_fault(req_addr);
            end
          endcase
        end
      end
    end
  end
endmodule

module cpu_v01_fpga_system_identity_mmio #(
  parameter cpu_v01_pkg::addr_t BASE_CELL = 48'h0000_00F0_0400,
  parameter logic [95:0] BUILD_ID = 96'd0,
  parameter logic [255:0] IMAGE_SHA256 = 256'd0
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

  localparam addr_t RESET_CAUSE_OFFSET = 48'h00;
  localparam addr_t BUILD_ID_LO_OFFSET = 48'h01;
  localparam addr_t BUILD_ID_HI_OFFSET = 48'h02;
  localparam addr_t IMAGE_SHA256_0_OFFSET = 48'h10;
  localparam addr_t IMAGE_SHA256_1_OFFSET = 48'h11;
  localparam addr_t IMAGE_SHA256_2_OFFSET = 48'h12;
  localparam addr_t IMAGE_SHA256_3_OFFSET = 48'h13;
  localparam addr_t IMAGE_SHA256_4_OFFSET = 48'h14;
  localparam addr_t IMAGE_SHA256_5_OFFSET = 48'h15;
  localparam addr_t IDENTITY_REGISTER_CELLS = 48'h16;

  logic [15:0] reset_cause_q;

  assign req_ready = 1'b1;

  function automatic logic register_address(input addr_t addr);
    return addr >= BASE_CELL && addr < BASE_CELL + IDENTITY_REGISTER_CELLS;
  endfunction

  function automatic addr_t register_offset(input addr_t addr);
    return addr - BASE_CELL;
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
      reset_cause_q <= 16'h0001;
      rsp_valid <= 1'b0;
      rsp_fault <= '0;
      for (int i = 0; i < CAPABILITY_OBJECT_CELLS; i++) begin
        rsp_rdata[i] <= '0;
      end
    end else begin
      automatic addr_t offset;
      offset = register_offset(req_addr);
      rsp_valid <= 1'b0;
      rsp_fault <= '0;
      for (int i = 0; i < CAPABILITY_OBJECT_CELLS; i++) begin
        rsp_rdata[i] <= '0;
      end

      if (req_valid && req_ready) begin
        if (!register_address(req_addr) || req_len_cells == 3'd0) begin
          if (!req_write) begin
            rsp_valid <= 1'b1;
            rsp_fault <= access_fault(req_addr);
          end
        end else if (req_write) begin
          if (offset == RESET_CAUSE_OFFSET) begin
            reset_cause_q <= reset_cause_q & ~req_wdata[0][15:0];
          end
        end else begin
          rsp_valid <= 1'b1;
          unique case (offset)
            RESET_CAUSE_OFFSET: begin
              rsp_rdata[0] <= {8'd0, reset_cause_q};
            end
            BUILD_ID_LO_OFFSET: begin
              rsp_rdata[0] <= BUILD_ID[23:0];
              rsp_rdata[1] <= BUILD_ID[47:24];
            end
            BUILD_ID_HI_OFFSET: begin
              rsp_rdata[0] <= BUILD_ID[71:48];
              rsp_rdata[1] <= BUILD_ID[95:72];
            end
            IMAGE_SHA256_0_OFFSET: begin
              rsp_rdata[0] <= IMAGE_SHA256[23:0];
              rsp_rdata[1] <= IMAGE_SHA256[47:24];
            end
            IMAGE_SHA256_1_OFFSET: begin
              rsp_rdata[0] <= IMAGE_SHA256[71:48];
              rsp_rdata[1] <= IMAGE_SHA256[95:72];
            end
            IMAGE_SHA256_2_OFFSET: begin
              rsp_rdata[0] <= IMAGE_SHA256[119:96];
              rsp_rdata[1] <= IMAGE_SHA256[143:120];
            end
            IMAGE_SHA256_3_OFFSET: begin
              rsp_rdata[0] <= IMAGE_SHA256[167:144];
              rsp_rdata[1] <= IMAGE_SHA256[191:168];
            end
            IMAGE_SHA256_4_OFFSET: begin
              rsp_rdata[0] <= IMAGE_SHA256[215:192];
              rsp_rdata[1] <= IMAGE_SHA256[239:216];
            end
            IMAGE_SHA256_5_OFFSET: begin
              rsp_rdata[0] <= {8'd0, IMAGE_SHA256[255:240]};
            end
            default: begin
              rsp_fault <= access_fault(req_addr);
            end
          endcase
        end
      end
    end
  end
endmodule

module cpu_v01_fpga_uart_status_streamer #(
  parameter bit ENABLE = 1'b1,
  parameter int CLOCK_HZ = 25_000_000,
  parameter int BAUD = 115_200,
  parameter int STATUS_INTERVAL_CYCLES = 25_000,
  parameter int PACKET_BYTES = 32
) (
  input  logic clk,
  input  logic rst_n,
  input  logic [(PACKET_BYTES * 8)-1:0] packet_i,
  output logic packet_started_o,
  output logic uart_tx_o
);
  localparam int BAUD_DIVISOR = (CLOCK_HZ + (BAUD / 2)) / BAUD;
  localparam int CLKS_PER_BIT = (BAUD_DIVISOR < 1) ? 1 : BAUD_DIVISOR;
  localparam int EFFECTIVE_INTERVAL_CYCLES =
      (STATUS_INTERVAL_CYCLES < 1) ? 1 : STATUS_INTERVAL_CYCLES;
  localparam int BAUD_COUNTER_BITS = (CLKS_PER_BIT <= 1) ? 1 : $clog2(CLKS_PER_BIT);
  localparam int INTERVAL_COUNTER_BITS =
      (EFFECTIVE_INTERVAL_CYCLES <= 1) ? 1 : $clog2(EFFECTIVE_INTERVAL_CYCLES);
  localparam logic [BAUD_COUNTER_BITS-1:0] BAUD_COUNT_RELOAD =
      BAUD_COUNTER_BITS'(CLKS_PER_BIT - 1);
  localparam logic [INTERVAL_COUNTER_BITS-1:0] INTERVAL_COUNT_RELOAD =
      INTERVAL_COUNTER_BITS'(EFFECTIVE_INTERVAL_CYCLES - 1);
  localparam logic [5:0] LAST_PACKET_BYTE = 6'(PACKET_BYTES - 1);

  logic [(PACKET_BYTES * 8)-1:0] packet_q;
  logic [5:0] byte_index_q;
  logic packet_active_q;
  logic [9:0] tx_shift_q;
  logic [3:0] tx_bit_count_q;
  logic [BAUD_COUNTER_BITS-1:0] baud_count_q;
  logic [INTERVAL_COUNTER_BITS-1:0] interval_count_q;
  logic tx_busy_q;

  assign uart_tx_o = (!ENABLE || !tx_busy_q) ? 1'b1 : tx_shift_q[0];

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      packet_q <= '0;
      byte_index_q <= 6'd0;
      packet_active_q <= 1'b0;
      tx_shift_q <= 10'h3FF;
      tx_bit_count_q <= 4'd0;
      baud_count_q <= '0;
      interval_count_q <= '0;
      tx_busy_q <= 1'b0;
      packet_started_o <= 1'b0;
    end else begin
      packet_started_o <= 1'b0;

      if (!ENABLE) begin
        packet_q <= '0;
        byte_index_q <= 6'd0;
        packet_active_q <= 1'b0;
        tx_shift_q <= 10'h3FF;
        tx_bit_count_q <= 4'd0;
        baud_count_q <= '0;
        interval_count_q <= '0;
        tx_busy_q <= 1'b0;
      end else if (tx_busy_q) begin
        if (baud_count_q != '0) begin
          baud_count_q <= baud_count_q - 1'b1;
        end else if (tx_bit_count_q == 4'd9) begin
          tx_busy_q <= 1'b0;
          tx_shift_q <= 10'h3FF;
        end else begin
          tx_shift_q <= {1'b1, tx_shift_q[9:1]};
          tx_bit_count_q <= tx_bit_count_q + 1'b1;
          baud_count_q <= BAUD_COUNT_RELOAD;
        end
      end else if (packet_active_q) begin
        tx_shift_q <= {1'b1, packet_q[(byte_index_q * 8) +: 8], 1'b0};
        tx_bit_count_q <= 4'd0;
        baud_count_q <= BAUD_COUNT_RELOAD;
        tx_busy_q <= 1'b1;
        if (byte_index_q == LAST_PACKET_BYTE) begin
          packet_active_q <= 1'b0;
        end else begin
          byte_index_q <= byte_index_q + 1'b1;
        end
      end else if (interval_count_q != '0) begin
        interval_count_q <= interval_count_q - 1'b1;
      end else begin
        packet_q <= packet_i;
        byte_index_q <= 6'd0;
        packet_active_q <= 1'b1;
        packet_started_o <= 1'b1;
        interval_count_q <= INTERVAL_COUNT_RELOAD;
      end
    end
  end
endmodule
