module cpu_v01_smoke_core #(
  parameter logic [cpu_v01_pkg::ADDR_BITS-1:0] RESET_VECTOR = 48'h0000_0000_1000,
  parameter bit FORCE_ILLEGAL_SLOT1 = 1'b0
) (
  input  logic clk,
  input  logic rst_n,
  output logic retire_valid,
  output cpu_v01_pkg::retire_packet_t retire_packet,
  output cpu_v01_pkg::int_reg_t d2_value,
  output logic done
);
  import cpu_v01_pkg::*;

  typedef enum logic [1:0] {
    ST_RESET,
    ST_RETIRE,
    ST_DONE
  } smoke_state_t;

  smoke_state_t state_q;
  addr_t pc_q;
  logic slot_q;
  logic [RETIRE_SEQUENCE_BITS-1:0] sequence_q;
  int_reg_t d_regs [INT_REG_COUNT];
  retire_packet_t retire_packet_q;

  wire logic placement_fault = slot_q != SLOT_0;
  wire logic [3:0] rd = 4'd2;
  wire logic [3:0] ra = 4'd0;
  wire logic [3:0] rb = 4'd1;
  wire int_reg_t add_result = d_regs[ra] + d_regs[rb];

  assign retire_packet = retire_packet_q;
  assign retire_valid = retire_packet_q.valid;
  assign d2_value = d_regs[2];
  assign done = state_q == ST_DONE;

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      state_q <= ST_RESET;
      pc_q <= RESET_VECTOR;
      slot_q <= FORCE_ILLEGAL_SLOT1 ? SLOT_1 : SLOT_0;
      sequence_q <= '0;
      retire_packet_q <= '0;
      for (int i = 0; i < INT_REG_COUNT; i++) begin
        d_regs[i] <= '0;
      end
      d_regs[0] <= 48'h0000_0000_0010;
      d_regs[1] <= 48'h0000_0000_0020;
    end else begin
      retire_packet_q <= '0;
      unique case (state_q)
        ST_RESET: begin
          state_q <= ST_RETIRE;
        end

        ST_RETIRE: begin
          retire_packet_q.valid <= 1'b1;
          retire_packet_q.sequence <= sequence_q;
          retire_packet_q.pc_cell <= pc_q;
          retire_packet_q.slot <= slot_q;
          retire_packet_q.instruction_length <= 2'd1;
          retire_packet_q.decoded.valid <= !placement_fault;
          retire_packet_q.decoded.opcode_id <= OPC_ADD_24;
          retire_packet_q.decoded.size_bits <= 8'd24;
          retire_packet_q.decoded.privileged <= 1'b0;

          if (placement_fault) begin
            retire_packet_q.normal_valid <= 1'b0;
            retire_packet_q.fault.valid <= 1'b1;
            retire_packet_q.fault.cause <= EXC_ALIGN_FAULT;
            retire_packet_q.fault.pc_cell <= pc_q;
            retire_packet_q.fault.slot <= slot_q;
            retire_packet_q.fault.tval <= pc_q;
          end else begin
            d_regs[rd] <= add_result;
            retire_packet_q.normal_valid <= 1'b1;
            retire_packet_q.integer_write_valid <= 1'b1;
            retire_packet_q.integer_write_index <= rd;
            retire_packet_q.integer_write_value <= add_result;
            pc_q <= pc_q + 48'd1;
            slot_q <= SLOT_0;
          end

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
