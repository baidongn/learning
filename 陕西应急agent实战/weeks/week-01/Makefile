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

