# Program Image Loader

Story: I11-S02

Status: Draft implementation profile

Owner sources:

- I11-S01 defines the program-image manifest and loader boundary.
- I07-S03 defines little-endian 3-octet serialization for ordinary cells.
- I02-S03 defines sparse `TaggedMemory` cells and capability-slot tags.

## Scope

This profile implements the first simulator loader for validated program images.
It loads ordinary serialized 24-bit cell payloads into `TaggedMemory`. It does
not start execution or construct reset state; that belongs to I11-S03.

## Load Order

The loader first validates all inputs without mutating memory:

- manifest acceptance from I11-S01;
- section overlap with protected return-stack storage;
- explicit capability sidecar target sections and slot coverage.

If validation reports any issue, the load fails as one `ProgramImageError` and
no image cell is written.

After validation succeeds:

1. ordinary section cells are written with `TaggedMemory.write_cells`;
2. ordinary writes clear every overlapped capability-slot tag;
3. trusted sidecar entries, if present, install capability payload and tag with
   `TaggedMemory.csc`;
4. the loader returns a count of sections, cells, and sidecar slots loaded.

## Tags

Serialized section octets never fabricate valid capability tags. Tagged initial
capability data can be installed only through explicit `CapabilitySidecarEntry`
values targeting a `CAPDATA` section whose manifest requested
`TRUSTED_CAPABILITY_SIDECAR`.

Every sidecar slot must be 4-cell aligned and inside the CAPDATA section. A
CAPDATA section must have one sidecar entry per naturally aligned capability
slot it covers. Untagged capability payloads are represented by sidecar entries
whose `Capability.tag` is false; absence of a sidecar entry is a load failure,
not an implicit untagged capability.

## Protected Storage

The loader is not a privileged return-stack repair path. Any section that
overlaps `TaggedMemory` protected storage is rejected before writes begin.
