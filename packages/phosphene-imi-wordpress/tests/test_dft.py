"""Tests for the DFT axioms module and the Clock/IdGenerator Protocols.

@dft
- A1 (pure-io-separation): tests are pure — no I/O.
- A2 (determinism): tests use DeterministicClock (no wall clock).
- A6 (check-result): Clock methods return values (the proof).
"""

from __future__ import annotations

from phosphene.imi_wordpress.dft import (
    A1_PURE_IO_SEPARATION,
    A2_DETERMINISM,
    A3_MANIFEST_CONFORMANCE,
    A4_DFT_DOCS,
    A5_MOCK_DOUBLES,
    A6_CHECK_RESULT,
    ALL_AXIOMS,
    DeterministicClock,
    DftViolation,
    SystemClock,
)


class TestAxiomConstants:
    """The six axioms are defined and exported."""

    def test_all_six_axioms_defined(self) -> None:
        assert A1_PURE_IO_SEPARATION == "pure-io-separation"
        assert A2_DETERMINISM == "determinism"
        assert A3_MANIFEST_CONFORMANCE == "manifest-conformance"
        assert A4_DFT_DOCS == "dft-docs"
        assert A5_MOCK_DOUBLES == "mock-doubles"
        assert A6_CHECK_RESULT == "check-result"

    def test_all_axioms_tuple_has_six(self) -> None:
        assert len(ALL_AXIOMS) == 6
        assert A1_PURE_IO_SEPARATION in ALL_AXIOMS


class TestDeterministicClock:
    """The DeterministicClock returns fixed, controllable time values."""

    def test_now_ts_returns_fixed_value(self) -> None:
        clock = DeterministicClock(start_ts=1_000_000.0)
        assert clock.now_ts() == 1_000_000.0

    def test_now_iso_returns_fixed_value(self) -> None:
        clock = DeterministicClock(start_iso="2026-08-07T00:00:00+00:00")
        assert clock.now_iso() == "2026-08-07T00:00:00+00:00"

    def test_advance_changes_timestamp(self) -> None:
        clock = DeterministicClock(start_ts=1_000_000.0)
        clock.advance(60.0)
        assert clock.now_ts() == 1_000_060.0

    def test_set_iso_changes_iso_string(self) -> None:
        clock = DeterministicClock()
        clock.set_iso("2026-08-08T12:00:00+00:00")
        assert clock.now_iso() == "2026-08-08T12:00:00+00:00"

    def test_same_sequence_same_output(self) -> None:
        """Determinism: same call sequence → same outputs."""
        clock1 = DeterministicClock(start_ts=100.0)
        clock2 = DeterministicClock(start_ts=100.0)
        for c in (clock1, clock2):
            c.advance(10.0)
            c.advance(20.0)
        assert clock1.now_ts() == clock2.now_ts()


class TestSystemClock:
    """The SystemClock reads real wall-clock time (production only)."""

    def test_now_ts_returns_float(self) -> None:
        clock = SystemClock()
        ts = clock.now_ts()
        assert isinstance(ts, float)
        assert ts > 1_000_000_000  # after ~2001

    def test_now_iso_returns_string(self) -> None:
        clock = SystemClock()
        iso = clock.now_iso()
        assert isinstance(iso, str)
        assert "T" in iso  # ISO format


class TestDftViolation:
    """The DftViolation dataclass carries its own proof (A6)."""

    def test_violation_has_axiom_file_message_severity(self) -> None:
        v = DftViolation(
            axiom=A1_PURE_IO_SEPARATION,
            file="logic.py",
            message="imports urllib",
            severity="error",
        )
        assert v.axiom == A1_PURE_IO_SEPARATION
        assert v.file == "logic.py"
        assert v.message == "imports urllib"
        assert v.severity == "error"

    def test_violation_is_frozen(self) -> None:
        v = DftViolation(axiom=A1_PURE_IO_SEPARATION, file="x.py", message="m", severity="error")
        try:
            v.axiom = "other"  # type: ignore[misc]
            raise AssertionError("Should have raised FrozenInstanceError")
        except AttributeError:
            pass  # frozen dataclass
