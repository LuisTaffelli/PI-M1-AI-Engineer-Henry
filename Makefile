PYTHON ?= .venv/bin/python

.PHONY: run test eval
run:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m src.main 'Me cobraron dos veces este mes.'
test:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m unittest discover -s tests -v
eval:
	PYTHONDONTWRITEBYTECODE=1 $(PYTHON) -m evals.run_evals
