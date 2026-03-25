Implement or update the UI for this repo using the existing planner as the source of truth.

Read these first:
- `AGENTS.md`
- `docs/product.md`
- `docs/ui_json_spec.md`
- `specs/ui_handoff_v1.json`
- `docs/assumptions.md`
- `examples/feasible_plan.json`
- `examples/infeasible_plan.json`
- `examples/goal_driven_plan.json`

Rules:
- do not move calculations into the frontend
- do not duplicate planner logic in the UI
- keep machine-readable contracts in JSON
- if UI behavior or scope changes, update `specs/ui_handoff_v1.json` first, then implementation, then docs and tests
- keep the UI thin, clean, and decision-oriented
- preserve raw JSON input and output visibility for agents and power users

Delivery expectations:
- implement the requested UI change end to end
- add or update tests
- update docs if behavior or setup changes
- run the relevant verification for the repo
- summarize what changed, assumptions made, and how to run or validate the UI locally
