"""部署清单的静态验收测试，不要求本机已经运行 Kubernetes。"""

from pathlib import Path

import yaml


WEEK_ROOT = Path(__file__).resolve().parents[2]


def test_docker_images_never_use_latest_tag() -> None:
    deployment_files = [
        WEEK_ROOT / "backend" / "Dockerfile",
        WEEK_ROOT / "frontend" / "Dockerfile",
        *sorted((WEEK_ROOT / "deploy" / "k8s").rglob("*.yaml")),
    ]

    assert all(path.exists() for path in deployment_files)
    for path in deployment_files:
        assert ":latest" not in path.read_text(encoding="utf-8")


def test_demo_compose_contains_complete_local_environment() -> None:
    compose = yaml.safe_load(
        (WEEK_ROOT / "compose.demo.yaml").read_text(encoding="utf-8")
    )

    assert set(compose["services"]) == {"postgres", "redis", "api", "web"}
    assert compose["services"]["api"]["depends_on"]["postgres"]["condition"] == "service_healthy"
    assert compose["services"]["web"]["ports"] == ["8080:80"]


def test_kustomize_has_base_dev_and_prod_without_prod_databases() -> None:
    base = yaml.safe_load(
        (WEEK_ROOT / "deploy/k8s/base/kustomization.yaml").read_text(encoding="utf-8")
    )
    dev = yaml.safe_load(
        (WEEK_ROOT / "deploy/k8s/overlays/dev/kustomization.yaml").read_text(
            encoding="utf-8"
        )
    )
    prod = yaml.safe_load(
        (WEEK_ROOT / "deploy/k8s/overlays/prod/kustomization.yaml").read_text(
            encoding="utf-8"
        )
    )

    assert "api-deployment.yaml" in base["resources"]
    assert "postgres.yaml" in dev["resources"]
    assert "redis.yaml" in dev["resources"]
    # API 通过 postgres/redis 短服务名访问，本地依赖必须位于同一命名空间。
    assert dev["namespace"] == "highway-agent"
    assert prod["namespace"] == "highway-agent"
    assert all("postgres" not in item and "redis" not in item for item in prod["resources"])


def test_production_compose_requires_external_database_and_redis() -> None:
    compose = yaml.safe_load(
        (WEEK_ROOT / "compose.prod.yaml").read_text(encoding="utf-8")
    )

    assert set(compose["services"]) == {"api", "web"}
    api_environment = compose["services"]["api"]["environment"]
    assert "DATABASE_URL" in api_environment
    assert "REDIS_URL" in api_environment
    assert "alembic upgrade head" in " ".join(compose["services"]["api"]["command"])


def test_production_kustomize_enables_live_model_mode() -> None:
    config_patch = yaml.safe_load(
        (WEEK_ROOT / "deploy/k8s/overlays/prod/config-patch.yaml").read_text(
            encoding="utf-8"
        )
    )

    assert config_patch["kind"] == "ConfigMap"
    assert config_patch["data"]["MODEL_MODE"] == "live"


def test_production_uses_single_migration_job_instead_of_pod_init() -> None:
    prod_source = (
        WEEK_ROOT / "deploy/k8s/overlays/prod/kustomization.yaml"
    ).read_text(encoding="utf-8")
    job = yaml.safe_load(
        (WEEK_ROOT / "deploy/k8s/overlays/prod/migration-job.yaml").read_text(
            encoding="utf-8"
        )
    )

    assert job["kind"] == "Job"
    assert "migration-job.yaml" in prod_source
    assert "/spec/template/spec/initContainers" in prod_source
    assert job["spec"]["template"]["spec"]["restartPolicy"] == "Never"


def test_alembic_uses_runtime_database_url() -> None:
    env_source = (WEEK_ROOT / "backend/alembic/env.py").read_text(encoding="utf-8")

    assert "Settings().database_url" in env_source
    assert "config.set_main_option(" in env_source
    assert '"sqlalchemy.url"' in env_source
