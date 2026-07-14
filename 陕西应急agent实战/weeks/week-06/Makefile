PYTHON ?= python3
VENV ?= .venv
COMPOSE ?= docker compose

.PHONY: setup infra-up infra-down migrate run test eval verify reset

setup:
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/python -m pip install -r backend/requirements.lock.txt

infra-up:
	$(COMPOSE) -f compose.dev.yaml up -d

infra-down:
	$(COMPOSE) -f compose.dev.yaml down

migrate:
	cd backend && ../$(VENV)/bin/alembic upgrade head

run:
	$(VENV)/bin/uvicorn highway_agent.main:app --app-dir backend/src --reload

test:
	$(VENV)/bin/python -m pytest backend/tests -q

eval:
	$(VENV)/bin/python -m pytest backend/tests -q -k "resource_agent"

verify: test
	$(COMPOSE) -f compose.dev.yaml config --quiet

reset:
	$(COMPOSE) -f compose.dev.yaml down -v
