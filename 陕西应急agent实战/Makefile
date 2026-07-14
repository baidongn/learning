PYTHON ?= .venv/bin/python

.PHONY: verify-structure test-all eval-final verify-deploy verify

verify-structure:
	bash scripts/verify_structure.sh

test-all:
	bash scripts/test_all_weeks.sh

eval-final:
	PYTHONPATH=weeks/week-12/backend/src $(PYTHON) weeks/week-12/evals/run.py weeks/week-12/evals/week12_cases.jsonl

verify-deploy:
	kubectl kustomize weeks/week-12/deploy/k8s/overlays/dev >/dev/null
	kubectl kustomize weeks/week-12/deploy/k8s/overlays/prod >/dev/null

verify: verify-structure test-all eval-final verify-deploy
