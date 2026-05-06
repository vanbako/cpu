# Minimal Scheduler Fixture

Story: I18-S04

Status: Draft executable fixture

## Scope

This story adds the first deterministic scheduler fixture above the user entry,
VM mapping, and syscall demo fixtures. It models a two-task timer preemption and
context switch. It is not a full OS scheduler, priority policy, or multiprocessor
run queue.

## Timer Preemption

The running task executes in user mode with a RADIX4 `SATP`, nonzero ASID, ABI
integer registers, capability registers, and user stack capabilities installed.
A timer interrupt is delivered through the existing interrupt entry path. The
scheduler saves:

- all `D0-D15` integer registers;
- all `C0-C7` capability registers and their tags;
- `PCC` through the saved `EPCC` trap frame;
- `DSC`, `RSC`, `DDC`, `TVC`, `KSC`, and `KRC`;
- trap context CSRs captured in the software frame;
- `SATP` and ASID.

## Switch And Resume

The fixture restores a second runnable task's saved ABI registers, capability
registers, special capabilities, trap frame, `SATP`, and ASID. It clears any
stale LL/SC reservations before resuming the restored task through the existing
`IRET` implementation. The final user state is the second task's saved `EPCC`
and status restored by `IRET`.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Timer preemption switches two runnable tasks. | Met. |
| ABI registers, trap context, capabilities, tags, `SATP`, and ASID are saved. | Met. |
| LL/SC reservations are cleared by preemption and context switch. | Met. |
| The restored task resumes through `IRET`. | Met. |
