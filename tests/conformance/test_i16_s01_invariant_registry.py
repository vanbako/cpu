"""I16-S01 conformance tests for the invariant registry and coverage matrix."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cpu_v01 import invariants


class InvariantRegistryTests(unittest.TestCase):
    def test_registry_self_validation_passes(self) -> None:
        self.assertEqual(invariants.validate_invariant_registry(), ())

    def test_registry_covers_i15_security_property_stories(self) -> None:
        coverage = invariants.invariant_coverage_by_story()

        for story in ("I15-S01", "I15-S02", "I15-S03"):
            with self.subTest(story=story):
                self.assertIn(story, coverage)
                self.assertTrue(
                    any(check.implementation_story == story for check in coverage[story])
                )

    def test_required_invariant_areas_have_executable_artifacts(self) -> None:
        for area in (
            invariants.InvariantArea.AUTHORITY,
            invariants.InvariantArea.TAG_INTEGRITY,
            invariants.InvariantArea.PRECISE_EFFECTS,
        ):
            with self.subTest(area=area):
                checks = invariants.invariant_checks(area)
                self.assertGreater(len(checks), 0)
                for check in checks:
                    self.assertTrue(
                        any(
                            artifact.startswith("tests\\conformance\\")
                            for artifact in check.artifacts
                        )
                    )
                    self.assertTrue(check.e15_coverage)

    def test_registry_artifacts_are_indexed_and_exist(self) -> None:
        indexed = (ROOT / "docs" / "implementation" / "conformance-test-index.md").read_text(
            encoding="utf-8"
        )

        for check in invariants.invariant_checks():
            for artifact in check.artifacts:
                with self.subTest(key=check.key, artifact=artifact):
                    self.assertTrue((ROOT / Path(artifact.replace("\\", "/"))).exists())
                    if artifact.startswith("tests\\conformance\\"):
                        self.assertIn(artifact, indexed)

    def test_coverage_matrix_groups_implementation_owner_and_e15_stories(self) -> None:
        coverage = invariants.invariant_coverage_by_story()

        self.assertIn("E15-S04", coverage)
        self.assertIn("E15-S05", coverage)
        self.assertIn("E15-S06", coverage)
        self.assertIn("E03-S03", coverage)
        self.assertIn("capability_monotonicity", {check.key for check in coverage["E03-S03"]})
        self.assertIn("precise_fault_effects", {check.key for check in coverage["E15-S04"]})
        self.assertIn("tag_non_forgery", {check.key for check in coverage["E15-S05"]})

    def test_invariant_keys_are_stable_and_unique(self) -> None:
        keys = invariants.invariant_keys()

        self.assertEqual(len(keys), len(set(keys)))
        self.assertIn("capability_monotonicity", keys)
        self.assertIn("tag_non_forgery", keys)
        self.assertIn("precise_fault_effects", keys)


if __name__ == "__main__":
    unittest.main()
