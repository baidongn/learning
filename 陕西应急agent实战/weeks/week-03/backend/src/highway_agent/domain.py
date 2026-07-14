"""与 Web 框架、数据库和模型供应商无关的领域契约。"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class IncidentType(StrEnum):
    """课程覆盖的五类典型高速公路事件。"""

    COLLISION = "collision"
    LANDSLIDE = "landslide"
    FLOODING = "flooding"
    SNOW_ICE = "snow_ice"
    TUNNEL_SMOKE = "tunnel_smoke"


class IncidentSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class IncidentStatus(StrEnum):
    REPORTED = "reported"
    ASSESSING = "assessing"
    AWAITING_APPROVAL = "awaiting_approval"
    RESPONDING = "responding"
    RESOLVED = "resolved"


class Incident(BaseModel):
    """事件在系统内流转时使用的稳定结构。"""

    model_config = ConfigDict(str_strip_whitespace=True)

    id: str = Field(min_length=1, max_length=40)
    incident_type: IncidentType
    severity: IncidentSeverity
    status: IncidentStatus = IncidentStatus.REPORTED
    road_code: str = Field(min_length=2, max_length=20)
    section_id: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=2000)
    reported_at: datetime

    @field_validator("road_code")
    @classmethod
    def normalize_road_code(cls, value: str) -> str:
        """入口统一规范化，避免工具查询时出现 g65/G65 两套键。"""

        return value.upper()


class RoadStatus(BaseModel):
    """模拟路况 API 的结构化响应。"""

    road_code: str
    section_id: str
    traffic_status: str
    average_speed_kmh: int = Field(ge=0)
    closed_lanes: int = Field(ge=0)
    source: str
    observed_at: datetime
    data_freshness: str = "fresh"


class WeatherWarning(BaseModel):
    section_id: str
    warning_type: str
    level: str
    description: str
    source: str
    observed_at: datetime


class EmergencyResource(BaseModel):
    id: str
    name: str
    resource_type: str
    section_id: str
    distance_km: float = Field(ge=0)
    available: bool


class ResourceList(BaseModel):
    items: list[EmergencyResource]
    source: str = "synthetic-demo-data"


class CameraAnalysis(BaseModel):
    """真实视觉模型的模拟结构化输出。"""

    camera_id: str
    smoke_detected: bool
    stopped_vehicle_detected: bool
    vehicle_count: int = Field(ge=0)
    source: str = "synthetic-demo-data"
    observed_at: datetime
