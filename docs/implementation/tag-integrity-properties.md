# Tag Integrity Properties

Story: I15-S02

The I15-S02 conformance fixture adds deterministic property-style coverage for
the architectural rule that capability tags are out-of-band metadata. Payload
bits alone are never enough to create a valid capability.

The fixture covers these non-forgery surfaces:

- ordinary cell writes and `ST48` clear overlapped capability-slot tags and
  never set them;
- `CLC` and `CSC` move payload and existing tag state exactly;
- serialized cell payloads remain untagged unless a trusted sidecar or trusted
  construction path explicitly installs a tag;
- tag-unaware DMA writes clear memory tags, and cache invalidation exposes the
  untagged payload rather than manufacturing a tag;
- cache integer writes and cache maintenance cannot restore a cleared tag;
- CCSR commit copies preserve the source tag bit for both valid and invalid
  capabilities;
- halted debug register observation can expose capability tags but cannot
  create them, and scalar debug views expose no tag state.

The cache/DMA cases preserve the v0.1 noncoherent-DMA rule: software may see a
stale cached capability until it performs maintenance, but maintenance does not
turn DMA-written payload bits into a tagged capability.
