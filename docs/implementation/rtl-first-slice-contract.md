# RTL First Slice Contract

Story: I20-S01

Status: Draft RTL contract

The first SystemVerilog work is a deliberately narrow single-core slice. It
must establish the interface and retire-trace contract that later capability,
memory/tag, trap, and protected-stack gates can extend without changing the
verification boundary.

## Slice Boundary

The first smoke slice includes:

| Surface | Required behavior |
| --- | --- |
| `reset_smoke` | Start core 0 from the configured reset vector with fixed fixture memories and all external asynchronous sources inactive. |
| `instruction_fetch` | Fetch 48-bit groups from a deterministic instruction-memory port addressed by cell address. |
| `slot_0_fetch` | Retire the straight-line smoke program from slot 0 and expose slot state in trace packets. |
| `legal_placement_fault` | Detect illegal 24-bit and 48-bit placement before retire and carry the selected fault to `RT`. |
| `integer_register_writes` | Execute the smoke integer ALU subset and commit `D0`-`D15` writes only through normal retire packets. |
| `retire_trace` | Emit one ordered retire packet per committed instruction or precise fault. |

The first smoke slice excludes, but must leave interface space for:

- capability register behavior;
- data-memory payload and tag writes;
- traps, `IRET`, direct `CALL`, and protected return-stack transactions;
- atomics and LL/SC reservations;
- TLB, page-table, cache, and coherence behavior;
- debug halt, interrupts, MMIO devices, DMA, and secondary cores.

## Pipeline Boundaries

The RTL trace must map each in-flight architectural instruction to the v0.1
stage order:

```text
FE0 -> FE1 -> PD -> XLT -> ISS -> EX -> MEM -> WB -> RT
```

The implementation may combine physical flops or split internal sub-states, but
the externally checked trace uses these boundaries:

| Stage | First-slice boundary |
| --- | --- |
| `FE0` | Select the next `PCC.cursor` and slot from reset, sequential fall-through, or a later redirect packet. |
| `FE1` | Request and receive one aligned 48-bit fetch group from instruction memory. |
| `PD` | Select the instruction by slot, determine length, and detect placement faults. |
| `XLT` | Decode supported smoke instructions or create a precise unsupported-instruction fault packet. |
| `ISS` | Accept at most one architectural instruction when all required operands and resources are ready. |
| `EX` | Compute smoke integer results and prepare branch/address/capability extension points. |
| `MEM` | Pass through non-memory smoke operations and reserve the data-memory/tag access boundary. |
| `WB` | Gather exactly one result packet for the oldest issued instruction. |
| `RT` | Select normal retire, precise fault, or redirect and make the architectural update atomic. |

## Stall And Flush Rules

- A stage with `valid` asserted keeps its payload stable while its downstream
  stage is not ready.
- A structural stall may be global in the first smoke slice, but it must not
  drop an instruction, duplicate a retire packet, or reorder retirement.
- `ISS` accepts at most one architectural instruction per cycle.
- `RT` retires in sequence order and commits at most one architectural
  instruction per cycle.
- A reset, trap, debug, interrupt, or branch redirect kills all younger
  wrong-path work before any younger payload reaches `RT`.
- Killed work clears its busy marks and must not write integer registers,
  capability registers, CSRs, memory payloads, memory tags, return-stack state,
  counters, predictor state, or debug state.
- Load-use, MDU, cache, TLB, and store-buffer hazards may be handled with
  conservative stalls until their later implementation stories add narrower
  forwarding or replay behavior.
- Branch prediction is not required in the first slice. The legal baseline is
  sequential fetch with recovery from the selected redirect packet.

## Commit Packet Timing

Every instruction carries its selected result packet to `RT`. The RTL emits the
retire trace packet in the same cycle that `RT` decides the outcome, and the
architectural state update occurs on that retire edge.

Required retire packet fields:

| Field | Meaning |
| --- | --- |
| `valid` | The packet contains one retired architectural instruction or one precise fault. |
| `sequence` | Monotonic in-order instruction sequence number. |
| `pc_cell` | Cell address of the architectural instruction. |
| `slot` | Hidden slot value used to select the instruction. |
| `instruction_length` | Architectural length in cells for fall-through and resume checks. |
| `opcode_id` | Decoded opcode selector or the unsupported encoding class. |
| `normal_effects` | Integer, capability, CSR, CCSR, memory, reservation, and return-stack effects selected for normal retire. |
| `fault_packet` | `cause`, `faulting_location`, `tval`, `capcause`, and `fault_cap_idx` for precise faults. |
| `redirect_packet` | Target capability payload, target tag, target slot, and redirect kind. |

Exactly one of `normal_effects`, `fault_packet`, or `redirect_packet` is selected
for a valid packet. Fault packets suppress all normal effects. Redirect packets
kill younger work before the redirected path can retire.

## Memory And Tag Assumptions

- A cell is 24 bits. Instruction and data interfaces are addressed by cell
  address.
- The first smoke slice may use direct fixture memories with no cache, TLB,
  page walk, coherence, or DMA.
- A capability slot is four naturally aligned cells with one sidecar tag bit.
- `CLC` and `CSC` transfer capability payload and tag together when enabled by
  I20-S06.
- Integer stores that overlap a capability slot clear that slot's tag when the
  store retires normally.
- Faulting, killed, or unsupported memory operations cannot create store-buffer
  entries, memory payload writes, or tag writes.
- The data-memory/tag port is allowed to be stubbed for I20-S05, but its
  payload/tag commit timing is fixed at `RT`.

## Unsupported Feature Behavior

Unsupported behavior must be explicit and deterministic:

| Feature | First-slice behavior |
| --- | --- |
| Unsupported opcode or instruction class | Decode to a precise illegal-instruction fault packet and retire that packet at `RT`. |
| Capability, data-memory, trap, call, and protected-stack instructions before their I20 gate | Excluded from the smoke corpus or mapped to the unsupported precise-fault path. |
| MMU, `RADIX4`, TLB, cache, and coherence behavior | Bypassed by fixture memory; instructions that require the feature are unsupported until implemented. |
| Interrupts, debug halt, MMIO, DMA, and secondary cores | Inputs are tied inactive and cannot create trace-visible events in the first smoke slice. |
| MDU, atomics, LL/SC, and fences | Unsupported or conservatively stalled only in tests that explicitly model the feature. |
| Branch predictor performance state | Not present; redirect correctness is required, predictor accuracy is not. |

No fixture may depend on an indefinite stall as the unsupported-feature
behavior. Unsupported work must either be absent from the fixture or produce a
bounded precise fault.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| First-slice inclusions and exclusions are fixed. | Met. |
| Pipeline boundaries are named from `FE0` through `RT`. | Met. |
| Stall and flush rules are explicit. | Met. |
| Commit packet timing and required fields are fixed. | Met. |
| Memory and tag assumptions are fixed before SV starts. | Met. |
| Unsupported-feature behavior is deterministic. | Met. |
