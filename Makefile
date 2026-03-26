PYTHONPATH_SRC = PYTHONPATH=src
PYTHON = .venv/bin/python
RUFF = .venv/bin/ruff
MYPY = .venv/bin/mypy

.PHONY: bootstrap test ui-test lint typecheck check ci run-feasible run-infeasible serve

bootstrap:
	python3 -m venv .venv
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install .[dev]

test:
	$(PYTHONPATH_SRC) $(PYTHON) -m unittest discover -s tests

ui-test:
	node --test tests/ui_logic.test.mjs

lint:
	$(RUFF) check .

typecheck:
	$(MYPY) src

check: test ui-test lint typecheck

ci: check

run-feasible:
	$(PYTHONPATH_SRC) $(PYTHON) -m capacity_planning_tool --input examples/feasible_plan.json

run-infeasible:
	$(PYTHONPATH_SRC) $(PYTHON) -m capacity_planning_tool --input examples/infeasible_plan.json

serve:
	$(PYTHONPATH_SRC) $(PYTHON) -m capacity_planning_tool.server
