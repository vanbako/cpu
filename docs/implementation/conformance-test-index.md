# Conformance Test Index

Story: I01-S03

This index maps executable implementation checks to their owning implementation
story, normative architecture owner stories, and E15 audit coverage. Test
filenames stay story-derived; when a `test_*.py` file is added, update this
table in the same change.

## Coverage Rules

- Every `tests/conformance/test_*.py` and `tests/litmus/test_*.py` file has one
  row.
- The implementation story in each test row matches the `test_iXX_sYY`
  filename.
- Every row names at least one architecture owner story or freeze artifact.
- Every row names E15 audit coverage or an E15-derived checker/matrix.
- Local check documentation is indexed because it is the acceptance artifact for
  I01-S02.

## Index

| Artifact | Implementation story | Architecture owner | E15 coverage |
| --- | --- | --- | --- |
| `docs\implementation\local-checks.md` | `I01-S02` | `E15-S07` | `E15-S01`, `E15-S02`, `E15-S07` |
| `tests\conformance\test_i01_s01_package.py` | `I01-S01` | `E15-S07` | `E15-S07` |
| `tests\conformance\test_i01_s03_test_index.py` | `I01-S03` | `E15-S07` | `E15-S01`, `E15-S06`, `E15-S07` |
| `tests\conformance\test_i02_s01_cells.py` | `I02-S01` | `E01-S01` | `E15-S02` |
| `tests\conformance\test_i02_s02_capabilities.py` | `I02-S02` | `E03-S01`, `E03-S02`, `E03-S05` | `E15-S02`, `E15-S05` |
| `tests\conformance\test_i02_s03_memory.py` | `I02-S03` | `E03-S04`, `E10-S03` | `E15-S05` |
| `tests\conformance\test_i02_s04_state.py` | `I02-S04` | `E01-S02`, `E01-S03`, `E01-S04`, `E01-S05` | `E15-S03`, `E15-S06` |
| `tests\conformance\test_i02_s05_reset_csrs.py` | `I02-S05` | `E02-S02`, `E02-S05`, `E11-S01`, `E11-S02` | `E15-S03`, `E15-S06` |
| `tests\conformance\test_i03_s01_instructions.py` | `I03-S01` | `E04-S01`, `E04-S06` | `E15-S06` |
| `tests\conformance\test_i03_s02_integer.py` | `I03-S02` | `E01-S02`, `E04-S02`, `E07-S02` | `E15-S02`, `E15-S04` |
| `tests\conformance\test_i03_s03_capability_derivation.py` | `I03-S03` | `E03-S03`, `E04-S05` | `E15-S05` |
| `tests\conformance\test_i03_s04_memory_ops.py` | `I03-S04` | `E03-S04`, `E03-S05`, `E04-S03`, `E09-S07` | `E15-S04`, `E15-S05` |
| `tests\conformance\test_i04_s01_fetch_slots.py` | `I04-S01` | `E01-S05`, `E04-S01` | `E15-S02`, `E15-S03` |
| `tests\conformance\test_i04_s02_trap_entry.py` | `I04-S02` | `E03-S06`, `E07-S02`, `E07-S03`, `E07-S04` | `E15-S03`, `E15-S04` |
| `tests\conformance\test_i04_s03_iret_epcc.py` | `I04-S03` | `E04-S04`, `E07-S06` | `E15-S03`, `E15-S04` |
| `tests\conformance\test_i04_s04_debug_halt.py` | `I04-S04` | `E12-S01`, `E12-S03` | `E15-S03`, `E15-S04` |
| `tests\conformance\test_i05_s01_call.py` | `I05-S01` | `E05-S04`, `E06-S03`, `E06-S04` | `E15-S03`, `E15-S05`, `E15-S06` |
| `tests\conformance\test_i05_s02_callc.py` | `I05-S02` | `E06-S02`, `E06-S03`, `E06-S04` | `E15-S03`, `E15-S05`, `E15-S06` |
| `tests\conformance\test_i05_s03_ret.py` | `I05-S03` | `E05-S04`, `E06-S03`, `E06-S04` | `E15-S03`, `E15-S05`, `E15-S06` |
| `tests\conformance\test_i06_s01_radix4.py` | `I06-S01` | `E09-S02`, `E09-S05`, `E09-S06`, `E09-S07` | `E15-S04`, `E15-S05` |
| `tests\conformance\test_i06_s02_tlb_sfence.py` | `I06-S02` | `E08-S04`, `E09-S03` | `E15-S05` |
| `tests\conformance\test_i06_s03_llsc.py` | `I06-S03` | `E08-S01`, `E08-S02` | `E15-S05` |
| `tests\litmus\test_i06_s04_memory_litmus.py` | `I06-S04` | `E08-S03`, `E10-S03`, `E10-S04`, `E10-S05` | `E15-S05`, `tools\memory_consistency_litmus.md` |
| `tests\conformance\test_i07_s01_opcodes.py` | `I07-S01` | `E02-S04`, `E02-S05`, `E04-S06` | `E15-S02`, `E15-S06` |
| `tests\conformance\test_i07_s02_assembler.py` | `I07-S02` | `E04-S06`, `E14-S02` | `E15-S02`, `E15-S06` |
| `tests\conformance\test_i07_s03_serialization.py` | `I07-S03` | `E01-S01`, `E14-S02` | `E15-S02`, `E15-S06` |
| `tests\conformance\test_i08_s01_platform_profile.py` | `I08-S01` | `E11-S01`, `E11-S02` | `E15-S03`, `E15-S06` |
| `tests\conformance\test_i08_s02_secondary_startup.py` | `I08-S02` | `E07-S05`, `E11-S03` | `E15-S03`, `E15-S06` |
| `tests\conformance\test_i09_s01_abi.py` | `I09-S01` | `E07-S06`, `E15-S06` | `E15-S06`, `tools\software_contract_matrix.md` |
| `tests\conformance\test_i09_s02_language_abi.py` | `I09-S02` | `E05-S01`, `E05-S02`, `E15-S06` | `E15-S06`, `tools\software_contract_matrix.md` |
| `tests\conformance\test_i09_s03_syscall_abi.py` | `I09-S03` | `E04-S04`, `E05-S01`, `E05-S02` | `E15-S06`, `tools\software_contract_matrix.md` |
| `tests\conformance\test_i09_s04_debug_abi.py` | `I09-S04` | `E05-S04`, `E12-S01`, `E12-S03` | `E15-S03`, `E15-S06`, `tools\software_contract_matrix.md` |
| `tests\conformance\test_i10_s01_rtl_handoff.py` | `I10-S01` | `E13-S01`, `E13-S02`, `E13-S03`, `E13-S04`, `E15-S07` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tests\conformance\test_i11_s01_program_image.py` | `I11-S01` | `E11-S01`, `E11-S02`, `E14-S02` | `E15-S03`, `E15-S05`, `E15-S06` |
| `tests\conformance\test_i11_s02_program_image_loader.py` | `I11-S02` | `E03-S04`, `E11-S01`, `E14-S02` | `E15-S03`, `E15-S05`, `E15-S06` |
| `tests\conformance\test_i11_s03_reset_to_trap_smoke.py` | `I11-S03` | `E04-S02`, `E04-S03`, `E07-S04`, `E11-S01` | `E15-S03`, `E15-S04`, `E15-S06` |
| `tests\conformance\test_i12_s01_local_checks.py` | `I12-S01` | `E15-S07` | `E15-S01`, `E15-S02`, `E15-S07` |
| `tests\conformance\test_i12_s02_story_coverage.py` | `I12-S02` | `E15-S07` | `E15-S01`, `E15-S06`, `E15-S07` |
| `tests\conformance\test_i12_s03_story_drift.py` | `I12-S03` | `E15-S07` | `E15-S01`, `E15-S06`, `E15-S07` |
| `tests\conformance\test_i13_s01_pipeline_trace.py` | `I13-S01` | `E13-S01`, `E07-S03`, `E07-S04` | `E15-S03`, `E15-S04`, `E15-S06` |
| `tests\conformance\test_i13_s02_pipeline_semantic_compare.py` | `I13-S02` | `E13-S01`, `E13-S02`, `E07-S03` | `E15-S03`, `E15-S04`, `E15-S06` |
| `tests\conformance\test_i13_s03_pipeline_hazards.py` | `I13-S03` | `E13-S02`, `E13-S03`, `E13-S04` | `E15-S03`, `E15-S04`, `E15-S06` |
| `tests\conformance\test_i14_s01_tiny_rom.py` | `I14-S01` | `E11-S02`, `E15-S03`, `E15-S06` | `E15-S03`, `E15-S04`, `E15-S06` |
| `tests\conformance\test_i14_s02_kernel_handlers.py` | `I14-S02` | `E07-S05`, `E07-S06`, `E15-S03` | `E15-S03`, `E15-S04`, `E15-S06` |
| `tests\conformance\test_i14_s03_secondary_boot_demo.py` | `I14-S03` | `E11-S03`, `E15-S03`, `E15-S06` | `E15-S03`, `E15-S04`, `E15-S06` |
| `tests\conformance\test_i15_s01_capability_monotonicity.py` | `I15-S01` | `E03-S03`, `E04-S05` | `E15-S01`, `E15-S05` |
| `tests\conformance\test_i15_s02_tag_integrity.py` | `I15-S02` | `E03-S04`, `E04-S03`, `E10-S03`, `E10-S04`, `E10-S05`, `E12-S03` | `E15-S01`, `E15-S05`, `E15-S06` |
| `tests\conformance\test_i15_s03_precise_fault_effects.py` | `I15-S03` | `E07-S03`, `E07-S04`, `E09-S02`, `E09-S07`, `E15-S04` | `E15-S01`, `E15-S04`, `E15-S05` |
| `tests\conformance\test_i16_s01_invariant_registry.py` | `I16-S01` | `E15-S01`, `E15-S04`, `E15-S05`, `E15-S06` | `E15-S01`, `E15-S04`, `E15-S05`, `E15-S06` |
| `tests\conformance\test_i16_s02_capability_generators.py` | `I16-S02` | `E03-S03`, `E04-S05` | `E15-S01`, `E15-S05` |
| `tests\conformance\test_i16_s03_invariant_runner.py` | `I16-S03` | `E03-S03`, `E04-S05`, `E15-S04`, `E15-S05` | `E15-S01`, `E15-S04`, `E15-S05` |
| `docs\implementation\rtl-first-slice-contract.md` | `I20-S01` | `E07-S03`, `E13-S01`, `E13-S03` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tests\conformance\test_i20_s01_rtl_first_slice_contract.py` | `I20-S01` | `E07-S03`, `E13-S01`, `E13-S03` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `docs\implementation\golden-retire-trace-corpus.md` | `I20-S02` | `E04-S02`, `E04-S03`, `E04-S05`, `E05-S04`, `E07-S03`, `E07-S04`, `E13-S01` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tools\golden_trace_corpus.py` | `I20-S02` | `E04-S02`, `E04-S03`, `E04-S05`, `E05-S04`, `E07-S03`, `E07-S04`, `E13-S01` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tests\conformance\test_i20_s02_golden_trace_corpus.py` | `I20-S02` | `E04-S02`, `E04-S03`, `E04-S05`, `E05-S04`, `E07-S03`, `E07-S04`, `E13-S01` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `docs\implementation\systemverilog-interface-spec.md` | `I20-S03` | `E04-S06`, `E07-S03`, `E13-S01` | `E15-S02`, `E15-S03`, `E15-S04`, `E15-S07` |
| `tools\sv_interface_spec.py` | `I20-S03` | `E04-S06`, `E07-S03`, `E13-S01` | `E15-S02`, `E15-S03`, `E15-S04`, `E15-S07` |
| `tests\conformance\test_i20_s03_sv_interface_spec.py` | `I20-S03` | `E04-S06`, `E07-S03`, `E13-S01` | `E15-S02`, `E15-S03`, `E15-S04`, `E15-S07` |
| `docs\implementation\verilator-differential-harness.md` | `I20-S04` | `E07-S03`, `E13-S01`, `E15-S07` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tools\verilator_diff_harness.py` | `I20-S04` | `E07-S03`, `E13-S01`, `E15-S07` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tests\conformance\test_i20_s04_verilator_harness.py` | `I20-S04` | `E07-S03`, `E13-S01`, `E15-S07` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `docs\implementation\rtl-smoke-slice.md` | `I20-S05` | `E04-S02`, `E04-S06`, `E07-S03`, `E13-S01` | `E15-S02`, `E15-S03`, `E15-S04`, `E15-S07` |
| `tools\rtl_smoke_slice.py` | `I20-S05` | `E04-S02`, `E04-S06`, `E07-S03`, `E13-S01` | `E15-S02`, `E15-S03`, `E15-S04`, `E15-S07` |
| `tests\conformance\test_i20_s05_rtl_smoke_slice.py` | `I20-S05` | `E04-S02`, `E04-S06`, `E07-S03`, `E13-S01` | `E15-S02`, `E15-S03`, `E15-S04`, `E15-S07` |
| `docs\implementation\rtl-capability-memory-slice.md` | `I20-S06` | `E03-S01`, `E03-S03`, `E03-S04`, `E04-S03`, `E04-S05`, `E07-S03` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tools\rtl_cap_mem_slice.py` | `I20-S06` | `E03-S01`, `E03-S03`, `E03-S04`, `E04-S03`, `E04-S05`, `E07-S03` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tests\conformance\test_i20_s06_rtl_cap_mem_slice.py` | `I20-S06` | `E03-S01`, `E03-S03`, `E03-S04`, `E04-S03`, `E04-S05`, `E07-S03` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `docs\implementation\rtl-fault-trap-slice.md` | `I20-S07` | `E04-S04`, `E05-S04`, `E06-S04`, `E07-S03`, `E07-S04`, `E07-S06` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tools\rtl_fault_trap_slice.py` | `I20-S07` | `E04-S04`, `E05-S04`, `E06-S04`, `E07-S03`, `E07-S04`, `E07-S06` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tests\conformance\test_i20_s07_rtl_fault_trap_slice.py` | `I20-S07` | `E04-S04`, `E05-S04`, `E06-S04`, `E07-S03`, `E07-S04`, `E07-S06` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `docs\implementation\rtl-readiness-gap-report.md` | `I20-S08` | `E13-S01`, `E15-S07` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tools\rtl_readiness_gap.py` | `I20-S08` | `E13-S01`, `E15-S07` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tests\conformance\test_i20_s08_rtl_readiness_gap.py` | `I20-S08` | `E13-S01`, `E15-S07` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
