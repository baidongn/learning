"""资源调度 Agent：查询约束并生成建议，不执行真实调度。"""

import math
from uuid import NAMESPACE_URL, uuid5

from pydantic import BaseModel, Field

from highway_agent.tools import MockApiToolClient


class DispatchRequest(BaseModel):
    """调度建议所需的最小输入。"""

    incident_id: str
    section_id: str
    required_types: list[str] = Field(min_length=1)


class ResourceAssignment(BaseModel):
    """单个资源的建议和预计到达时间。"""

    resource_id: str
    name: str
    resource_type: str
    distance_km: float
    eta_minutes: int


class DispatchProposal(BaseModel):
    """可审计、可幂等重放的调度建议。"""

    proposal_id: str
    incident_id: str
    status: str
    assignments: list[ResourceAssignment]
    unmet_requirements: list[str]


class ResourceDispatchAgent:
    """第三个专业 Agent；只有只读 Tool 权限。"""

    def __init__(self, tools: MockApiToolClient) -> None:
        self.tools = tools

    async def ainvoke(self, request: DispatchRequest) -> DispatchProposal:
        """查询资源和路线，无法满足时明确列出缺口。"""

        result = await self.tools.query_nearby_resources(request.section_id)
        available = list((result.data or {}).get("items", [])) if result.success else []
        assignments: list[ResourceAssignment] = []
        unmet: list[str] = []
        for resource_type in request.required_types:
            candidate = next(
                (
                    item
                    for item in available
                    if item["resource_type"] == resource_type and item["available"]
                ),
                None,
            )
            if candidate is None:
                unmet.append(resource_type)
                continue
            route = await self.tools.estimate_route(
                origin=candidate["id"],
                destination=request.section_id,
                distance_km=float(candidate["distance_km"]),
            )
            if not route.success:
                unmet.append(resource_type)
                continue
            assignments.append(
                ResourceAssignment(
                    resource_id=candidate["id"],
                    name=candidate["name"],
                    resource_type=resource_type,
                    distance_km=float(candidate["distance_km"]),
                    eta_minutes=math.ceil(float((route.data or {})["eta_minutes"])),
                )
            )
        assignments.sort(key=lambda item: item.eta_minutes)
        stable_key = f"{request.incident_id}:{','.join(sorted(request.required_types))}"
        return DispatchProposal(
            proposal_id=str(uuid5(NAMESPACE_URL, stable_key)),
            incident_id=request.incident_id,
            status="ready" if not unmet else "partial",
            assignments=assignments,
            unmet_requirements=unmet,
        )

