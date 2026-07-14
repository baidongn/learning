"""事件研判 Agent：负责抽取事实、补充上下文和提出风险建议。"""

from datetime import datetime

from pydantic import BaseModel, Field

from highway_agent.tools import MockApiToolClient, ToolResult


class IncidentAnalysisRequest(BaseModel):
    """人工上报和已知定位信息。"""

    raw_text: str = Field(min_length=2, max_length=2000)
    road_code: str
    section_id: str
    camera_id: str | None = None


class ToolTrace(BaseModel):
    """可展示、可评测的工具调用摘要。"""

    tool_name: str
    success: bool
    trace_id: str
    error_code: str | None = None
    source: str = ""
    observed_at: datetime


class IncidentAssessment(BaseModel):
    """事件研判 Agent 的稳定输出。"""

    incident_type: str
    risk_level: str
    known_facts: list[str]
    missing_fields: list[str]
    tool_trace: list[ToolTrace]


def _trace(tool_name: str, result: ToolResult) -> ToolTrace:
    """从完整 ToolResult 中提取适合状态和前端展示的轨迹。"""

    return ToolTrace(
        tool_name=tool_name,
        success=result.success,
        trace_id=result.trace_id,
        error_code=result.error_code,
        source=result.source,
        observed_at=result.observed_at,
    )


class IncidentAnalysisAgent:
    """最多调用三个只读工具，不执行任何真实业务动作。"""

    def __init__(self, tools: MockApiToolClient) -> None:
        self.tools = tools

    async def ainvoke(self, request: IncidentAnalysisRequest) -> IncidentAssessment:
        """按固定顺序补充路况、气象和可选摄像头上下文。"""

        road = await self.tools.query_road_status(request.road_code, request.section_id)
        weather = await self.tools.query_weather_warning(request.section_id)
        results: list[tuple[str, ToolResult]] = [
            ("query_road_status", road),
            ("query_weather_warning", weather),
        ]
        camera: ToolResult | None = None
        if request.camera_id:
            camera = await self.tools.query_camera_analysis(request.camera_id)
            results.append(("query_camera_analysis", camera))

        text = request.raw_text
        smoke_detected = "烟" in text or bool(camera and camera.data and camera.data.get("smoke_detected"))
        if smoke_detected:
            incident_type = "tunnel_smoke"
        elif "滑坡" in text or "落石" in text:
            incident_type = "landslide"
        elif "积水" in text:
            incident_type = "flooding"
        elif "雪" in text or "结冰" in text:
            incident_type = "snow_ice"
        else:
            incident_type = "collision"

        closed_lanes = int((road.data or {}).get("closed_lanes", 0))
        severe_weather = (weather.data or {}).get("level") in {"orange", "red"}
        if smoke_detected:
            risk_level = "critical"
        elif closed_lanes >= 2 or severe_weather:
            risk_level = "high"
        else:
            risk_level = "medium"

        missing_fields: list[str] = []
        if not any(keyword in text for keyword in ("伤亡", "受伤", "轻伤", "重伤", "死亡")):
            missing_fields.append("casualties")
        if not any(keyword in text for keyword in ("车道", "占用")):
            missing_fields.append("lane_occupancy")

        known_facts = [text]
        if road.success:
            known_facts.append(f"模拟路况关闭车道数：{closed_lanes}")
        if weather.success:
            known_facts.append(f"模拟气象预警：{(weather.data or {}).get('warning_type', 'none')}")

        return IncidentAssessment(
            incident_type=incident_type,
            risk_level=risk_level,
            known_facts=known_facts,
            missing_fields=missing_fields,
            tool_trace=[_trace(name, result) for name, result in results],
        )
