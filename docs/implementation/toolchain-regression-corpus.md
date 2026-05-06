# Toolchain Regression Corpus

Story: I17-S04

Status: Draft executable corpus

## Scope

This story publishes the first executable CPU v0.1 toolchain regression corpus.
It gathers the assembler, serializer, relocatable object, linker, debug
metadata, and selected semantic golden-trace fixtures into one deterministic
check.

The corpus is intentionally small. It is a regression boundary for the current
fixture toolchain, not a final object-file ABI or system distribution format.

## Command

Validate the corpus directly:

```text
python tools\toolchain_corpus.py --check
```

List case IDs and categories:

```text
python tools\toolchain_corpus.py --list
```

Print machine-readable JSON:

```text
python tools\toolchain_corpus.py
```

The full local gate also runs the corpus check through:

```text
python tools\local_checks.py
```

## Coverage

| Category | Required surface |
| --- | --- |
| `reset_smoke` | Serialized reset-to-trap smoke binary sections. |
| `call_return` | Direct `CALL` and packed `RET` binary fixture. |
| `syscall_trap` | Packed `SYS`/`PAUSE` trap site and aligned `IRET`. |
| `capability_memory` | `CSC`, `CLC`, `ST48`, and `LD48` binary fixture. |
| `relocation` | Golden object fixture for branch, call, conditional branch, and data relocations. |
| `debug_metadata` | Linked source lines, symbols, ABI registers, unwind hints, and symbolic locations. |
| `bad_object` | Rejected object fixture with deterministic validation errors. |

Every binary fixture must assemble, serialize, deserialize, and disassemble
back to its canonical source. Every valid object fixture must link without
issues. Every bad-object fixture must fail with its expected diagnostic text.
Cases that reference I20-S02 semantic golden traces must resolve to an existing
trace case ID.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Golden binary fixtures cover reset smoke, call/return, syscall/trap, and capability memory. | Met. |
| Golden object fixtures cover relocation and debug metadata. | Met. |
| Bad-object fixtures are rejected deterministically. | Met. |
| Corpus output is machine-readable JSON. | Met. |
| The corpus runs through `python tools\local_checks.py`. | Met. |
