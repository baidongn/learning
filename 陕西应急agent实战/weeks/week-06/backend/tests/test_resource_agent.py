import httpx
import pytest

from highway_agent.agents.resource_dispatch import DispatchRequest, ResourceDispatchAgent
from highway_agent.api import create_app
from highway_agent.tools import MockApiToolClient


def build_agent() -> ResourceDispatchAgent:
    app = create_app()
    tools = MockApiToolClient(transport=httpx.ASGITransport(app=app))
    return ResourceDispatchAgent(tools)


@pytest.mark.asyncio
async def test_dispatch_agent_selects_available_resources_with_eta() -> None:
    agent = build_agent()

    proposal = await agent.ainvoke(
        DispatchRequest(
            incident_id="INC-DISPATCH-001",
            section_id="QINLING-01",
            required_types=["ambulance", "tow_truck"],
        )
    )

    assert proposal.status == "ready"
    assert [item.resource_type for item in proposal.assignments] == ["tow_truck", "ambulance"]
    assert all(item.eta_minutes > 0 for item in proposal.assignments)
    assert proposal.unmet_requirements == []


@pytest.mark.asyncio
async def test_dispatch_agent_reports_missing_resource_instead_of_inventing_one() -> None:
    agent = build_agent()

    proposal = await agent.ainvoke(
        DispatchRequest(
            incident_id="INC-DISPATCH-002",
            section_id="QINLING-01",
            required_types=["helicopter"],
        )
    )

    assert proposal.assignments == []
    assert proposal.unmet_requirements == ["helicopter"]
    assert proposal.status == "partial"


@pytest.mark.asyncio
async def test_same_incident_request_is_idempotent() -> None:
    agent = build_agent()
    request = DispatchRequest(
        incident_id="INC-DISPATCH-003",
        section_id="QINLING-01",
        required_types=["ambulance"],
    )

    first = await agent.ainvoke(request)
    second = await agent.ainvoke(request)

    assert first.proposal_id == second.proposal_id
    assert first == second

