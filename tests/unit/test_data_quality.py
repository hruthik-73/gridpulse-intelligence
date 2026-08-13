"""Tests for GridPulse Data Quality Intelligence."""

from gridpulse_intelligence.data_quality import (
    derive_data_quality_metrics,
)


def test_balanced_quality_metrics() -> None:
    """Removed rows should reconcile into failures plus deduplication."""

    metrics = derive_data_quality_metrics(
        bronze_rows=47129,
        silver_rows=47109,
        quality_failure_rows=7,
    )

    assert metrics.removed_before_silver == 20

    assert metrics.quality_failure_rows == 7

    assert metrics.deduplicated_rows == 13

    assert metrics.silver_retention_pct == 99.958

    assert metrics.conservation_state == "BALANCED"


def test_quality_failure_count_cannot_exceed_removed_rows() -> None:
    """Impossible conservation should be surfaced rather than hidden."""

    metrics = derive_data_quality_metrics(
        bronze_rows=100,
        silver_rows=90,
        quality_failure_rows=15,
    )

    assert metrics.removed_before_silver == 10

    assert metrics.deduplicated_rows is None

    assert metrics.conservation_state == "CHECK"


def test_missing_quarantine_is_partial() -> None:
    """Missing quarantine data should not invent deduplication."""

    metrics = derive_data_quality_metrics(
        bronze_rows=100,
        silver_rows=95,
        quality_failure_rows=None,
    )

    assert metrics.removed_before_silver == 5

    assert metrics.deduplicated_rows is None

    assert metrics.conservation_state == "PARTIAL"


def test_missing_materialization_is_unknown() -> None:
    """Missing Bronze or Silver storage should produce unknown metrics."""

    metrics = derive_data_quality_metrics(
        bronze_rows=None,
        silver_rows=95,
        quality_failure_rows=2,
    )

    assert metrics.removed_before_silver is None

    assert metrics.conservation_state == "UNKNOWN"
