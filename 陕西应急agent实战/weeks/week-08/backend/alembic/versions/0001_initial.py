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
    op.create_table("incidents",
        sa.Column("id", sa.String(length=40), primary_key=True),
        sa.Column("incident_type", sa.String(length=40), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("road_code", sa.String(length=20), nullable=False),
        sa.Column("section_id", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("reported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table("plan_documents",
        sa.Column("id", sa.String(length=40), primary_key=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("section", sa.String(length=120), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=500), nullable=False),
        sa.Column("embedding", Vector(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("plan_documents")
    op.drop_table("incidents")
