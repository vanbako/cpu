# Precise Fault Properties

Story: I15-S03

The I15-S03 conformance fixture adds deterministic property-style coverage for
fault side-effect boundaries. It focuses on surfaces that previously had
targeted story tests and checks them as a shared invariant: a faulting operation
does not commit partial architectural updates.

The fixture covers:

- memory-operation fault priority with unchanged destination registers, memory
  payloads, memory tags, and local TLB state;
- RADIX4 page faults that do not install partial TLB entries;
- `SFENCE.VM` privilege faults that do not apply pending TLB invalidation or
  reservation effects before a normal retire commit;
- LL/SC faults that clear the existing reservation as specified, without
  installing a new reservation or changing integer, memory, or tag state;
- fatal trap-delivery failures through invalid `TVC`, preserving trap CSRs,
  `PCC`, and `EPCC` while still clearing the active reservation at trap entry;
- protected return-stack `CALL` and `RET` failures that leave `PCC`, `RSC`, and
  protected slots unchanged.

The reservation clears above are explicit architectural effects for trap and
faulting LL/SC paths, not partial stores or destination-register commits.
