# cpu_v01 Source Package

This directory will hold the CPU v0.1 semantic simulator and implementation libraries.

The first implementation target is an internal decoded-instruction semantic model. Binary opcode decoding and assembler integration should be added after the semantic model has conformance coverage.

Current implementation story:

- I01-S01: package skeleton and import smoke test.
- I02-S01: 24-bit cell and 48-bit address helpers.
- I02-S02: capability payload, tag, permission, flag, and object-type data types.
- I02-S03: cell-addressed memory and capability-slot tag storage.
