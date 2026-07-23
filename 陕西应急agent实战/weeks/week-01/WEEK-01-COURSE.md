# 第 1 周：开发底座、领域模型与确定性模拟 API

> 学习方式：本周 5 天，每天约 2～3 小时。不要只阅读代码；请按文件路径逐段创建或修改文件，每完成一步就运行对应命令。
>
> 本周起点：一个空的课程周目录。
>
> 本周终点：得到可独立安装、启动、测试和验收的 FastAPI 后端，并在本地启动 PostgreSQL、pgvector 与 Redis。默认 `MODEL_MODE=mock`，不需要 DeepSeek Key。

## 1. 本周学习地图与最终成果

第 1 周不急着写 Agent。我们先搭好后面 11 周都会依赖的工程底座。

你会亲手完成下面这条调用链：

```text
HTTP 请求
  -> FastAPI 路由
  -> Pydantic 请求/响应模型
  -> 确定性的陕西高速模拟数据
  -> JSON 响应

Alembic
  -> PostgreSQL
  -> incidents 事件表
  -> plan_documents 预案向量表
  -> pgvector Vector(16)
```

本周五天安排如下：

| Day | 用时 | 当天产出 |
|---|---:|---|
| Day 1 | 2～3 小时 | Python 工程、配置入口、环境变量、统一 Make 命令 |
| Day 2 | 2～3 小时 | 事件、路况、气象、资源等领域模型 |
| Day 3 | 2～3 小时 | SQLAlchemy 表、Alembic 迁移、PostgreSQL/pgvector/Redis |
| Day 4 | 2～3 小时 | 路况、气象、资源和健康检查模拟 API |
| Day 5 | 2～3 小时 | 自动测试、评测、验收与本周综合作业 |

完成后你应该能回答：

1. 为什么领域模型和数据库模型要分开？
2. 为什么模拟 API 不能靠随机数制造故障？
3. 为什么 Agent 项目一开始就要设计结构化输入输出？
4. PostgreSQL、pgvector 和 Redis 在最终项目中分别负责什么？
5. 没有模型 Key 时，项目为什么仍然能够完整测试？

本周必做：

- 完成五天全部代码和命令。
- 让 `make test`、`make eval`、`make verify` 通过。
- 完成第 9 章唯一实战作业。

本周选做：

- 使用数据库客户端观察 Alembic 创建的表。
- 为模拟 API 增加一组新的陕西高速路段数据。
- 在 Swagger UI 中手动构造错误场景。

## 2. 前置知识、环境准备和本周起点

本课程以 macOS/Linux 命令为主。Windows 学习者建议使用 WSL2。

先检查工具：

```bash
python3 --version
uv --version
docker --version
docker compose version
make --version
```

预期版本：

```text
Python 3.11 或更高
uv 0.6 或更高
Docker 27 或更高
Docker Compose v2
GNU Make 或 BSD Make
```

如果没有 uv，可以按照 uv 官方安装方式安装。课程统一用 uv 管理 Python 环境，不要同时混用系统 pip、Conda 和 Poetry。

进入本周目录：

```bash
cd weeks/week-01
pwd
```

后面所有命令默认都在 `weeks/week-01` 执行。

本周最终目录是：

```text
week-01/
├── .env.example
├── CHANGELOG.md
├── Makefile
├── README.md
├── WEEK-01-COURSE.md
├── compose.dev.yaml
├── backend/
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   │       └── 0001_initial.py
│   ├── pyproject.toml
│   ├── src/highway_agent/
│   │   ├── __init__.py
│   │   ├── api.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── domain.py
│   │   └── main.py
│   └── tests/
│       ├── test_config.py
│       ├── test_database_models.py
│       ├── test_domain.py
│       ├── test_local_environment.py
│       └── test_mock_api.py
├── data/
├── docs/
├── evals/
└── tests/
```

如果你使用课程成品仓库，这些文件已经存在。学习时仍然要按 Day 顺序打开文件、理解改动并亲自运行；不要一次性只执行最终测试。

## 3. 本周架构、目录变化与完整调用链

本周采用三层分离：

```text
domain.py
  业务语言与数据校验
       |
       +----> api.py
       |       HTTP 路由与模拟外部系统
       |
       +----> database.py
               PostgreSQL 表结构
```

关键职责：

| 文件 | 职责 | 不负责 |
|---|---|---|
| `config.py` | 读取环境变量，提供统一配置 | 业务判断 |
| `domain.py` | 定义事件和工具数据契约 | HTTP、SQL |
| `database.py` | 定义数据库表 | API 响应 |
| `api.py` | 暴露模拟接口和错误场景 | 数据库迁移 |
| `main.py` | 提供 Uvicorn 应用入口 | 业务实现 |
| Alembic | 管理可追踪的数据库结构变化 | 运行 Web 服务 |

为什么现在就保留 pgvector？

第 2 周要做 RAG。预案文档需要向量字段。第 1 周提前把扩展和表结构准备好，第 2 周就可以集中学习检索逻辑，而不是重新打断去补基础设施。

为什么现在就保留 Redis？

本周暂不写缓存代码。Redis 会在后续用于幂等键、临时状态和可靠性控制。提前用 Compose 固定镜像和健康检查，能让每周的运行环境保持一致。

## 4. Day 1：创建工程骨架、配置入口与统一命令

### 今天目标

1. 创建标准 `src` 布局的 Python 工程。
2. 用 `pyproject.toml` 管理正式依赖和开发依赖。
3. 创建唯一配置入口 `Settings`。
4. 理解 `MODEL_MODE=mock|live`。
5. 用 Makefile 固定每周启动、测试、评测和验收命令。
6. 跑通第一条配置测试。

### 上一节衔接

这是整个 12 周项目的第一天，没有上一周代码可以继承。

今天先解决“项目怎样稳定启动”的问题。配置、命令和目录如果一开始混乱，后面 Agent、Tool、RAG 和部署都会反复返工。

### 先说结论

今天的核心不是 FastAPI，而是建立三个稳定入口：

```text
依赖入口：backend/pyproject.toml
配置入口：highway_agent/config.py
命令入口：Makefile
```

以后新增模型、数据库或工作流配置，都进入 `Settings`；以后启动和测试，都优先使用 `make` 命令。

### 第 1 步：创建 Python 项目配置

新建 `backend/pyproject.toml`：

```toml
[project]
name = "shaanxi-highway-agent-week01"
version = "0.1.0"
description = "Week 1 domain models and deterministic mock APIs"
requires-python = ">=3.11"
dependencies = [
  "fastapi>=0.115,<1",
  "uvicorn>=0.34,<1",
  "pydantic-settings>=2.7,<3",
  "sqlalchemy>=2.0,<3",
  "asyncpg>=0.30,<1",
  "alembic>=1.14,<2",
  "pgvector>=0.3,<1",
]

[dependency-groups]
dev = [
  "httpx>=0.28,<1",
  "pytest>=8.3,<9",
  "pytest-asyncio>=0.25,<2",
  "pytest-cov>=6,<8",
  "pyyaml>=6,<7",
]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
addopts = "-q"
filterwarnings = [
  "ignore:Using .*starlette.testclient.*",
]

[tool.coverage.run]
source = ["highway_agent"]
```

这里把依赖分成两组：

- `dependencies`：运行服务必须安装。
- `dependency-groups.dev`：测试和开发时使用，生产镜像可以不带。

`pythonpath = ["src"]` 让 pytest 能导入 `highway_agent` 包。

### 第 2 步：创建包入口

新建空文件：

```text
backend/src/highway_agent/__init__.py
```

再新建 `backend/src/highway_agent/main.py`：

```python
from highway_agent.api import app

__all__ = ["app"]
```

今天 `api.py` 还没创建，暂时不要启动 Uvicorn。这个入口会在 Day 4 完成。

### 第 3 步：创建环境变量模板

新建 `.env.example`：

```dotenv
MODEL_MODE=mock
DATABASE_URL=postgresql+asyncpg://highway:highway@localhost:5432/highway_agent
REDIS_URL=redis://localhost:6379/0
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_API_KEY=
DEEPSEEK_MODEL=deepseek-v4-flash
```

复制成自己的本地配置：

```bash
cp .env.example .env
```

注意：

- `.env.example` 可以提交，里面不能放真实 Key。
- `.env` 是本机配置，不应提交。
- 第 1～12 周默认都使用 `MODEL_MODE=mock`。
- 只有主动练习真实模型时，才设置 `MODEL_MODE=live` 和 `DEEPSEEK_API_KEY`。

### 第 4 步：实现统一 Settings

新建 `backend/src/highway_agent/config.py`：

```python
"""应用配置：所有外部依赖都通过环境变量注入。"""

from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """课程项目的统一配置入口。

    Mock 是默认模式，确保没有模型 Key 时仍可运行全部基础测试。
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "陕西高速路网应急指挥 Agent"
    model_mode: Literal["mock", "live"] = "mock"
    database_url: str = "postgresql+asyncpg://highway:highway@localhost:5432/highway_agent"
    redis_url: str = "redis://localhost:6379/0"
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_api_key: str = ""
    deepseek_model: str = "deepseek-v4-flash"
```

重点理解：

1. `Literal["mock", "live"]` 会拒绝拼错的模式。
2. `env_file=".env"` 允许从本地文件读配置。
3. `extra="ignore"` 允许根目录存在后续周才使用的环境变量。
4. 默认值让配置测试不依赖外部服务。

### 第 5 步：创建统一 Makefile

新建 `Makefile`，命令行前必须是 Tab：

```make
UV ?= uv
COMPOSE ?= docker compose

.PHONY: setup infra-up infra-down migrate run test eval verify reset

setup:
	$(UV) sync --project backend

infra-up:
	$(COMPOSE) -f compose.dev.yaml up -d

infra-down:
	$(COMPOSE) -f compose.dev.yaml down

migrate:
	cd backend && $(UV) run alembic upgrade head

run:
	$(UV) run --project backend uvicorn highway_agent.main:app --app-dir backend/src --reload

test:
	$(UV) run --project backend pytest backend/tests -q

eval:
	$(UV) run --project backend pytest backend/tests -q -k "domain or mock"

verify: test
	$(COMPOSE) -f compose.dev.yaml config --quiet

reset:
	$(COMPOSE) -f compose.dev.yaml down -v
```

安装依赖：

```bash
make setup
```

### 第 6 步：为配置写第一条测试

新建 `backend/tests/test_config.py`：

```python
from highway_agent.config import Settings


def test_live_provider_defaults_to_current_deepseek_model() -> None:
    settings = Settings()

    assert settings.deepseek_base_url == "https://api.deepseek.com"
    assert settings.deepseek_model == "deepseek-v4-flash"
```

运行单测：

```bash
uv run --project backend pytest backend/tests/test_config.py -q
```

### 运行与预期输出

预期看到：

```text
.                                                                        [100%]
1 passed
```

再直接观察配置：

```bash
uv run --project backend python -c "from highway_agent.config import Settings; print(Settings().model_dump())"
```

结果中应包含：

```text
'model_mode': 'mock'
'deepseek_base_url': 'https://api.deepseek.com'
'deepseek_api_key': ''
```

### 对应测试

今天必须通过：

```bash
uv run --project backend pytest backend/tests/test_config.py -q
```

它验证的是配置默认值，不会调用 DeepSeek，也不会连接数据库。

### 常见错误

错误 1：`No module named highway_agent`

检查 `pyproject.toml` 是否有：

```toml
[tool.pytest.ini_options]
pythonpath = ["src"]
```

错误 2：`Makefile: missing separator`

Makefile 命令前用了空格。删除空格，输入一个真正的 Tab。

错误 3：配置读取不到 `.env`

确保命令在 `weeks/week-01` 执行，因为 `env_file=".env"` 按当前工作目录读取。

错误 4：没有 DeepSeek Key

本周不需要。确认：

```dotenv
MODEL_MODE=mock
DEEPSEEK_API_KEY=
```

### 当天小练习

临时运行：

```bash
MODEL_MODE=live uv run --project backend python -c "from highway_agent.config import Settings; print(Settings().model_mode)"
```

确认输出 `live`。然后不要修改 `.env`，继续保持 mock 模式。

### 今日总结与明日预告

今天建立了依赖、配置和命令三个入口。

明天开始定义领域模型。你会看到 Pydantic 不只是“接口参数校验”，它还会成为 Agent、Tool 和工作流之间稳定的数据契约。

## 5. Day 2：定义事件、路况、气象和资源领域模型

### 今天目标

1. 用 `StrEnum` 表达有限业务状态。
2. 用 Pydantic 定义事件结构。
3. 自动规范化高速编号。
4. 拒绝空描述和非法数值。
5. 为模拟 Tool 的返回值定义结构化契约。
6. 用测试验证模型行为。

### 上一节衔接

Day 1 已经创建 `Settings` 和 pytest 环境。

今天不写数据库，不写 HTTP 路由。我们先确定业务系统内部“说什么语言”，再让 API 和数据库分别适配这些语言。

### 先说结论

领域模型解决的是：

```text
用户自然语言
  -> 稳定、可校验的事件字段
  -> Agent/Tool/数据库共同理解
```

如果全部使用无约束 `dict`，后续很容易出现 `road`、`road_code`、`route_code` 三种字段名，工作流会变得脆弱。

### 第 1 步：创建事件枚举

新建 `backend/src/highway_agent/domain.py`，先写枚举：

```python
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
```

使用 `StrEnum` 的好处：

- JSON 序列化时是普通字符串。
- Python 内仍然有明确枚举成员。
- Agent 的结构化输出只能选择允许的值。

### 第 2 步：创建 Incident

继续在同一文件添加：

```python
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
```

两个关键点：

1. `str_strip_whitespace=True` 先把 `"   "` 变成空字符串，再由 `min_length=1` 拒绝。
2. `road_code.upper()` 统一了数据键，后续工具不需要同时维护 `g65` 和 `G65`。

### 第 3 步：创建模拟外部数据模型

继续添加：

```python
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
```

这些结构会成为 Day 4 API 的 `response_model`，后面也会成为 Tool 的返回结构。

### 第 4 步：测试默认状态与规范化

新建 `backend/tests/test_domain.py`：

```python
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
```

运行：

```bash
uv run --project backend pytest backend/tests/test_domain.py::test_incident_normalizes_road_code_and_starts_reported -q
```

### 第 5 步：测试非法空描述

继续在测试文件添加：

```python
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
```

运行完整领域测试：

```bash
uv run --project backend pytest backend/tests/test_domain.py -q
```

### 第 6 步：手动观察结构化结果

执行：

```bash
uv run --project backend python -c "from datetime import UTC, datetime; from highway_agent.domain import Incident; print(Incident(id='INC-DEMO', incident_type='collision', severity='high', road_code='g65', section_id='QINLING-01', description='两车追尾', reported_at=datetime.now(UTC)).model_dump(mode='json'))"
```

注意输入中是 `g65`，输出会变成 `G65`。

### 运行与预期输出

领域测试预期：

```text
..                                                                       [100%]
2 passed
```

手动运行预期包含：

```text
'road_code': 'G65'
'status': 'reported'
'incident_type': 'collision'
```

### 对应测试

今天的测试范围：

```bash
uv run --project backend pytest backend/tests/test_domain.py -q
```

测试关注“可观察行为”，不要断言 Pydantic 内部实现。

### 常见错误

错误 1：Python 版本过低，无法导入 `StrEnum`

课程要求 Python 3.11 或更高。

错误 2：空格描述没有被拒绝

确认 `Incident` 中存在：

```python
model_config = ConfigDict(str_strip_whitespace=True)
```

错误 3：时间没有时区

应使用：

```python
datetime.now(UTC)
```

不要在应急事件中使用没有时区信息的 `datetime.now()`。

错误 4：把数据库字段写进领域模型

`created_at`、`updated_at` 属于持久化审计字段，明天放在 ORM 模型中。

### 当天小练习

创建一个 `snow_ice`、`critical` 的秦岭事件，并打印 JSON。

要求：

- `road_code` 输入 `g5`，输出必须是 `G5`。
- `status` 不传，输出必须是 `reported`。
- `reported_at` 必须带 UTC 时区。

### 今日总结与明日预告

今天完成了项目的业务词汇表。领域模型不依赖 FastAPI、SQLAlchemy 或 DeepSeek，因此以后可以在 API、Agent、Tool 和测试中复用。

明天把领域概念映射到 PostgreSQL 表，并启用 pgvector。

## 6. Day 3：创建 SQLAlchemy 表、Alembic 迁移与本地基础设施

### 今天目标

1. 区分领域模型与 ORM 模型。
2. 用 SQLAlchemy 2 声明事件表。
3. 创建带 `Vector(16)` 的预案文档表。
4. 用 Alembic 创建可追踪迁移。
5. 用 Docker Compose 启动 PostgreSQL/pgvector 和 Redis。
6. 执行迁移并检查表结构。

### 上一节衔接

Day 2 已经定义系统内部的数据契约。

今天解决持久化：哪些字段进表、哪些字段建索引、向量列怎样创建、数据库结构怎样随课程演进。

### 先说结论

领域模型和 ORM 模型分开，是因为它们变化原因不同：

```text
Incident
  为业务输入输出服务
  可以做字段规范化

IncidentRecord
  为 PostgreSQL 存储和查询服务
  包含索引、主键、审计时间
```

不要让数据库列直接成为 Agent 的输出 Schema。

### 第 1 步：创建 SQLAlchemy 基类和事件表

新建 `backend/src/highway_agent/database.py`：

```python
"""SQLAlchemy 持久化模型。

领域模型描述业务含义；本模块描述 PostgreSQL 表结构，两者刻意分离。
"""

from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """所有 ORM 表的声明式基类。"""

    pass


class IncidentRecord(Base):
    """事件主表；索引字段服务后续队列和统计查询。"""

    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    incident_type: Mapped[str] = mapped_column(String(40), index=True)
    severity: Mapped[str] = mapped_column(String(20), index=True)
    status: Mapped[str] = mapped_column(String(40), index=True)
    road_code: Mapped[str] = mapped_column(String(20), index=True)
    section_id: Mapped[str] = mapped_column(String(80), index=True)
    description: Mapped[str] = mapped_column(Text)
    reported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
```

需要索引的字段是后续常用过滤条件：事件类型、等级、状态、道路和路段。

### 第 2 步：创建预案向量表

继续添加：

```python
class PlanDocumentRecord(Base):
    """预案切片与教学向量表，Week 2 将用于 RAG。"""

    __tablename__ = "plan_documents"

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    section: Mapped[str] = mapped_column(String(120), index=True)
    content: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(500))
    embedding: Mapped[list[float]] = mapped_column(Vector(16))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
```

本课程的确定性教学向量是 16 维，因此数据库列固定为 `Vector(16)`。正式生产系统应根据真实 Embedding 模型维度设置。

### 第 3 步：创建首次迁移

Alembic 初始化文件已经按标准结构放在 `backend/alembic`。本节重点完成版本文件 `backend/alembic/versions/0001_initial.py`：

```python
"""创建事件表和预案文档表。"""

from alembic import op
from pgvector.sqlalchemy import Vector
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # pgvector 必须先启用，后续才能创建 Vector 列。
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "incidents",
        sa.Column("id", sa.String(length=40), primary_key=True),
        sa.Column("incident_type", sa.String(length=40), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("road_code", sa.String(length=20), nullable=False),
        sa.Column("section_id", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("reported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_table(
        "plan_documents",
        sa.Column("id", sa.String(length=40), primary_key=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("section", sa.String(length=120), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=500), nullable=False),
        sa.Column("embedding", Vector(16), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("plan_documents")
    op.drop_table("incidents")
```

`upgrade()` 向前创建结构，`downgrade()` 按依赖逆序删除表。

### 第 4 步：创建本地 Compose

新建 `compose.dev.yaml`：

```yaml
services:
  postgres:
    image: pgvector/pgvector:0.8.1-pg17
    environment:
      POSTGRES_DB: highway_agent
      POSTGRES_USER: highway
      POSTGRES_PASSWORD: highway
    ports:
      - "5432:5432"
    volumes:
      - highway_pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U highway -d highway_agent"]
      interval: 5s
      timeout: 3s
      retries: 10

  redis:
    image: redis:7.4.2-alpine
    ports:
      - "6379:6379"
    command: ["redis-server", "--appendonly", "yes"]
    volumes:
      - highway_redisdata:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 10

volumes:
  highway_pgdata:
  highway_redisdata:
```

镜像必须锁定版本，不能使用 `latest`。

### 第 5 步：启动基础设施并迁移

启动：

```bash
make infra-up
docker compose -f compose.dev.yaml ps
```

两个容器变为 healthy 后执行：

```bash
make migrate
```

检查迁移版本和表：

```bash
docker compose -f compose.dev.yaml exec postgres psql -U highway -d highway_agent -c "SELECT extname FROM pg_extension WHERE extname = 'vector';"
docker compose -f compose.dev.yaml exec postgres psql -U highway -d highway_agent -c "\dt"
```

### 第 6 步：测试 ORM 与环境配置

新建 `backend/tests/test_database_models.py`：

```python
from sqlalchemy import inspect

from pgvector.sqlalchemy import Vector

from highway_agent.database import Base, IncidentRecord, PlanDocumentRecord


def test_incident_table_contains_audit_fields() -> None:
    columns = {column.name for column in inspect(IncidentRecord).columns}

    assert {"id", "incident_type", "severity", "status", "created_at", "updated_at"} <= columns
    assert Base.metadata.tables["incidents"] is IncidentRecord.__table__


def test_plan_document_uses_pgvector_embedding() -> None:
    embedding_type = PlanDocumentRecord.__table__.c.embedding.type

    assert isinstance(embedding_type, Vector)
    assert embedding_type.dim == 16
```

运行：

```bash
uv run --project backend pytest backend/tests/test_database_models.py -q
```

### 运行与预期输出

测试预期：

```text
..                                                                       [100%]
2 passed
```

`\dt` 预期包含：

```text
public | alembic_version | table
public | incidents       | table
public | plan_documents  | table
```

扩展查询预期返回：

```text
vector
```

### 对应测试

今天必须运行：

```bash
uv run --project backend pytest backend/tests/test_database_models.py backend/tests/test_local_environment.py -q
```

其中环境测试会静态检查镜像版本、健康检查和迁移中的 pgvector 扩展语句。

### 常见错误

错误 1：5432 端口被占用

查看占用程序，或先停止本机已有 PostgreSQL。课程默认数据库地址使用 5432。

错误 2：迁移提示 Vector 类型不存在

检查迁移中 `CREATE EXTENSION IF NOT EXISTS vector` 是否在建表之前。

错误 3：容器一直 unhealthy

执行：

```bash
docker compose -f compose.dev.yaml logs postgres
docker compose -f compose.dev.yaml logs redis
```

错误 4：重复迁移没有效果

Alembic 迁移具备幂等版本记录。用下面命令查看当前版本：

```bash
cd backend
uv run alembic current
cd ..
```

错误 5：希望完全重建数据

只有确认不需要本地数据时才执行：

```bash
make reset
make infra-up
make migrate
```

`make reset` 会删除本周 Compose 数据卷。

### 当天小练习

使用 SQL 查询 `plan_documents.embedding` 的类型：

```bash
docker compose -f compose.dev.yaml exec postgres psql -U highway -d highway_agent -c "SELECT column_name, udt_name FROM information_schema.columns WHERE table_name = 'plan_documents';"
```

找到 `embedding`，确认数据库已识别向量列。

### 今日总结与明日预告

今天完成了 PostgreSQL、pgvector、Redis 和迁移底座。

明天开始写确定性的模拟外部 API。后面 Agent 调用的路况、天气和资源 Tool，会先通过这些接口练习，不依赖真实高速数据权限。

## 7. Day 4：实现确定性的路况、气象和资源模拟 API

### 今天目标

1. 创建 FastAPI 应用工厂。
2. 实现健康检查。
3. 实现路况、天气、救援资源三类模拟接口。
4. 用响应模型保证结构合法。
5. 用 Header 精确触发 stale 和 unavailable。
6. 测试正常、404、过期和服务不可用场景。

### 上一节衔接

Day 3 已经完成领域结构和基础设施。

今天把 `RoadStatus`、`WeatherWarning`、`ResourceList` 暴露为 HTTP API，为第 3 周 Tool 调用准备稳定的外部系统。

### 先说结论

模拟 API 必须满足：

```text
同样输入 + 同样故障 Header = 同样业务结果
```

不要使用 `random.random()` 随机返回 503。随机故障会让测试偶尔失败，无法判断是代码问题还是运气问题。

### 第 1 步：准备固定路况和资源数据

新建 `backend/src/highway_agent/api.py`，先写导入和 fixtures：

```python
"""确定性的模拟外部系统 API。

模拟数据不使用随机失败；测试通过 Header 精确选择故障场景，避免 flaky test。
"""

from datetime import UTC, datetime, timedelta

from fastapi import FastAPI, Header, HTTPException

from highway_agent.config import Settings
from highway_agent.domain import EmergencyResource, ResourceList, RoadStatus, WeatherWarning


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
```

固定 fixture 能让工具选择和评测有稳定答案。

### 第 2 步：实现显式故障入口

继续添加：

```python
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
```

之后各接口都读取 `X-Mock-Scenario` Header。

### 第 3 步：创建应用工厂与健康检查

继续添加：

```python
def create_app(settings: Settings | None = None) -> FastAPI:
    """创建可注入配置的 FastAPI 应用，方便测试 Mock/Live 两种模式。"""

    app_settings = settings or Settings()
    app = FastAPI(title=app_settings.app_name, version="0.1.0")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "model_mode": app_settings.model_mode}
```

先不要结束 `create_app`，下面三个路由都保持在函数内部。

应用工厂允许测试传入不同 Settings，避免依赖全局配置。

### 第 4 步：实现路况接口

在 `create_app` 内继续添加：

```python
    @app.get(
        "/mock/roads/{road_code}/sections/{section_id}/status",
        response_model=RoadStatus,
    )
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
```

路况接口支持四种可验证结果：

- 已知路段：200。
- 未知路段：404。
- Header 为 stale：200，但 `data_freshness=stale`。
- Header 为 unavailable：503。

### 第 5 步：实现气象和资源接口

继续在 `create_app` 内添加：

```python
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
        matches = [
            item
            for item in RESOURCE_FIXTURES
            if item.section_id == section_id
        ]
        if resource_type:
            matches = [
                item
                for item in matches
                if item.resource_type == resource_type
            ]
        return ResourceList(items=matches)

    return app


app = create_app()
```

确认 `backend/src/highway_agent/main.py` 为：

```python
from highway_agent.api import app

__all__ = ["app"]
```

### 第 6 步：启动并手动调用

启动服务：

```bash
make run
```

另开终端执行：

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/mock/roads/G65/sections/QINLING-01/status
curl "http://127.0.0.1:8000/mock/weather/warnings?section_id=QINLING-01"
curl "http://127.0.0.1:8000/mock/resources/nearby?section_id=QINLING-01&resource_type=ambulance"
```

模拟过期：

```bash
curl -H "X-Mock-Scenario: stale" http://127.0.0.1:8000/mock/roads/G65/sections/QINLING-01/status
```

模拟不可用：

```bash
curl -i -H "X-Mock-Scenario: unavailable" "http://127.0.0.1:8000/mock/weather/warnings?section_id=QINLING-01"
```

### 运行与预期输出

健康检查：

```json
{
  "status": "ok",
  "model_mode": "mock"
}
```

G65 秦岭路况应包含：

```json
{
  "road_code": "G65",
  "section_id": "QINLING-01",
  "traffic_status": "congested",
  "average_speed_kmh": 22,
  "closed_lanes": 2,
  "source": "synthetic-demo-data",
  "data_freshness": "fresh"
}
```

unavailable 应返回 HTTP 503，并包含：

```json
{
  "detail": {
    "error_code": "MOCK_SERVICE_UNAVAILABLE",
    "message": "模拟服务暂不可用"
  }
}
```

### 对应测试

新建并运行 `backend/tests/test_mock_api.py`。课程成品文件覆盖健康检查、正常路况、stale、404、天气、资源过滤和 503 七个场景。

运行：

```bash
uv run --project backend pytest backend/tests/test_mock_api.py -q
```

预期 7 条测试全部通过。

### 常见错误

错误 1：路由函数不在 `create_app` 内

路由装饰器必须作用于局部的 `app` 实例，最后再 `return app`。

错误 2：Header 没被识别

FastAPI 会把参数 `x_mock_scenario` 映射成 `X-Mock-Scenario`。不要把它写成 Query 参数。

错误 3：响应模型校验失败

检查 `observed_at`、`source` 和非负数值是否都已提供。

错误 4：访问 G999 得到 500

未知路段要显式抛出 `HTTPException(status_code=404)`，不能直接对 `None` 解包。

错误 5：测试偶发失败

搜索并删除模拟代码中的 `random`。故障只能由明确 Header 触发。

### 当天小练习

用 curl 查询：

```text
G5 / HANTAI-01
```

确认它返回 `open`、平均速度 78、封闭车道 0。

然后查询不存在的 `G30/BAOJI-01`，观察标准 404。这个不存在的路段会成为本周综合作业。

### 今日总结与明日预告

今天已经拥有可启动、可故障注入、可测试的模拟业务系统。

明天不再新增主功能，而是把测试、评测、静态配置验收和综合作业完整收口。

## 8. Day 5：完成测试、评测、验收与演示闭环

### 今天目标

1. 理解单元测试、API 测试和环境静态测试的边界。
2. 一次运行本周完整测试。
3. 运行本周轻量评测。
4. 使用 `make verify` 做交付验收。
5. 完成从启动到 API 调用的演示。
6. 学会按层排查失败。

### 上一节衔接

Day 1～4 已经完成配置、领域模型、数据库、迁移和模拟 API。

今天要证明它们不仅“能看懂”，而且“能重复运行并得到相同结果”。

### 先说结论

本课程统一四个命令：

```text
make run     启动并手动体验
make test    运行全部自动测试
make eval    运行本周核心场景评测
make verify  执行交付前总验收
```

后面每周都会保留这四个入口。

### 第 1 步：理解测试分层

本周测试分为：

| 测试文件 | 目标 |
|---|---|
| `test_config.py` | 配置默认值 |
| `test_domain.py` | 领域校验和规范化 |
| `test_database_models.py` | ORM 列与 pgvector 维度 |
| `test_local_environment.py` | Compose 镜像、健康检查和迁移内容 |
| `test_mock_api.py` | HTTP 正常与故障场景 |

前四类不需要启动 Docker；API 测试使用 FastAPI `TestClient`，也不需要真实监听端口。

### 第 2 步：运行完整测试

执行：

```bash
make test
```

如果失败，不要直接改测试。先看失败属于哪一层，再回到对应文件定位。

需要更详细输出时：

```bash
uv run --project backend pytest backend/tests -vv
```

### 第 3 步：运行核心场景评测

执行：

```bash
make eval
```

本周 Makefile 使用：

```make
eval:
	$(UV) run --project backend pytest backend/tests -q -k "domain or mock"
```

它聚焦两个核心能力：

- 事件数据能否稳定结构化。
- 模拟 API 能否稳定返回正常和故障结果。

第 11 周会把它升级为专门的 Agent 数据集评测。

### 第 4 步：运行交付验收

执行：

```bash
make verify
```

本周验收包含：

1. 完整 Python 测试。
2. `docker compose config --quiet` 静态解析。

即使 Docker 守护进程没有启动，静态 Compose 校验仍能发现 YAML 和字段问题。

### 第 5 步：完成一遍完整演示

终端 A：

```bash
make infra-up
make migrate
make run
```

终端 B：

```bash
curl http://127.0.0.1:8000/health
curl http://127.0.0.1:8000/mock/roads/G65/sections/QINLING-01/status
curl -H "X-Mock-Scenario: stale" http://127.0.0.1:8000/mock/roads/G65/sections/QINLING-01/status
curl -i -H "X-Mock-Scenario: unavailable" "http://127.0.0.1:8000/mock/weather/warnings?section_id=QINLING-01"
```

演示顺序要能向面试官说明：

```text
健康 -> 正常业务 -> 过期降级信号 -> 外部服务失败
```

### 第 6 步：记录本周完成状态

检查：

```bash
test -f README.md
test -f WEEK-01-COURSE.md
test -f backend/src/highway_agent/api.py
test -f backend/alembic/versions/0001_initial.py
test -f docs/expected-output.svg
```

然后在根目录 `PROGRESS.md` 勾选 Week 1。

### 运行与预期输出

`make test` 预期：

```text
..............                                                           [100%]
14 passed
```

`make eval` 预期只选择领域和 mock 相关测试，并全部通过。

`make verify` 最后应以退出码 0 结束，Compose 不输出错误。

### 对应测试

最终再运行一次：

```bash
make test
make eval
make verify
```

三个命令必须全部成功。本周不要求真实 DeepSeek、不要求浏览器前端，也不要求向外部 API 发送网络请求。

### 常见错误

错误 1：单个测试通过，完整测试失败

检查测试是否修改环境变量或共享全局数据。本周 fixtures 是只读对象，不应在测试中原地修改。

错误 2：`make verify` 的测试通过，但 Compose 失败

执行：

```bash
docker compose -f compose.dev.yaml config
```

查看具体 YAML 路径和缩进错误。

错误 3：本地 curl 不通，但 pytest 通过

pytest 使用进程内 TestClient。手动 curl 还需要另一个终端运行 `make run`。

错误 4：迁移失败但 pytest 通过

ORM 静态测试不等于真实数据库迁移。启动 Docker 后必须手动运行一次 `make migrate`。

错误 5：想切 live 模式验证 DeepSeek

第 1 周没有 LLM 调用代码。保持 mock；第 2 周再接入 DeepSeek。

### 当天小练习

故意把测试请求路段改为 `G999/UNKNOWN`，先预测 HTTP 状态和 `error_code`，再运行测试验证。

练习后恢复测试文件，重新执行 `make test`，确保全绿。

### 今日总结与明日预告

第 1 周完整闭环已经建立：

```text
配置 -> 领域契约 -> ORM/迁移 -> 模拟 API -> 测试/评测/验收
```

第 2 周会继承这套工程，在不删除任何现有能力的前提下加入预案文档、向量检索和第一个独立 Agent：预案专家 Agent。

## 9. 本周唯一实战作业

任务：为 G30 连霍高速宝鸡路段增加确定性模拟数据。

业务要求：

1. 道路编号：`G30`。
2. 路段编号：`BAOJI-01`。
3. 路况：缓行。
4. 平均速度：35 km/h。
5. 封闭车道：1。
6. 非秦岭路段天气保持 normal。
7. 新增测试，确保小写 `g30` 请求也能匹配。
8. 不得用随机数。
9. 不得破坏 G65 和 G5 现有结果。

实施步骤：

1. 在 `ROAD_FIXTURES` 增加 `("G30", "BAOJI-01")`。
2. 在 `test_mock_api.py` 增加成功测试。
3. 用小写道路编号发请求，验证路由规范化。
4. 执行 `make test`。
5. 执行 `make eval`。
6. 执行 `make verify`。

验收请求：

```bash
curl http://127.0.0.1:8000/mock/roads/g30/sections/BAOJI-01/status
```

验收结果至少包含：

```json
{
  "road_code": "G30",
  "section_id": "BAOJI-01",
  "traffic_status": "slow",
  "average_speed_kmh": 35,
  "closed_lanes": 1
}
```

作业完成标准：

- 新测试先能复现缺失数据导致的失败。
- 添加 fixture 后测试通过。
- 三个统一验收命令全部通过。
- 代码仍然使用 Pydantic 响应结构。
- 没有真实外部网络依赖。

## 10. 测试、常见错误与系统排查

遇到问题时，按下面顺序排查：

```text
命令是否在 week-01 执行？
  -> Python/uv 版本是否正确？
  -> 依赖是否完成 make setup？
  -> 是配置/领域/ORM/API 哪一层失败？
  -> Docker 容器是否 healthy？
  -> Alembic 是否到 head？
  -> 最后才看业务断言
```

快速诊断命令：

```bash
pwd
uv run --project backend python --version
uv run --project backend python -c "import highway_agent; print(highway_agent.__file__)"
docker compose -f compose.dev.yaml ps
cd backend
uv run alembic current
cd ..
make test
```

常见症状映射：

| 症状 | 最可能原因 | 优先检查 |
|---|---|---|
| 无法导入包 | src 布局未配置 | pyproject 的 pythonpath |
| 422 | 请求参数或响应模型不合法 | Pydantic 字段 |
| 404 | fixture 键不匹配 | 大写 road_code 与 section_id |
| 503 | 主动设置 unavailable | X-Mock-Scenario |
| stale | 主动设置 stale | Header 与 data_freshness |
| 连接 PostgreSQL 失败 | 容器未健康或端口冲突 | compose ps/logs |
| Vector 不存在 | 扩展未启用 | Alembic upgrade 顺序 |
| YAML 解析错误 | 缩进或冒号错误 | docker compose config |

安全提醒：

- 不要把真实 DeepSeek Key 写进课程文件。
- 不要在不确认数据价值时运行 `make reset`。
- 模拟 API 只用于课程，不代表真实陕西高速生产接口。
- 本周没有任何真实调度、封路或通知动作。

## 11. 通关清单与三道面试题

通关前逐项确认：

- [ ] 能说明 `Settings` 如何读取环境变量。
- [ ] 能解释 mock/live 模式的用途。
- [ ] 能创建合法 `Incident` 并触发非法数据校验。
- [ ] 能解释领域模型与 ORM 模型的边界。
- [ ] 能说明 `Vector(16)` 的来源和限制。
- [ ] 能启动 PostgreSQL/pgvector 和 Redis。
- [ ] 能执行 Alembic 首次迁移。
- [ ] 能调用三类模拟接口。
- [ ] 能主动触发 404、stale 和 503。
- [ ] 能让 `make test`、`make eval`、`make verify` 全部通过。
- [ ] 能独立完成 G30/BAOJI-01 作业。

### 面试题 1

为什么 Agent 项目里要同时使用 Pydantic 领域模型和 SQLAlchemy ORM 模型？

回答要点：

Pydantic 模型服务业务输入输出、结构化校验和 Agent/Tool 契约；ORM 模型服务数据库表、索引、主键和审计字段。两者变化原因不同，分开后可以避免数据库细节污染模型输出，也便于单独测试和替换持久化实现。

### 面试题 2

为什么模拟 API 使用 Header 选择故障场景，而不是随机返回错误？

回答要点：

自动测试必须可重复。显式 Header 让同一输入得到确定结果，可以准确断言 stale、404 和 503，并能复现 Agent 降级逻辑。随机故障会制造 flaky test，难以定位问题。

### 面试题 3

PostgreSQL、pgvector 和 Redis 在这个项目中分别承担什么职责？

回答要点：

PostgreSQL 保存事件、预案、审批和工作流持久数据；pgvector 是 PostgreSQL 扩展，负责预案向量存储和相似度检索；Redis 只负责缓存、幂等和短期状态，不作为核心业务事实来源。

## 12. 本周总结与下一周衔接

本周没有写 Agent，但已经完成后面所有 Agent 的共同底座：

```text
可配置
+ 可校验
+ 可持久化
+ 可模拟外部系统
+ 可测试
+ 可独立运行
```

请保留 Week 1 完整目录。Week 2 不是重新建一个无关项目，而是复制并继承 Week 1 的成果，然后新增：

- 预案文档模型。
- 确定性 16 维教学 Embedding。
- 余弦相似度检索。
- RAG 引用与证据阈值。
- Mock/Live 两种预案专家 Agent。
- DeepSeek HTTP Client。
- 预案查询 API 与评测。

进入 Week 2 前最后执行：

```bash
make test
make eval
make verify
```

全部通过后，再阅读 `weeks/week-02/WEEK-02-COURSE.md`。
