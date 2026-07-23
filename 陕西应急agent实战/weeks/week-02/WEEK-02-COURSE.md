# 第 2 周：RAG 与预案专家 Agent

> 学习方式：5 天，每天 2～3 小时。第 2 周直接继承第 1 周完整工程，不重建简化项目。
>
> 本周终点：实现第一个能够独立运行、测试和评测的 Agent——预案专家 Agent。Mock 模式无需 DeepSeek Key；Live 模式通过 DeepSeek 的 OpenAI-compatible 接口生成建议，但引用来源始终由检索代码绑定。

## 1. 本周学习地图与最终成果

本周从“普通业务 API”进入第一个真正的 Agent 场景。

完整调用链：

```text
POST /api/agents/plan-expert/invoke
  -> PlanQuery 结构校验
  -> InMemoryPlanRetriever.search
  -> 找到课程模拟预案切片
  -> MODEL_MODE=mock
       -> PlanExpertAgent 确定性生成建议
     MODEL_MODE=live
       -> DeepSeekPlanExpertAgent
       -> DeepSeekChatClient
  -> 由代码绑定 Citation
  -> PlanRecommendation
```

五天安排：

| Day | 重点 | 当天结果 |
|---|---|---|
| Day 1 | 预案切片和确定性教学 Embedding | 能把中英文文本转换为稳定 16 维向量 |
| Day 2 | 相关度、阈值和 Retriever | 能正确排序隧道、冰雪、滑坡预案 |
| Day 3 | Mock 预案专家 Agent | 能基于证据输出 actions/citations |
| Day 4 | DeepSeek Live 适配层 | 能真实调用模型且拒绝模型伪造引用 |
| Day 5 | FastAPI、评测和验收 | 完成 ready/insufficient_evidence 演示 |

本周只新增一个 Agent：

```text
PlanExpertAgent（预案专家）
```

它必须先独立运行、测试和评测。暂不接 LangGraph，不新增 Supervisor，不调用路况和天气 Tool。

本周必做：

- 完成 Mock RAG。
- 完成 Mock 预案专家。
- 理解 DeepSeek 适配层，即使暂时没有 Key。
- 通过 `make test`、`make eval`、`make verify`。
- 完成第 9 章危险品运输事件预案作业。

本周选做：

- 使用真实 DeepSeek Key 调用一次 Live 模式。
- 增加更多课程模拟预案切片。
- 调整阈值并观察误召回和漏召回。

## 2. 前置知识、环境准备和本周起点

先确认第 1 周已经通关：

```bash
cd weeks/week-01
make test
make eval
make verify
```

然后进入第 2 周：

```bash
cd ../week-02
cp .env.example .env
make setup
```

第 2 周目录保存“截至本周的完整代码”，因此其中已经包含第 1 周的配置、领域模型、数据库、迁移和模拟 API。

你不是从空项目开始，而是在已有系统中增加：

```text
backend/src/highway_agent/
├── agents/
│   ├── __init__.py
│   └── plan_expert.py          # 新增
├── api.py                      # 增加 Agent API
├── config.py                   # 继承
├── database.py                 # 继承
├── domain.py                   # 继承
├── models.py                   # 新增 DeepSeek 适配层
└── rag.py                      # 新增检索
```

默认配置：

```dotenv
MODEL_MODE=mock
DEEPSEEK_API_KEY=
```

Mock 模式下：

- 不访问互联网。
- 不调用 DeepSeek。
- 检索、建议和引用完全确定。
- 所有核心测试都能执行。

Live 模式下：

```dotenv
MODEL_MODE=live
DEEPSEEK_API_KEY=你的真实Key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-v4-flash
```

不要把真实 Key 写进 `.env.example`、测试或截图。

## 3. 本周架构、目录变化与完整调用链

本周把 RAG 拆成四个明确职责：

```text
PlanDocument
  预案切片结构
       |
       v
InMemoryPlanRetriever
  负责检索和阈值
       |
       v
PlanExpertAgent / DeepSeekPlanExpertAgent
  负责组织建议
       |
       v
PlanRecommendation
  负责稳定输出和引用
```

RAG 不是“把一整份文档塞给模型”。本周的流程是：

```text
Retrieve：根据事件摘要检索小范围证据
Augment：把证据放入模型输入
Generate：根据证据生成处置建议
```

本周有两种“向量/相关度”概念：

1. `embed()`：用哈希生成稳定 16 维教学向量，用于理解和匹配数据库 `Vector(16)`。
2. `search()`：当前 Mock 检索使用查询词覆盖率，便于解释、断言和离线测试。

这不是生产级中文 Embedding，但它让你先学会 RAG 边界：

- 文档从哪里来。
- 相关度如何计算。
- 低证据时如何拒答。
- 引用如何与真实检索结果绑定。
- 模型只能生成建议，不能生成“证据事实”。

## 4. Day 1：创建预案切片与确定性 16 维教学 Embedding

### 今天目标

1. 理解文档切片的最小字段。
2. 为课程模拟预案添加明确来源。
3. 提取英文单词和中文二元组。
4. 用 SHA-256 哈希得到稳定向量。
5. 归一化为 16 维向量。
6. 写测试证明同一文本结果稳定。

### 上一节衔接

第 1 周已经在 PostgreSQL 中创建 `plan_documents` 表和 `Vector(16)` 字段。

今天先实现离线 Retriever。等检索语义稳定后，再把 Repository 替换为 pgvector 查询会更容易。

### 先说结论

今天的教学 Embedding 满足三个要求：

```text
同一文本 -> 同一向量
任意文本 -> 恰好 16 维
无模型 Key -> 仍然可计算
```

它只用于 Mock 和测试，不冒充真实语义 Embedding。

### 第 1 步：创建预案文档结构

新建 `backend/src/highway_agent/rag.py`：

```python
"""Week 2 的最小 RAG 实现。

Mock 模式使用确定性字符二元组，既能处理中文，又不依赖外部 Embedding API。
"""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass

from pydantic import BaseModel


class PlanDocument(BaseModel):
    """可检索的课程模拟预案切片。"""

    id: str
    title: str
    section: str
    content: str
    source: str
```

字段含义：

- `id`：切片稳定标识，引用时使用。
- `title`：预案标题。
- `section`：原文小节。
- `content`：可送入 Agent 的证据文本。
- `source`：来源地址，本课程使用 `synthetic://` 明确标记模拟数据。

### 第 2 步：创建检索结果结构

继续添加：

```python
@dataclass(frozen=True)
class SearchMatch:
    """检索结果及可用于评测的相关度分数。"""

    document: PlanDocument
    score: float
```

为什么不用普通字典？

因为检索结果在 Agent 和测试之间传递，需要明确 `document` 和 `score`。冻结 dataclass 还能避免后续代码意外修改结果。

### 第 3 步：提取中英文术语

继续添加：

```python
def _terms(text: str) -> set[str]:
    """提取英文单词和中文二元组，避免依赖额外分词库。"""

    normalized = re.sub(r"\s+", "", text.lower())
    ascii_words = set(re.findall(r"[a-z0-9]+", normalized))
    chinese = "".join(re.findall(r"[\u4e00-\u9fff]", normalized))
    bigrams = {
        chinese[index : index + 2]
        for index in range(max(0, len(chinese) - 1))
    }
    return ascii_words | bigrams
```

例如：

```text
秦岭隧道追尾
-> 秦岭、岭隧、隧道、道追、追尾
```

中文二元组不是完整分词，但对“隧道追尾”“道路结冰”“边坡滑坡”等课程词汇足够稳定。

### 第 4 步：创建 Retriever 和 embed

继续添加：

```python
class InMemoryPlanRetriever:
    """与 pgvector Repository 共享语义的本地确定性检索器。"""

    def __init__(
        self,
        documents: list[PlanDocument],
        threshold: float = 0.08,
    ) -> None:
        self.documents = documents
        self.threshold = threshold

    def embed(self, text: str) -> list[float]:
        """生成 16 维教学向量；仅用于 Mock 和单元测试。"""

        vector = [0.0] * 16
        for term in _terms(text):
            digest = hashlib.sha256(term.encode("utf-8")).digest()
            vector[digest[0] % len(vector)] += 1.0

        norm = math.sqrt(
            sum(value * value for value in vector)
        ) or 1.0

        return [
            round(value / norm, 8)
            for value in vector
        ]
```

算法步骤：

1. 将文本拆成术语集合。
2. 对每个术语计算 SHA-256。
3. 用第一个字节对 16 取模，决定落到哪个维度。
4. 对出现次数做累加。
5. 用 L2 范数归一化。
6. 保留 8 位小数，便于稳定测试。

### 第 5 步：创建演示预案

先在文件底部加入完整数据函数：

```python
def load_demo_documents() -> list[PlanDocument]:
    """返回明确标注为 synthetic 的课程预案，避免冒充官方文件。"""

    return [
        PlanDocument(
            id="PLAN-TUNNEL-001",
            title="课程模拟隧道交通事件预案",
            section="追尾与烟雾告警",
            content=(
                "核实火情与伤亡；确认车道占用；准备交通管制；"
                "通知消防和医疗资源待命。"
            ),
            source="synthetic://plans/tunnel-incident",
        ),
        PlanDocument(
            id="PLAN-SNOW-001",
            title="课程模拟冰雪保畅预案",
            section="降雪和道路结冰",
            content=(
                "巡查路面结冰；准备融雪物资；降低通行速度；"
                "必要时分流车辆。"
            ),
            source="synthetic://plans/snow-ice",
        ),
        PlanDocument(
            id="PLAN-LANDSLIDE-001",
            title="课程模拟边坡灾害预案",
            section="滑坡和落石",
            content=(
                "封控危险区域；核实阻断范围；联系抢险队伍；"
                "评估次生灾害风险。"
            ),
            source="synthetic://plans/landslide",
        ),
    ]
```

所有内容都是课程模拟数据，不代表陕西高速正式预案。

### 第 6 步：写向量稳定性测试

新建 `backend/tests/test_rag.py`，先加入测试数据和向量测试：

```python
from highway_agent.rag import InMemoryPlanRetriever, PlanDocument


DOCUMENTS = [
    PlanDocument(
        id="PLAN-TUNNEL",
        title="课程模拟隧道事件预案",
        section="烟雾与追尾",
        content=(
            "隧道发生追尾并出现烟雾时，应核实火情、"
            "伤亡和车道占用，准备交通管制。"
        ),
        source="synthetic://plans/tunnel",
    ),
    PlanDocument(
        id="PLAN-SNOW",
        title="课程模拟冰雪保畅预案",
        section="道路结冰",
        content="道路结冰时，应巡查路面、准备融雪物资并控制车辆速度。",
        source="synthetic://plans/snow",
    ),
]


def test_deterministic_embedding_is_stable_and_has_16_dimensions() -> None:
    retriever = InMemoryPlanRetriever(DOCUMENTS)

    first = retriever.embed("隧道追尾")
    second = retriever.embed("隧道追尾")

    assert first == second
    assert len(first) == 16
```

### 运行与预期输出

运行单个测试：

```bash
uv run --project backend pytest backend/tests/test_rag.py::test_deterministic_embedding_is_stable_and_has_16_dimensions -q
```

预期：

```text
.                                                                        [100%]
1 passed
```

手动查看向量：

```bash
uv run --project backend python -c "from highway_agent.rag import InMemoryPlanRetriever, load_demo_documents; print(InMemoryPlanRetriever(load_demo_documents()).embed('秦岭隧道追尾'))"
```

应输出包含 16 个浮点数的列表。重复执行结果相同。

### 对应测试

今天只聚焦：

```bash
uv run --project backend pytest backend/tests/test_rag.py -q -k embedding
```

不要连接数据库，不要调用模型。

### 常见错误

错误 1：每次向量不同

不要使用 Python 内置 `hash()`。它可能随进程改变；课程使用 SHA-256 保证稳定。

错误 2：中文术语集合为空

检查正则是否使用 `[\u4e00-\u9fff]`。

错误 3：空文本除以 0

代码中的：

```python
norm = math.sqrt(sum(value * value for value in vector)) or 1.0
```

保证空向量也不会除零。

错误 4：把 synthetic 来源写成真实官网

课程数据不是正式预案，必须保留 `synthetic://` 标识。

### 当天小练习

分别计算：

```text
秦岭隧道追尾
秦岭隧道追尾
高速公路降雪结冰
```

验证前两个向量完全一致，第三个通常不同。记录向量长度，不需要人工比较每一维语义。

### 今日总结与明日预告

今天创建了预案切片和离线教学向量。

明天实现 `search()`，重点学习相关度、阈值、排序和“证据不足时返回空列表”。

## 5. Day 2：实现可解释的检索、阈值与排序

### 今天目标

1. 使用查询词覆盖率计算相关度。
2. 过滤低于阈值的文档。
3. 按得分降序排列。
4. 限制返回数量。
5. 测试正确召回与无关问题拒绝。
6. 理解召回、误召回和漏召回。

### 上一节衔接

Day 1 已经能够把文本转成稳定 16 维教学向量。

今天的 Mock `search()` 使用更容易解释的术语覆盖率。向量保留给 pgvector 结构和后续替换练习。

### 先说结论

相关度公式：

```text
score = 查询术语与文档术语的交集数量 / 查询术语数量
```

查询：

```text
秦岭隧道两车追尾并出现烟雾
```

隧道预案包含“隧道、追尾、烟雾”等大量重合术语，因此应排第一。

### 第 1 步：实现 search

在 `InMemoryPlanRetriever` 内，紧接 `embed()` 添加：

```python
    def search(
        self,
        query: str,
        limit: int = 3,
    ) -> list[SearchMatch]:
        """按查询词覆盖率排序，并丢弃低于阈值的弱相关文档。"""

        query_terms = _terms(query)
        if not query_terms:
            return []

        matches: list[SearchMatch] = []
        for document in self.documents:
            document_terms = _terms(
                f"{document.title}{document.section}{document.content}"
            )
            score = len(query_terms & document_terms) / len(query_terms)
            if score >= self.threshold:
                matches.append(
                    SearchMatch(
                        document=document,
                        score=round(score, 4),
                    )
                )

        return sorted(
            matches,
            key=lambda item: item.score,
            reverse=True,
        )[:limit]
```

这里有四个安全边界：

1. 空查询直接返回空列表。
2. 低于阈值的文档不进入结果。
3. 先按分数排序。
4. 最后用 `limit` 控制上下文规模。

### 第 2 步：测试隧道预案排第一

在 `test_rag.py` 添加：

```python
def test_retriever_ranks_tunnel_plan_first() -> None:
    retriever = InMemoryPlanRetriever(DOCUMENTS)

    matches = retriever.search(
        "秦岭隧道两车追尾并出现烟雾",
        limit=2,
    )

    assert matches[0].document.id == "PLAN-TUNNEL"
    assert matches[0].score > 0.5
```

运行：

```bash
uv run --project backend pytest backend/tests/test_rag.py::test_retriever_ranks_tunnel_plan_first -q
```

### 第 3 步：测试无关问题不召回

继续添加：

```python
def test_retriever_returns_no_match_below_threshold() -> None:
    retriever = InMemoryPlanRetriever(DOCUMENTS)

    matches = retriever.search(
        "服务区餐饮价格咨询",
        limit=2,
    )

    assert matches == []
```

这条测试很重要。RAG 的目标不是“任何问题都找一个最像的文档”，而是证据不足时明确返回空。

### 第 4 步：观察阈值影响

手动执行默认阈值：

```bash
uv run --project backend python -c "from highway_agent.rag import InMemoryPlanRetriever, load_demo_documents; r=InMemoryPlanRetriever(load_demo_documents()); print([(m.document.id,m.score) for m in r.search('秦岭隧道追尾并出现烟雾')])"
```

再提高阈值：

```bash
uv run --project backend python -c "from highway_agent.rag import InMemoryPlanRetriever, load_demo_documents; r=InMemoryPlanRetriever(load_demo_documents(), threshold=0.8); print([(m.document.id,m.score) for m in r.search('秦岭隧道追尾并出现烟雾')])"
```

阈值更高不代表一定更好：

- 太低：无关文档也被召回。
- 太高：相关文档可能被漏掉。
- 应使用评测集选择，不凭感觉。

### 第 5 步：理解 limit

执行：

```bash
uv run --project backend python -c "from highway_agent.rag import InMemoryPlanRetriever, load_demo_documents; r=InMemoryPlanRetriever(load_demo_documents(), threshold=0); print(len(r.search('应急处置', limit=1)))"
```

结果最多是 1。

在真实系统里，返回过多文档会：

- 增加 Token。
- 稀释重点证据。
- 增大模型把不同预案混合的风险。

### 第 6 步：运行完整检索测试

执行：

```bash
uv run --project backend pytest backend/tests/test_rag.py -q
```

三条测试分别覆盖排序、拒召回和确定性向量。

### 运行与预期输出

预期：

```text
...                                                                      [100%]
3 passed
```

隧道查询的手动结果第一项应类似：

```text
('PLAN-TUNNEL-001', 0.6)
```

具体分数由术语集合决定，但必须大于 0，且隧道预案排第一。

### 对应测试

今天必须通过：

```bash
uv run --project backend pytest backend/tests/test_rag.py -q
```

如果排序测试失败，先打印每个文档得分，而不是直接降低断言。

### 常见错误

错误 1：对空查询除零

必须在计算分数前：

```python
if not query_terms:
    return []
```

错误 2：先切 limit 再排序

必须先收集、排序，最后 `[:limit]`。

错误 3：无关问题仍召回

检查阈值是否被设为 0，或文档是否包含过于泛化的词。

错误 4：认为 score 是概率

本周 score 只是查询术语覆盖率，不是可信概率，也不能直接表示处置可靠性。

### 当天小练习

新增查询：

```text
连续降雨导致山体落石和边坡滑坡
```

打印匹配结果，确认 `PLAN-LANDSLIDE-001` 排第一。不要修改正式阈值来“硬凑答案”。

### 今日总结与明日预告

今天完成了 RAG 的 Retrieve 部分。

明天创建 Mock 预案专家 Agent：先检索，再生成结构化建议；检索为空时必须拒答。

## 6. Day 3：创建可独立运行的 Mock 预案专家 Agent

### 今天目标

1. 定义 Agent 输入 `PlanQuery`。
2. 定义引用 `Citation`。
3. 定义稳定输出 `PlanRecommendation`。
4. 实现有证据时的确定性建议。
5. 实现无证据时的明确拒答。
6. 测试引用和安全边界。

### 上一节衔接

Day 2 已完成可解释 Retriever。

今天 Agent 不直接访问文档列表，而是只依赖 Retriever。这使检索实现以后可以替换为 pgvector Repository。

### 先说结论

第一个 Agent 的循环很简单：

```text
输入事件摘要
  -> 调一次 Retriever
  -> 有证据：生成建议 + 引用
  -> 无证据：insufficient_evidence
```

Agent 不执行交通管制，也不通知任何真实单位。

### 第 1 步：创建 Agent 包和输入输出模型

新建空文件 `backend/src/highway_agent/agents/__init__.py`。

新建 `backend/src/highway_agent/agents/plan_expert.py`：

```python
"""预案专家 Agent：Mock 确定性实现与 DeepSeek Live 实现。"""

import json
from typing import Protocol

from pydantic import BaseModel, Field

from highway_agent.models import ModelJsonResponse
from highway_agent.rag import InMemoryPlanRetriever, SearchMatch


class PlanQuery(BaseModel):
    """预案专家的最小输入。"""

    event_summary: str = Field(min_length=2, max_length=2000)


class Citation(BaseModel):
    """让每条建议可以追溯到具体预案切片。"""

    document_id: str
    title: str
    section: str
    source: str
    score: float


class PlanRecommendation(BaseModel):
    """预案专家的稳定结构化输出。"""

    status: str
    summary: str
    actions: list[str]
    citations: list[Citation]
```

### 第 2 步：创建引用绑定函数

继续添加：

```python
def _build_citations(
    matches: list[SearchMatch],
) -> list[Citation]:
    """引用只能来自检索结果，不能接受模型自行生成的来源。"""

    return [
        Citation(
            document_id=match.document.id,
            title=match.document.title,
            section=match.document.section,
            source=match.document.source,
            score=match.score,
        )
        for match in matches
    ]
```

引用由程序根据 `SearchMatch` 构建。这个边界会在 Live 模式继续保持。

### 第 3 步：实现 Mock Agent

继续添加：

```python
class PlanExpertAgent:
    """只允许调用一个检索工具，控制第一位 Agent 的学习难度。"""

    def __init__(
        self,
        retriever: InMemoryPlanRetriever,
    ) -> None:
        self.retriever = retriever

    def invoke(
        self,
        query: PlanQuery,
    ) -> PlanRecommendation:
        """检索证据后生成确定性的 Mock 建议；无证据时明确拒答。"""

        matches = self.retriever.search(
            query.event_summary,
            limit=2,
        )
        if not matches:
            return PlanRecommendation(
                status="insufficient_evidence",
                summary=(
                    "未检索到与当前事件相关的课程预案，"
                    "不能生成处置建议。"
                ),
                actions=[],
                citations=[],
            )

        top_document = matches[0].document
        actions = [
            item.strip()
            for item in top_document.content.split("；")
            if item.strip()
        ]
        citations = _build_citations(matches)

        return PlanRecommendation(
            status="ready",
            summary=(
                f"已基于《{top_document.title}》"
                "生成初步建议。"
            ),
            actions=actions,
            citations=citations,
        )
```

Mock 建议来自文档分号拆分，因此结果确定，适合先测试 Agent 输入输出。

### 第 4 步：测试有证据场景

新建 `backend/tests/test_plan_agent.py`，先添加：

```python
from highway_agent.agents.plan_expert import (
    PlanExpertAgent,
    PlanQuery,
)
from highway_agent.rag import (
    InMemoryPlanRetriever,
    load_demo_documents,
)


def test_plan_expert_returns_actions_with_citations() -> None:
    agent = PlanExpertAgent(
        InMemoryPlanRetriever(load_demo_documents())
    )

    result = agent.invoke(
        PlanQuery(
            event_summary="隧道内发生追尾并出现烟雾"
        )
    )

    assert result.status == "ready"
    assert result.actions
    assert result.citations[0].document_id == "PLAN-TUNNEL-001"
    assert result.citations[0].source.startswith("synthetic://")
```

### 第 5 步：测试证据不足

继续添加：

```python
def test_plan_expert_refuses_when_evidence_is_missing() -> None:
    agent = PlanExpertAgent(
        InMemoryPlanRetriever(load_demo_documents())
    )

    result = agent.invoke(
        PlanQuery(
            event_summary="服务区餐饮价格投诉"
        )
    )

    assert result.status == "insufficient_evidence"
    assert result.actions == []
    assert "未检索到" in result.summary
```

这条拒答测试是 Agent 可靠性的第一条底线。

### 第 6 步：手动调用 Agent

执行：

```bash
uv run --project backend python -c "from highway_agent.agents.plan_expert import PlanExpertAgent,PlanQuery; from highway_agent.rag import InMemoryPlanRetriever,load_demo_documents; a=PlanExpertAgent(InMemoryPlanRetriever(load_demo_documents())); print(a.invoke(PlanQuery(event_summary='秦岭隧道追尾并出现烟雾')).model_dump_json(indent=2))"
```

### 运行与预期输出

核心结果：

```json
{
  "status": "ready",
  "summary": "已基于《课程模拟隧道交通事件预案》生成初步建议。",
  "actions": [
    "核实火情与伤亡",
    "确认车道占用",
    "准备交通管制",
    "通知消防和医疗资源待命。"
  ],
  "citations": [
    {
      "document_id": "PLAN-TUNNEL-001",
      "source": "synthetic://plans/tunnel-incident"
    }
  ]
}
```

测试：

```bash
uv run --project backend pytest backend/tests/test_plan_agent.py -q -k "returns_actions or refuses"
```

预期 2 条通过。

### 对应测试

今天关注：

```bash
uv run --project backend pytest backend/tests/test_plan_agent.py -q -k "returns_actions or refuses"
```

测试既验证正常路径，也验证证据不足路径。

### 常见错误

错误 1：无证据时仍返回通用建议

必须返回空 `actions` 和空 `citations`。

错误 2：引用由 Agent 文本生成

引用只能调用 `_build_citations(matches)`，不能从自然语言解析。

错误 3：直接返回字典

返回 `PlanRecommendation`，让 Pydantic 保证结构。

错误 4：把“建议”写成“已执行”

预案专家只给建议，不声称已经封路、通知或调度。

### 当天小练习

调用冰雪事件：

```text
高速公路降雪结冰，车辆行驶缓慢
```

确认：

- `status=ready`。
- 第一引用是 `PLAN-SNOW-001`。
- actions 来自冰雪预案。
- 输出没有“已经完成分流”之类执行声明。

### 今日总结与明日预告

今天完成了第一个可独立运行的 Agent。

明天在保持输入输出不变的前提下增加 DeepSeek Live 实现，并用 MockTransport 测试真实 HTTP 适配层。

## 7. Day 4：接入 DeepSeek Live 模式并锁定引用边界

### 今天目标

1. 创建模型供应商适配层。
2. 使用 DeepSeek Chat Completions。
3. 请求 JSON Object 输出。
4. 记录 total_tokens。
5. 为 Live Agent 注入模型客户端。
6. 阻止模型自造引用。
7. 不用真实 Key 测试完整 HTTP 请求。

### 上一节衔接

Day 3 的 Mock Agent 已经稳定输出 `PlanRecommendation`。

今天新增 Live 实现，但 API 契约不变。调用方不需要知道建议来自 Mock 还是 DeepSeek。

### 先说结论

DeepSeek 只负责：

```text
根据已检索 evidence 生成 summary 和 actions
```

DeepSeek 不负责：

- 选择引用来源。
- 声称动作已执行。
- 在无证据时自由回答。
- 访问真实交通系统。

### 第 1 步：创建统一模型响应

新建 `backend/src/highway_agent/models.py`：

```python
"""模型供应商适配层；Agent 不直接依赖 DeepSeek HTTP 细节。"""

import json
from dataclasses import dataclass

import httpx

from highway_agent.config import Settings


@dataclass(frozen=True)
class ModelJsonResponse:
    """统一模型响应，保留课程需要的 Token 统计。"""

    content: dict[str, object]
    total_tokens: int
```

Agent 不直接处理 httpx Response，而是只接收统一结构。

### 第 2 步：实现 DeepSeek 客户端

继续添加：

```python
class DeepSeekChatClient:
    """DeepSeek OpenAI-compatible Chat Completions 客户端。"""

    def __init__(
        self,
        settings: Settings,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not settings.deepseek_api_key:
            raise ValueError(
                "Live 模式必须配置 DEEPSEEK_API_KEY"
            )
        self.settings = settings
        self.transport = transport

    async def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> ModelJsonResponse:
        """请求 JSON 输出；工具型 Agent 默认关闭思考模式以降低延迟。"""

        payload = {
            "model": self.settings.deepseek_model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            "thinking": {"type": "disabled"},
            "response_format": {"type": "json_object"},
            "stream": False,
        }
        headers = {
            "Authorization": (
                f"Bearer {self.settings.deepseek_api_key}"
            )
        }

        async with httpx.AsyncClient(
            base_url=self.settings.deepseek_base_url,
            headers=headers,
            transport=self.transport,
            timeout=30.0,
        ) as client:
            response = await client.post(
                "/chat/completions",
                json=payload,
            )
            response.raise_for_status()

        body = response.json()
        content = json.loads(
            body["choices"][0]["message"]["content"]
        )

        return ModelJsonResponse(
            content=content,
            total_tokens=int(
                body.get("usage", {}).get("total_tokens", 0)
            ),
        )
```

`transport` 参数用于测试注入 `httpx.MockTransport`，不会改变生产调用方式。

### 第 3 步：定义 Agent 所需的 Protocol

回到 `plan_expert.py`，在输出模型后添加：

```python
class JsonModelClient(Protocol):
    """Live Agent 只依赖 JSON 模型接口，便于测试注入替身。"""

    async def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> ModelJsonResponse: ...
```

这里的 `...` 是 Python Protocol 方法的合法函数体，不代表省略课程代码。Protocol 只描述调用契约，不提供运行实现；`DeepSeekChatClient` 和测试替身分别实现它。

### 第 4 步：实现 Live Agent

在 Mock Agent 后添加：

```python
class DeepSeekPlanExpertAgent:
    """Live 模式的预案专家：先检索，再让 DeepSeek 基于证据生成建议。"""

    def __init__(
        self,
        retriever: InMemoryPlanRetriever,
        model: JsonModelClient,
    ) -> None:
        self.retriever = retriever
        self.model = model

    async def ainvoke(
        self,
        query: PlanQuery,
    ) -> PlanRecommendation:
        """调用 DeepSeek，但由代码绑定真实检索引用并校验结构。"""

        matches = self.retriever.search(
            query.event_summary,
            limit=2,
        )
        if not matches:
            return PlanRecommendation(
                status="insufficient_evidence",
                summary=(
                    "未检索到与当前事件相关的课程预案，"
                    "不能生成处置建议。"
                ),
                actions=[],
                citations=[],
            )

        evidence = [
            {
                "document_id": match.document.id,
                "title": match.document.title,
                "section": match.document.section,
                "content": match.document.content,
            }
            for match in matches
        ]

        response = await self.model.complete_json(
            (
                "你是高速应急预案助手。只能依据提供的预案证据，"
                "输出 JSON："
                '{"summary":"文本","actions":["动作"]}。'
                "不得生成引用或声称已经执行。"
            ),
            json.dumps(
                {
                    "event_summary": query.event_summary,
                    "evidence": evidence,
                },
                ensure_ascii=False,
            ),
        )

        summary = response.content.get("summary")
        actions = response.content.get("actions")
        if (
            not isinstance(summary, str)
            or not isinstance(actions, list)
            or not all(isinstance(item, str) for item in actions)
        ):
            raise ValueError(
                "DeepSeek 返回的预案建议不符合结构化契约"
            )

        return PlanRecommendation(
            status="ready",
            summary=summary,
            actions=actions,
            citations=_build_citations(matches),
        )
```

注意：最终 `citations` 来自 `matches`，不是 `response.content`。

### 第 5 步：测试 HTTP 请求结构

新建 `backend/tests/test_deepseek_client.py`，使用 `httpx.MockTransport`：

```python
import json

import httpx
import pytest

from highway_agent.config import Settings
from highway_agent.models import DeepSeekChatClient


@pytest.mark.asyncio
async def test_deepseek_client_uses_current_model_and_openai_compatible_endpoint() -> None:
    captured: dict[str, object] = {}

    def handler(
        request: httpx.Request,
    ) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "message": {
                            "content": '{"status":"ok"}'
                        }
                    }
                ],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 3,
                    "total_tokens": 13,
                },
            },
        )

    settings = Settings(
        model_mode="live",
        deepseek_api_key="test-key",
    )
    client = DeepSeekChatClient(
        settings,
        transport=httpx.MockTransport(handler),
    )

    response = await client.complete_json(
        "system",
        "user",
    )

    assert captured["url"] == (
        "https://api.deepseek.com/chat/completions"
    )
    assert captured["body"]["model"] == "deepseek-v4-flash"
    assert captured["body"]["thinking"] == {"type": "disabled"}
    assert response.content == {"status": "ok"}
    assert response.total_tokens == 13
```

### 第 6 步：测试模型不能伪造引用

在 `test_plan_agent.py` 中，正式测试使用一个 `FakeDeepSeekClient` 返回包含伪造 citation 的内容，然后断言最终结果只包含检索到的 `PLAN-TUNNEL-001`。

运行：

```bash
uv run --project backend pytest backend/tests/test_deepseek_client.py backend/tests/test_plan_agent.py -q -k "deepseek or live"
```

### 运行与预期输出

预期相关测试全部通过，且不发真实网络请求。

MockTransport 捕获的 URL：

```text
https://api.deepseek.com/chat/completions
```

捕获的请求体关键字段：

```json
{
  "model": "deepseek-v4-flash",
  "thinking": {"type": "disabled"},
  "response_format": {"type": "json_object"},
  "stream": false
}
```

### 对应测试

执行：

```bash
uv run --project backend pytest backend/tests/test_deepseek_client.py -q
uv run --project backend pytest backend/tests/test_plan_agent.py -q -k live
```

即使没有真实 Key，也必须通过。

### 常见错误

错误 1：测试意外访问真实网络

确认创建客户端时传入：

```python
transport=httpx.MockTransport(handler)
```

错误 2：模型返回 JSON 字符串但未解析

Chat Completions 的 `message.content` 是字符串，需要 `json.loads`。

错误 3：把 test-key 写入真实配置

`test-key` 只存在测试对象中，不写入 `.env`。

错误 4：接受模型返回 citations

Live Agent 只读取 `summary` 和 `actions`，引用必须由 `_build_citations` 创建。

错误 5：输出字段类型错误

模型返回后仍要检查 summary 是字符串、actions 是字符串列表。

### 当天小练习

修改测试替身，让模型返回：

```json
{
  "summary": 123,
  "actions": "核实火情"
}
```

确认 Agent 抛出结构错误。练习后恢复测试，确保正常套件通过。

### 今日总结与明日预告

今天完成了 DeepSeek 供应商适配层和 Live Agent，同时守住了引用可信边界。

明天把 Agent 接入 FastAPI，运行数据集场景并完成本周验收。

## 8. Day 5：接入 API、运行场景评测并完成验收

### 今天目标

1. 在应用工厂中创建 Retriever 和两种 Agent。
2. 根据 `MODEL_MODE` 选择 Mock/Live。
3. 增加预案专家 API。
4. 测试 HTTP 契约。
5. 运行四类核心场景。
6. 完成本周统一验收。

### 上一节衔接

Day 1～4 已完成 Retriever、Mock Agent 和 DeepSeek Live Agent。

今天把它们装配进第 1 周已有 FastAPI 应用，不删除原来的健康、路况、天气和资源接口。

### 先说结论

模式选择只发生在应用创建时：

```text
MODEL_MODE=mock
  -> PlanExpertAgent

MODEL_MODE=live
  -> DeepSeekPlanExpertAgent + DeepSeekChatClient
```

API 路径和响应模型完全相同。

### 第 1 步：增加 API 导入

在 `backend/src/highway_agent/api.py` 的现有导入区加入：

```python
import httpx

from highway_agent.agents.plan_expert import (
    DeepSeekPlanExpertAgent,
    PlanExpertAgent,
    PlanQuery,
    PlanRecommendation,
)
from highway_agent.models import DeepSeekChatClient
from highway_agent.rag import (
    InMemoryPlanRetriever,
    load_demo_documents,
)
```

保留 Week 1 的 FastAPI、Settings 和 domain 导入。

### 第 2 步：扩展应用工厂参数

把原来的：

```python
def create_app(
    settings: Settings | None = None,
) -> FastAPI:
```

修改为：

```python
def create_app(
    settings: Settings | None = None,
    model_transport: httpx.AsyncBaseTransport | None = None,
) -> FastAPI:
```

`model_transport` 只为测试注入，默认 `None` 时使用真实 HTTP 传输。

### 第 3 步：装配 Retriever 和 Agent

在：

```python
app = FastAPI(
    title=app_settings.app_name,
    version="0.1.0",
)
```

之后添加：

```python
    retriever = InMemoryPlanRetriever(
        load_demo_documents()
    )
    plan_agent = PlanExpertAgent(retriever)

    live_plan_agent = (
        DeepSeekPlanExpertAgent(
            retriever,
            DeepSeekChatClient(
                app_settings,
                transport=model_transport,
            ),
        )
        if app_settings.model_mode == "live"
        else None
    )
```

Mock 模式不会实例化 `DeepSeekChatClient`，因此空 Key 不会报错。

### 第 4 步：增加预案专家路由

在三个 Week 1 模拟路由之后、`return app` 之前添加：

```python
    @app.post(
        "/api/agents/plan-expert/invoke",
        response_model=PlanRecommendation,
    )
    async def invoke_plan_expert(
        query: PlanQuery,
    ) -> PlanRecommendation:
        """Mock 使用确定性实现，Live 使用 DeepSeek 且引用由检索结果绑定。"""

        if live_plan_agent is not None:
            return await live_plan_agent.ainvoke(query)

        return plan_agent.invoke(query)
```

### 第 5 步：测试 API

在 `test_plan_agent.py` 添加：

```python
from fastapi.testclient import TestClient

from highway_agent.api import create_app


def test_plan_expert_api_is_available_in_mock_mode() -> None:
    client = TestClient(create_app())

    response = client.post(
        "/api/agents/plan-expert/invoke",
        json={
            "event_summary": "秦岭隧道追尾并出现烟雾"
        },
    )

    assert response.status_code == 200
    assert response.json()["status"] == "ready"
    assert response.json()["citations"]
```

运行：

```bash
uv run --project backend pytest backend/tests/test_plan_agent.py -q
```

### 第 6 步：启动并演示

保持 `.env`：

```dotenv
MODEL_MODE=mock
DEEPSEEK_API_KEY=
```

启动：

```bash
make run
```

调用相关事件：

```bash
curl -X POST http://127.0.0.1:8000/api/agents/plan-expert/invoke -H "Content-Type: application/json" -d '{"event_summary":"秦岭隧道追尾并出现烟雾"}'
```

调用无关问题：

```bash
curl -X POST http://127.0.0.1:8000/api/agents/plan-expert/invoke -H "Content-Type: application/json" -d '{"event_summary":"服务区餐饮价格投诉"}'
```

### 运行与预期输出

相关事件：

```json
{
  "status": "ready",
  "summary": "已基于《课程模拟隧道交通事件预案》生成初步建议。",
  "actions": [
    "核实火情与伤亡",
    "确认车道占用",
    "准备交通管制",
    "通知消防和医疗资源待命。"
  ],
  "citations": [
    {
      "document_id": "PLAN-TUNNEL-001",
      "source": "synthetic://plans/tunnel-incident"
    }
  ]
}
```

无关问题：

```json
{
  "status": "insufficient_evidence",
  "summary": "未检索到与当前事件相关的课程预案，不能生成处置建议。",
  "actions": [],
  "citations": []
}
```

### 对应测试

运行统一命令：

```bash
make test
make eval
make verify
```

本周 `make eval` 选择名称包含 `rag`、`plan_agent` 或 `deepseek` 的测试，覆盖 Retriever、Agent 和模型适配层。

### 常见错误

错误 1：Mock 模式启动时提示缺少 Key

说明无条件创建了 `DeepSeekChatClient`。必须只在 `model_mode == "live"` 分支创建。

错误 2：输入太短返回 422

`event_summary` 最少 2 个字符，这是 Pydantic 契约，不要在路由内绕过。

错误 3：Live 测试没有走 MockTransport

确保 `create_app` 把 `model_transport` 传给 `DeepSeekChatClient`。

错误 4：相关查询返回 insufficient_evidence

先直接调用 Retriever 打印 matches，确认是检索问题还是 Agent 问题。

错误 5：引用出现模型提供的虚构 ID

检查最终输出是否仍调用 `_build_citations(matches)`。

### 当天小练习

分别调用：

```text
高速公路降雪结冰车辆缓行
连续降雨造成边坡滑坡落石
服务区餐饮价格投诉
```

记录三个状态和第一引用，确认前两个 ready，最后一个 insufficient_evidence。

### 今日总结与明日预告

第一个 Agent 已完成独立开发、测试、评测和 API 接入。

第 3 周会继续保留它，并新增事件研判 Agent。新 Agent 将第一次使用多个模拟业务 Tool 获取路况、天气和资源信息。

## 9. 本周唯一实战作业

任务：新增“危险品运输车辆事故”课程模拟预案，并让预案专家正确引用。

业务要求：

1. 文档 ID：`PLAN-HAZMAT-001`。
2. 标题明确包含“危险品运输事件”。
3. 来源使用 `synthetic://plans/hazmat-incident`。
4. 内容至少包含：确认危险品类型、设置警戒区、通知消防和环保力量待命。
5. 查询“危化品运输车辆泄漏”时状态为 ready。
6. 第一引用必须是 `PLAN-HAZMAT-001`。
7. 餐饮投诉仍然 insufficient_evidence。
8. 不修改已有三份文档的 ID 和来源。
9. 不把课程模拟内容描述为正式预案。

实施顺序：

1. 先在 `test_rag.py` 写排序测试。
2. 运行该测试，确认缺文档时失败。
3. 在 `load_demo_documents()` 增加正式切片。
4. 在 `test_plan_agent.py` 增加 Agent 引用测试。
5. 手动调用 API。
6. 运行 `make test`。
7. 运行 `make eval`。
8. 运行 `make verify`。

验收请求：

```bash
curl -X POST http://127.0.0.1:8000/api/agents/plan-expert/invoke -H "Content-Type: application/json" -d '{"event_summary":"G30发生危化品运输车辆泄漏事故"}'
```

完成标准：

- 结果为 `ready`。
- actions 来自新增预案。
- 第一 citation ID 正确。
- source 以 `synthetic://` 开头。
- 原有测试全部通过。
- Mock 模式无外部网络请求。

## 10. 测试、常见错误与系统排查

分层诊断：

```text
PlanRecommendation 不对
  -> PlanQuery 是否通过校验？
  -> Retriever 是否返回匹配？
  -> score 是否超过 threshold？
  -> Mock 还是 Live？
  -> Live 响应是否满足 JSON 结构？
  -> Citation 是否由 matches 绑定？
```

调试命令：

```bash
uv run --project backend pytest backend/tests/test_rag.py -vv
uv run --project backend pytest backend/tests/test_plan_agent.py -vv
uv run --project backend pytest backend/tests/test_deepseek_client.py -vv
make test
```

症状对应：

| 症状 | 层 | 检查 |
|---|---|---|
| matches 为空 | Retriever | terms、threshold、文档内容 |
| 第一文档错误 | 排序 | score 和 reverse=True |
| actions 为空 | Agent | content 分隔符和 evidence |
| citations 虚构 | 安全边界 | _build_citations |
| JSONDecodeError | 模型适配 | message.content |
| 401 | Live 配置 | API Key |
| 422 | API 契约 | event_summary 长度 |
| Mock 访问网络 | 模式装配 | 条件创建 Live Agent |

不要通过以下方式“修复”：

- 把阈值永久改成 0。
- 无证据时返回模型常识。
- 信任模型生成的 source。
- 在测试里访问真实 DeepSeek。
- 删除 insufficient_evidence 分支。

## 11. 通关清单与三道面试题

- [ ] 能解释 RAG 三个阶段。
- [ ] 能说明 PlanDocument 五个字段。
- [ ] 能解释中文二元组的作用与局限。
- [ ] 能生成稳定 16 维教学向量。
- [ ] 能说明 threshold 太高和太低的影响。
- [ ] 能让隧道、冰雪、滑坡文档正确排序。
- [ ] 能实现无证据拒答。
- [ ] 能区分 Mock Agent 和 Live Agent。
- [ ] 能说明 DeepSeekChatClient 的适配职责。
- [ ] 能用 MockTransport 验证 HTTP 请求。
- [ ] 能证明模型无法伪造 citation。
- [ ] 能让 `make test`、`make eval`、`make verify` 通过。

### 面试题 1

RAG 为什么仍然需要“证据不足”状态？

回答要点：

向量或词项检索总能找到一个相对最像的结果，但最像不代表相关。设置阈值并允许空结果，可以防止 Agent 在无关预案上生成看似合理的处置建议；这比强行回答更可靠。

### 面试题 2

为什么引用不能直接接受大模型输出？

回答要点：

模型可能生成不存在的文档 ID、标题或来源。引用属于可审计事实，应由检索系统根据真实 SearchMatch 构建；模型只负责在证据范围内生成 summary 和 actions。

### 面试题 3

如何在没有 DeepSeek Key 的情况下测试 Live 适配逻辑？

回答要点：

通过依赖注入把 `httpx.MockTransport` 传给客户端，捕获请求 URL、Header 和 JSON body，并返回固定的 Chat Completions 响应。这样可以测试真实序列化和解析路径，又不会访问外部网络。

## 12. 本周总结与下一周衔接

本周完成：

```text
课程模拟预案
  -> 可解释 Retriever
  -> 证据阈值
  -> Mock 预案专家
  -> DeepSeek Live 预案专家
  -> 可信引用
  -> FastAPI
  -> 自动测试与评测
```

进入第 3 周前执行：

```bash
make test
make eval
make verify
```

第 3 周将从本周完整代码继续，新增：

- HTTP Tool 输入输出 Schema。
- 路况、气象、资源三个模拟 Tool。
- ToolRegistry。
- 事件研判 Agent。
- 工具选择与调用轨迹。
- stale、503 和未知路段错误处理。
- Mock/Live 结构化研判。

不会删除预案专家，也不会提前引入多 Agent Supervisor。
