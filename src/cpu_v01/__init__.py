"""CPU v0.1 semantic simulator package.

The package starts with implementation backlog story I01-S01: a minimal
importable skeleton for the simulator and conformance tests.
"""

from __future__ import annotations

__all__ = ["__version__", "package_info"]

__version__ = "0.0.0"


def package_info() -> dict[str, str]:
    """Return stable package metadata for smoke tests and tooling."""
    return {
        "name": "cpu_v01",
        "architecture": "CPU v0.1",
        "implementation_story": "I01-S01",
    }
