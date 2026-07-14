PYTHON ?= python3
VENV ?= .venv
COMPOSE ?= docker compose

.PHONY: setup infra-up infra-down migrate run run-backend run-frontend test eval verify reset

setup:
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/python -m pip install -r backend/requirements.lock.txt
	cd frontend && npm install

infra-up:
	$(COMPOSE) -f compose.dev.yaml up -d

infra-down:
	$(COMPOSE) -f compose.dev.yaml down

migrate:
	cd backend && ../$(VENV)/bin/alembic upgrade head

run: run-backend

run-backend:
	$(VENV)/bin/uvicorn highway_agent.main:app --app-dir backend/src --reload

run-frontend:
	cd frontend && npm run dev

test:
	$(VENV)/bin/python -m pytest backend/tests -q
	cd frontend && npm run test:run

eval:
	PYTHONPATH=backend/src $(VENV)/bin/python evals/run.py evals/week11_cases.jsonl

verify: test
	$(COMPOSE) -f compose.dev.yaml config --quiet
	cd frontend && npm run build

reset:
	$(COMPOSE) -f compose.dev.yaml down -v
