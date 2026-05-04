# RTL Handoff Checklist

Story: I10-S01

RTL should consume the semantic model, opcode table, and conformance suite rather than reinterpreting prose independently.

## Decoder Table

The executable decoder table is derived from `src/cpu_v01/opcodes.py` and exposed through `src/cpu_v01/rtl.py`. Each row carries:

- canonical mnemonic;
- instruction size;
- opcode selector;
- fixed mask/value;
- binary operand format;
- privilege class.

`SCALL` resolves to canonical `SYS`. CSR instructions expose both fast and long forms.

## Commit Points

The first RTL must define explicit RT commit boundaries for:

- normal retire effect packets;
- fault/debug priority and normal-effect suppression;
- control redirects;
- payload/tag memory commits;
- protected return-stack transactions;
- LL/SC reservation updates;
- TLB and cache-maintenance effects.

Fault packets carry `cause`, `faulting_location`, `tval`, `capcause`, and `fault_cap_idx`.

## Tag Paths

RTL must keep tags explicit on:

- general and special capability registers;
- naturally aligned memory capability slots;
- `CLC`/`CSC` transfers;
- CCSR copies;
- debug observability paths.

No integer payload, scalar CSR write, or byte/container serialization path may synthesize a valid tag.

## Conformance Hooks

Before RTL changes are considered compatible with the semantic model, run:

```text
python -m unittest discover -s tests\conformance -p "test_*.py"
python -m unittest discover -s tests\litmus -p "test_*.py"
python tools\spec_reference_check.py
python tools\spec_constants_model.py
```
