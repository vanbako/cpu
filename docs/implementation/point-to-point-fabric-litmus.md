# Point-To-Point Fabric Litmus

Story: I19-S04

Status: Draft executable litmus suite

## Scope

This story adds the first deterministic CPU-side integration suite for a future
point-to-point module fabric. It still does not define packet formats, link
training, switch routing, discovery, endpoint identity, or address-window
assignment. The separate computer-architecture repository should own those.

The CPU repository fixture only proves that the current CPU-visible contracts
compose across four cores and logical ingress names.

## Covered Litmus Cases

The suite covers:

- four-core startup from reset through the existing secondary-start mailbox;
- fabric event delivery through logical left, right, fabric 0, and fabric 1
  ingress names;
- shared-memory visibility after `FENCE` drains all four store buffers;
- LL/SC contention where one core succeeds and three contending stores fail;
- coherence/tag visibility where `CSC` publishes a valid tag and integer store
  clears it for peers;
- external-agent ordering by reusing the noncoherent ownership handoff fixture.

The logical ingress names are adapter-facing identifiers. They are not a bus and
do not imply any physical topology inside this repository.

## Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Four-core startup runs deterministically. | Met. |
| Fabric-delivered external events vector and acknowledge on all four cores. | Met. |
| Shared-memory ordering is deterministic after fences. | Met. |
| LL/SC contention has one successful `SC48` and deterministic failures. | Met. |
| Capability payload/tag visibility composes with coherent writes. | Met. |
| External-agent ordering composes through the I19-S03 handoff fixture. | Met. |
