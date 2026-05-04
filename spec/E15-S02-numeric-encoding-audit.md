# E15-S02: Numeric Constants and Encoding Audit

Story: E15-S02

Status: Complete

Prerequisite:

- `spec/E15-S01-terminology-cross-reference-audit.md`

Audit tool:

- `tools/spec_constants_model.py`

## Decision

The v0.1 numeric architecture contract is internally consistent after the corrections listed below.

No unresolved blocking numeric, encoding, or bitfield inconsistency remains in this audit scope.

## Corrections Applied

| Finding | Severity | Correction |
| --- | --- | --- |
| E15-S02-F01: Two `SATP` examples in E09-S02 placed `ASID` four bits too low. The normative layout says `SATP[44:37] = ASID[7:0]`, so `ASID=7` must encode as `7 << 37`, and `ASID=1` must encode as `1 << 37`. | Blocking example inconsistency | Updated `spec/E09-S02-satp-layout.md`: `0x000E_0000_0000` -> `0x00E0_0000_0000`, and `0x2002_0001_2345` -> `0x2020_0001_2345`. |
| E15-S02-F02: The new E15-S01 glossary incorrectly said general capability registers were `C0-C15`. E01-S03 defines `C0-C7`. | Non-blocking audit-artifact inconsistency | Updated `spec/E15-S01-terminology-cross-reference-audit.md` to say `C0-C7`. |

## Model Result

Command:

```text
python tools\spec_constants_model.py
```

Observed result:

```text
CPU v0.1 constants model
Checks: 466
Issues: 0
Derived values:
- Base page cells: 2048
- PTEs per page-table page: 1024
- VPN split: 7 + 10 + 10 + 10 = 37
- Cache line: 16 cells = 48 bytes
- SATP RADIX4 ASID 1 root 0x12345: 0x2020_0001_2345
```

The model checks arithmetic invariants, field coverage, map collisions, selected example values, and known stale-text patterns.

## Core Width and Size Constants

| Item | Value | Owner | Result |
| --- | ---: | --- | --- |
| Cell size | 24 bits | E01-S01 | Pass. |
| Host serialization size for one cell | 3 bytes | E14-S02 | Pass: `24 / 8 = 3`. |
| Architectural address width | 48 bits | E01-S01, E09-S01 | Pass. |
| Integer register count | 16, `D0-D15` | E01-S02 | Pass. |
| Integer register width | 48 bits | E01-S02 | Pass. |
| General capability register count | 8, `C0-C7` | E01-S03 | Pass. |
| Capability payload width | 96 bits | E03-S01 | Pass. |
| Capability memory object size | 4 cells | E01-S01, E03-S04 | Pass: `4 * 24 = 96`. |
| Capability tag width | 1 out-of-band bit | E03-S01, E03-S04 | Pass. |
| Fetch group size | 2 cells, 48 bits | E04-S01 | Pass. |
| Cache line size | 16 cells, 48 bytes | E10-S02 | Pass. |

## Capability Layout

| Field | Width | Owner | Result |
| --- | ---: | --- | --- |
| `cursor/address` | 48 bits | E03-S01 | Pass. |
| `bounds metadata` | 30 bits | E03-S01, E14-S01 | Pass. |
| `permissions` | 8 bits | E03-S01, E03-S02 | Pass. |
| `object type` | 8 bits | E03-S01, E03-S03 | Pass. |
| `flags` | 2 bits | E03-S01, E03-S05 | Pass. |
| Total payload | 96 bits | E03-S01 | Pass: `48 + 30 + 8 + 8 + 2 = 96`. |

Permission-bit count is also consistent with the eight named permissions: `LD`, `ST`, `EX`, `LC`, `SC`, `SL`, `SEAL`, and `UNSEAL`.

## Page and Cache Geometry

| Item | Value | Owner | Result |
| --- | ---: | --- | --- |
| Base page size | `2^11` cells = 2048 cells | E09-S01 | Pass. |
| PTE size | 48 bits = 2 cells | E09-S05 | Pass. |
| PTEs per page-table page | 1024 | E09-S04 | Pass: `2048 / 2 = 1024`. |
| Full PTE index bits | 10 | E09-S04 | Pass: `log2(1024) = 10`. |
| VPN bits | 37 | E09-S04 | Pass: `48 - 11 = 37`. |
| VPN split | `7 + 10 + 10 + 10` | E09-S04 | Pass. |
| PPN width | 37 bits | E09-S02, E09-S05 | Pass: `37 + 11 = 48`. |
| Cache line payload | 16 cells = 384 bits = 48 bytes | E10-S02 | Pass. |
| Capability slots per line | 4 | E10-S02, E14-S04 | Pass: `16 / 4 = 4`. |
| Integer slots per line | 8 | E10-S02 | Pass: `16 / 2 = 8`. |
| Fetch groups per line | 8 | E10-S02 | Pass: `16 / 2 = 8`. |

Reserved future page sizes `2^15` and `2^19` cells remain non-implemented v0.1 reservations. E14-S03 already records that they do not naturally match the selected radix leaf sizes.

## Scalar CSR Numbering

Mandatory fast-window CSRs are contiguous and collision-free.

| Range | Names | Owner | Result |
| --- | --- | --- | --- |
| `0x00-0x0F` | `SR`, `COREID`, `CYCLE`, `INSTRET`, `TVEC`, `CAUSE`, `TVAL`, `SCRATCH`, `IENABLE`, `IPENDING`, `TIMER`, `TIMECMP`, `SATP`, `ASID`, `DEBUGCTL`, `PERFSEL` | E02-S02 | Pass. |
| `0x40-0x47` | `PMC0-PMC7` | E02-S03, E12-S05 | Pass. |
| `0x48` | `CACHECTL` | E02-S03, E10-S05 | Pass. |
| `0x49` | `TLBCTL` | E02-S03, E09-S03, E08-S04 | Pass. |
| `0x4A` | `FAULTCAPIDX` | E02-S03, E03-S06, E07-S04 | Pass. |
| `0x4B` | `CAPCAUSE` | E02-S03, E03-S06, E07-S04 | Pass. |
| `0x4C-0x53` | `IBP0ADDR`, `IBP0CTL`, `IBP1ADDR`, `IBP1CTL`, `DWP0ADDR`, `DWP0CTL`, `DWP1ADDR`, `DWP1CTL` | E12-S02 | Pass. |

The E12-S02 debug comparator assignment is compatible with the E02-S03 `0x4C-0x5F` reserved performance/debug/observability range.

## CCSR Numbering

| CCSR index range | Names | Owner | Result |
| --- | --- | --- | --- |
| `0-7` | `PCC`, `DSC`, `RSC`, `DDC`, `EPCC`, `TVC`, `KSC`, `KRC` | E01-S04, E02-S05 | Pass. |
| `8-255` | Reserved | E02-S05 | Pass. |

CCSR indices are distinct from scalar CSR numbers. No scalar CSR collision exists.

## Bitfield Layouts

The model checks that these 48-bit layouts cover all bits exactly once and have no overlaps:

- `SR`
- `SATP`
- `PTE`
- final `DEBUGCTL` after E12-S03 assigns `STEP`
- `PERFSEL`
- instruction breakpoint control CSRs
- data watchpoint control CSRs

Field-width results:

| Field group | Key result |
| --- | --- |
| `SR` | Bits `0-9` are assigned; bits `47:10` are `RES0`. |
| `SATP` | `MODE[47:45]`, `ASID[44:37]`, and `ROOT_PPN[36:0]` exactly fill 48 bits. |
| `PTE` | `PPN[47:11]` plus control bits `10:0` exactly fill 48 bits. |
| `DEBUGCTL` | E12-S03 correctly refines E12-S01 by assigning bit `5` to `STEP`, leaving `7:6` reserved. |
| `PERFSEL` | `IDX`, `EVENT`, `EN`, `CLR`, `CFGW`, and reserved fields exactly fill 48 bits. |
| `IBPCTL` and `DWPCTL` | ASID and reserved fields fit the 48-bit comparator control layout. |

## Cause, Selector, and Mode Encodings

| Namespace | Assigned values | Result |
| --- | --- | --- |
| Synchronous `CAUSE` values | `0x0000-0x000E`, `0x0020-0x0026`, `0x0030-0x0032` | Pass; no collisions. |
| Interrupt `CAUSE` values | Bit 47 set, codes `0x0001-0x0003` | Pass; no collisions with synchronous causes. |
| `IPENDING`/`IENABLE` source bits | Timer bit 0, software IPI bit 1, external bit 2 | Pass. |
| Interrupt vector indexes | Direct exception index 0; timer/software/external indexes 1/2/3; debug-monitor index 4 | Pass. |
| `CAPCAUSE` values | `0x0-0x5` assigned, `0x6-0xF` reserved | Pass. |
| `FAULTCAPIDX` values | `NONE`, `UNKNOWN`, `C0-C7`, and special capability registers | Pass. |
| `SATP.MODE` | `BARE=0b000`, `RADIX4=0b001`, others reserved | Pass. |
| PTE `MT` | `NORMAL_COHERENT=0b00`, `NORMAL_UNCACHEABLE=0b01`, `DEVICE_ORDERED=0b10`, `0b11` reserved | Pass. |
| `DCAUSE` | `0x0-0x7` assigned, `0x8-0xF` reserved | Pass. |
| `PERFSEL.EVENT` | `0x00-0x09` assigned, higher ranges reserved/platform/implementation-specific | Pass. |

## Example-value Checks

The model recalculates selected examples from owner-story formulas.

| Example group | Result |
| --- | --- |
| `SATP` examples in E09-S02 | Pass after correction. |
| PTE examples in E09-S05 | Pass. |
| `C0-C7` text in completed specs and audits | Pass. No stale `C0-C15` string remains. |

Corrected `SATP` examples now follow:

```text
satp = (MODE << 45) | (ASID << 37) | ROOT_PPN
```

So:

- `BARE`, ASID 7, root 0 = `0x00E0_0000_0000`
- `RADIX4`, ASID 1, root PPN `0x12345` = `0x2020_0001_2345`

## Reserved and Deferred Numeric Areas

These are intentional non-findings:

- Final binary opcode bit positions are not frozen in v0.1. E04-S06 owns mandatory opcode coverage, not numeric opcode allocation.
- `CACHECTL` and `TLBCTL` CSR numbers are assigned reservations. Their required architectural effects are expressed through instructions and owning stories.
- Platform interrupt-controller CSRs in `0x80-0xBF` are reserved for platform profiles.
- Implementation-specific CSRs in `0xC0-0xEF` are allowed only with implementation/platform documentation.
- Future architectural CSRs in `0xF0-0xFF`, reserved PTE memory type `0b11`, reserved `SATP.MODE` values, reserved `CAPCAUSE` values, and reserved debug causes remain unavailable in v0.1.
- WARL legal-value subsets for `TVEC.VSHIFT`, `SATP`, `PERFSEL.EVENT`, and implementation-dependent predictor sizes are bounded by owner stories, not fully enumerated here.

## Story Acceptance Review

| Acceptance criterion | Result |
| --- | --- |
| Cell, byte, object-size, alignment, fetch-group, cache-line, and page-size values are consistent. | Met. |
| Virtual address, physical address, PPN, VPN, ASID, CSR, CCSR, PTE, and capability field widths are consistent. | Met. |
| CSR numbers, CCSR indices, exception cause codes, debug cause codes, interrupt bits, permission bits, memory-type encodings, and reserved fields do not collide unless explicitly aliased. | Met. |
| Instruction-size and slot rules agree across fetch, control transfer, single-step, branch prediction, trap, and ABI stories. | Met for numeric slot/fetch-group values; behavioral state-transition details continue in E15-S03. |
| All reserved encodings say whether access traps, reads as zero, writes ignore, writes fault, or is platform-defined. | Met for the audited numeric namespaces; remaining WARL legal subsets are intentionally implementation/profile constrained by owner stories. |
| Any numeric correction identifies every artifact that must change. | Met: E09-S02 and E15-S01 were corrected. |
