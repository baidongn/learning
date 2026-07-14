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
