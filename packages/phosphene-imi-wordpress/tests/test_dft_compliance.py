"""DFT compliance spec — validates all source modules against the six axioms.

This is the CI guard. It runs the pure validator on every Python source
file in the package and asserts zero violations. A violation fails CI.

@dft
- A5 (mock-doubles): reads real source files — no mocks.
- A6 (check-result): the validator returns DftViolation[] — the test
  asserts the list is empty and prints every violation if it isn't.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from phosphene.imi_wordpress.foundry import (
    has_errors,
    validate_package,
)

# The source directory: src/phosphene/imi_wordpress
SRC_DIR = Path(__file__).resolve().parent.parent / "src" / "phosphene" / "imi_wordpress"


def test_source_directory_exists() -> None:
    """The source directory must exist for compliance checks."""
    assert SRC_DIR.exists(), f"Source directory not found: {SRC_DIR}"
    assert SRC_DIR.is_dir()


def test_all_modules_pass_dft_axioms() -> None:
    """Every source module must pass all six DFT axioms.

    This is the CI guard — a violation fails the build. The test prints
    every violation so the CI log shows exactly what's wrong.
    """
    violations = validate_package(SRC_DIR)

    if has_errors(violations):
        details = "\n".join(
            f"  {v.severity == 'error' and '✗' or '⚠'} [{v.axiom}] {v.file}: {v.message}"
            for v in violations
        )
        pytest.fail(f"{len(violations)} DFT violation(s) found:\n{details}")
