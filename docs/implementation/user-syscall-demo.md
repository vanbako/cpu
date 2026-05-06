# User Syscall Demo

Story: I18-S03

Status: Draft executable fixture

## Scope

This story demonstrates one user-to-kernel syscall round trip on top of the
I18-S01 user entry fixture and the I18-S02 RADIX4 VM mapping fixture. It is a
small executable contract for trap-frame preservation, syscall argument
validation, user-pointer validation, scalar returns, and capability results.

It is not a general syscall table or process ABI. The minimal scheduler remains
I18-S04.

## Service Contract

The fixture exposes one demo service number. The user passes the service in
`D0`, two scalar addends in `D1` and `D2`, and a user readable pointer in `C0`.
The kernel handler:

- enters through the existing `SYS` trap path;
- saves the software trap frame from `EPCC`, `SR`, `CAUSE`, `TVAL`,
  `CAPCAUSE`, and `FAULTCAPIDX`;
- validates service numbers before reading user pointers;
- validates scalar argument range before reading user pointers;
- validates the user pointer through the existing `LD48` capability and page
  translation path;
- returns status in `D0`, a scalar result or rejection detail in `D1`, and a
  capability result in `C0` on success;
- restores the saved frame with sequential `EPCC` and returns through `IRET`.

Bad service numbers, out-of-range scalar arguments, bad user pointers, and
invalid capability tags all return deterministic status values. Bad user
pointers preserve the underlying fault detail so tests can distinguish page
faults from capability tag faults.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| User `SYS` preserves trap-frame state and returns through `IRET`. | Met. |
| Service numbers and scalar arguments are validated before pointer reads. | Met. |
| Success returns scalar and capability results. | Met. |
| Bad user pointers and invalid tags are rejected deterministically. | Met. |
