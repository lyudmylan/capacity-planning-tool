PYTHONPATH_SRC = PYTHONPATH=src
PYTHON = .venv/bin/python
RUFF = .venv/bin/ruff
MYPY = .venv/bin/mypy

.PHONY: test ui-test lint typecheck check run-feasible run-infeasible serve

test:
	$(PYTHONPATH_SRC) $(PYTHON) -m unittest discover -s tests

ui-test:
	node --test tests/ui_logic.test.mjs

lint:
	$(RUFF) check .

typecheck:
	$(MYPY) src

check: test ui-test lint typecheck

run-feasible:
	$(PYTHONPATH_SRC) $(PYTHON) -m capacity_planning_tool --input examples/feasible_plan.json

run-infeasible:
	$(PYTHONPATH_SRC) $(PYTHON) -m capacity_planning_tool --input examples/infeasible_plan.json

serve:
	$(PYTHONPATH_SRC) $(PYTHON) -m capacity_planning_tool.server
