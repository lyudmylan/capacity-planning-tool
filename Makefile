PYTHONPATH_SRC = PYTHONPATH=src
PYTHON = .venv/bin/python
RUFF = .venv/bin/ruff
MYPY = .venv/bin/mypy

.PHONY: test lint typecheck check run-feasible run-infeasible

test:
	$(PYTHONPATH_SRC) $(PYTHON) -m unittest discover -s tests

lint:
	$(RUFF) check .

typecheck:
	$(MYPY) src

check: test lint typecheck

run-feasible:
	$(PYTHONPATH_SRC) $(PYTHON) -m capacity_planning_tool --input examples/feasible_plan.json

run-infeasible:
	$(PYTHONPATH_SRC) $(PYTHON) -m capacity_planning_tool --input examples/infeasible_plan.json
