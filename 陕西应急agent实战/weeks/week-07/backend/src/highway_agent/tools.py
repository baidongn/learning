"""普通 HTTP Tool 适配层。

Agent 只接收 ToolResult，不需要理解 HTTP 状态码、Header 或供应商错误格式。
"""

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import httpx
from pydantic import BaseModel, Field


class ToolResult(BaseModel):
    """所有工具共享的成功/失败契约。"""

    success: bool
    data: dict[str, Any] | None = None
    error_code: str | None = None
    message: str = ""
    source: str = ""
    observed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    trace_id: str


class MockApiToolClient:
    """把课程模拟 REST API 包装成 Agent 可调用的只读工具。"""

    def __init__(
        self,
        base_url: str = "http://mock.local",
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.base_url = base_url
        self.transport = transport

    async def _get(
        self,
        path: str,
        *,
        params: dict[str, str] | None = None,
        scenario: str | None = None,
    ) -> ToolResult:
        """统一处理 HTTP 错误，确保 Agent 的分支逻辑保持简单。"""

        trace_id = str(uuid4())
        headers = {"X-Mock-Scenario": scenario} if scenario else {}
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                transport=self.transport,
                timeout=5.0,
            ) as client:
                response = await client.get(path, params=params, headers=headers)
        except httpx.TimeoutException:
            return ToolResult(
                success=False,
                error_code="TOOL_TIMEOUT",
                message="模拟工具调用超时",
                trace_id=trace_id,
            )
        except httpx.RequestError:
            return ToolResult(
                success=False,
                error_code="TOOL_CONNECTION_ERROR",
                message="模拟工具连接失败",
                trace_id=trace_id,
            )

        if response.is_error:
            detail = response.json().get("detail", {})
            return ToolResult(
                success=False,
                error_code=detail.get("error_code", f"HTTP_{response.status_code}"),
                message=detail.get("message", "工具调用失败"),
                trace_id=trace_id,
            )
        data = response.json()
        return ToolResult(
            success=True,
            data=data,
            source=data.get("source", "synthetic-demo-data"),
            observed_at=data.get("observed_at", datetime.now(UTC)),
            trace_id=trace_id,
        )

    async def query_road_status(
        self, road_code: str, section_id: str, scenario: str | None = None
    ) -> ToolResult:
        """查询指定路段的模拟通行状态。"""

        return await self._get(
            f"/mock/roads/{road_code}/sections/{section_id}/status",
            scenario=scenario,
        )

    async def query_weather_warning(
        self, section_id: str, scenario: str | None = None
    ) -> ToolResult:
        """查询指定路段的模拟气象预警。"""

        return await self._get(
            "/mock/weather/warnings",
            params={"section_id": section_id},
            scenario=scenario,
        )

    async def query_camera_analysis(
        self, camera_id: str, scenario: str | None = None
    ) -> ToolResult:
        """查询已经完成的模拟摄像头结构化分析，不处理真实视频。"""

        return await self._get(f"/mock/cameras/{camera_id}/analysis", scenario=scenario)

    async def query_nearby_resources(
        self, section_id: str, resource_type: str | None = None
    ) -> ToolResult:
        """查询可用救援资源。"""

        params = {"section_id": section_id}
        if resource_type:
            params["resource_type"] = resource_type
        return await self._get("/mock/resources/nearby", params=params)

    async def estimate_route(
        self, origin: str, destination: str, distance_km: float
    ) -> ToolResult:
        """调用模拟路线 API；写成 POST 但仍是无副作用计算。"""

        trace_id = str(uuid4())
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                transport=self.transport,
                timeout=5.0,
            ) as client:
                response = await client.post(
                    "/mock/routes/estimate",
                    json={
                        "origin": origin,
                        "destination": destination,
                        "distance_km": distance_km,
                    },
                )
        except httpx.TimeoutException:
            return ToolResult(
                success=False,
                error_code="TOOL_TIMEOUT",
                message="路线估算超时",
                trace_id=trace_id,
            )
        except httpx.RequestError:
            return ToolResult(
                success=False,
                error_code="TOOL_CONNECTION_ERROR",
                message="路线工具连接失败",
                trace_id=trace_id,
            )
        if response.is_error:
            return ToolResult(
                success=False,
                error_code=f"HTTP_{response.status_code}",
                message="路线估算失败",
                trace_id=trace_id,
            )
        data = response.json()
        return ToolResult(
            success=True,
            data=data,
            source=data["source"],
            observed_at=data.get("observed_at", datetime.now(UTC)),
            trace_id=trace_id,
        )
