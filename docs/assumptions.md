# Assumptions and Formulas

## Current Version Status

The current implementation uses deterministic calculations plus a bounded agentic replanning loop.

- Capacity and demand calculations are deterministic.
- Candidate plan evaluation is deterministic.
- `business_goals` can guide replanning decisions.
- `risks`, `suggestions`, and `tradeoff_summary` are currently deterministic output fields.
- The replanning loop is agentic in structure, but it is still rule-based and does not call an external LLM.

## Scope

V1 evaluates a single planning horizon at a time. It does not split work by week, by sprint assignment, or by engineer specialization.

## Input Assumptions

- `planning_horizon` must be one of `year`, `half_year`, `quarter`, `month`, or `sprint`.
- `working_days` is provided directly for the selected planning horizon.
- Teams are modeled as role groups.
- Features may optionally define `id`. If `id` is omitted, the feature name is used as its business-goal reference.
- A role group must define either:
  - `count`, or
  - `members`
- `capacity_percent` can be set at the role-group level or on individual members.
- If a member omits `capacity_percent`, the role-group value is used.
- If both omit it, the default from `config/defaults.json` is used.
- If `business_goals.must_deliver_feature_ids` is present, every referenced feature must exist.

## Demand Formula

- `effective_dev_days_per_sprint = sprint_days - overhead_days_per_sprint`
- `XS = effective_dev_days_per_sprint / 2`
- `S = effective_dev_days_per_sprint`
- `M = effective_dev_days_per_sprint * 2`
- `L = effective_dev_days_per_sprint * 3`

The implementation stores the size multipliers in `config/defaults.json` and multiplies them by `effective_dev_days_per_sprint`.

## Capacity Formula

- `net_days_per_engineer = working_days - holidays_days - vacation_days - sick_days`
- `effective_capacity_per_engineer = net_days_per_engineer * capacity_percent * focus_factor`
- `total_capacity = sum(effective capacity across engineers)`

## Evaluation Rules

- The original plan is considered feasible when `demand_dev_days <= capacity_dev_days`.
- Healthy utilization is targeted between `0.8` and `0.9`.
- Healthy buffer is targeted at `10%` or more of total capacity.

## Replanning Logic

The current version runs a bounded replanning loop driven by explicit business goals.

At each iteration:

1. Evaluate the current plan deterministically
2. Protect `must_deliver_feature_ids` from removal
3. Propose a small set of candidate removals using `defer_preference`
4. Re-score each candidate deterministically
5. Keep the best candidate and stop once no better plan is found or the limit is reached

The default agentic loop bounds live in `config/defaults.json`.

The candidate-sorting order and plan-scoring priority order also live in `config/defaults.json` so replanning policy is not buried in code.

## Business Goal Evaluation

Hard constraints:

- plan must be feasible
- utilization must be less than or equal to `business_goals.max_utilization`
- buffer must be greater than or equal to `capacity_dev_days * business_goals.min_buffer_ratio`
- all `must_deliver_feature_ids` must remain in scope

Soft constraints:

- priorities listed in `preserve_priorities` should stay in scope when possible

## Deferred vs Dropped

- Removed `Low` priority items are classified as `dropped_features`.
- Removed `Medium`, `High`, and `Critical` items are classified as `deferred_features`.

This keeps the output deterministic while still distinguishing low-value scope cuts from work that should move to a later horizon.

## Remaining Gap

The current agentic loop is rule-based. A future version may add an optional LLM-backed advisor for richer candidate generation or narrative output, but all calculations should remain deterministic.

## Logging and Errors

- Runtime logging goes to standard error through Python's `logging` module.
- The default log level lives in `config/defaults.json` and is currently `WARNING` so normal CLI runs keep stdout clean for JSON consumers.
- `--log-level` can raise verbosity for troubleshooting, and `--quiet` suppresses everything except errors.
- CLI validation and output-write failures are returned as clean user-facing errors instead of raw tracebacks for common input and filesystem issues.
