module cpu_v01_cap_mem_core (
  input  logic clk,
  input  logic rst_n,
  output logic retire_valid,
  output cpu_v01_pkg::retire_packet_t retire_packet,
  output cpu_v01_pkg::cap_t c2_value,
  output cpu_v01_pkg::cap_t c3_value,
  output cpu_v01_pkg::cap_t c4_value,
  output cpu_v01_pkg::cap_t c5_value,
  output cpu_v01_pkg::cap_t c6_value,
  output cpu_v01_pkg::int_reg_t d3_value,
  output cpu_v01_pkg::int_reg_t d8_value,
  output logic memory_tag_value,
  output logic done
);
  import cpu_v01_pkg::*;

  typedef enum logic [3:0] {
    ST_RESET,
    ST_CMOVE,
    ST_CGETADDR,
    ST_CSETADDR,
    ST_CANDPERM,
    ST_CSC,
    ST_CLC,
    ST_ST48,
    ST_LD48,
    ST_INVALID_TAG_FAULT,
    ST_DONE
  } cap_mem_state_t;

  cap_mem_state_t state_q;
  logic [RETIRE_SEQUENCE_BITS-1:0] sequence_q;
  addr_t pc_q;
  int_reg_t d_regs [INT_REG_COUNT];
  cap_t c_regs [CAP_REG_COUNT];
  cap_t memory_cap_slot_q;
  int_reg_t memory_int_value_q;
  logic memory_tag_q;
  retire_packet_t retire_packet_q;

  assign retire_packet = retire_packet_q;
  assign retire_valid = retire_packet_q.valid;
  assign c2_value = c_regs[2];
  assign c3_value = c_regs[3];
  assign c4_value = c_regs[4];
  assign c5_value = c_regs[5];
  assign c6_value = c_regs[6];
  assign d3_value = d_regs[3];
  assign d8_value = d_regs[8];
  assign memory_tag_value = memory_tag_q;
  assign done = state_q == ST_DONE;

  function automatic cap_t data_cap(input addr_t cursor, input logic tag, input logic [7:0] permissions);
    cap_t value;
    value.payload.cursor = cursor;
    value.payload.bounds_metadata = 30'd46139392;
    value.payload.permissions = permissions;
    value.payload.otype = 8'd0;
    value.payload.flags = 2'd1;
    value.tag = tag;
    return value;
  endfunction

  function automatic cap_t cap_with_cursor(input cap_t source, input addr_t cursor);
    cap_t value;
    value = source;
    value.payload.cursor = cursor;
    return value;
  endfunction

  function automatic cap_t cap_with_permissions(input cap_t source, input logic [7:0] permissions);
    cap_t value;
    value = source;
    value.payload.permissions = permissions;
    return value;
  endfunction

  task automatic start_packet(input logic [OPCODE_ID_BITS-1:0] opcode_id, input logic [7:0] size_bits);
    retire_packet_q <= '0;
    retire_packet_q.valid <= 1'b1;
    retire_packet_q.sequence <= sequence_q;
    retire_packet_q.pc_cell <= pc_q;
    retire_packet_q.slot <= SLOT_0;
    retire_packet_q.instruction_length <= size_bits == 8'd48 ? 2'd2 : 2'd1;
    retire_packet_q.decoded.valid <= 1'b1;
    retire_packet_q.decoded.opcode_id <= opcode_id;
    retire_packet_q.decoded.size_bits <= size_bits;
    retire_packet_q.normal_valid <= 1'b1;
  endtask

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      state_q <= ST_RESET;
      sequence_q <= '0;
      pc_q <= 48'h0000_0000_1250;
      retire_packet_q <= '0;
      memory_cap_slot_q <= '0;
      memory_int_value_q <= '0;
      memory_tag_q <= 1'b0;
      for (int i = 0; i < INT_REG_COUNT; i++) begin
        d_regs[i] <= '0;
      end
      for (int i = 0; i < CAP_REG_COUNT; i++) begin
        c_regs[i] <= '0;
      end
      d_regs[0] <= 48'h0000_0000_2080;
      d_regs[1] <= 48'h0000_0000_0001;
      d_regs[7] <= 48'h1234_5678_9ABC;
      c_regs[1] <= data_cap(48'h0000_0000_2200, 1'b1, 8'd27);
    end else begin
      retire_packet_q <= '0;
      unique case (state_q)
        ST_RESET: begin
          state_q <= ST_CMOVE;
        end

        ST_CMOVE: begin
          start_packet(OPC_CMOVE_48, 8'd48);
          c_regs[2] <= c_regs[1];
          retire_packet_q.capability_write_valid <= 1'b1;
          retire_packet_q.capability_write_index <= 3'd2;
          retire_packet_q.capability_write_value <= c_regs[1];
          pc_q <= 48'h0000_0000_1252;
          sequence_q <= sequence_q + 64'd1;
          state_q <= ST_CGETADDR;
        end

        ST_CGETADDR: begin
          start_packet(OPC_CGETADDR_48, 8'd48);
          d_regs[3] <= c_regs[2].payload.cursor;
          retire_packet_q.integer_write_valid <= 1'b1;
          retire_packet_q.integer_write_index <= 4'd3;
          retire_packet_q.integer_write_value <= c_regs[2].payload.cursor;
          pc_q <= 48'h0000_0000_1200;
          c_regs[1] <= data_cap(48'h0000_0000_2000, 1'b1, 8'd27);
          sequence_q <= sequence_q + 64'd1;
          state_q <= ST_CSETADDR;
        end

        ST_CSETADDR: begin
          start_packet(OPC_CSETADDR_48, 8'd48);
          c_regs[4] <= cap_with_cursor(c_regs[1], d_regs[0]);
          retire_packet_q.capability_write_valid <= 1'b1;
          retire_packet_q.capability_write_index <= 3'd4;
          retire_packet_q.capability_write_value <= cap_with_cursor(c_regs[1], d_regs[0]);
          pc_q <= 48'h0000_0000_1202;
          sequence_q <= sequence_q + 64'd1;
          state_q <= ST_CANDPERM;
        end

        ST_CANDPERM: begin
          start_packet(OPC_CANDPERM_48, 8'd48);
          c_regs[5] <= cap_with_permissions(c_regs[4], c_regs[4].payload.permissions & d_regs[1][7:0]);
          retire_packet_q.capability_write_valid <= 1'b1;
          retire_packet_q.capability_write_index <= 3'd5;
          retire_packet_q.capability_write_value <= cap_with_permissions(c_regs[4], c_regs[4].payload.permissions & d_regs[1][7:0]);
          pc_q <= 48'h0000_0000_1300;
          c_regs[1] <= data_cap(48'h0000_0000_2000, 1'b1, 8'd27);
          c_regs[2] <= data_cap(48'h0000_0000_2100, 1'b1, 8'd27);
          d_regs[0] <= '0;
          sequence_q <= sequence_q + 64'd1;
          state_q <= ST_CSC;
        end

        ST_CSC: begin
          start_packet(OPC_CSC_24, 8'd24);
          memory_cap_slot_q <= c_regs[2];
          memory_tag_q <= c_regs[2].tag;
          retire_packet_q.memory_effect_kind <= MEM_EFFECT_CSC;
          retire_packet_q.memory_effect_address <= 48'h0000_0000_2000;
          retire_packet_q.memory_capability_value <= c_regs[2];
          retire_packet_q.tag_write_valid <= 1'b1;
          retire_packet_q.tag_write_value <= c_regs[2].tag;
          pc_q <= 48'h0000_0000_1301;
          sequence_q <= sequence_q + 64'd1;
          state_q <= ST_CLC;
        end

        ST_CLC: begin
          start_packet(OPC_CLC_24, 8'd24);
          c_regs[6] <= memory_cap_slot_q;
          retire_packet_q.capability_write_valid <= 1'b1;
          retire_packet_q.capability_write_index <= 3'd6;
          retire_packet_q.capability_write_value <= memory_cap_slot_q;
          pc_q <= 48'h0000_0000_1302;
          sequence_q <= sequence_q + 64'd1;
          state_q <= ST_ST48;
        end

        ST_ST48: begin
          start_packet(OPC_ST48_24, 8'd24);
          memory_int_value_q <= d_regs[7];
          memory_tag_q <= 1'b0;
          retire_packet_q.memory_effect_kind <= MEM_EFFECT_ST48;
          retire_packet_q.memory_effect_address <= 48'h0000_0000_2000;
          retire_packet_q.memory_integer_value <= d_regs[7];
          retire_packet_q.tag_write_valid <= 1'b1;
          retire_packet_q.tag_write_value <= 1'b0;
          pc_q <= 48'h0000_0000_1303;
          sequence_q <= sequence_q + 64'd1;
          state_q <= ST_LD48;
        end

        ST_LD48: begin
          start_packet(OPC_LD48_24, 8'd24);
          d_regs[8] <= memory_int_value_q;
          retire_packet_q.integer_write_valid <= 1'b1;
          retire_packet_q.integer_write_index <= 4'd8;
          retire_packet_q.integer_write_value <= memory_int_value_q;
          pc_q <= 48'h0000_0000_1650;
          c_regs[1] <= data_cap(48'h0000_0000_2000, 1'b0, 8'd27);
          d_regs[0] <= 48'h0000_0000_2080;
          sequence_q <= sequence_q + 64'd1;
          state_q <= ST_INVALID_TAG_FAULT;
        end

        ST_INVALID_TAG_FAULT: begin
          retire_packet_q <= '0;
          retire_packet_q.valid <= 1'b1;
          retire_packet_q.sequence <= sequence_q;
          retire_packet_q.pc_cell <= pc_q;
          retire_packet_q.slot <= SLOT_0;
          retire_packet_q.instruction_length <= 2'd2;
          retire_packet_q.decoded.valid <= 1'b1;
          retire_packet_q.decoded.opcode_id <= OPC_CSETADDR_48;
          retire_packet_q.decoded.size_bits <= 8'd48;
          retire_packet_q.normal_valid <= 1'b0;
          retire_packet_q.fault.valid <= 1'b1;
          retire_packet_q.fault.cause <= EXC_CAPABILITY_TAG_FAULT;
          retire_packet_q.fault.pc_cell <= pc_q;
          retire_packet_q.fault.slot <= SLOT_0;
          retire_packet_q.fault.capcause <= CAPCAUSE_TAG;
          retire_packet_q.fault.fault_cap_idx <= FAULT_CAP_IDX_C1;
          sequence_q <= sequence_q + 64'd1;
          state_q <= ST_DONE;
        end

        default: begin
          state_q <= ST_DONE;
        end
      endcase
    end
  end
endmodule
