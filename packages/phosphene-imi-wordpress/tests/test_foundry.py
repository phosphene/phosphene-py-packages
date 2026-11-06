"""Foundry validator tests — pure logic unit tests for the DFT validator.

Tests the validator itself: green (compliant) and red (violating) cases.

@dft
- A1 (pure-io-separation): tests are pure — no I/O, inline source strings.
- A2 (determinism): no datetime/random/uuid.
- A6 (check-result): validator returns DftViolation[] (the proof).
"""

from __future__ import annotations

from phosphene.imi_wordpress.dft import (
    A1_PURE_IO_SEPARATION,
    A2_DETERMINISM,
    A4_DFT_DOCS,
    DftViolation,
)
from phosphene.imi_wordpress.foundry import (
    _extract_call_names,
    _extract_imports,
    _has_dft_docstring,
    format_violations,
    has_errors,
    validate_module,
)

# ── Compliant source (green cases) ──────────────────────────────

COMPLIANT_PURE = '''"""A pure logic module.

@dft
- A1 (pure-io-separation): no I/O imports.
- A2 (determinism): no datetime/random/uuid.
"""

from __future__ import annotations
import json

def add(a: int, b: int) -> int:
    return a + b
'''

COMPLIANT_IO = '''"""An I/O wiring module.

@dft
- A1 (pure-io-separation): I/O wiring — imports urllib (allowed).
"""

from __future__ import annotations
import urllib.request

def fetch(url: str) -> str:
    return urllib.request.urlopen(url).read().decode()
'''


# ── Violating source (red cases) ────────────────────────────────

VIOLATING_NO_DFT = '''"""A module missing the dft annotation."""

def add(a: int, b: int) -> int:
    return a + b
'''

VIOLATING_IO_IN_LOGIC = '''"""A logic module that imports I/O.

@dft
- A1 (pure-io-separation): claims to be pure but imports urllib.
"""

import urllib.request

def fetch(url: str) -> str:
    return urllib.request.urlopen(url).read().decode()
'''

VIOLATING_NON_DETERMINISTIC = '''"""A logic module that calls datetime.now().

@dft
- A2 (determinism): claims determinism but calls datetime.now().
"""

import datetime

def timestamp() -> str:
    return datetime.datetime.now().isoformat()
'''


# ── Tests ────────────────────────────────────────────────────────


class TestValidateModuleGreen:
    """Tests that compliant modules produce zero violations."""

    def test_compliant_pure_module(self) -> None:
        violations = validate_module("logic.py", COMPLIANT_PURE)
        assert violations == []

    def test_compliant_io_module(self) -> None:
        violations = validate_module("client.py", COMPLIANT_IO)
        assert violations == []


class TestValidateModuleRed:
    """Tests that violating modules produce the expected violations."""

    def test_missing_dft_docstring(self) -> None:
        violations = validate_module("logic.py", VIOLATING_NO_DFT)
        assert len(violations) == 1
        assert violations[0].axiom == A4_DFT_DOCS
        assert violations[0].severity == "error"

    def test_io_import_in_logic(self) -> None:
        violations = validate_module("logic.py", VIOLATING_IO_IN_LOGIC)
        a1_violations = [v for v in violations if v.axiom == A1_PURE_IO_SEPARATION]
        assert len(a1_violations) >= 1
        assert "urllib" in a1_violations[0].message

    def test_non_deterministic_call_in_logic(self) -> None:
        violations = validate_module("logic.py", VIOLATING_NON_DETERMINISTIC)
        a2_violations = [v for v in violations if v.axiom == A2_DETERMINISM]
        assert len(a2_violations) >= 1
        assert "datetime.now" in a2_violations[0].message

    def test_io_module_allows_urllib(self) -> None:
        """I/O wiring modules (client.py) are allowed to import urllib."""
        violations = validate_module("client.py", VIOLATING_IO_IN_LOGIC)
        a1_violations = [v for v in violations if v.axiom == A1_PURE_IO_SEPARATION]
        # No A1 violation because client.py is in IO_WIRING_MODULES
        assert a1_violations == []


class TestHelpers:
    """Tests for the helper functions."""

    def test_extract_imports(self) -> None:
        source = "import os\nimport json\nfrom typing import Any\n"
        imports = _extract_imports(source)
        assert "os" in imports
        assert "json" in imports
        assert "typing" in imports

    def test_extract_call_names(self) -> None:
        source = "import datetime\nx = datetime.datetime.now()\n"
        calls = _extract_call_names(source)
        assert "datetime.datetime.now" in calls

    def test_has_dft_docstring_present(self) -> None:
        source = '"""Module.\n\n@dft\n- A1: pure.\n"""\n'
        assert _has_dft_docstring(source) is True

    def test_has_dft_docstring_absent(self) -> None:
        source = '"""Module without dft."""\n'
        assert _has_dft_docstring(source) is False

    def test_has_dft_docstring_no_docstring(self) -> None:
        source = "x = 1\n"
        assert _has_dft_docstring(source) is False


class TestResultHelpers:
    """Tests for has_errors and format_violations (A6 check-result)."""

    def test_has_errors_true_with_error(self) -> None:
        violations = [DftViolation(axiom=A4_DFT_DOCS, file="x.py", message="m", severity="error")]
        assert has_errors(violations) is True

    def test_has_errors_false_with_only_warnings(self) -> None:
        violations = [DftViolation(axiom=A4_DFT_DOCS, file="x.py", message="m", severity="warn")]
        assert has_errors(violations) is False

    def test_has_errors_false_empty(self) -> None:
        assert has_errors([]) is False

    def test_format_violations_empty(self) -> None:
        result = format_violations([])
        assert "✓" in result

    def test_format_violations_with_errors(self) -> None:
        violations = [
            DftViolation(axiom=A4_DFT_DOCS, file="x.py", message="missing", severity="error")
        ]
        result = format_violations(violations)
        assert "✗" in result
        assert "1 error(s)" in result
        assert "x.py" in result
