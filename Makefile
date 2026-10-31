PYTHON ?= .venv/bin/python
RUFF ?= .venv/bin/ruff

.PHONY: run test eval lint format format-check check
run:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m src.main 'Me cobraron dos veces este mes.'
test:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest discover -s tests -v
eval:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m evals.run_evals

lint:
	$(RUFF) check src evals tests
format:
	$(RUFF) format src evals tests
format-check:
	$(RUFF) format --check src evals tests
check: lint format-check test
