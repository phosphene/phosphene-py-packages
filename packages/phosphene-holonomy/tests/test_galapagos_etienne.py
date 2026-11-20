"""Unit and integration tests for canonical Galápagos Etienne master equation solver in phosphene-holonomy."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np
import pytest

from phosphene.holonomy.macroevo import (
    MasterEquationParams,
    compute_etienne_branching_loglik,
    profile_etienne_k,
    load_galapagos_csv,
    load_galapagos_json,
    ColonistStatus,
    DomainComparisonReport,
    generate_canonical_comparison,
)


@pytest.fixture
def galapagos_csv_path() -> Path:
    return Path(__file__).parent / "data" / "Galapagos_datatable.csv"


@pytest.fixture
def galapagos_json_path() -> Path:
    return Path(__file__).parent / "data" / "Galapagos_avifauna.json"


def test_galapagos_raw_schema_ingestion(galapagos_csv_path: Path, galapagos_json_path: Path):
    """Verify that both CSV and JSON representations parse accurately and match."""
    csv_ds = load_galapagos_csv(galapagos_csv_path)
    json_ds = load_galapagos_json(galapagos_json_path)

    assert csv_ds.total_colonizations == 8
    assert json_ds.total_colonizations == 8
    assert csv_ds.island_age_myr == 4.0
    assert csv_ds.mainland_pool_size == 1000

    finches_csv = csv_ds.finches
    finches_json = json_ds.finches
    assert finches_csv.clade_name == "Finches"
    assert finches_csv.status == ColonistStatus.ENDEMIC
    assert len(finches_csv.branching_times) == 15
    assert len(finches_json.branching_times) == 15
    assert finches_csv.species_count == 15
    assert finches_csv.colonization_time == pytest.approx(3.0282)

    coccyzus = csv_ds.get_clade("Coccyzus")
    assert coccyzus.status == ColonistStatus.NON_ENDEMIC_MAX_AGE
    assert coccyzus.species_count == 1


def test_etienne_physical_carrying_capacity_invariants():
    """Verify physical invariant: clade size S cannot exceed carrying capacity ceiling K."""
    brts = [3.0, 2.0, 1.0, 0.5]  # 4 branching events -> 4 species
    params_invalid = MasterEquationParams(
        lambda0=1.0,
        mu0=0.1,
        K=3.0,  # S=4 > K=3 -> physically forbidden
    )
    ll = compute_etienne_branching_loglik(params_invalid, brts)
    assert ll == -np.inf


def test_etienne_numerical_stability():
    """Verify that numerical master equation handles very close branching times without exploding."""
    brts = [2.0, 1.5, 1.0, 1.00001, 0.5]
    params = MasterEquationParams(
        lambda0=1.5,
        mu0=0.2,
        K=20.0,
    )
    ll = compute_etienne_branching_loglik(params, brts)
    assert not np.isnan(ll)
    assert not np.isinf(ll)
    assert ll < 0.0


def test_darwin_finches_profile_likelihood(galapagos_csv_path: Path):
    """Verify profile log-likelihood evaluates smoothly across K for Darwin's finches."""
    ds = load_galapagos_csv(galapagos_csv_path)
    finches = ds.finches
    k_grid = [16.0, 20.0, 25.0, 30.0, 40.0]

    ks, lls = profile_etienne_k(
        finches.branching_times,
        k_grid=k_grid,
        fixed_lambda0=1.2,
        fixed_mu0=0.1,
    )

    assert len(ks) == len(k_grid)
    assert np.all(np.isfinite(lls))
    assert lls[0] < lls[-1]


def test_comparative_metrics_report():
    """Verify that cross-domain comparison report evaluates properly."""
    report = generate_canonical_comparison()
    assert isinstance(report, DomainComparisonReport)
    assert report.insular_carrying_capacity_k_identified is True
    assert report.hominin_carrying_capacity_identified is False
    d = report.to_dict()
    assert "category_error_verdict" in d
