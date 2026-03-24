# Product Spec

This document captures the original requested product specification that kicked off the project.

## Original Request

### Goal

Given team capacity, planning horizon, and roadmap demand, determine whether the plan is feasible and suggest a better alternative if not.

### Engineering Requirements

- Use agent-friendly development practices
- Create an `AGENTS.md` file with project instructions, architecture, coding conventions, and workflow
- Use JSON for all machine-readable inputs and outputs
- Keep runtime defaults and numeric constants in JSON config files, not hardcoded
- Keep assumptions, formulas, and explanations in Markdown docs
- Add tests for all new features and bug fixes
- Run tests until green before considering work complete
- Include linting / type checking / CI setup
- Perform a review pass before finalizing code

### Input

- `team_structure`
  - teams, roles, seniority
  - number of engineers or explicit members
  - `capacity_percent` per member or role group with default `1.0`
- `planning_horizon`
  - supported values: `year`, `half_year`, `quarter`, `month`, `sprint`
- `working_days`
  - number of working days in the selected planning horizon
- `holidays_days`
- `vacation_days`
- `sick_days`
- `focus_factor` with default `0.8`
- `sprint_days` with default `10`
- `overhead_days_per_sprint` with default `2`
- `roadmap`
  - features
  - size: `XS`, `S`, `M`, `L`
  - priority: `Critical`, `High`, `Medium`, `Low`

### Demand Formula

- `effective_dev_days_per_sprint = sprint_days - overhead_days_per_sprint`
- `XS = effective_dev_days_per_sprint / 2`
- `S = effective_dev_days_per_sprint`
- `M = effective_dev_days_per_sprint * 2`
- `L = effective_dev_days_per_sprint * 3`

### Capacity Formula

- `net_days_per_engineer = working_days - holidays_days - vacation_days - sick_days`
- `effective_capacity_per_engineer = net_days_per_engineer * capacity_percent * focus_factor`
- `total_capacity = sum of effective capacity across engineers`

### Output JSON

- `capacity_dev_days`
- `demand_dev_days`
- `utilization`
- `feasibility`
- `buffer_dev_days`
- `delivered_features`
- `deferred_features`
- `dropped_features`
- `risks`
- `suggestions`
- `tradeoff_summary`

### Evaluator

- `demand_dev_days <= capacity_dev_days`
- utilization target: `0.8` to `0.9`
- buffer target: at least `10%` of capacity

### Improvement Logic

- if plan is not feasible, recalculate once
- improve by delaying or dropping features
- choose features in this order:
  1. lowest priority first
  2. if same priority, largest feature first

### LLM Usage

- explain risks
- suggest which features to defer or drop
- summarize tradeoffs
- do not use LLM for calculations

### Project Requirements

- all inputs and outputs must be JSON
- include example input JSON files
- include defaults in `config/defaults.json`
- include formulas and assumptions in `docs/assumptions.md`
- provide a CLI entry point
- keep V1 simple: no UI, no DB, no integrations, no scheduling by week or sprint allocation

## New Direction For The Next Phase

The next phase may add a UI, but it should follow a JSON-first contract so it remains useful for both coding agents and human users.

### UI Direction

- define the UI in a machine-readable JSON spec first
- keep that spec versioned in the repo
- let coding agents implement against the JSON contract instead of prose-only requests
- ensure a future web interface maps directly to planner JSON inputs and outputs
- keep calculations out of the frontend

The human-readable explanation for this direction lives in [`ui_json_spec.md`](ui_json_spec.md), and the machine-readable handoff contract lives in [`../specs/ui_handoff_v1.json`](../specs/ui_handoff_v1.json).

## Current Implementation Status

The current implementation satisfies most of the deterministic planning and repository-engineering parts of this spec:

- JSON input and output
- config-driven defaults
- Markdown formulas and assumptions
- CLI entry point
- tests, linting, type checking, CI, and review flow
- bounded agentic replanning loop with deterministic candidate scoring
- explicit business-goal input support

## What Is Now Implemented

The current version now includes:

- a bounded propose -> evaluate -> revise replanning loop
- must-deliver feature protection
- business-goal-aware candidate evaluation
- deterministic rescoring of every proposed alternative
- JSON output that includes selected-plan details and evaluated alternatives

## Remaining Gap Against the Original Request

The remaining gap is narrower now:

- the replanning loop is agentic in structure
- but it is still rule-based rather than LLM-backed
- `risks`, `suggestions`, and `tradeoff_summary` are still deterministic planner outputs

## Next Step

The remaining optional extension is documented in [`agentic_replanning_plan.md`](agentic_replanning_plan.md). If we add an LLM later, it should sit on top of the deterministic evaluator rather than replacing the calculation layer.

The next interface-oriented extension is documented in [`ui_json_spec.md`](ui_json_spec.md), with the machine-readable contract in [`../specs/ui_handoff_v1.json`](../specs/ui_handoff_v1.json).
