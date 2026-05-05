# Tiny ROM Initialization

Story: I14-S01

Status: Draft executable fixture

Owner sources:

- E11-S02 defines ROM/firmware responsibility for capability initialization.
- I08-S01 defines the simulator test-platform profile.
- I11-S03 provides the earlier reset-to-program smoke path.

## Scope

The tiny ROM fixture models the trusted firmware work that happens after the
hardware reset `PCC` reaches `RESET_VECTOR` and before control transfers to the
first kernel handoff point.

It is intentionally small. The fixture validates the test-platform profile,
loads a serialized ROM image, installs trusted tagged capabilities, protects the
return-stack range, clears unowned general capability registers, and installs a
slot-0 `PCC` for the kernel handoff stub.

## Handoff State

At handoff:

- `PCC` names the ROM-resident kernel handoff stub and has `EX`.
- `KRC` is a valid global root capability with broad derivation authority.
- `KSC`, `DSC`, and `RSC` are valid local RAM stack capabilities with `LD`,
  `ST`, `LC`, `SC`, and `SL`, but no `EX`.
- `TVC` is a valid ROM execute capability.
- `DDC` is intentionally invalid.
- `C0-C7` are invalid unless a later handoff ABI explicitly assigns them.
- `D0` carries a small handoff magic value for the executable fixture.

The fixture uses trusted ROM construction for capability tags. It does not imply
that ordinary integer payloads, scalar CSRs, ROM bytes, or RAM data can forge
valid capability tags.

## Kernel Handoff

The first handoff target is a ROM-resident stub in this implementation profile.
Later I14 stories can replace that stub with richer firmware/kernel fixtures,
including trap/syscall/timer handlers and secondary-core bring-up.
