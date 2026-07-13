# Python 关键知识点：Agent 开发版

目标：用最短篇幅覆盖 Python 完整知识地图，并标出 Agent 开发的优先级。`P0` 必须会写，`P1` 会读会改，`P2` 知道何时查。

## 1. 基础语法与数据 `[P0]`

- 变量是对象引用；`None` 表示缺失；`is` 判断同一对象，`==` 判断值相等。
- 基础类型：`bool`、`int`、`float`、`str`、`bytes`。
- 容器：`list` 有序可变，`tuple` 有序不可变，`dict` 键值映射，`set` 去重与集合运算。
- 可变对象不要作为函数默认值；使用 `None` 或 `default_factory`。
- 切片 `items[start:stop:step]` 左闭右开；负索引从尾部开始。
- 解包：`a, b = pair`、`head, *rest = items`、`func(**mapping)`。
- 推导式适合短转换；复杂分支用普通循环提高可读性。

```python
def append_message(message: str, history: list[str] | None = None) -> list[str]:
    # 每次创建新列表，避免默认列表被不同会话共享。
    history = [] if history is None else history
    history.append(message)
    return history
```

控制流：`if/elif/else`、`for`、`while`、`break`、`continue`、`match/case`。遍历常用 `enumerate`、`zip`、`sorted(key=...)`、`any`、`all`。

## 2. 函数、作用域与函数式工具 `[P0]`

- 参数种类：位置参数、关键字参数、默认参数、`*args`、`**kwargs`、仅位置 `/`、仅关键字 `*`。
- 函数是一等对象，可传入 Tool Registry 或回调系统。
- LEGB 作用域：Local → Enclosing → Global → Builtins；少用可变全局状态。
- 闭包保存外层变量；循环创建闭包时注意晚绑定。
- `lambda` 只用于短表达式。
- 纯函数容易测试；I/O、时间和随机数通过参数或依赖注入。

```python
from collections.abc import Callable
from functools import wraps
from time import perf_counter
from typing import ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")

def timed(func: Callable[P, R]) -> Callable[P, R]:
    @wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        started = perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            # 生产环境写结构化日志，不直接打印敏感参数。
            print({"function": func.__name__, "seconds": perf_counter() - started})
    return wrapper
```

装饰器常用于鉴权、重试、缓存和追踪；不要让装饰器偷偷改变返回契约。

## 3. 迭代器、生成器与流式输出 `[P0]`

- Iterable 能产生迭代器；Iterator 实现 `__iter__` 和 `__next__`。
- 生成器用 `yield` 惰性产生数据，适合大文件和流式 Token。
- `yield from` 委托另一个迭代器。
- 异步生成器使用 `async def` + `yield`，通过 `async for` 消费。

```python
from collections.abc import AsyncIterator

async def stream_chunks(text: str, size: int = 6) -> AsyncIterator[str]:
    for index in range(0, len(text), size):
        yield text[index:index + size]
```

生成器被消费一次后会耗尽。流式接口要处理客户端断开、取消、异常事件和最终完成事件。

## 4. 类、数据类与接口设计 `[P0/P1]`

- 实例属性属于对象，类属性由类共享。
- `@property` 暴露计算值；不要在 property 中做网络 I/O。
- 继承表达“是一个”，组合表达“拥有一个”；业务代码优先组合。
- `super()` 协作调用父类；多继承要理解 MRO。
- `dataclass` 适合内部轻量数据，Pydantic 适合外部输入和校验。
- `ABC` 是运行时抽象基类；`Protocol` 是结构化类型接口，更适合模型/检索器网关。
- 常用魔术方法：`__init__`、`__repr__`、`__len__`、`__iter__`、`__enter__`、`__aenter__`、`__call__`。

```python
from typing import Protocol

class Retriever(Protocol):
    def retrieve(self, query: str, top_k: int = 4) -> list[str]: ...

class Agent:
    def __init__(self, retriever: Retriever) -> None:
        # 依赖接口而非具体向量库，测试可替换为内存实现。
        self.retriever = retriever
```

## 5. 类型提示 `[P0/P1]`

- 基础：`list[str]`、`dict[str, object]`、`str | None`、`Literal`、`TypeAlias`。
- `TypedDict` 描述字典形状，适合 LangGraph State。
- `Protocol` 描述行为；`Generic[T]` 保留输入输出类型关系。
- `Callable[[str], Awaitable[str]]` 描述异步函数。
- 类型提示不自动校验运行时输入；外部边界用 Pydantic。
- `Any` 关闭检查；只放在动态 SDK 边界并尽快转换。

```python
from typing import Literal, TypedDict

class AgentState(TypedDict, total=False):
    query: str
    route: Literal["rag", "tool", "direct"]
    citations: list[str]
```

## 6. Pydantic v2 `[P0]`

- `BaseModel` 定义外部数据契约；`Field` 定长度、范围、正则和描述。
- `model_validate` 校验 Python 对象，`model_validate_json` 校验 JSON。
- `model_dump`/`model_dump_json` 序列化。
- `field_validator` 校验单字段，`model_validator` 校验字段组合。
- `ConfigDict(extra="forbid")` 拒绝额外字段；工具参数推荐开启。
- v1 的 `dict/parse_obj/validator/from_orm` 分别迁移到 v2 API；`from_attributes=True` 替代 ORM 模式。

```python
from pydantic import BaseModel, ConfigDict, Field

class RefundInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    order_id: str = Field(pattern=r"^\d{4,}$")
    reason: str = Field(min_length=2, max_length=200)
```

## 7. 异常与资源管理 `[P0]`

- 捕获最具体异常；不要裸 `except`；不要吞掉错误。
- `raise NewError(...) from exc` 保留因果链。
- 业务异常、权限异常、参数异常、暂时性基础设施异常要分开。
- `finally` 一定执行；上下文管理器更适合连接、文件和锁。

```python
class ToolTimeoutError(RuntimeError):
    """工具执行超时。"""

try:
    result = await asyncio.wait_for(call(), timeout=5)
except TimeoutError as exc:
    raise ToolTimeoutError("订单服务暂时不可用") from exc
```

同步上下文实现 `__enter__/__exit__`，异步资源实现 `__aenter__/__aexit__`；也可用 `contextlib.contextmanager/asynccontextmanager`。

## 8. 文件、文本与标准库 `[P0/P1]`

- `pathlib.Path` 处理跨平台路径；显式 `encoding="utf-8"`。
- JSON：`json.loads/dumps`；日期、Decimal、自定义对象需明确编码。
- 正则：原始字符串 `r"..."`；先用普通字符串方法，复杂模式再用 `re`。
- 日期：使用带时区 `datetime`，存 UTC，展示时转换；避免本地无时区时间。
- `csv` 处理 CSV；二进制流处理图片/PDF；大文件分块读取。
- 反序列化不可信 `pickle` 会执行代码，禁止用于外部输入。

```python
from pathlib import Path
import json

data = json.loads(Path("config.json").read_text(encoding="utf-8"))
```

## 9. 模块、包与依赖 `[P0]`

- 一个 `.py` 是模块，带包结构的目录是一组模块；使用绝对导入。
- `if __name__ == "__main__":` 只在脚本直接运行时执行。
- 避免循环导入：下沉共享类型、使用依赖注入、必要时仅类型检查导入。
- `pyproject.toml` 统一项目元数据、依赖和工具配置。
- `uv.lock` 锁定完整依赖图；应用部署应使用锁文件。

```bash
uv python install 3.11
uv sync --dev
uv add fastapi
uv add --dev pytest ruff
uv run pytest
```

## 10. async/await 与并发 `[P0]`

- 协程适合网络、数据库等 I/O；CPU 密集任务不会因 async 自动变快。
- `await` 交还事件循环；同步阻塞调用会卡住所有请求。
- `asyncio.gather` 并发等待相互独立任务；`TaskGroup` 提供结构化并发。
- `Semaphore` 限制并发；`Queue` 解耦生产者/消费者。
- 超时使用 `asyncio.timeout` 或 `wait_for`；取消要清理资源并继续传播 `CancelledError`。
- 线程适合阻塞 I/O 兼容；进程适合 CPU 密集，但有序列化和启动成本。

```python
import asyncio

async def fetch_all(queries: list[str]) -> list[str]:
    semaphore = asyncio.Semaphore(5)

    async def limited(query: str) -> str:
        async with semaphore:
            async with asyncio.timeout(10):
                return await fetch_one(query)

    return await asyncio.gather(*(limited(query) for query in queries))
```

GIL 限制一个进程内 Python 字节码的 CPU 并行，但不妨碍 I/O 并发；扩展库和多进程情况不同。

## 11. HTTP、SSE 与 WebSocket `[P0/P1]`

- HTTP 要理解方法、状态码、Header、JSON、超时、重试、幂等和连接池。
- 重试通常只用于暂时性错误；写操作需幂等键，不能盲重试。
- SSE 是服务端到客户端的单向文本事件流，自动重连简单，适合 Token 输出。
- WebSocket 是双向长连接，适合实时语音、音视频控制和交互事件。
- 流式响应要处理代理缓冲、心跳、断开、取消、审核和最终统计。

```python
async def events():
    yield 'event: token\ndata: {"text":"你"}\n\n'
    yield 'event: done\ndata: {"status":"completed"}\n\n'
```

HTTP 客户端复用连接；限制响应大小；防 SSRF 时使用域名白名单并检查重定向与解析后的 IP。

## 12. SQL、ORM 与迁移 `[P0/P1]`

- SQL 基础：表、主键、外键、唯一约束、事务、索引、`SELECT/INSERT/UPDATE/DELETE/JOIN/GROUP BY`。
- 参数化查询防 SQL 注入；不要拼接模型生成的 SQL。
- 事务保证一组操作原子性；隔离级别影响并发可见性。
- 索引加速读但增加写和空间成本；用查询计划验证。
- SQLAlchemy：Engine/Connection、Session、Model、查询和事务。
- Alembic：Schema 版本迁移；迁移脚本需要评审、回滚或前向修复策略。
- pgvector 在 PostgreSQL 中存向量并做距离检索；权限过滤应进入查询条件。

```python
with Session(engine) as session, session.begin():
    # ORM 参数化生成 SQL；事务退出时提交，异常时回滚。
    session.add(Message(thread_id=thread_id, role="user", content=text))
```

## 13. 缓存与任务队列 `[P1]`

- Redis 可做缓存、限流、取消信号、短期状态和 Celery Broker，不同用途应分 Key 前缀/数据库。
- 缓存 Key 包含模型、Prompt 版本、输入、租户和权限；设置 TTL。
- 不缓存敏感内容或把不同用户结果混用；写后考虑失效策略。
- Celery 适合文档解析、Embedding、批量评测等耗时任务；任务必须幂等、可重试、可追踪。
- “至少一次投递”意味着任务可能重复执行，数据库需唯一约束/幂等键。

## 14. FastAPI 与服务工程 `[P0/P1]`

- Pydantic 请求/响应模型即接口契约；不要直接返回 ORM 对象。
- 使用依赖注入处理鉴权、租户和数据库 Session。
- 统一异常映射；4xx 是调用问题，5xx 是服务问题。
- CORS 只允许真实前端来源；`*` 只用于本地演示。
- Uvicorn 是 ASGI Server；Gunicorn 可管理多进程 Worker；容器编排也可直接复制实例。
- 健康检查分存活和就绪；优雅关闭停止接流量并等待在途任务。

## 15. 测试、Mock 与质量 `[P0]`

- 测试金字塔：大量单元测试、适量集成测试、少量端到端测试。
- PyTest：fixture、参数化、异常断言、async 测试、临时目录。
- Mock 外部边界，不 Mock 被测业务内部；Fake 模型比脆弱的字符串 Mock 更适合 Agent。
- 固定时间、随机数和模型输出，避免随机失败。
- Agent 必测：结构化输出错误、未知工具、参数错误、超时、重试、幂等、无检索结果、错误引用、循环超限、Injection、审批拒绝和恢复。
- Ruff 负责 Lint/导入/常见 Bug；类型检查可加 Pyright/Mypy。

```python
async def test_dangerous_tool_needs_approval(agent):
    result = await agent.run("退款订单1002", "u1", "t1")
    assert result.status == "pending_approval"
```

## 16. 日志、调试、性能与安全 `[P1]`

- 结构化日志至少含 request/thread/user/tenant、节点、工具、耗时、结果类型和错误码。
- 不记录 API Key、完整身份证/手机号、未脱敏 Prompt 和工具密钥。
- 使用 traceback 定位异常；`breakpoint()` 本地调试；生产用 Trace 串模型与工具调用。
- 先测量再优化：延迟拆成排队、模型、检索、工具和序列化。
- 常用分析：`time.perf_counter`、`cProfile`、内存采样、数据库查询计划。
- 安全：最小权限、依赖扫描、Secret 管理、输入限制、输出编码、SSRF/SQL 注入/路径穿越防护、审计和数据保留。

## 17. 部署 `[P1]`

- Docker 镜像固定 Python 和依赖，使用非 root、较小基础镜像和 `.dockerignore`。
- 配置与镜像分离；Secret 不写镜像层。
- 反向代理处理 TLS、大小限制、SSE 缓冲和基础限流。
- 数据库/Redis 使用持久卷、备份和健康检查。
- 部署前执行测试、Lint、迁移检查、镜像扫描和冒烟测试。
- 监控延迟、错误率、饱和度、Token、工具成功率、引用质量和业务结果。

## 18. 高级索引 `[P2]`

- **描述符**：`__get__/__set__` 控制属性访问，`property`、ORM 字段和部分校验框架基于此思想。
- **元类**：控制类创建；框架源码会遇到，业务代码通常不该自定义。
- **MRO**：多继承的方法解析顺序；用 `Class.mro()` 检查。
- **对象模型**：名称绑定对象；引用计数 + 循环 GC；浅拷贝与深拷贝不同。
- **内存**：大列表、完整文档和未释放任务会占用内存；流式/迭代器只是工具，仍需观察生命周期。
- **GIL**：解释 CPython 线程与 CPU 并行边界；I/O 并发仍适用。
- **`__slots__`**：大量简单对象可节省内存，但限制动态属性并增加继承复杂度。
- **协变/逆变**：设计泛型库时重要，普通业务先正确使用 `Protocol`。

## 学习验收

能独立完成以下任务即可进入 Agent 主线：

1. 用 uv 创建项目并锁定依赖。
2. 用 Pydantic 定义一个 Tool 输入和一个结构化输出。
3. 写异步 HTTP 调用，含超时、错误分类和有限重试。
4. 用 Protocol 抽象模型或 Retriever，并写 Fake 实现测试。
5. 用 FastAPI 返回普通 JSON 和 SSE。
6. 用 PyTest 验证参数错误、超时和幂等。
7. 解释线程、进程、协程分别适合什么。
8. 解释事务、索引、缓存和任务幂等。

完整示例见 [最终代码](final-code/README.md)。
