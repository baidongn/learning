"""确定性的模拟外部系统 API。

模拟数据不使用随机失败；测试通过 Header 精确选择故障场景，避免 flaky test。
"""

from datetime import UTC, datetime, timedelta
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, Header, HTTPException

import httpx
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import BaseModel

from highway_agent.agents.incident_analysis import (
    IncidentAnalysisAgent,
    IncidentAnalysisRequest,
    IncidentAssessment,
)
from highway_agent.agents.resource_dispatch import (
    DispatchProposal,
    DispatchRequest,
    ResourceDispatchAgent,
)
from highway_agent.agents.plan_expert import (
    DeepSeekPlanExpertAgent,
    PlanExpertAgent,
    PlanQuery,
    PlanRecommendation,
)
from highway_agent.config import Settings
from highway_agent.checkpoints import configured_checkpointer
from highway_agent.models import DeepSeekChatClient
from highway_agent.domain import (
    CameraAnalysis,
    EmergencyResource,
    ResourceList,
    RoadStatus,
    RouteEstimate,
    RouteEstimateRequest,
    WeatherWarning,
)
from highway_agent.rag import InMemoryPlanRetriever, load_demo_documents
from highway_agent.tools import MockApiToolClient
from highway_agent.workflows.approval_flow import ApprovalEmergencyWorkflow
from highway_agent.workflows.incident_response import EmergencyWorkflow


class ApprovalDecision(BaseModel):
    """人工审批 API 的输入。"""

    decision: Literal["approve", "edit", "reject"]
    comment: str = ""


ROAD_FIXTURES: dict[tuple[str, str], dict[str, object]] = {
    ("G65", "QINLING-01"): {
        "traffic_status": "congested",
        "average_speed_kmh": 22,
        "closed_lanes": 2,
    },
    ("G5", "HANTAI-01"): {
        "traffic_status": "open",
        "average_speed_kmh": 78,
        "closed_lanes": 0,
    },
}

RESOURCE_FIXTURES = [
    EmergencyResource(
        id="RES-AMB-001",
        name="秦岭应急救援站救护车",
        resource_type="ambulance",
        section_id="QINLING-01",
        distance_km=8.5,
        available=True,
    ),
    EmergencyResource(
        id="RES-TOW-001",
        name="秦岭清障车",
        resource_type="tow_truck",
        section_id="QINLING-01",
        distance_km=5.2,
        available=True,
    ),
]


def _raise_if_unavailable(scenario: str | None) -> None:
    """把显式故障场景转换成稳定、可断言的 HTTP 错误。"""

    if scenario == "unavailable":
        raise HTTPException(
            status_code=503,
            detail={
                "error_code": "MOCK_SERVICE_UNAVAILABLE",
                "message": "模拟服务暂不可用",
            },
        )


def create_app(
    settings: Settings | None = None,
    model_transport: httpx.AsyncBaseTransport | None = None,
) -> FastAPI:
    """创建可注入配置的 FastAPI 应用，方便测试 Mock/Live 两种模式。"""

    app_settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(application: FastAPI):
        """部署时在应用生命周期内保持 PostgreSQL Checkpointer 连接。"""

        async with configured_checkpointer(app_settings) as checkpointer:
            application.state.approval_checkpointer = checkpointer
            yield

    app = FastAPI(title=app_settings.app_name, version="0.1.0", lifespan=lifespan)
    retriever = InMemoryPlanRetriever(load_demo_documents())
    plan_agent = PlanExpertAgent(retriever)
    live_plan_agent = (
        DeepSeekPlanExpertAgent(
            retriever,
            DeepSeekChatClient(app_settings, transport=model_transport),
        )
        if app_settings.model_mode == "live"
        else None
    )
    selected_plan_agent = live_plan_agent or plan_agent

    def get_approval_workflow() -> ApprovalEmergencyWorkflow:
        """开发模式共享内存 Checkpointer；生产模式由生命周期注入 PostgreSQL。"""

        if not hasattr(app.state, "approval_workflow"):
            tools = MockApiToolClient(transport=httpx.ASGITransport(app=app))
            app.state.approval_workflow = ApprovalEmergencyWorkflow(
                tools,
                selected_plan_agent,
                checkpointer=getattr(
                    app.state,
                    "approval_checkpointer",
                    InMemorySaver(),
                ),
            )
        return app.state.approval_workflow

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "model_mode": app_settings.model_mode}

    @app.get("/mock/roads/{road_code}/sections/{section_id}/status", response_model=RoadStatus)
    async def road_status(
        road_code: str,
        section_id: str,
        x_mock_scenario: str | None = Header(default=None),
    ) -> RoadStatus:
        """查询模拟路况，并可返回过期数据供后续 Tool 降级练习。"""

        _raise_if_unavailable(x_mock_scenario)
        normalized_code = road_code.upper()
        fixture = ROAD_FIXTURES.get((normalized_code, section_id))
        if fixture is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "error_code": "ROAD_SECTION_NOT_FOUND",
                    "message": "未找到模拟路段",
                },
            )
        observed_at = datetime.now(UTC)
        freshness = "fresh"
        if x_mock_scenario == "stale":
            observed_at -= timedelta(hours=2)
            freshness = "stale"
        return RoadStatus(
            road_code=normalized_code,
            section_id=section_id,
            source="synthetic-demo-data",
            observed_at=observed_at,
            data_freshness=freshness,
            **fixture,
        )

    @app.get("/mock/weather/warnings", response_model=WeatherWarning)
    async def weather_warning(
        section_id: str,
        x_mock_scenario: str | None = Header(default=None),
    ) -> WeatherWarning:
        """查询模拟气象预警。"""

        _raise_if_unavailable(x_mock_scenario)
        return WeatherWarning(
            section_id=section_id,
            warning_type="snow" if section_id == "QINLING-01" else "none",
            level="orange" if section_id == "QINLING-01" else "normal",
            description="秦岭山区未来两小时有降雪和道路结冰风险",
            source="synthetic-demo-data",
            observed_at=datetime.now(UTC),
        )

    @app.get("/mock/resources/nearby", response_model=ResourceList)
    async def nearby_resources(
        section_id: str,
        resource_type: str | None = None,
        x_mock_scenario: str | None = Header(default=None),
    ) -> ResourceList:
        """按路段和资源类型筛选可用的模拟救援资源。"""

        _raise_if_unavailable(x_mock_scenario)
        matches = [item for item in RESOURCE_FIXTURES if item.section_id == section_id]
        if resource_type:
            matches = [item for item in matches if item.resource_type == resource_type]
        return ResourceList(items=matches)

    @app.get("/mock/cameras/{camera_id}/analysis", response_model=CameraAnalysis)
    async def camera_analysis(
        camera_id: str,
        x_mock_scenario: str | None = Header(default=None),
    ) -> CameraAnalysis:
        """返回模拟视觉分析结果；课程不会读取或保存真实视频。"""

        _raise_if_unavailable(x_mock_scenario)
        return CameraAnalysis(
            camera_id=camera_id,
            smoke_detected=camera_id == "CAM-QINLING-01",
            stopped_vehicle_detected=True,
            vehicle_count=7,
            observed_at=datetime.now(UTC),
        )

    @app.post("/mock/routes/estimate", response_model=RouteEstimate)
    async def estimate_route(request: RouteEstimateRequest) -> RouteEstimate:
        """按 60 km/h 教学速度生成确定性 ETA。"""

        return RouteEstimate(
            origin=request.origin,
            destination=request.destination,
            distance_km=request.distance_km,
            eta_minutes=request.distance_km,
        )

    @app.post("/api/agents/plan-expert/invoke", response_model=PlanRecommendation)
    async def invoke_plan_expert(query: PlanQuery) -> PlanRecommendation:
        """Mock 使用确定性实现，Live 使用 DeepSeek 且引用由检索结果绑定。"""

        if live_plan_agent is not None:
            return await live_plan_agent.ainvoke(query)
        return plan_agent.invoke(query)

    @app.post("/api/agents/incident-analysis/invoke", response_model=IncidentAssessment)
    async def invoke_incident_analysis(request: IncidentAnalysisRequest) -> IncidentAssessment:
        """通过真实 HTTP ASGI 边界调用本应用提供的三个模拟 Tool。"""

        tools = MockApiToolClient(transport=httpx.ASGITransport(app=app))
        return await IncidentAnalysisAgent(tools).ainvoke(request)

    @app.post("/api/agents/resource-dispatch/invoke", response_model=DispatchProposal)
    async def invoke_resource_dispatch(request: DispatchRequest) -> DispatchProposal:
        """生成模拟调度建议；接口不会产生真实副作用。"""

        tools = MockApiToolClient(transport=httpx.ASGITransport(app=app))
        return await ResourceDispatchAgent(tools).ainvoke(request)

    @app.post("/api/workflows/incident-response/run")
    async def run_incident_response(request: IncidentAnalysisRequest) -> dict[str, object]:
        """运行固定双 Agent 图；Week 4 不允许模型自行改变节点顺序。"""

        tools = MockApiToolClient(transport=httpx.ASGITransport(app=app))
        workflow = EmergencyWorkflow(tools=tools, plan_agent=selected_plan_agent)
        return await workflow.ainvoke(request.model_dump(mode="json"))

    @app.post("/api/workflows/incident-response/{thread_id}/start")
    async def start_approval_flow(
        thread_id: str, request: IncidentAnalysisRequest
    ) -> dict[str, object]:
        """启动带人工审批的可恢复线程。"""

        return await get_approval_workflow().start(request.model_dump(mode="json"), thread_id)

    @app.post("/api/workflows/incident-response/{thread_id}/resume")
    async def resume_approval_flow(thread_id: str, decision: ApprovalDecision) -> dict[str, object]:
        """用人工决定恢复指定线程。"""

        return await get_approval_workflow().resume(thread_id, decision.model_dump())

    return app


app = create_app()
