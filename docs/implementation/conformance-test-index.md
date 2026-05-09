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
| `docs\implementation\relocatable-object-metadata.md` | `I17-S01` | `E01-S05`, `E03-S04`, `E05-S04`, `E14-S02` | `E15-S02`, `E15-S05`, `E15-S06`, `E15-S07` |
| `tests\conformance\test_i17_s01_object_metadata.py` | `I17-S01` | `E01-S05`, `E03-S04`, `E05-S04`, `E14-S02` | `E15-S02`, `E15-S05`, `E15-S06`, `E15-S07` |
| `docs\implementation\linker-relocation-fixtures.md` | `I17-S02` | `E01-S05`, `E04-S01`, `E04-S04`, `E14-S02` | `E15-S02`, `E15-S06`, `E15-S07` |
| `tests\conformance\test_i17_s02_linker_relocations.py` | `I17-S02` | `E01-S05`, `E04-S01`, `E04-S04`, `E14-S02` | `E15-S02`, `E15-S06`, `E15-S07` |
| `docs\implementation\debug-metadata.md` | `I17-S03` | `E12-S01`, `I09-S04` | `E15-S02`, `E15-S06`, `E15-S07` |
| `tests\conformance\test_i17_s03_debug_metadata.py` | `I17-S03` | `E12-S01`, `I09-S04` | `E15-S02`, `E15-S06`, `E15-S07` |
| `docs\implementation\toolchain-regression-corpus.md` | `I17-S04` | `E01-S05`, `E04-S01`, `E04-S04`, `E04-S05`, `E05-S04`, `E12-S01`, `E14-S02` | `E15-S02`, `E15-S06`, `E15-S07` |
| `tools\toolchain_corpus.py` | `I17-S04` | `E01-S05`, `E04-S01`, `E04-S04`, `E04-S05`, `E05-S04`, `E12-S01`, `E14-S02` | `E15-S02`, `E15-S06`, `E15-S07` |
| `tests\conformance\test_i17_s04_toolchain_corpus.py` | `I17-S04` | `E01-S05`, `E04-S01`, `E04-S04`, `E04-S05`, `E05-S04`, `E12-S01`, `E14-S02` | `E15-S02`, `E15-S06`, `E15-S07` |
| `docs\implementation\user-process-entry.md` | `I18-S01` | `E05-S01`, `E05-S02`, `E07-S01`, `E09-S02`, `E09-S07`, `E11-S01` | `E15-S02`, `E15-S03`, `E15-S06`, `E15-S07` |
| `tests\conformance\test_i18_s01_user_process.py` | `I18-S01` | `E05-S01`, `E05-S02`, `E07-S01`, `E09-S02`, `E09-S07`, `E11-S01` | `E15-S02`, `E15-S03`, `E15-S06`, `E15-S07` |
| `docs\implementation\vm-page-mapping.md` | `I18-S02` | `E09-S02`, `E09-S03`, `E09-S06`, `E09-S07`, `E11-S01`, `I18-S01` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tests\conformance\test_i18_s02_vm_mapping.py` | `I18-S02` | `E09-S02`, `E09-S03`, `E09-S06`, `E09-S07`, `E11-S01`, `I18-S01` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `docs\implementation\user-syscall-demo.md` | `I18-S03` | `E04-S04`, `E05-S01`, `E05-S02`, `E07-S06`, `I09-S03`, `I14-S02`, `I18-S01`, `I18-S02` | `E15-S03`, `E15-S04`, `E15-S06`, `E15-S07` |
| `tests\conformance\test_i18_s03_syscall_demo.py` | `I18-S03` | `E04-S04`, `E05-S01`, `E05-S02`, `E07-S06`, `I09-S03`, `I14-S02`, `I18-S01`, `I18-S02` | `E15-S03`, `E15-S04`, `E15-S06`, `E15-S07` |
| `docs\implementation\minimal-scheduler.md` | `I18-S04` | `E05-S01`, `E05-S02`, `E07-S05`, `E07-S06`, `E08-S02`, `E09-S02`, `I18-S01`, `I18-S02`, `I18-S03` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S06`, `E15-S07` |
| `tests\conformance\test_i18_s04_scheduler.py` | `I18-S04` | `E05-S01`, `E05-S02`, `E07-S05`, `E07-S06`, `E08-S02`, `E09-S02`, `I18-S01`, `I18-S02`, `I18-S03` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S06`, `E15-S07` |
| `docs\implementation\external-fabric-cpu-boundary.md` | `I19-S01` | `E07-S05`, `E09-S06`, `E10-S04`, `E10-S05`, `E11-S03` | `E15-S03`, `E15-S05`, `E15-S06`, `E15-S07` |
| `docs\implementation\endpoint-event-routing.md` | `I19-S02` | `E07-S05`, `E11-S03`, `I14-S03`, `I18-S04`, `I19-S01` | `E15-S03`, `E15-S05`, `E15-S06`, `E15-S07` |
| `tests\conformance\test_i19_s02_endpoint_events.py` | `I19-S02` | `E07-S05`, `E11-S03`, `I14-S03`, `I18-S04`, `I19-S01` | `E15-S03`, `E15-S05`, `E15-S06`, `E15-S07` |
| `docs\implementation\external-agent-transfers.md` | `I19-S03` | `E10-S03`, `E10-S04`, `E10-S05`, `I06-S04`, `I15-S02`, `I18-S02`, `I19-S01` | `E15-S03`, `E15-S05`, `E15-S06`, `E15-S07` |
| `tests\conformance\test_i19_s03_external_transfers.py` | `I19-S03` | `E10-S03`, `E10-S04`, `E10-S05`, `I06-S04`, `I15-S02`, `I18-S02`, `I19-S01` | `E15-S03`, `E15-S05`, `E15-S06`, `E15-S07` |
| `docs\implementation\point-to-point-fabric-litmus.md` | `I19-S04` | `E08-S03`, `E10-S03`, `I06-S03`, `I06-S04`, `I19-S02`, `I19-S03` | `E15-S03`, `E15-S05`, `E15-S06`, `E15-S07` |
| `tests\litmus\test_i19_s04_fabric_integration.py` | `I19-S04` | `E08-S03`, `E10-S03`, `I06-S03`, `I06-S04`, `I19-S02`, `I19-S03` | `E15-S03`, `E15-S05`, `E15-S06`, `E15-S07` |
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
| `docs\implementation\rtl-scalar-control-slice.md` | `I21-S01` | `E02-S04`, `E02-S05`, `E04-S02`, `E04-S04`, `E04-S06`, `E07-S03` | `E15-S02`, `E15-S03`, `E15-S04`, `E15-S07` |
| `tools\rtl_scalar_control_slice.py` | `I21-S01` | `E02-S04`, `E02-S05`, `E04-S02`, `E04-S04`, `E04-S06`, `E07-S03` | `E15-S02`, `E15-S03`, `E15-S04`, `E15-S07` |
| `tests\conformance\test_i21_s01_rtl_scalar_control.py` | `I21-S01` | `E02-S04`, `E02-S05`, `E04-S02`, `E04-S04`, `E04-S06`, `E07-S03` | `E15-S02`, `E15-S03`, `E15-S04`, `E15-S07` |
| `docs\implementation\rtl-mmu-tlb-slice.md` | `I21-S02` | `E08-S04`, `E09-S02`, `E09-S03`, `E09-S05`, `E09-S07`, `I06-S01`, `I06-S02`, `I18-S02` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tools\rtl_mmu_tlb_slice.py` | `I21-S02` | `E08-S04`, `E09-S02`, `E09-S03`, `E09-S05`, `E09-S07`, `I06-S01`, `I06-S02`, `I18-S02` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tests\conformance\test_i21_s02_rtl_mmu_tlb.py` | `I21-S02` | `E08-S04`, `E09-S02`, `E09-S03`, `E09-S05`, `E09-S07`, `I06-S01`, `I06-S02`, `I18-S02` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `docs\implementation\rtl-atomic-cache-slice.md` | `I21-S03` | `E08-S01`, `E08-S02`, `E08-S04`, `E10-S05`, `I06-S03`, `I06-S04`, `I21-S02` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tools\rtl_atomic_cache_slice.py` | `I21-S03` | `E08-S01`, `E08-S02`, `E08-S04`, `E10-S05`, `I06-S03`, `I06-S04`, `I21-S02` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tests\conformance\test_i21_s03_rtl_atomic_cache.py` | `I21-S03` | `E08-S01`, `E08-S02`, `E08-S04`, `E10-S05`, `I06-S03`, `I06-S04`, `I21-S02` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `docs\implementation\rtl-control-trap-slice.md` | `I21-S04` | `E04-S04`, `E05-S04`, `E06-S02`, `E06-S04`, `E07-S06`, `I14-S02`, `I18-S03`, `I21-S01`, `I21-S02` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S06`, `E15-S07` |
| `tools\rtl_control_trap_slice.py` | `I21-S04` | `E04-S04`, `E05-S04`, `E06-S02`, `E06-S04`, `E07-S06`, `I14-S02`, `I18-S03`, `I21-S01`, `I21-S02` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S06`, `E15-S07` |
| `tests\conformance\test_i21_s04_rtl_control_trap.py` | `I21-S04` | `E04-S04`, `E05-S04`, `E06-S02`, `E06-S04`, `E07-S06`, `I14-S02`, `I18-S03`, `I21-S01`, `I21-S02` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S06`, `E15-S07` |
| `docs\implementation\verilator-regression-gate.md` | `I21-S05` | `E07-S03`, `E13-S01`, `E15-S07`, `I17-S04`, `I20-S02`, `I20-S04`, `I21-S04` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tools\verilator_diff_harness.py` | `I21-S05` | `E07-S03`, `E13-S01`, `E15-S07`, `I17-S04`, `I20-S02`, `I20-S04`, `I21-S04` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tests\conformance\test_i21_s05_verilator_regression_gate.py` | `I21-S05` | `E07-S03`, `E13-S01`, `E15-S07`, `I17-S04`, `I20-S02`, `I20-S04`, `I21-S04` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `docs\implementation\rtl-semantic-closure.md` | `I21-S06` | `E04-S06`, `E07-S03`, `E13-S01`, `E15-S01`, `E15-S04`, `E15-S05`, `E15-S07`, `I16-S01`, `I20-S08`, `I21-S05` | `E15-S01`, `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tools\rtl_semantic_closure.py` | `I21-S06` | `E04-S06`, `E07-S03`, `E13-S01`, `E15-S01`, `E15-S04`, `E15-S05`, `E15-S07`, `I16-S01`, `I20-S08`, `I21-S05` | `E15-S01`, `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tests\conformance\test_i21_s06_rtl_semantic_closure.py` | `I21-S06` | `E04-S06`, `E07-S03`, `E13-S01`, `E15-S01`, `E15-S04`, `E15-S05`, `E15-S07`, `I16-S01`, `I20-S08`, `I21-S05` | `E15-S01`, `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `docs\implementation\rtl-integrated-core-plan.md` | `I22-S01` | `E07-S03`, `E13-S01`, `E15-S07`, `I20-S03`, `I21-S06` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `docs\implementation\rtl-integrated-core-shell.md` | `I22-S01` | `E11-S01`, `E11-S02`, `E13-S01`, `I20-S03`, `I21-S06` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tools\rtl_core_shell.py` | `I22-S01` | `E11-S01`, `E11-S02`, `E13-S01`, `I20-S03`, `I21-S06` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tests\conformance\test_i22_s01_rtl_core_shell.py` | `I22-S01` | `E11-S01`, `E11-S02`, `E13-S01`, `I20-S03`, `I21-S06` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `docs\implementation\rtl-integrated-core-plan.md` | `I22-S02` | `E01-S05`, `E04-S01`, `E04-S06`, `E07-S03`, `I20-S02`, `I21-S01` | `E15-S02`, `E15-S03`, `E15-S04`, `E15-S07` |
| `docs\implementation\rtl-integrated-core-fetch-decode.md` | `I22-S02` | `E01-S05`, `E04-S01`, `E04-S06`, `E07-S03`, `I20-S02`, `I22-S01` | `E15-S02`, `E15-S03`, `E15-S04`, `E15-S07` |
| `tools\rtl_core_fetch_decode.py` | `I22-S02` | `E01-S05`, `E04-S01`, `E04-S06`, `E07-S03`, `I20-S02`, `I22-S01` | `E15-S02`, `E15-S03`, `E15-S04`, `E15-S07` |
| `tests\conformance\test_i22_s02_rtl_core_fetch_decode.py` | `I22-S02` | `E01-S05`, `E04-S01`, `E04-S06`, `E07-S03`, `I20-S02`, `I22-S01` | `E15-S02`, `E15-S03`, `E15-S04`, `E15-S07` |
| `docs\implementation\rtl-integrated-core-plan.md` | `I22-S03` | `E02-S04`, `E02-S05`, `E04-S02`, `E04-S04`, `E07-S03`, `I21-S01` | `E15-S02`, `E15-S03`, `E15-S04`, `E15-S07` |
| `docs\implementation\rtl-integrated-core-scalar-control.md` | `I22-S03` | `E02-S04`, `E02-S05`, `E04-S02`, `E04-S04`, `I21-S01`, `I22-S02` | `E15-S02`, `E15-S03`, `E15-S04`, `E15-S07` |
| `tools\rtl_core_scalar_control.py` | `I22-S03` | `E02-S04`, `E02-S05`, `E04-S02`, `E04-S04`, `I21-S01`, `I22-S02` | `E15-S02`, `E15-S03`, `E15-S04`, `E15-S07` |
| `tests\conformance\test_i22_s03_rtl_core_scalar_control.py` | `I22-S03` | `E02-S04`, `E02-S05`, `E04-S02`, `E04-S04`, `I21-S01`, `I22-S02` | `E15-S02`, `E15-S03`, `E15-S04`, `E15-S07` |
| `docs\implementation\rtl-integrated-core-plan.md` | `I22-S04` | `E03-S01`, `E03-S04`, `E04-S03`, `E04-S05`, `E09-S07`, `I20-S06` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `docs\implementation\rtl-integrated-core-cap-mem.md` | `I22-S04` | `E03-S01`, `E03-S04`, `E04-S03`, `E04-S05`, `E09-S07`, `I20-S06`, `I22-S03` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tools\rtl_core_cap_mem.py` | `I22-S04` | `E03-S01`, `E03-S04`, `E04-S03`, `E04-S05`, `E09-S07`, `I20-S06`, `I22-S03` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tests\conformance\test_i22_s04_rtl_core_cap_mem.py` | `I22-S04` | `E03-S01`, `E03-S04`, `E04-S03`, `E04-S05`, `E09-S07`, `I20-S06`, `I22-S03` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `docs\implementation\rtl-integrated-core-plan.md` | `I22-S05` | `E04-S04`, `E05-S04`, `E06-S02`, `E06-S04`, `E07-S04`, `E07-S06`, `I21-S04` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S06`, `E15-S07` |
| `docs\implementation\rtl-integrated-core-control-trap.md` | `I22-S05` | `E04-S04`, `E05-S04`, `E06-S02`, `E06-S04`, `E07-S04`, `E07-S06`, `I21-S04`, `I22-S04` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S06`, `E15-S07` |
| `tools\rtl_core_control_trap.py` | `I22-S05` | `E04-S04`, `E05-S04`, `E06-S02`, `E06-S04`, `E07-S04`, `E07-S06`, `I21-S04`, `I22-S04` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S06`, `E15-S07` |
| `tests\conformance\test_i22_s05_rtl_core_control_trap.py` | `I22-S05` | `E04-S04`, `E05-S04`, `E06-S02`, `E06-S04`, `E07-S04`, `E07-S06`, `I21-S04`, `I22-S04` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S06`, `E15-S07` |
| `docs\implementation\rtl-integrated-core-plan.md` | `I22-S06` | `E08-S04`, `E09-S02`, `E09-S03`, `E09-S05`, `E09-S07`, `I21-S02` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `docs\implementation\rtl-integrated-core-mmu-tlb.md` | `I22-S06` | `E08-S04`, `E09-S02`, `E09-S03`, `E09-S05`, `E09-S07`, `I21-S02`, `I22-S05` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tools\rtl_core_mmu_tlb.py` | `I22-S06` | `E08-S04`, `E09-S02`, `E09-S03`, `E09-S05`, `E09-S07`, `I21-S02`, `I22-S05` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tests\conformance\test_i22_s06_rtl_core_mmu_tlb.py` | `I22-S06` | `E08-S04`, `E09-S02`, `E09-S03`, `E09-S05`, `E09-S07`, `I21-S02`, `I22-S05` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `docs\implementation\rtl-integrated-core-plan.md` | `I22-S07` | `E08-S01`, `E08-S02`, `E08-S03`, `E08-S04`, `E10-S05`, `I21-S03` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `docs\implementation\rtl-integrated-core-atomic-cache.md` | `I22-S07` | `E08-S01`, `E08-S02`, `E08-S03`, `E08-S04`, `E10-S05`, `I21-S03`, `I22-S06` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tools\rtl_core_atomic_cache.py` | `I22-S07` | `E08-S01`, `E08-S02`, `E08-S03`, `E08-S04`, `E10-S05`, `I21-S03`, `I22-S06` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tests\conformance\test_i22_s07_rtl_core_atomic_cache.py` | `I22-S07` | `E08-S01`, `E08-S02`, `E08-S03`, `E08-S04`, `E10-S05`, `I21-S03`, `I22-S06` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `docs\implementation\rtl-integrated-core-plan.md` | `I22-S08` | `E07-S03`, `E13-S01`, `E15-S07`, `I17-S04`, `I20-S02`, `I21-S05`, `I22-S01` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `docs\implementation\rtl-integrated-core-regression-gate.md` | `I22-S08` | `E07-S03`, `E13-S01`, `E15-S07`, `I17-S04`, `I20-S02`, `I21-S05`, `I22-S01`, `I22-S07` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tools\verilator_diff_harness.py` | `I22-S08` | `E07-S03`, `E13-S01`, `E15-S07`, `I17-S04`, `I20-S02`, `I21-S05`, `I22-S01`, `I22-S07` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tests\conformance\test_i22_s08_rtl_core_regression_gate.py` | `I22-S08` | `E07-S03`, `E13-S01`, `E15-S07`, `I17-S04`, `I20-S02`, `I21-S05`, `I22-S01`, `I22-S07` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `docs\implementation\fpga-first-test-plan.md` | `I23-S01` | `E11-S01`, `E11-S02`, `E13-S01`, `I08-S01`, `I14-S01`, `I20-S03`, `I22-S08` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `src\cpu_v01\fpga_first_test.py` | `I23-S01` | `E11-S01`, `E11-S02`, `E13-S01`, `I08-S01`, `I14-S01`, `I20-S03`, `I22-S08` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tools\fpga_first_test_profile.py` | `I23-S01` | `E11-S01`, `E11-S02`, `E13-S01`, `I08-S01`, `I14-S01`, `I20-S03`, `I22-S08` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tests\conformance\test_i23_s01_fpga_first_test_profile.py` | `I23-S01` | `E11-S01`, `E11-S02`, `E13-S01`, `I08-S01`, `I14-S01`, `I20-S03`, `I22-S08` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `docs\implementation\fpga-first-test-plan.md` | `I23-S02` | `E11-S01`, `E13-S01`, `I20-S03`, `I22-S01`, `I22-S08`, `I23-S01` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `docs\implementation\fpga-top-wrapper.md` | `I23-S02` | `E11-S01`, `E13-S01`, `I20-S03`, `I22-S01`, `I22-S08`, `I23-S01` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `rtl\cpu_v01_fpga_top.sv` | `I23-S02` | `E11-S01`, `E13-S01`, `I20-S03`, `I22-S01`, `I22-S08`, `I23-S01` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `rtl\cpu_v01_fpga_top_tb.sv` | `I23-S02` | `E11-S01`, `E13-S01`, `I20-S03`, `I22-S01`, `I22-S08`, `I23-S01` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `src\cpu_v01\fpga_top.py` | `I23-S02` | `E11-S01`, `E13-S01`, `I20-S03`, `I22-S01`, `I22-S08`, `I23-S01` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tools\fpga_top_wrapper.py` | `I23-S02` | `E11-S01`, `E13-S01`, `I20-S03`, `I22-S01`, `I22-S08`, `I23-S01` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tests\conformance\test_i23_s02_fpga_top_wrapper.py` | `I23-S02` | `E11-S01`, `E13-S01`, `I20-S03`, `I22-S01`, `I22-S08`, `I23-S01` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `docs\implementation\fpga-first-test-plan.md` | `I23-S03` | `E03-S04`, `E10-S03`, `E14-S02`, `I11-S02`, `I14-S01`, `I22-S04`, `I23-S02` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `docs\implementation\fpga-memory-adapters.md` | `I23-S03` | `E03-S04`, `E10-S03`, `E14-S02`, `I11-S02`, `I14-S01`, `I22-S04`, `I23-S02` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `rtl\cpu_v01_fpga_memories.sv` | `I23-S03` | `E03-S04`, `E10-S03`, `E14-S02`, `I11-S02`, `I14-S01`, `I22-S04`, `I23-S02` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `rtl\cpu_v01_fpga_memory_tb.sv` | `I23-S03` | `E03-S04`, `E10-S03`, `E14-S02`, `I11-S02`, `I14-S01`, `I22-S04`, `I23-S02` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `src\cpu_v01\fpga_memory.py` | `I23-S03` | `E03-S04`, `E10-S03`, `E14-S02`, `I11-S02`, `I14-S01`, `I22-S04`, `I23-S02` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tools\fpga_memory_adapters.py` | `I23-S03` | `E03-S04`, `E10-S03`, `E14-S02`, `I11-S02`, `I14-S01`, `I22-S04`, `I23-S02` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tests\conformance\test_i23_s03_fpga_memory_adapters.py` | `I23-S03` | `E03-S04`, `E10-S03`, `E14-S02`, `I11-S02`, `I14-S01`, `I22-S04`, `I23-S02` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `docs\implementation\fpga-first-test-plan.md` | `I23-S04` | `E04-S02`, `E07-S03`, `E11-S01`, `I14-S01`, `I17-S04`, `I22-S03`, `I23-S03` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `docs\implementation\fpga-smoke-firmware.md` | `I23-S04` | `E04-S02`, `E07-S03`, `E11-S01`, `I14-S01`, `I17-S04`, `I22-S03`, `I23-S03` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `rtl\cpu_v01_fpga_first_test_tb.sv` | `I23-S04` | `E04-S02`, `E07-S03`, `E11-S01`, `I14-S01`, `I17-S04`, `I22-S03`, `I23-S03` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `src\cpu_v01\fpga_smoke.py` | `I23-S04` | `E04-S02`, `E07-S03`, `E11-S01`, `I14-S01`, `I17-S04`, `I22-S03`, `I23-S03` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tools\fpga_smoke_firmware.py` | `I23-S04` | `E04-S02`, `E07-S03`, `E11-S01`, `I14-S01`, `I17-S04`, `I22-S03`, `I23-S03` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tests\conformance\test_i23_s04_fpga_smoke_firmware.py` | `I23-S04` | `E04-S02`, `E07-S03`, `E11-S01`, `I14-S01`, `I17-S04`, `I22-S03`, `I23-S03` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `docs\implementation\fpga-first-test-plan.md` | `I23-S05` | `E13-S01`, `E15-S07`, `I20-S04`, `I22-S08`, `I23-S04` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `docs\implementation\fpga-synthesis-gate.md` | `I23-S05` | `E13-S01`, `E15-S07`, `I20-S04`, `I22-S08`, `I23-S04` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `src\cpu_v01\fpga_synthesis.py` | `I23-S05` | `E13-S01`, `E15-S07`, `I20-S04`, `I22-S08`, `I23-S04` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tools\fpga_synthesis_gate.py` | `I23-S05` | `E13-S01`, `E15-S07`, `I20-S04`, `I22-S08`, `I23-S04` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tests\conformance\test_i23_s05_fpga_synthesis_gate.py` | `I23-S05` | `E13-S01`, `E15-S07`, `I20-S04`, `I22-S08`, `I23-S04` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `docs\implementation\fpga-first-test-plan.md` | `I23-S06` | `E11-S01`, `E12-S01`, `E15-S07`, `I23-S05` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `docs\implementation\fpga-board-bringup.md` | `I23-S06` | `E11-S01`, `E12-S01`, `E15-S07`, `I23-S05` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `src\cpu_v01\fpga_bringup.py` | `I23-S06` | `E11-S01`, `E12-S01`, `E15-S07`, `I23-S05` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tools\fpga_bringup_runbook.py` | `I23-S06` | `E11-S01`, `E12-S01`, `E15-S07`, `I23-S05` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tests\conformance\test_i23_s06_fpga_board_bringup.py` | `I23-S06` | `E11-S01`, `E12-S01`, `E15-S07`, `I23-S05` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `docs\implementation\fpga-board-identity.md` | `I24-S01` | `E11-S01`, `E12-S01`, `E15-S07`, `I23-S06` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `src\cpu_v01\fpga_board_identity.py` | `I24-S01` | `E11-S01`, `E12-S01`, `E15-S07`, `I23-S06` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tools\fpga_board_identity.py` | `I24-S01` | `E11-S01`, `E12-S01`, `E15-S07`, `I23-S06` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tests\conformance\test_i24_s01_fpga_board_identity.py` | `I24-S01` | `E11-S01`, `E12-S01`, `E15-S07`, `I23-S06` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `docs\implementation\fpga-constraints-overlay.md` | `I24-S02` | `E11-S01`, `E13-S01`, `E15-S07`, `I23-S05`, `I24-S01` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `constraints\tang_mega_138k_first_test.cst.template` | `I24-S02` | `E11-S01`, `E13-S01`, `E15-S07`, `I23-S05`, `I24-S01` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `constraints\tang_mega_138k_first_test.sdc` | `I24-S02` | `E11-S01`, `E13-S01`, `E15-S07`, `I23-S05`, `I24-S01` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `src\cpu_v01\fpga_constraints.py` | `I24-S02` | `E11-S01`, `E13-S01`, `E15-S07`, `I23-S05`, `I24-S01` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tools\fpga_constraints_overlay.py` | `I24-S02` | `E11-S01`, `E13-S01`, `E15-S07`, `I23-S05`, `I24-S01` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tests\conformance\test_i24_s02_fpga_constraints_overlay.py` | `I24-S02` | `E11-S01`, `E13-S01`, `E15-S07`, `I23-S05`, `I24-S01` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `docs\implementation\fpga-gowin-build.md` | `I24-S03` | `E13-S01`, `E15-S07`, `I20-S04`, `I22-S08`, `I23-S05`, `I24-S02` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `src\cpu_v01\fpga_gowin_build.py` | `I24-S03` | `E13-S01`, `E15-S07`, `I20-S04`, `I22-S08`, `I23-S05`, `I24-S02` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tools\fpga_gowin_build.py` | `I24-S03` | `E13-S01`, `E15-S07`, `I20-S04`, `I22-S08`, `I23-S05`, `I24-S02` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tests\conformance\test_i24_s03_fpga_gowin_build.py` | `I24-S03` | `E13-S01`, `E15-S07`, `I20-S04`, `I22-S08`, `I23-S05`, `I24-S02` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `docs\implementation\fpga-board-programming.md` | `I24-S04` | `E11-S01`, `E12-S01`, `E15-S07`, `I23-S06`, `I24-S03` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `src\cpu_v01\fpga_programming.py` | `I24-S04` | `E11-S01`, `E12-S01`, `E15-S07`, `I23-S06`, `I24-S03` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tools\fpga_board_programming.py` | `I24-S04` | `E11-S01`, `E12-S01`, `E15-S07`, `I23-S06`, `I24-S03` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tests\conformance\test_i24_s04_fpga_board_programming.py` | `I24-S04` | `E11-S01`, `E12-S01`, `E15-S07`, `I23-S06`, `I24-S03` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `docs\implementation\fpga-first-board-evidence.md` | `I24-S05` | `E11-S01`, `E12-S01`, `E15-S07`, `I23-S06`, `I24-S04` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `src\cpu_v01\fpga_first_board_archive.py` | `I24-S05` | `E11-S01`, `E12-S01`, `E15-S07`, `I23-S06`, `I24-S04` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tools\fpga_first_board_archive.py` | `I24-S05` | `E11-S01`, `E12-S01`, `E15-S07`, `I23-S06`, `I24-S04` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tests\conformance\test_i24_s05_fpga_first_board_archive.py` | `I24-S05` | `E11-S01`, `E12-S01`, `E15-S07`, `I23-S06`, `I24-S04` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `docs\implementation\fpga-debug-status-packet.md` | `I25-S01` | `E12-S01`, `E15-S07`, `I23-S04`, `I24-S04` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `src\cpu_v01\fpga_debug_status.py` | `I25-S01` | `E12-S01`, `E15-S07`, `I23-S04`, `I24-S04` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tools\fpga_debug_status_packet.py` | `I25-S01` | `E12-S01`, `E15-S07`, `I23-S04`, `I24-S04` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tests\conformance\test_i25_s01_fpga_debug_status_packet.py` | `I25-S01` | `E12-S01`, `E15-S07`, `I23-S04`, `I24-S04` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `docs\implementation\fpga-uart-status-streamer.md` | `I25-S02` | `E12-S01`, `E15-S07`, `I23-S02`, `I23-S04`, `I24-S04`, `I25-S01` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `rtl\cpu_v01_fpga_top.sv` | `I25-S02` | `E12-S01`, `E15-S07`, `I23-S02`, `I23-S04`, `I24-S04`, `I25-S01` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `rtl\cpu_v01_fpga_top_tb.sv` | `I25-S02` | `E12-S01`, `E15-S07`, `I23-S02`, `I23-S04`, `I24-S04`, `I25-S01` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `rtl\cpu_v01_fpga_first_test_tb.sv` | `I25-S02` | `E12-S01`, `E15-S07`, `I23-S02`, `I23-S04`, `I24-S04`, `I25-S01` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `src\cpu_v01\fpga_uart_status.py` | `I25-S02` | `E12-S01`, `E15-S07`, `I23-S02`, `I23-S04`, `I24-S04`, `I25-S01` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tools\fpga_uart_status_streamer.py` | `I25-S02` | `E12-S01`, `E15-S07`, `I23-S02`, `I23-S04`, `I24-S04`, `I25-S01` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tests\conformance\test_i25_s02_fpga_uart_status_streamer.py` | `I25-S02` | `E12-S01`, `E15-S07`, `I23-S02`, `I23-S04`, `I24-S04`, `I25-S01` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `docs\implementation\fpga-probe-bundles.md` | `I25-S03` | `E12-S01`, `E15-S07`, `I24-S02`, `I25-S01` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `src\cpu_v01\fpga_probe_bundles.py` | `I25-S03` | `E12-S01`, `E15-S07`, `I24-S02`, `I25-S01` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tools\fpga_probe_bundles.py` | `I25-S03` | `E12-S01`, `E15-S07`, `I24-S02`, `I25-S01` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tests\conformance\test_i25_s03_fpga_probe_bundles.py` | `I25-S03` | `E12-S01`, `E15-S07`, `I24-S02`, `I25-S01` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `docs\implementation\fpga-replay-mapper.md` | `I25-S04` | `E12-S01`, `E15-S07`, `I22-S08`, `I23-S06`, `I25-S02` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `src\cpu_v01\fpga_replay_mapper.py` | `I25-S04` | `E12-S01`, `E15-S07`, `I22-S08`, `I23-S06`, `I25-S02` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tools\fpga_replay_mapper.py` | `I25-S04` | `E12-S01`, `E15-S07`, `I22-S08`, `I23-S06`, `I25-S02` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tests\conformance\test_i25_s04_fpga_replay_mapper.py` | `I25-S04` | `E12-S01`, `E15-S07`, `I22-S08`, `I23-S06`, `I25-S02` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `docs\implementation\fpga-debug-evidence-gate.md` | `I25-S05` | `E12-S01`, `E15-S07`, `I24-S05`, `I25-S02`, `I25-S03`, `I25-S04` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `src\cpu_v01\fpga_debug_evidence.py` | `I25-S05` | `E12-S01`, `E15-S07`, `I24-S05`, `I25-S02`, `I25-S03`, `I25-S04` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tools\fpga_debug_evidence.py` | `I25-S05` | `E12-S01`, `E15-S07`, `I24-S05`, `I25-S02`, `I25-S03`, `I25-S04` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tests\conformance\test_i25_s05_fpga_debug_evidence.py` | `I25-S05` | `E12-S01`, `E15-S07`, `I24-S05`, `I25-S02`, `I25-S03`, `I25-S04` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `docs\implementation\fpga-program-image-manifest.md` | `I26-S01` | `E11-S01`, `E11-S02`, `E14-S02`, `I17-S04`, `I23-S03` | `E15-S03`, `E15-S05`, `E15-S06`, `E15-S07` |
| `src\cpu_v01\fpga_program_manifest.py` | `I26-S01` | `E11-S01`, `E11-S02`, `E14-S02`, `I17-S04`, `I23-S03` | `E15-S03`, `E15-S05`, `E15-S06`, `E15-S07` |
| `tools\fpga_program_manifest.py` | `I26-S01` | `E11-S01`, `E11-S02`, `E14-S02`, `I17-S04`, `I23-S03` | `E15-S03`, `E15-S05`, `E15-S06`, `E15-S07` |
| `tests\conformance\test_i26_s01_fpga_program_manifest.py` | `I26-S01` | `E11-S01`, `E11-S02`, `E14-S02`, `I17-S04`, `I23-S03` | `E15-S03`, `E15-S05`, `E15-S06`, `E15-S07` |
| `docs\implementation\fpga-bram-image-generation.md` | `I26-S02` | `E11-S01`, `E11-S02`, `E14-S02`, `I23-S04`, `I26-S01` | `E15-S03`, `E15-S05`, `E15-S06`, `E15-S07` |
| `src\cpu_v01\fpga_bram_images.py` | `I26-S02` | `E11-S01`, `E11-S02`, `E14-S02`, `I23-S04`, `I26-S01` | `E15-S03`, `E15-S05`, `E15-S06`, `E15-S07` |
| `tools\fpga_bram_images.py` | `I26-S02` | `E11-S01`, `E11-S02`, `E14-S02`, `I23-S04`, `I26-S01` | `E15-S03`, `E15-S05`, `E15-S06`, `E15-S07` |
| `tests\conformance\test_i26_s02_fpga_bram_images.py` | `I26-S02` | `E11-S01`, `E11-S02`, `E14-S02`, `I23-S04`, `I26-S01` | `E15-S03`, `E15-S05`, `E15-S06`, `E15-S07` |
| `docs\implementation\fpga-image-update-flow.md` | `I26-S03` | `E15-S07`, `I24-S03`, `I26-S02` | `E15-S03`, `E15-S05`, `E15-S06`, `E15-S07` |
| `src\cpu_v01\fpga_image_update_flow.py` | `I26-S03` | `E15-S07`, `I24-S03`, `I26-S02` | `E15-S03`, `E15-S05`, `E15-S06`, `E15-S07` |
| `tools\fpga_image_update_flow.py` | `I26-S03` | `E15-S07`, `I24-S03`, `I26-S02` | `E15-S03`, `E15-S05`, `E15-S06`, `E15-S07` |
| `tests\conformance\test_i26_s03_fpga_image_update_flow.py` | `I26-S03` | `E15-S07`, `I24-S03`, `I26-S02` | `E15-S03`, `E15-S05`, `E15-S06`, `E15-S07` |
| `docs\implementation\fpga-smoke-program-corpus.md` | `I26-S05` | `E15-S07`, `I25-S04`, `I26-S02` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `src\cpu_v01\fpga_smoke_corpus.py` | `I26-S05` | `E15-S07`, `I25-S04`, `I26-S02` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tools\fpga_smoke_corpus.py` | `I26-S05` | `E15-S07`, `I25-S04`, `I26-S02` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `tests\conformance\test_i26_s05_fpga_smoke_corpus.py` | `I26-S05` | `E15-S07`, `I25-S04`, `I26-S02` | `E15-S03`, `E15-S04`, `E15-S05`, `E15-S07` |
| `docs\implementation\fpga-soc-platform.md` | `I27-S01` | `E11-S01`, `I23-S01`, `I24-S05` | `E15-S03`, `E15-S05`, `E15-S07` |
| `src\cpu_v01\fpga_soc_platform.py` | `I27-S01` | `E11-S01`, `I23-S01`, `I24-S05` | `E15-S03`, `E15-S05`, `E15-S07` |
| `tools\fpga_soc_platform.py` | `I27-S01` | `E11-S01`, `I23-S01`, `I24-S05` | `E15-S03`, `E15-S05`, `E15-S07` |
| `tests\conformance\test_i27_s01_fpga_soc_platform.py` | `I27-S01` | `E11-S01`, `I23-S01`, `I24-S05` | `E15-S03`, `E15-S05`, `E15-S07` |
