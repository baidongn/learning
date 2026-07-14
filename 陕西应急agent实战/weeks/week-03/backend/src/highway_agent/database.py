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
