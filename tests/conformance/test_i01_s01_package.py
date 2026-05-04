"""I01-S01 package skeleton conformance smoke tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


class PackageSkeletonTests(unittest.TestCase):
    def test_package_imports(self) -> None:
        import cpu_v01

        self.assertEqual(cpu_v01.__version__, "0.0.0")

    def test_package_info_identifies_first_story(self) -> None:
        import cpu_v01

        self.assertEqual(
            cpu_v01.package_info(),
            {
                "name": "cpu_v01",
                "architecture": "CPU v0.1",
                "implementation_story": "I01-S01",
            },
        )


if __name__ == "__main__":
    unittest.main()
