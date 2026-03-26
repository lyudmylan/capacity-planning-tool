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

## VNext Direction

The next version should make capacity planning more automated and more realistic for multi-function R&D organizations.

The planning model should evolve from a single pooled capacity calculation toward:

- an explicit `rd_org` input model
- country-based capacity derivation
- function-level feature estimation
- support for both high-level capacity checks and schedule-aware planning

VNext should be treated as a schema-breaking `v2`.

The v2 product should support two related but distinct use cases:

- `Capacity Check`
- `Planning Schedule`

These use cases should share the same R&D org model and function-level estimation model, but they should not force the same planning logic.

The input contract should include an explicit top-level `planning_mode` field.

Supported values:

- `capacity_check`
- `planning_schedule`

### Capacity Check

`Capacity Check` is the high-level planning mode.

Its primary use case is roadmap review over a large planning horizon such as a year, half year, or quarter.

It should answer:

- can the current R&D organization likely deliver the roadmap within the selected horizon
- which functions are bottlenecks
- where capacity is insufficient by function

This mode should:

- use function-level demand and function-level capacity
- stay aggregate at the planning-horizon level
- avoid schedule dependency rules
- avoid sequencing logic

### Planning Schedule

`Planning Schedule` is the more operational planning mode.

Its purpose is to support more precise delivery planning when downstream functions such as QA and DevOps can overlap with engineering work but cannot fully finish before engineering is complete enough to unblock them.

It should answer:

- can the plan finish within the selected horizon once cross-function delivery dependencies are considered
- which downstream dependency rules create schedule pressure

This mode should:

- use the same function-level estimation model as `Capacity Check`
- remain deterministic
- add dependency-aware schedule rules for downstream functions
- stop short of a full sprint-by-sprint scheduling engine

## VNext Functional Design

The next input model should introduce an `rd_org` root for organizational planning data.

The v2 input contract should include:

- `planning_mode`
- `planning_horizon`
- period selector fields for the selected horizon
- `focus_factor`
- `rd_org`
- `roadmap`

Mode-specific field rules:

- `org_schedule_policies` is optional for `planning_schedule`
- `org_schedule_policies` should not affect `capacity_check`

### R&D Org

`rd_org` should represent the delivery organization for the selected planning horizon.

It should contain:

- `teams`
- `country_profiles`
- `org_schedule_policies`

### Teams and Members

The product should support multiple teams inside one R&D organization.

Each team member should define:

- `id`
- `function`
- `seniority`
- `capacity_percent`
- `country_profile`

Supported functions for the next version should be:

- `eng`
- `qa`
- `devops`

`capacity_percent` should default to `1.0`.

Each member should belong to exactly one function in v2.

### Country Profiles

Country profiles should automate the inputs that are manual today.

Each country profile should define:

- `id`
- `country_code`
- working-day rules
- holiday calendar rules
- `vacation_days_per_employee`
- `sick_days_per_employee`

For simplicity, vacation and sick policy should be the same within one country profile.

The planning input should also define period selector fields.

In v2:

- holidays and working days should be derived using the selected period and the selected country profile
- `vacation_days_per_employee` and `sick_days_per_employee` should be annual allowances
- annual vacation and sick allowances should be prorated to the selected planning horizon

The first v2 version should support these period selectors:

- `year`: requires `calendar_year`
- `half_year`: requires `calendar_year` and `half_year_index`
- `quarter`: requires `calendar_year` and `quarter_index`
- `month`: requires `calendar_year` and `month_index`
- `sprint`: requires `start_date` and `end_date`

For `year`, `half_year`, `quarter`, and `month`, calendar derivation should be calendar-based.

For `sprint`, calendar derivation should use the explicit date window.

### Org Schedule Policies

Schedule dependency rules should live at the R&D org level rather than on individual features.

`org_schedule_policies` should apply to `Planning Schedule` mode, not to `Capacity Check` mode.

The first scheduling policy should support:

- `post_dev_min_ratio.qa`
- `post_dev_min_ratio.devops`

These values represent the share of downstream function demand that cannot be completed until engineering work for the same scope is complete enough to unblock that downstream work.

For the first deterministic implementation:

- `blocked_demand_f = demand_by_function[f] * post_dev_min_ratio[f]`
- `blocked_utilization_f = blocked_demand_f / capacity_by_function[f]`
- `eng_utilization = demand_by_function["eng"] / capacity_by_function["eng"]`

For each downstream function `f` in `qa` and `devops`:

- the raw function-capacity check must pass
- the schedule dependency check passes only when `eng_utilization + blocked_utilization_f <= 1`

This means:

- some downstream work may overlap with engineering
- the blocked portion of downstream work must still fit into the remaining portion of the planning horizon after engineering work consumes its share of the horizon

This rule should apply only to `planning_schedule`.

### Function-Level Estimation

Feature estimation should move from one pooled size to function-level estimates.

Each feature should be able to define effort for:

- `eng`
- `qa`
- `devops`

That allows the planner to model cases such as:

- engineering work estimated as `L`
- QA work estimated as `M`
- DevOps work estimated as `S`

If a function estimate is omitted for a feature, that function should be treated as having zero demand for that feature.

The first v2 version should use the existing shared size scale.

In v2, equal size labels should represent equal effort units across `eng`, `qa`, and `devops`.

For example:

- `M` for QA and `M` for engineering should map to the same number of effort units in the first v2 version

Per-function size multipliers can be introduced later only as an explicit schema and rules change.

### Capacity and Feasibility Rules

The planner should derive member availability from:

- the selected planning period
- country profile
- vacation policy
- sick policy
- capacity percent
- focus factor

`focus_factor` should remain a top-level global input in the first v2 version.

It should apply uniformly across all members and functions, preserving the current product behavior while the new org model is introduced.

Capacity should then be evaluated by function across the full R&D organization rather than as one pooled engineering bucket.

For both `Capacity Check` and `Planning Schedule`, the planner should:

- calculate capacity separately for `eng`, `qa`, and `devops`
- calculate feature demand separately for `eng`, `qa`, and `devops`
- report bottlenecks by function

`Capacity Check` should evaluate feasibility against function capacity only.

At a minimum:

- `feasible = true` only when every function's demand fits within that function's capacity

`Planning Schedule` should evaluate:

- function-level capacity fit
- downstream dependency rules from `org_schedule_policies`

At a minimum:

- `function_capacity_fit = true` only when every function's demand fits within that function's capacity
- `dependency_rules_pass = true` only when every downstream dependency rule passes
- `feasible = true` only when both `function_capacity_fit` and `dependency_rules_pass` are true

The dependency model should remain deterministic.

The first version of this capability should use dependency-aware feasibility rules, not a full sprint-by-sprint scheduling engine.

### Validation Direction

The v2 model should validate at least the following:

- member ids are unique within the R&D org
- every member references an existing `country_profile`
- country profile ids are unique
- vacation and sick values are non-negative
- derived unavailable days do not exceed derived working days for the selected horizon

### Output Direction

The output model should remain JSON-first and should become function-aware in v2.

All v2 outputs should include:

- `capacity_by_function`
- `demand_by_function`
- `utilization_by_function`
- `buffer_by_function`
- `bottleneck_functions`

`capacity_check` outputs should also include:

- `planning_mode`
- `function_capacity_fit`
- `feasibility`

`planning_schedule` outputs should also include:

- `planning_mode`
- `function_capacity_fit`
- `dependency_rules_pass`
- `dependency_violations`
- `feasibility`

The first v2 version does not need to preserve the old aggregate-only output shape.

### Business Goals and Replanning

The current product includes business-goal support and deterministic replanning.

The first v2 release should focus on the new input model and feasibility engine.

For that reason:

- business goals should be out of scope for the first v2 release
- automated replanning should be out of scope for the first v2 release
- both may return later once `capacity_check` and `planning_schedule` are stable in v2

## VNext Epics

- `R&D Org Model`
- `Country-Based Capacity Automation`
- `Function-Level Estimation`
- `Capacity Check`
- `Planning Schedule`
- `Function-Aware Outputs`

## Next Steps

- implement the `rd_org` planning model for multi-team R&D organizations
- automate country-based working-day, holiday, vacation, and sick inputs
- add function-level estimation for `eng`, `qa`, and `devops`
- implement `Capacity Check` as the first v2 planning mode
- add org-level `org_schedule_policies` for `Planning Schedule`
- expose capacity, demand, and feasibility by function in planner outputs
- keep the v2 JSON contracts stable and explicit once the schema break is introduced

## Documentation Map

- [`assumptions.md`](assumptions.md)
  Formulas, defaults, and behavioral assumptions.
- [`ui_json_spec.md`](ui_json_spec.md)
  Human-readable explanation of the JSON UI contract.
- [`../AGENTS.md`](../AGENTS.md)
  Repo-specific instructions for working in this codebase.
