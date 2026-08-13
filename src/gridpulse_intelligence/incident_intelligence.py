"""Operational incident intelligence for GridPulse."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from gridpulse_intelligence.source_freshness import (
    SourceFreshnessSignal,
)

SEVERITY_RANK = {
    "CRITICAL": 4,
    "HIGH": 3,
    "ELEVATED": 2,
    "NORMAL": 1,
}


@dataclass(frozen=True)
class ComponentState:
    """Normalized runtime component state."""

    name: str
    status: str
    detail: str
    latency_ms: float


@dataclass(frozen=True)
class OperationalIncident:
    """One actionable GridPulse operational incident."""

    incident_id: str

    severity: str
    category: str

    title: str
    source: str

    current_state: str

    evidence: str
    recommended_action: str


def _freshness_incident(
    signal: SourceFreshnessSignal,
) -> OperationalIncident | None:
    """Convert one source freshness breach into an incident."""

    if signal.state == "FRESH":
        return None

    age = f"{signal.age_hours:.1f}h old" if signal.age_hours is not None else "age unavailable"

    if signal.state == "STALE":
        return OperationalIncident(
            incident_id=(f"source:{signal.source}:stale"),
            severity="HIGH",
            category="DATA_FRESHNESS",
            title=(f"{signal.display_name} source is stale"),
            source=signal.source,
            current_state=signal.state,
            evidence=(
                f"Latest signal is {age}. "
                f"GridPulse stale threshold is "
                f"{signal.stale_after_hours:.0f}h. "
                f"Basis: {signal.timestamp_basis}."
            ),
            recommended_action=(
                "Verify the source ingestion path and upstream "
                "availability before treating downstream analytics "
                "as current."
            ),
        )

    if signal.state == "DELAYED":
        return OperationalIncident(
            incident_id=(f"source:{signal.source}:delayed"),
            severity="ELEVATED",
            category="DATA_FRESHNESS",
            title=(f"{signal.display_name} source is delayed"),
            source=signal.source,
            current_state=signal.state,
            evidence=(
                f"Latest signal is {age}. "
                f"Freshness target is "
                f"{signal.fresh_within_hours:.0f}h. "
                f"Basis: {signal.timestamp_basis}."
            ),
            recommended_action=(
                "Review the next ingestion cycle and verify that "
                "source latency is not continuing to increase."
            ),
        )

    return OperationalIncident(
        incident_id=(f"source:{signal.source}:unknown"),
        severity="ELEVATED",
        category="DATA_FRESHNESS",
        title=(f"{signal.display_name} freshness is unknown"),
        source=signal.source,
        current_state="UNKNOWN",
        evidence=(
            "GridPulse could not establish a usable freshness "
            f"timestamp. Basis: {signal.timestamp_basis}."
        ),
        recommended_action=(
            "Verify that the analytical mart exists and exposes "
            "a supported source, event, or ingestion timestamp."
        ),
    )


def _component_incident(
    component: ComponentState,
) -> OperationalIncident | None:
    """Convert one runtime health problem into an incident."""

    normalized_status = component.status.strip().lower()

    if normalized_status == "healthy":
        return None

    display_name = component.name.replace(
        "_",
        " ",
    ).title()

    if normalized_status == "unhealthy":
        severity = "CRITICAL"

        recommended_action = (
            "Investigate the failed runtime dependency immediately "
            "and verify downstream pipeline availability."
        )

    elif normalized_status == "degraded":
        severity = "HIGH"

        recommended_action = (
            "Investigate degraded dependency performance before "
            "the condition becomes a complete service interruption."
        )

    else:
        severity = "ELEVATED"

        recommended_action = (
            "Verify runtime health reporting and confirm the component's actual operational state."
        )

    return OperationalIncident(
        incident_id=(f"component:{component.name}:{normalized_status}"),
        severity=severity,
        category="PLATFORM_RUNTIME",
        title=(f"{display_name} is {normalized_status}"),
        source=component.name,
        current_state=normalized_status.upper(),
        evidence=(f"{component.detail} Observed latency: {component.latency_ms:.1f} ms."),
        recommended_action=recommended_action,
    )


def build_operational_incidents(
    freshness: Iterable[SourceFreshnessSignal],
    components: Iterable[ComponentState],
) -> list[OperationalIncident]:
    """Build and prioritize current GridPulse incidents."""

    incidents: list[OperationalIncident] = []

    for signal in freshness:
        incident = _freshness_incident(signal)

        if incident is not None:
            incidents.append(incident)

    for component in components:
        incident = _component_incident(component)

        if incident is not None:
            incidents.append(incident)

    return sorted(
        incidents,
        key=lambda incident: (
            -SEVERITY_RANK.get(
                incident.severity,
                0,
            ),
            incident.incident_id,
        ),
    )


def highest_operational_severity(
    incidents: Iterable[OperationalIncident],
) -> str:
    """Return the highest active incident severity."""

    severities = [incident.severity for incident in incidents]

    if not severities:
        return "NORMAL"

    return max(
        severities,
        key=lambda severity: SEVERITY_RANK.get(
            severity,
            0,
        ),
    )
