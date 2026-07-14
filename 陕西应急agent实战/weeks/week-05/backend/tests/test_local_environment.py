from pathlib import Path

import yaml


WEEK_ROOT = Path(__file__).resolve().parents[2]


def test_compose_defines_pinned_postgres_and_redis_services() -> None:
    compose = yaml.safe_load((WEEK_ROOT / "compose.dev.yaml").read_text(encoding="utf-8"))

    assert compose["services"]["postgres"]["image"] == "pgvector/pgvector:0.8.1-pg17"
    assert compose["services"]["redis"]["image"] == "redis:7.4.2-alpine"
    assert "healthcheck" in compose["services"]["postgres"]
    assert "healthcheck" in compose["services"]["redis"]


def test_initial_migration_enables_vector_extension() -> None:
    migration = WEEK_ROOT / "backend" / "alembic" / "versions" / "0001_initial.py"

    content = migration.read_text(encoding="utf-8")
    assert 'CREATE EXTENSION IF NOT EXISTS vector' in content
    assert 'op.create_table("incidents"' in content

