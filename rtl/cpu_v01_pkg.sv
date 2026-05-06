package cpu_v01_pkg;
  localparam int CELL_BITS = 24;
  localparam int ADDR_BITS = 48;
  localparam int FETCH_GROUP_CELLS = 2;
  localparam int INTEGER_OBJECT_CELLS = 2;
  localparam int CAPABILITY_OBJECT_CELLS = 4;
  localparam int CAP_PAYLOAD_BITS = 96;
  localparam int CAP_CURSOR_BITS = 48;
  localparam int CAP_BOUNDS_METADATA_BITS = 30;
  localparam int CAP_PERMISSION_BITS = 8;
  localparam int CAP_OTYPE_BITS = 8;
  localparam int CAP_FLAG_BITS = 2;
  localparam int CAP_TAG_BITS = 1;
  localparam int INT_REG_BITS = 48;
  localparam int INT_REG_COUNT = 16;
  localparam int CAP_REG_COUNT = 8;
  localparam int CSR_BITS = 48;
  localparam int OPCODE_ID_BITS = 8;
  localparam int RETIRE_SEQUENCE_BITS = 64;

  localparam logic [OPCODE_ID_BITS-1:0] OPC_ADD_24 = 8'h12;
  localparam logic [15:0] EXC_ILLEGAL_INSTRUCTION = 16'h0001;
  localparam logic [15:0] EXC_ALIGN_FAULT = 16'h0005;
  localparam logic SLOT_0 = 1'b0;
  localparam logic SLOT_1 = 1'b1;

  typedef logic [CELL_BITS-1:0] cell_t;
  typedef logic [ADDR_BITS-1:0] addr_t;
  typedef logic [INT_REG_BITS-1:0] int_reg_t;

  typedef struct packed {
    logic [CAP_CURSOR_BITS-1:0] cursor;
    logic [CAP_BOUNDS_METADATA_BITS-1:0] bounds_metadata;
    logic [CAP_PERMISSION_BITS-1:0] permissions;
    logic [CAP_OTYPE_BITS-1:0] otype;
    logic [CAP_FLAG_BITS-1:0] flags;
  } cap_payload_t;

  typedef struct packed {
    cap_payload_t payload;
    logic tag;
  } cap_t;

  typedef struct packed {
    logic valid;
    logic [OPCODE_ID_BITS-1:0] opcode_id;
    logic [7:0] size_bits;
    logic privileged;
  } decoded_opcode_t;

  typedef struct packed {
    logic valid;
    logic [15:0] cause;
    addr_t pc_cell;
    logic slot;
    addr_t tval;
    logic [3:0] capcause;
    logic [7:0] fault_cap_idx;
  } fault_packet_t;

  typedef struct packed {
    logic valid;
    logic [RETIRE_SEQUENCE_BITS-1:0] sequence;
    addr_t pc_cell;
    logic slot;
    logic [1:0] instruction_length;
    decoded_opcode_t decoded;
    logic normal_valid;
    fault_packet_t fault;
    logic redirect_valid;
    cap_t redirect_target;
    logic redirect_slot;
    logic integer_write_valid;
    logic [3:0] integer_write_index;
    int_reg_t integer_write_value;
  } retire_packet_t;
endpackage
