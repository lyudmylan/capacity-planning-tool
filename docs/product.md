# Product

## Goal

Given team capacity, planning horizon, roadmap demand, and optional business goals, determine whether the plan is feasible and suggest a better alternative if not.

## Original Direction

The project started with these core constraints:

- JSON for all machine-readable inputs and outputs
- runtime defaults and numeric constants in JSON config rather than hardcoded
- formulas, assumptions, and explanations in Markdown docs
- tests, linting, type checking, CI, and review as part of normal delivery
- no LLM usage for calculations

## Current Shape

The shipped product now includes:

- JSON-in / JSON-out capacity planning CLI
- deterministic capacity and demand calculations
- bounded replanning loop with explicit business-goal support
- thin Flask-backed web UI on top of the existing planner
- JSON-first UI handoff contract in `specs/ui_handoff_v1.json`

## Still Deterministic

The current planner remains deterministic.

- no LLM is used for capacity or demand calculations
- no LLM is used for candidate rescoring
- `risks`, `suggestions`, and `tradeoff_summary` remain deterministic outputs today

## Current Constraints

- no database
- no external integrations
- no week-by-week or sprint allocation engine
- no LLM-backed advisor yet

## Roadmap Inputs

The planner currently accepts:

- `team_structure`
- `planning_horizon`
- `working_days`
- `holidays_days`
- `vacation_days`
- `sick_days`
- `focus_factor`
- `sprint_days`
- `overhead_days_per_sprint`
- `roadmap`
- optional `business_goals`

See [`assumptions.md`](assumptions.md) for behavior and formulas.

## Output Shape

The planner returns JSON with fields including:

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

The current implementation also returns richer planning fields such as `selected_plan`, `business_goal_assessment`, `evaluated_alternatives`, and `agentic_iterations`.

## UI Direction

The UI is intentionally thin.

- calculations stay in the Python planner
- the frontend should not duplicate planner logic
- `specs/ui_handoff_v1.json` is the machine-readable UI source of truth
- [`ui_json_spec.md`](ui_json_spec.md) explains that contract for humans

## Known Gaps

- the replanning loop is agentic in structure, but not yet LLM-backed
- the UI is intentionally operational rather than expansive

## Next Steps

- add an optional LLM-backed advisor without moving calculations into the model
- deepen the UI only where it improves decision support
- keep the JSON contracts stable and explicit for both agents and humans

## Documentation Map

- [`assumptions.md`](assumptions.md)
  Formulas, defaults, and behavioral assumptions.
- [`ui_json_spec.md`](ui_json_spec.md)
  Human-readable explanation of the JSON UI contract.
- [`../AGENTS.md`](../AGENTS.md)
  Repo-specific instructions for working in this codebase.
