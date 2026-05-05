# Reset To Trap Smoke Fixture

Story: I11-S03

Status: Draft executable fixture

Owner sources:

- I11-S01 defines the program-image manifest.
- I11-S02 loads serialized cell sections into simulator memory.
- I04-S02 defines direct trap entry through `TVC`.
- I04-S03 defines `IRET` and slot-aware `EPCC` restore.

## Scope

This fixture is the first reset-to-program execution path for the semantic
simulator. It is intentionally small and does not replace a real ROM or kernel.
Firmware bring-up remains I14.

The fixture uses the test platform reset path, a serialized ROM image, a
hand-authored decoded program matching the serialized cells, and a small
simulator authority hook that installs the data capability and `TVC` required by
the smoke test.

## Main Program

The main serialized source is:

```text
ADD D2, D0, D1
ST48 C0, D3, D2
LD48 D4, C0, D3
SYS
PAUSE
```

`SYS` and `PAUSE` are packed 12-bit instructions in the same architectural
cell. `SYS` starts at slot 0. `PAUSE` is reached only after the trap handler
restores `EPCC` to slot 1.

## Trap Handler

The handler serialized source is:

```text
EPCCRD C1, D5
CPY D5, D7
EPCCWR C1, D5
IRET
```

The smoke harness initializes `D7` to slot 1. The handler therefore leaves the
saved `EPCC` payload unchanged and changes only the saved slot before `IRET`.

## Expected Outcome

A successful run:

- loads the serialized ROM sections through the program-image loader;
- resets core 0 through the test platform;
- executes integer `ADD`, `ST48`, and `LD48`;
- raises a `SYSCALL_TRAP` for `SYS`;
- enters `TVC`;
- returns with `IRET` to the packed slot-1 `PAUSE`;
- retires `PAUSE` and finishes at the next cell, slot 0.
