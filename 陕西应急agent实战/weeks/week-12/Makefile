PYTHON ?= python3
VENV ?= .venv
COMPOSE ?= docker compose
KUBECTL ?= kubectl

.PHONY: setup infra-up infra-down migrate run run-backend run-frontend test eval verify k8s-render reset

setup:
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/python -m pip install -r backend/requirements.lock.txt
	cd frontend && npm install

infra-up:
	$(COMPOSE) -f compose.demo.yaml up -d --build

infra-down:
	$(COMPOSE) -f compose.demo.yaml down

run: infra-up

run-backend:
	$(VENV)/bin/uvicorn highway_agent.main:app --app-dir backend/src --reload

run-frontend:
	cd frontend && npm run dev

migrate:
	cd backend && ../$(VENV)/bin/alembic upgrade head

test:
	$(VENV)/bin/python -m pytest backend/tests -q
	cd frontend && npm run test:run

eval:
	PYTHONPATH=backend/src $(VENV)/bin/python evals/run.py evals/week12_cases.jsonl

k8s-render:
	$(KUBECTL) kustomize deploy/k8s/overlays/dev >/dev/null
	$(KUBECTL) kustomize deploy/k8s/overlays/prod >/dev/null

verify: test k8s-render
	$(COMPOSE) -f compose.demo.yaml config --quiet
	cd frontend && npm run build

reset:
	$(COMPOSE) -f compose.demo.yaml down -v
