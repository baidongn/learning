"""FastAPI 服务与 SSE 流式接口。"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

from agent_lab.agent import AgentResult, CustomerServiceAgent
from agent_lab.config import get_settings
from agent_lab.deepseek import DeepSeekClient, FakeDeepSeekClient
from agent_lab.retrieval import Document, InMemoryRetriever


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8_000)
    user_id: str = Field(min_length=1, max_length=100)
    thread_id: str = Field(min_length=1, max_length=100)


class ApprovalRequest(BaseModel):
    thread_id: str
    user_id: str = Field(min_length=1, max_length=100)
    approved: bool


class KnowledgeRequest(Document):
    """新增知识文档的请求。"""


class CancelRequest(BaseModel):
    thread_id: str = Field(min_length=1, max_length=100)


def build_default_agent() -> CustomerServiceAgent:
    settings = get_settings()
    model = (
        DeepSeekClient(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
            chat_model=settings.deepseek_chat_model,
            reasoning_model=settings.deepseek_reasoning_model,
        )
        if settings.deepseek_api_key
        else FakeDeepSeekClient()
    )
    retriever = InMemoryRetriever(
        [
            Document(
                id="leave-policy",
                text="员工申请年假需要至少提前三天，并由直属主管审批。",
                source="员工手册/休假制度",
            ),
            Document(
                id="after-sale",
                text="商品签收七天内且不影响二次销售时，可以申请退货。",
                source="客服知识库/售后政策",
            ),
        ]
    )
    return CustomerServiceAgent(model=model, retriever=retriever)


def create_app(agent: CustomerServiceAgent | None = None) -> FastAPI:
    service = agent or build_default_agent()
    app = FastAPI(title="DeepSeek Agent Lab", version="0.1.0")
    app.state.agent = service
    app.state.metrics = {"chat_requests": 0, "stream_requests": 0}
    app.state.running_tasks: dict[str, asyncio.Task[AgentResult]] = {}
    settings = get_settings()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[item.strip() for item in settings.cors_origins.split(",")],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.exception_handler(ValueError)
    async def invalid_operation(_request: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(
            status_code=400,
            content={"code": "invalid_operation", "message": str(exc)},
        )

    @app.exception_handler(PermissionError)
    async def forbidden(_request: Request, exc: PermissionError) -> JSONResponse:
        return JSONResponse(
            status_code=403,
            content={"code": "forbidden", "message": str(exc)},
        )

    @app.get("/", response_class=FileResponse)
    async def index() -> Path:
        return Path(__file__).with_name("static") / "index.html"

    @app.get("/api/v1/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "mode": service.mode}

    async def run_tracked(request: ChatRequest) -> AgentResult:
        """跟踪当前任务，使取消只作用于正在执行的请求。"""
        current = app.state.running_tasks.get(request.thread_id)
        if current is not None and not current.done():
            raise HTTPException(status_code=409, detail="该会话已有任务正在执行")
        task = asyncio.create_task(
            service.run(request.message, request.user_id, request.thread_id)
        )
        app.state.running_tasks[request.thread_id] = task
        try:
            return await task
        except asyncio.CancelledError:
            return AgentResult(answer="执行已取消。", status="blocked")
        finally:
            if app.state.running_tasks.get(request.thread_id) is task:
                app.state.running_tasks.pop(request.thread_id, None)

    @app.post("/api/v1/chat", response_model=AgentResult)
    async def chat(request: ChatRequest) -> AgentResult:
        app.state.metrics["chat_requests"] += 1
        return await run_tracked(request)

    @app.post("/api/v1/approve", response_model=AgentResult)
    async def approve(request: ApprovalRequest) -> AgentResult:
        return await service.resume(request.thread_id, request.approved, request.user_id)

    @app.post("/api/v1/chat/stream")
    async def stream_chat(request: ChatRequest) -> StreamingResponse:
        app.state.metrics["stream_requests"] += 1

        async def events() -> AsyncIterator[str]:
            result = await run_tracked(request)
            for index in range(0, len(result.answer), 6):
                payload = json.dumps(
                    {"text": result.answer[index : index + 6]}, ensure_ascii=False
                )
                yield f"event: token\ndata: {payload}\n\n"
            payload = result.model_dump_json()
            yield f"event: done\ndata: {payload}\n\n"

        return StreamingResponse(events(), media_type="text/event-stream")

    @app.post("/api/v1/knowledge", status_code=201)
    async def add_knowledge(request: KnowledgeRequest) -> dict[str, str]:
        add = getattr(service.retriever, "add", None)
        if add is None:
            raise RuntimeError("当前检索器不支持动态写入")
        add(Document.model_validate(request.model_dump()))
        return {"id": request.id, "status": "created"}

    @app.get("/api/v1/metrics")
    async def metrics() -> dict[str, int]:
        return dict(app.state.metrics)

    @app.post("/api/v1/cancel")
    async def cancel(request: CancelRequest) -> dict[str, str | bool]:
        task = app.state.running_tasks.get(request.thread_id)
        cancelled = task is not None and not task.done()
        if cancelled:
            task.cancel()
        return {"thread_id": request.thread_id, "cancelled": cancelled}

    @app.get("/api/v1/sessions/{thread_id}")
    async def get_session(thread_id: str) -> dict[str, object]:
        session = await service.get_session(thread_id)
        if session is None:
            raise HTTPException(status_code=404, detail="会话不存在")
        return session

    return app


app = create_app()
