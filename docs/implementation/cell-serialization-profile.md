# Cell Serialization Profile

Story: I07-S03

Status: Draft implementation profile

Owner sources:

- E01-S01 requires every external binary container to define 24-bit cell serialization.
- E09-S01 fixes base-page payload size at 2048 cells.
- E10-S02 fixes cache-line payload size at 16 cells.
- E14-S02 records the toolchain spike for cell-addressed object containers.

## Scope

This profile defines how CPU v0.1 architectural cells are represented in byte-oriented host artifacts such as binary fixtures, loader images, and debugger object containers.

It does not add byte-addressed architectural memory. All architectural labels, relocation addends, trap values, page numbers, cache-line bases, and instruction addresses remain cell addresses. Octet offsets are only host-container offsets.

## Cell Encoding

Each 24-bit architectural cell is serialized as exactly three octets in little-endian order:

```text
cell[7:0], cell[15:8], cell[23:16]
```

Examples:

| Cell value | Serialized octets |
| --- | --- |
| `0x000000` | `00 00 00` |
| `0x123456` | `56 34 12` |
| `0xFFFFFF` | `FF FF FF` |

A serialized payload is valid only when its length is a multiple of three octets. A host-container byte offset names a CPU v0.1 cell boundary only when `offset % 3 == 0`; the corresponding architectural cell address is `offset / 3` plus the section base selected by the container.

## Sections

Object-file sections are cell-addressed:

- Section virtual addresses are expressed in cells.
- Section alignment is expressed in cells.
- Section size is expressed in cells or as a byte payload whose length is exactly `size_cells * 3`.
- Relocation offsets and addends are expressed in cells unless a relocation type explicitly says it patches host-container metadata.

The provisional section magic for raw cell payload fixtures is `CV01CELLS`. A compact object container may wrap these payloads with section metadata, symbol tables, and relocation records, but the payload rule above remains fixed for v0.1 fixtures.

## Fixed Architectural Payload Sizes

| Structure | Cells | Serialized size |
| --- | ---: | ---: |
| Cache line | 16 | 48 octets |
| Base page | 2048 | 6144 octets |

These sizes describe ordinary 24-bit cell payloads. Capability tags are not encoded by ordinary cell bytes and cannot be fabricated by loading a byte container as integer data.

## Capability Tags

Ordinary serialized cell payloads carry no valid capability tags. A trusted loader profile that needs tagged initial authority must provide tag sidecar data or another trusted construction path and must document how payload and tag are installed atomically.

Until that loader profile exists, byte-oriented fixtures should treat serialized capability payload bits as untagged data unless a test harness constructs the tagged capability directly through simulator APIs.
