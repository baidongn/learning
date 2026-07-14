from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from highway_agent.domain import (
    Incident,
    IncidentSeverity,
    IncidentStatus,
    IncidentType,
)


def test_incident_normalizes_road_code_and_starts_reported() -> None:
    incident = Incident(
        id="INC-001",
        incident_type=IncidentType.COLLISION,
        severity=IncidentSeverity.MEDIUM,
        road_code="g65",
        section_id="QINLING-01",
        description="隧道内两车追尾",
        reported_at=datetime(2026, 7, 13, 8, 0, tzinfo=UTC),
    )

    assert incident.road_code == "G65"
    assert incident.status is IncidentStatus.REPORTED


def test_incident_rejects_empty_description() -> None:
    with pytest.raises(ValidationError):
        Incident(
            id="INC-002",
            incident_type=IncidentType.LANDSLIDE,
            severity=IncidentSeverity.HIGH,
            road_code="G5",
            section_id="HANTAI-01",
            description="   ",
            reported_at=datetime.now(UTC),
        )

